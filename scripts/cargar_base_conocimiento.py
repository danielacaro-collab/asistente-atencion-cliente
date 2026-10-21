#!/usr/bin/env python3
"""
Carga (o actualiza) la base de conocimiento en DynamoDB desde data/base_conocimiento.json.
Las entradas que ya no están en el JSON se marcan como inactivas (no se borran).

Uso:
  python3 scripts/cargar_base_conocimiento.py --tabla asistente-tecnohogar-kb [--region us-east-1]
Requiere una sesión de AWS activa (CloudShell del Learner Lab o ~/.aws local).
"""
import argparse
import json
from pathlib import Path

import boto3

RAIZ = Path(__file__).resolve().parents[1]
CAMPOS = ("id", "categoria", "pregunta", "respuesta", "fuente")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tabla", required=True)
    ap.add_argument("--region", default=None)
    ap.add_argument("--archivo", default=str(RAIZ / "data" / "base_conocimiento.json"))
    a = ap.parse_args()

    entradas = json.loads(Path(a.archivo).read_text(encoding="utf-8"))
    for e in entradas:
        faltan = [c for c in CAMPOS if not e.get(c)]
        if faltan:
            raise SystemExit(f"Entrada {e.get('id')} incompleta: faltan {faltan}")

    tabla = boto3.resource("dynamodb", region_name=a.region).Table(a.tabla)
    with tabla.batch_writer(overwrite_by_pkeys=["id"]) as bw:
        for e in entradas:
            bw.put_item(Item={**e, "activo": True})

    ids = {e["id"] for e in entradas}
    existentes = tabla.scan(ProjectionExpression="id")["Items"]
    obsoletas = [i["id"] for i in existentes if i["id"] not in ids]
    for oid in obsoletas:
        tabla.update_item(Key={"id": oid}, UpdateExpression="SET activo = :f",
                          ExpressionAttributeValues={":f": False})
    print(f"    ✔ {len(entradas)} entradas cargadas en {a.tabla}"
          + (f"; {len(obsoletas)} marcadas inactivas" if obsoletas else ""))


if __name__ == "__main__":
    main()
