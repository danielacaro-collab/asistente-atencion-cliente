#!/usr/bin/env python3
"""Genera docs/arquitectura.png y docs/arquitectura.pdf con matplotlib.
Uso: pip install matplotlib && python3 scripts/generar_diagrama.py"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

RAIZ = Path(__file__).resolve().parents[1]
C = {"s3": "#3F8624", "lambda": "#D86613", "apigw": "#8C4FFF", "ddb": "#3B48CC",
     "cw": "#C7254E", "user": "#232F3E", "iam": "#DD344C", "fondo": "#F7F7F5", "nube": "#EEF3FA"}

fig, ax = plt.subplots(figsize=(16, 9.6), dpi=150)
ax.set_xlim(0, 160); ax.set_ylim(0, 96); ax.axis("off")
fig.patch.set_facecolor("white")


def caja(x, y, w, h, color, titulo, sub="", borde=2.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.6",
                                fc="white", ec=color, lw=borde))
    ax.add_patch(FancyBboxPatch((x, y + h - 4.2), w, 4.2, boxstyle="round,pad=0.4,rounding_size=1.6",
                                fc=color, ec=color, lw=borde))
    ax.text(x + w / 2, y + h - 2.1, titulo, ha="center", va="center", color="white", fontsize=10.5, weight="bold")
    if sub:
        ax.text(x + w / 2, y + (h - 4.2) / 2, sub, ha="center", va="center", fontsize=8.3, color="#222", linespacing=1.35)


def flecha(p1, p2, texto="", color="#333", estilo="-", num=None, dx=0, dy=1.6, rad=0.0, pos=None):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=15, lw=1.7, color=color,
                                 linestyle=estilo, connectionstyle=f"arc3,rad={rad}"))
    if texto:
        mx, my = pos if pos else ((p1[0] + p2[0]) / 2 + dx, (p1[1] + p2[1]) / 2 + dy)
        etiqueta = f"({num}) {texto}" if num else texto
        ax.text(mx, my, etiqueta, ha="center", va="center", fontsize=7.8, color=color,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.92))


ax.text(80, 93, "Asistente inteligente de atención al cliente — Arquitectura serverless en AWS (Learner Lab)",
        ha="center", fontsize=14, weight="bold", color=C["user"])
ax.text(80, 89.6, "Reto 02 · Búsqueda por similitud TF-IDF + coseno + Jaccard en Python · sin Lex ni Bedrock",
        ha="center", fontsize=9.5, color="#555")

# Nube AWS
ax.add_patch(FancyBboxPatch((24, 4), 133, 82, boxstyle="round,pad=0.5,rounding_size=2.5",
                            fc=C["nube"], ec="#7A8CA8", lw=1.4, ls="--"))
ax.text(27, 83, "AWS Cloud · región us-east-1 · cuenta Learner Lab", fontsize=9, color="#41506B", weight="bold")

# Usuario
caja(2, 44, 18, 14, C["user"], "Usuario", "Cliente de la\nempresa\n(navegador)")

# S3 web
caja(30, 60, 26, 16, C["s3"], "Amazon S3 — Web", "Hosting estático\nindex.html · app.js\nconfig.js (URLs)")
# API GW
caja(30, 32, 26, 16, C["apigw"], "API Gateway (HTTP API)", "Ruta principal\nPOST /preguntar\nthrottling 5 rps / ráf. 10")
# Function URL
caja(30, 8, 26, 14, C["lambda"], "Lambda Function URL", "Ruta ALTERNATIVA\n(si API Gateway falla)\nauth NONE · CORS en Lambda")

# Lambda
caja(70, 30, 34, 30, C["lambda"], "AWS Lambda (Python 3.12)",
     "lambda_function.py\n1. Validación de entrada\n2. Límite de uso por cliente\n3. similitud.py: TF-IDF·coseno\n   + Jaccard trigramas\n4. Umbral 0.38 → respuesta\n   o \"no documentado\"\n5. Registro + métricas EMF")

# IAM
caja(70, 66, 34, 12, C["iam"], "IAM — LabRole", "Rol de ejecución de la Lambda\nsin claves en el código")

# DynamoDB
caja(118, 62, 36, 16, C["ddb"], "DynamoDB — kb", "Base de conocimiento\n38 entradas pregunta/respuesta\n(fuente principal)")
caja(118, 40, 36, 16, C["ddb"], "DynamoDB — consultas", "Registro de cada consulta\nestado · score · hash cliente\nTTL 30 días")
caja(118, 22, 36, 13, C["ddb"], "DynamoDB — limites", "Contador por cliente/minuto\nTTL 2 min")
# S3 docs
caja(70, 8, 34, 15, C["s3"], "Amazon S3 — Documentos", "Documentación autorizada (.md)\nkb/base_conocimiento.json\n(respaldo) · privado · SSE-S3")
# CloudWatch
caja(118, 5, 36, 13, C["cw"], "Amazon CloudWatch", "Logs (7 días) · métricas EMF\nDashboard · 2 alarmas")

# Flujos
flecha((20, 53), (30, 67), "carga la página", C["s3"], num=1, dx=-2, dy=2)
flecha((20, 49), (30, 40), "pregunta (HTTPS JSON)", C["apigw"], num=2, pos=(12, 41))
flecha((20, 46), (30, 16), "si falla → URL", C["lambda"], "--", num="2b", pos=(16, 37))
flecha((56, 40), (70, 43), "proxy v2.0", C["apigw"], num=3, dy=2.2)
flecha((56, 15), (70, 33), "", C["lambda"], "--")
flecha((87, 66), (87, 60.5), "asume rol", C["iam"], dx=6, dy=0)
flecha((104, 54), (118, 68), "Scan + caché 5 min", C["ddb"], num=4, dx=-1, dy=2.5)
flecha((104, 46), (118, 48), "PutItem", C["ddb"], num=5, dy=1.8)
flecha((104, 38), (118, 29), "UpdateItem ADD", C["ddb"], num=6, pos=(108.5, 31.5))
flecha((87, 30), (87, 23.5), "respaldo si\nDynamoDB falla", C["s3"], "--", dx=-7, dy=0)
flecha((104, 32), (118, 13), "logs + métricas", C["cw"], num=7, pos=(110.5, 19.5))

# Leyenda
ax.text(2, 31, "Flujo", fontsize=9, weight="bold")
for i, t in enumerate(["(1) Carga del frontend", "(2) Consulta principal",
                       "(2b) Ruta alternativa", "(3) Invocación Lambda", "(4) Lee base conocim.",
                       "(5) Registra consulta", "(6) Límite de uso", "(7) Observabilidad"]):
    ax.text(2, 27.8 - i * 3.0, t, fontsize=7.6, color="#333")

for ext in ("png", "pdf"):
    fig.savefig(RAIZ / "docs" / f"arquitectura.{ext}", bbox_inches="tight", facecolor="white")
print("Diagrama generado en docs/arquitectura.png y docs/arquitectura.pdf")
