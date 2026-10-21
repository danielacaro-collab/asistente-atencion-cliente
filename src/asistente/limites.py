"""
Límite de uso por cliente (ventana fija de 1 minuto) con un contador en DynamoDB.

Complementa el throttling de API Gateway (que protege a nivel global) con un
límite por cliente que también aplica cuando se usa la URL de función de
Lambda (la ruta alternativa no tiene throttling propio).

Clave del contador: "<hash_cliente>#<minuto_epoch>", con TTL de 2 minutos.
Si DynamoDB falla, se permite la solicitud (fail-open) y se registra el error.
"""
from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)
_tabla = None


def _tabla_limites():
    global _tabla
    if _tabla is None:
        import boto3

        _tabla = boto3.resource("dynamodb").Table(os.environ["RATE_TABLE"])
    return _tabla


def permitir(cliente_hash: str) -> tuple[bool, int, int]:
    """Devuelve (permitido, conteo_actual, limite)."""
    limite = int(os.environ.get("LIMITE_POR_MINUTO", "20"))
    if not os.environ.get("RATE_TABLE") or limite <= 0:
        return True, 0, limite
    minuto = int(time.time() // 60)
    try:
        resp = _tabla_limites().update_item(
            Key={"clave": f"{cliente_hash}#{minuto}"},
            UpdateExpression="ADD conteo :uno SET expira = :exp",
            ExpressionAttributeValues={":uno": 1, ":exp": (minuto + 2) * 60},
            ReturnValues="UPDATED_NEW",
        )
        conteo = int(resp["Attributes"]["conteo"])
        return conteo <= limite, conteo, limite
    except Exception:
        logger.exception("Fallo el control de límite; se permite la solicitud")
        return True, 0, limite
