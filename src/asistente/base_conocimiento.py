"""
Carga de la base de conocimiento (documentación autorizada) con caché en memoria.

Fuentes soportadas (variable de entorno KB_SOURCE):
  - "dynamodb" (por defecto): tabla KB_TABLE, una entrada por ítem.
  - "s3": objeto JSON en s3://DOCS_BUCKET/KB_S3_KEY (respaldo si DynamoDB falla).
  - "local": archivo JSON en KB_LOCAL_PATH (solo pruebas locales).

El índice de similitud se construye una vez por contenedor de Lambda y se
refresca cada KB_CACHE_SEGUNDOS (arranque en frío ≈ milisegundos para ~100 entradas).
"""
from __future__ import annotations

import json
import logging
import os
import time

from similitud import IndiceSimilitud

logger = logging.getLogger(__name__)

_cache = {"indice": None, "cargado_en": 0.0, "fuente": None}


def _desde_dynamodb(tabla_nombre: str) -> list[dict]:
    import boto3  # incluido en el runtime de Lambda

    tabla = boto3.resource("dynamodb").Table(tabla_nombre)
    items, kwargs = [], {}
    while True:
        resp = tabla.scan(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return [i for i in items if i.get("activo", True)]


def _desde_s3(bucket: str, clave: str) -> list[dict]:
    import boto3

    obj = boto3.client("s3").get_object(Bucket=bucket, Key=clave)
    return json.loads(obj["Body"].read().decode("utf-8"))


def _desde_local(ruta: str) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def cargar_entradas() -> tuple[list[dict], str]:
    fuente = os.environ.get("KB_SOURCE", "dynamodb").lower()
    if fuente == "local":
        return _desde_local(os.environ["KB_LOCAL_PATH"]), "local"
    if fuente == "s3":
        return _desde_s3(os.environ["DOCS_BUCKET"], os.environ.get("KB_S3_KEY", "kb/base_conocimiento.json")), "s3"
    try:
        return _desde_dynamodb(os.environ["KB_TABLE"]), "dynamodb"
    except Exception:  # degradación controlada: usar el respaldo en S3
        if os.environ.get("DOCS_BUCKET"):
            logger.exception("Fallo leyendo DynamoDB; usando respaldo en S3")
            return _desde_s3(os.environ["DOCS_BUCKET"], os.environ.get("KB_S3_KEY", "kb/base_conocimiento.json")), "s3-respaldo"
        raise


def obtener_indice() -> tuple[IndiceSimilitud, str]:
    ttl = float(os.environ.get("KB_CACHE_SEGUNDOS", "300"))
    ahora = time.time()
    if _cache["indice"] is None or ahora - _cache["cargado_en"] > ttl:
        entradas, fuente = cargar_entradas()
        _cache.update(indice=IndiceSimilitud(entradas), cargado_en=ahora, fuente=fuente)
        logger.info("Base de conocimiento cargada: %d entradas desde %s", len(entradas), fuente)
    return _cache["indice"], _cache["fuente"]


def invalidar_cache() -> None:
    _cache.update(indice=None, cargado_en=0.0, fuente=None)
