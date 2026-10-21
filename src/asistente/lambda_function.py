"""
Asistente inteligente de atención al cliente — función Lambda principal.

Rutas (mismo código para API Gateway HTTP API y para la URL de función):
  POST /preguntar   {"pregunta": "..."}  -> respuesta basada en la documentación
  GET  /salud                            -> estado y número de entradas cargadas
  OPTIONS *                              -> preflight CORS

Estados posibles de la respuesta:
  respondida     score >= UMBRAL_RESPUESTA           -> se devuelve la respuesta y su fuente
  sugerencia     UMBRAL_SUGERENCIA <= score < UMBRAL -> "no tengo certeza", se sugiere la pregunta más parecida
  sin_respuesta  score <  UMBRAL_SUGERENCIA          -> la documentación no contiene la respuesta

Variables de entorno: ver infra/config.env y docs/guia_consola_aws.md.
Sin credenciales en el código: los permisos vienen del rol de ejecución (LabRole).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time

from base_conocimiento import obtener_indice
from limites import permitir
from registro import emitir_metricas, hash_cliente, registrar_consulta

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

MAX_CARACTERES = int(os.environ.get("MAX_CARACTERES", "500"))

MSG_SIN_RESPUESTA = (
    "Lo siento, la documentación autorizada no contiene información sobre esa consulta. "
    "La registré para que el equipo la revise. Puedes escribirnos por WhatsApp al "
    "+591 70000000 o a atencion@tecnohogar.example."
)
MSG_SUGERENCIA = (
    "No encontré una respuesta exacta en la documentación autorizada. "
    "¿Tu consulta es sobre: \"{pregunta}\"? Si es así, reformúlala con más detalle."
)


# ----------------------------------------------------------------------------- HTTP
def _cabeceras() -> dict:
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGIN", "*"),
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "3600",
        "X-Content-Type-Options": "nosniff",
    }


def _respuesta(status: int, cuerpo: dict | None = None) -> dict:
    return {
        "statusCode": status,
        "headers": _cabeceras(),
        "body": json.dumps(cuerpo, ensure_ascii=False) if cuerpo is not None else "",
    }


def _datos_evento(event: dict) -> tuple[str, str, str | None, str]:
    """Normaliza eventos v1 (REST), v2 (HTTP API) y URL de función.
    Devuelve (metodo, ruta, ip, origen)."""
    ctx = event.get("requestContext", {}) or {}
    if "http" in ctx:  # payload 2.0 (HTTP API y URL de función)
        metodo = ctx["http"].get("method", "GET")
        ruta = ctx["http"].get("path", event.get("rawPath", "/"))
        ip = ctx["http"].get("sourceIp")
        dominio = ctx.get("domainName", "")
        origen = "function-url" if ".lambda-url." in dominio else "api-gateway"
    else:  # payload 1.0 (REST API) o invocación de prueba en la consola
        metodo = event.get("httpMethod", "POST")
        ruta = event.get("path", "/preguntar")
        ip = (ctx.get("identity") or {}).get("sourceIp")
        origen = "api-gateway-rest" if ctx else "consola"
    return metodo.upper(), ruta.rstrip("/") or "/", ip, origen


def _leer_cuerpo(event: dict) -> dict:
    cuerpo = event.get("body")
    if cuerpo is None:
        # Invocación directa desde la consola de Lambda: {"pregunta": "..."}
        return {k: v for k, v in event.items() if k == "pregunta"}
    if event.get("isBase64Encoded"):
        cuerpo = base64.b64decode(cuerpo).decode("utf-8")
    datos = json.loads(cuerpo) if cuerpo else {}
    if not isinstance(datos, dict):
        raise ValueError("El cuerpo debe ser un objeto JSON")
    return datos


# ----------------------------------------------------------------------------- lógica
def clasificar(score: float) -> str:
    umbral = float(os.environ.get("UMBRAL_RESPUESTA", "0.38"))
    umbral_sug = float(os.environ.get("UMBRAL_SUGERENCIA", "0.22"))
    if score >= umbral:
        return "respondida"
    if score >= umbral_sug:
        return "sugerencia"
    return "sin_respuesta"


def responder(pregunta: str) -> dict:
    indice, fuente_kb = obtener_indice()
    resultado = indice.buscar(pregunta)
    estado = clasificar(resultado.score)
    salida = {
        "estado": estado,
        "score": resultado.score,
        "umbral": float(os.environ.get("UMBRAL_RESPUESTA", "0.38")),
        "fuente_base": fuente_kb,
    }
    if estado == "respondida":
        e = resultado.entrada
        salida.update(
            respuesta=e["respuesta"],
            entrada_id=e["id"],
            categoria=e.get("categoria"),
            pregunta_relacionada=e["pregunta"],
            fuente=e.get("fuente"),
        )
    elif estado == "sugerencia":
        salida.update(
            respuesta=MSG_SUGERENCIA.format(pregunta=resultado.entrada["pregunta"]),
            sugerencia=resultado.entrada["pregunta"],
            entrada_id=None,
        )
    else:
        salida.update(respuesta=MSG_SIN_RESPUESTA, entrada_id=None)
    if os.environ.get("DEBUG_SIMILITUD", "false").lower() == "true":
        salida["detalle"] = resultado.detalle
        salida["candidatos"] = resultado.candidatos
    salida["_candidatos"] = resultado.candidatos  # interno, para el registro
    return salida


# ----------------------------------------------------------------------------- handler
def lambda_handler(event, context):
    inicio = time.perf_counter()
    request_id = getattr(context, "aws_request_id", None)
    metodo, ruta, ip, origen = _datos_evento(event or {})

    if metodo == "OPTIONS":
        return _respuesta(204)

    if metodo == "GET" and ruta.endswith("/salud"):
        try:
            indice, fuente = obtener_indice()
            return _respuesta(200, {"estado": "ok", "entradas": len(indice.entradas), "fuente_base": fuente})
        except Exception:
            logger.exception("Fallo el chequeo de salud")
            return _respuesta(503, {"estado": "error", "mensaje": "Base de conocimiento no disponible"})

    if metodo != "POST" or not (ruta.endswith("/preguntar") or ruta == "/"):
        return _respuesta(404, {"error": "Ruta no encontrada. Usa POST /preguntar o GET /salud."})

    # 1. Validación de entrada -------------------------------------------------
    try:
        datos = _leer_cuerpo(event)
    except (ValueError, UnicodeDecodeError):
        return _respuesta(400, {"error": "El cuerpo debe ser JSON válido: {\"pregunta\": \"...\"}"})

    pregunta = str(datos.get("pregunta", "")).strip()
    if not pregunta:
        return _respuesta(400, {"error": "El campo 'pregunta' es obligatorio."})
    if len(pregunta) > MAX_CARACTERES:
        return _respuesta(413, {"error": f"La pregunta supera el máximo de {MAX_CARACTERES} caracteres."})

    # 2. Límite de uso por cliente ----------------------------------------------
    cliente = hash_cliente(ip)
    permitido, conteo, limite = permitir(cliente)
    if not permitido:
        latencia = (time.perf_counter() - inicio) * 1000
        emitir_metricas(estado="rechazada", score=0.0, latencia_ms=latencia, origen=origen)
        logger.warning("Límite excedido cliente=%s conteo=%s", cliente, conteo)
        resp = _respuesta(429, {"error": f"Demasiadas consultas. Límite: {limite} por minuto."})
        resp["headers"]["Retry-After"] = "60"
        return resp

    # 3. Búsqueda por similitud -------------------------------------------------
    try:
        salida = responder(pregunta)
    except Exception:
        logger.exception("Error interno al responder")
        return _respuesta(500, {"error": "Error interno. Intenta nuevamente en unos minutos."})

    latencia = (time.perf_counter() - inicio) * 1000
    candidatos = salida.pop("_candidatos", None)

    # 4. Registro y métricas ----------------------------------------------------
    consulta_id = registrar_consulta(
        pregunta=pregunta, estado=salida["estado"], score=salida["score"],
        entrada_id=salida.get("entrada_id"), latencia_ms=latencia, origen=origen,
        ip=ip, candidatos=candidatos, request_id=request_id,
    )
    emitir_metricas(estado=salida["estado"], score=salida["score"], latencia_ms=latencia, origen=origen)
    logger.info(json.dumps({
        "evento": "consulta", "consulta_id": consulta_id, "estado": salida["estado"],
        "score": salida["score"], "entrada_id": salida.get("entrada_id"), "origen": origen,
        "latencia_ms": round(latencia, 1),
    }, ensure_ascii=False))

    salida.update(consulta_id=consulta_id, latencia_ms=round(latencia, 1))
    return _respuesta(200, salida)
