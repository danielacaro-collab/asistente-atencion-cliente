#!/usr/bin/env python3
"""
Prueba de aceptación del Reto 02.

Criterio (tal como lo define el enunciado):
  1. Responder las preguntas sustentadas por el material de prueba
     -> estado "respondida" y entrada_id == esperado_id.
  2. Reconocer cuándo la documentación no contiene la respuesta
     -> estado distinto de "respondida" (sin_respuesta o sugerencia).
  + Casos de error: pregunta vacía, JSON inválido, pregunta demasiado larga.

Uso:
  python3 scripts/prueba_aceptacion.py --url https://xxxx.execute-api.us-east-1.amazonaws.com
  python3 scripts/prueba_aceptacion.py --url https://xxxx.lambda-url.us-east-1.on.aws   # ruta alternativa
  python3 scripts/prueba_aceptacion.py --local      # sin AWS, invoca el handler en local

Genera evidencias/prueba_aceptacion_<origen>_<fecha>.md y .json.
Solo usa la biblioteca estándar (funciona en CloudShell sin instalar nada).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CASOS = json.loads((RAIZ / "data" / "casos_prueba.json").read_text(encoding="utf-8"))


# ----------------------------------------------------------------- transporte
def cliente_http(url_base):
    url = url_base.rstrip("/") + "/preguntar"

    def enviar(cuerpo_crudo: str):
        req = urllib.request.Request(url, data=cuerpo_crudo.encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            texto = e.read().decode("utf-8")
            try:
                return e.code, json.loads(texto)
            except ValueError:
                return e.code, {"error": texto}
    return enviar


def cliente_local():
    sys.path.insert(0, str(RAIZ / "src" / "asistente"))
    os.environ.update(KB_SOURCE="local", KB_LOCAL_PATH=str(RAIZ / "data" / "base_conocimiento.json"))
    for v in ("LOG_TABLE", "RATE_TABLE"):
        os.environ.pop(v, None)  # sin DynamoDB: no registra ni limita
    import io
    import contextlib
    import lambda_function

    def enviar(cuerpo_crudo: str):
        ev = {"version": "2.0", "body": cuerpo_crudo, "isBase64Encoded": False,
              "requestContext": {"domainName": "local", "http": {"method": "POST", "path": "/preguntar", "sourceIp": "127.0.0.1"}}}
        with contextlib.redirect_stdout(io.StringIO()):  # silencia líneas EMF
            r = lambda_function.lambda_handler(ev, None)
        return r["statusCode"], json.loads(r["body"] or "{}")
    return enviar


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--url", help="URL base de API Gateway o de la URL de función")
    g.add_argument("--local", action="store_true")
    ap.add_argument("--pausa", type=float, default=0.3, help="segundos entre solicitudes (respeta el límite de uso)")
    a = ap.parse_args()

    enviar = cliente_local() if a.local else cliente_http(a.url)
    origen = "local" if a.local else ("function-url" if ".lambda-url." in a.url else "api-gateway")
    filas, aprobados, total = [], 0, 0

    print(f"\nPrueba de aceptación — destino: {'local' if a.local else a.url}\n")
    for c in CASOS["casos"]:
        t0 = time.perf_counter()
        status, b = enviar(json.dumps({"pregunta": c["pregunta"]}, ensure_ascii=False))
        ms = (time.perf_counter() - t0) * 1000
        if c["esperado_id"]:
            ok = status == 200 and b.get("estado") == "respondida" and b.get("entrada_id") == c["esperado_id"]
        else:
            ok = status == 200 and b.get("estado") in ("sin_respuesta", "sugerencia")
        total += 1
        aprobados += ok
        filas.append({**c, "status": status, "estado": b.get("estado"), "obtenido_id": b.get("entrada_id"),
                      "score": b.get("score"), "ms": round(ms), "ok": ok, "respuesta": b.get("respuesta", b.get("error"))})
        print(f"  {'✅' if ok else '❌'} {c['id']}  {str(b.get('estado')):13} score={b.get('score', 0):<6} "
              f"{str(b.get('entrada_id')):8} {c['pregunta']}")
        time.sleep(a.pausa)

    print("\nCasos de error / condiciones límite:")
    errores = []
    for c in CASOS["casos_error"]:
        if "cuerpo_crudo" in c:
            crudo = c["cuerpo_crudo"]
        elif c["cuerpo"]["pregunta"] == "LARGA":
            crudo = json.dumps({"pregunta": "¿horario? " * 60})
        else:
            crudo = json.dumps(c["cuerpo"])
        status, b = enviar(crudo)
        ok = status == c["status_esperado"]
        total += 1
        aprobados += ok
        errores.append({**c, "status": status, "ok": ok, "mensaje": b.get("error")})
        print(f"  {'✅' if ok else '❌'} {c['id']}  HTTP {status} (esperado {c['status_esperado']})  {c['descripcion']}: {b.get('error')}")
        time.sleep(a.pausa)

    con = [f for f in filas if f["esperado_id"]]
    sin = [f for f in filas if not f["esperado_id"]]
    resumen = {
        "fecha": datetime.now().isoformat(timespec="seconds"), "origen": origen, "destino": a.url or "local",
        "aprobados": aprobados, "total": total,
        "con_respuesta": f"{sum(f['ok'] for f in con)}/{len(con)}",
        "sin_respuesta_reconocida": f"{sum(f['ok'] for f in sin)}/{len(sin)}",
        "latencia_promedio_ms": round(sum(f["ms"] for f in filas) / len(filas)),
    }
    print(f"\nResultado: {aprobados}/{total} aprobados · con respuesta {resumen['con_respuesta']} · "
          f"sin respuesta reconocida {resumen['sin_respuesta_reconocida']} · latencia media {resumen['latencia_promedio_ms']} ms")

    # ---- evidencias
    out = RAIZ / "evidencias"
    out.mkdir(exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = out / f"prueba_aceptacion_{origen}_{sello}"
    base.with_suffix(".json").write_text(json.dumps({"resumen": resumen, "casos": filas, "errores": errores},
                                                    ensure_ascii=False, indent=2), encoding="utf-8")
    md = [f"# Prueba de aceptación — {origen}", "",
          f"- Fecha: {resumen['fecha']}", f"- Destino: `{resumen['destino']}`",
          f"- **Resultado: {aprobados}/{total} aprobados**",
          f"- Preguntas con respuesta en la documentación: {resumen['con_respuesta']}",
          f"- Preguntas fuera de la documentación reconocidas: {resumen['sin_respuesta_reconocida']}",
          f"- Latencia media (cliente): {resumen['latencia_promedio_ms']} ms", "",
          "| Caso | Pregunta | Esperado | Obtenido | Estado | Score | OK |", "|---|---|---|---|---|---|---|"]
    md += [f"| {f['id']} | {f['pregunta']} | {f['esperado_id'] or '— (no documentado)'} | {f['obtenido_id'] or '—'} "
           f"| {f['estado']} | {f['score']} | {'✅' if f['ok'] else '❌'} |" for f in filas]
    md += ["", "## Casos de error", "", "| Caso | Descripción | HTTP esperado | HTTP obtenido | Mensaje | OK |", "|---|---|---|---|---|---|"]
    md += [f"| {e['id']} | {e['descripcion']} | {e['status_esperado']} | {e['status']} | {e['mensaje']} | {'✅' if e['ok'] else '❌'} |"
           for e in errores]
    base.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Evidencia guardada en {base.relative_to(RAIZ)}.md / .json\n")
    sys.exit(0 if aprobados == total else 1)


if __name__ == "__main__":
    main()
