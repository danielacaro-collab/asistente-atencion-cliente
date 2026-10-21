"""
Registro de consultas (DynamoDB) y métricas personalizadas (CloudWatch).

- Cada consulta se guarda en LOG_TABLE con su estado:
    respondida | sugerencia | sin_respuesta | rechazada
  Las consultas sin respuesta quedan disponibles para que el equipo amplíe la
  documentación (ver scripts/consultas_sin_respuesta.py).
- La IP del cliente NO se guarda: solo un hash SHA-256 truncado (privacidad).
- Los ítems expiran automáticamente con TTL (atributo "expira", LOG_TTL_DIAS).
- Las métricas se emiten con CloudWatch Embedded Metric Format (EMF): un JSON
  escrito en el log que CloudWatch convierte en métricas. No requiere llamadas
  a la API PutMetricData (menos latencia y costo; funciona con LabRole).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

NAMESPACE = os.environ.get("METRIC_NAMESPACE", "AsistenteAtencionCliente")
_tabla = None


def _tabla_log():
    global _tabla
    if _tabla is None:
        import boto3

        _tabla = boto3.resource("dynamodb").Table(os.environ["LOG_TABLE"])
    return _tabla


def hash_cliente(ip: str | None) -> str:
    return hashlib.sha256((ip or "desconocido").encode()).hexdigest()[:16]


def registrar_consulta(*, pregunta: str, estado: str, score: float, entrada_id: str | None,
                       latencia_ms: float, origen: str, ip: str | None,
                       candidatos: list | None = None, request_id: str | None = None) -> str:
    """Guarda la consulta en DynamoDB. Nunca lanza excepción: si el registro
    falla, se deja constancia en CloudWatch Logs y la respuesta al usuario sigue."""
    consulta_id = str(uuid.uuid4())
    ahora = datetime.now(timezone.utc)
    dias_ttl = int(os.environ.get("LOG_TTL_DIAS", "30"))
    item = {
        "consulta_id": consulta_id,
        "fecha": ahora.isoformat(timespec="seconds"),
        "fecha_dia": ahora.strftime("%Y-%m-%d"),
        "pregunta": pregunta[:500],
        "estado": estado,
        "score": Decimal(str(round(score, 4))),
        "entrada_id": entrada_id or "-",
        "latencia_ms": Decimal(str(round(latencia_ms, 1))),
        "origen": origen,
        "cliente_hash": hash_cliente(ip),
        "request_id": request_id or "-",
        "expira": int(time.time()) + dias_ttl * 86400,
    }
    if candidatos:
        item["candidatos"] = json.dumps(candidatos, ensure_ascii=False)[:1000]
    if os.environ.get("LOG_TABLE"):
        try:
            _tabla_log().put_item(Item=item)
        except Exception:
            logger.exception("No se pudo registrar la consulta %s en DynamoDB", consulta_id)
    return consulta_id


def emitir_metricas(*, estado: str, score: float, latencia_ms: float, origen: str) -> None:
    """Imprime un registro EMF. CloudWatch crea las métricas automáticamente."""
    metricas = {
        "Consultas": 1,
        "Respondidas": 1 if estado == "respondida" else 0,
        "Sugerencias": 1 if estado == "sugerencia" else 0,
        "SinRespuesta": 1 if estado in ("sin_respuesta", "sugerencia") else 0,
        "Rechazadas": 1 if estado == "rechazada" else 0,
        "ScoreSimilitud": round(score, 4),
        "LatenciaMs": round(latencia_ms, 1),
    }
    unidades = {"LatenciaMs": "Milliseconds", "ScoreSimilitud": "None"}
    emf = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": NAMESPACE,
                "Dimensions": [["Servicio"]],
                "Metrics": [{"Name": k, "Unit": unidades.get(k, "Count")} for k in metricas],
            }],
        },
        "Servicio": "asistente",
        "Origen": origen,
        "Estado": estado,
        **metricas,
    }
    print(json.dumps(emf))
