"""Pruebas de integración del handler con DynamoDB y S3 simulados (moto)."""
import base64
import json
import os

import boto3
import pytest
from moto import mock_aws

from conftest import RAIZ

KB = json.loads((RAIZ / "data" / "base_conocimiento.json").read_text(encoding="utf-8"))


def evento_http(pregunta=None, metodo="POST", ruta="/preguntar", dominio="abc123.execute-api.us-east-1.amazonaws.com",
                cuerpo_crudo=None, ip="190.0.0.1", b64=False):
    cuerpo = cuerpo_crudo if cuerpo_crudo is not None else (json.dumps({"pregunta": pregunta}) if pregunta is not None else None)
    if b64 and cuerpo:
        cuerpo = base64.b64encode(cuerpo.encode()).decode()
    return {
        "version": "2.0", "rawPath": ruta, "body": cuerpo, "isBase64Encoded": b64,
        "requestContext": {"domainName": dominio, "http": {"method": metodo, "path": ruta, "sourceIp": ip}},
    }


@pytest.fixture
def aws():
    with mock_aws():
        os.environ.update({
            "KB_SOURCE": "dynamodb", "KB_TABLE": "kb", "LOG_TABLE": "consultas",
            "RATE_TABLE": "limites", "LIMITE_POR_MINUTO": "5", "DOCS_BUCKET": "docs-bucket",
        })
        ddb = boto3.resource("dynamodb")
        for nombre, clave in (("kb", "id"), ("consultas", "consulta_id"), ("limites", "clave")):
            ddb.create_table(TableName=nombre, BillingMode="PAY_PER_REQUEST",
                             KeySchema=[{"AttributeName": clave, "KeyType": "HASH"}],
                             AttributeDefinitions=[{"AttributeName": clave, "AttributeType": "S"}])
        with ddb.Table("kb").batch_writer() as bw:
            for e in KB:
                bw.put_item(Item=e)
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket="docs-bucket")
        s3.put_object(Bucket="docs-bucket", Key="kb/base_conocimiento.json", Body=json.dumps(KB).encode())

        import base_conocimiento, limites, registro
        base_conocimiento.invalidar_cache()
        registro._tabla = None
        limites._tabla = None
        import lambda_function
        yield lambda_function, ddb


def cuerpo(resp):
    return json.loads(resp["body"])


def test_pregunta_con_respuesta_registra(aws):
    lf, ddb = aws
    r = lf.lambda_handler(evento_http("¿Aceptan pagos con QR?"), None)
    b = cuerpo(r)
    assert r["statusCode"] == 200 and b["estado"] == "respondida" and b["entrada_id"] == "PAG-001"
    assert "QR" in b["respuesta"] and b["fuente"].startswith("documentos/")
    item = ddb.Table("consultas").get_item(Key={"consulta_id": b["consulta_id"]})["Item"]
    assert item["estado"] == "respondida" and item["origen"] == "api-gateway"
    assert "190.0.0.1" not in json.dumps(item, default=str), "la IP no debe guardarse en claro"


def test_pregunta_sin_respuesta(aws):
    lf, ddb = aws
    b = cuerpo(lf.lambda_handler(evento_http("¿Quién ganó el partido de fútbol ayer?"), None))
    assert b["estado"] == "sin_respuesta" and b["entrada_id"] is None
    assert "no contiene" in b["respuesta"]
    items = ddb.Table("consultas").scan()["Items"]
    assert any(i["estado"] == "sin_respuesta" for i in items)


def test_origen_function_url_y_base64(aws):
    lf, ddb = aws
    ev = evento_http("horario de los sábados", dominio="xyz.lambda-url.us-east-1.on.aws", b64=True)
    b = cuerpo(lf.lambda_handler(ev, None))
    assert b["estado"] == "respondida"
    item = ddb.Table("consultas").get_item(Key={"consulta_id": b["consulta_id"]})["Item"]
    assert item["origen"] == "function-url"


def test_invocacion_directa_consola(aws):
    lf, _ = aws
    r = lf.lambda_handler({"pregunta": "¿Venden garantía extendida?"}, None)
    assert cuerpo(r)["entrada_id"] == "GAR-004"


@pytest.mark.parametrize("ev,status", [
    (evento_http("   "), 400),
    (evento_http(cuerpo_crudo="{pregunta: sin comillas"), 400),
    (evento_http(cuerpo_crudo="[1,2]"), 400),
    (evento_http("x" * 501), 413),
    (evento_http(metodo="DELETE"), 404),
])
def test_errores_validacion(aws, ev, status):
    lf, _ = aws
    assert lf.lambda_handler(ev, None)["statusCode"] == status


def test_options_y_salud(aws):
    lf, _ = aws
    assert lf.lambda_handler(evento_http(metodo="OPTIONS"), None)["statusCode"] == 204
    r = lf.lambda_handler(evento_http(metodo="GET", ruta="/salud"), None)
    assert r["statusCode"] == 200 and cuerpo(r)["entradas"] == len(KB)


def test_limite_por_minuto(aws):
    lf, _ = aws
    codigos = [lf.lambda_handler(evento_http("horario", ip="10.0.0.9"), None)["statusCode"] for _ in range(7)]
    assert codigos[:5] == [200] * 5 and codigos[5:] == [429, 429]
    # otro cliente no se ve afectado
    assert lf.lambda_handler(evento_http("horario", ip="10.0.0.10"), None)["statusCode"] == 200


def test_respaldo_s3_si_dynamodb_falla(aws):
    lf, ddb = aws
    import base_conocimiento
    ddb.Table("kb").delete()
    base_conocimiento.invalidar_cache()
    r = lf.lambda_handler(evento_http(metodo="GET", ruta="/salud"), None)
    assert cuerpo(r)["fuente_base"] == "s3-respaldo"


def test_metricas_emf(aws, capsys):
    lf, _ = aws
    lf.lambda_handler(evento_http("¿Aceptan pagos con QR?"), None)
    lineas = [l for l in capsys.readouterr().out.splitlines() if '"_aws"' in l]
    emf = json.loads(lineas[-1])
    assert emf["_aws"]["CloudWatchMetrics"][0]["Namespace"] == "AsistenteAtencionCliente"
    assert emf["Respondidas"] == 1 and emf["Consultas"] == 1
