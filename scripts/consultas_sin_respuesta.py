#!/usr/bin/env python3
"""
Lista las consultas que el asistente NO pudo responder (estado sin_respuesta o
sugerencia), agrupadas por frecuencia. Sirve para decidir qué documentación
agregar y como evidencia del "registro de consultas sin respuesta".

Uso:
  python3 scripts/consultas_sin_respuesta.py --tabla asistente-tecnohogar-consultas [--csv evidencias/sin_respuesta.csv]
"""
import argparse
import csv
from collections import Counter

import boto3
from boto3.dynamodb.conditions import Attr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tabla", required=True)
    ap.add_argument("--region", default=None)
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()

    tabla = boto3.resource("dynamodb", region_name=a.region).Table(a.tabla)
    filtro = Attr("estado").is_in(["sin_respuesta", "sugerencia"])
    items, kwargs = [], {"FilterExpression": filtro}
    while True:
        r = tabla.scan(**kwargs)
        items += r["Items"]
        if "LastEvaluatedKey" not in r:
            break
        kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]

    items.sort(key=lambda i: i["fecha"], reverse=True)
    frecuencia = Counter(i["pregunta"].strip().lower() for i in items)
    print(f"\n{len(items)} consultas sin respuesta registradas\n")
    print(f"{'Veces':>5}  Pregunta")
    for p, n in frecuencia.most_common(20):
        print(f"{n:>5}  {p}")
    print("\nÚltimas 10:")
    for i in items[:10]:
        print(f"  {i['fecha']}  {i['estado']:13} score={i['score']}  {i['pregunta']}")

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["fecha", "estado", "score", "origen", "pregunta"])
            for i in items:
                w.writerow([i["fecha"], i["estado"], i["score"], i["origen"], i["pregunta"]])
        print(f"\nExportado a {a.csv}")


if __name__ == "__main__":
    main()
