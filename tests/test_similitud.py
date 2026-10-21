"""Pruebas del motor de similitud y de la prueba de aceptación (sin AWS)."""
import json
import os

import pytest

from conftest import RAIZ
from similitud import IndiceSimilitud, jaccard, quitar_tildes, tokenizar

KB = json.loads((RAIZ / "data" / "base_conocimiento.json").read_text(encoding="utf-8"))
CASOS = json.loads((RAIZ / "data" / "casos_prueba.json").read_text(encoding="utf-8"))["casos"]
UMBRAL = float(os.environ.get("UMBRAL_RESPUESTA", "0.38"))


@pytest.fixture(scope="module")
def indice():
    return IndiceSimilitud(KB)


def test_normalizacion():
    assert quitar_tildes("Garantía Ñandú") == "Garantia Nandu"
    assert tokenizar("¿Cuál es el HORARIO?") == tokenizar("horario")
    assert tokenizar("") == []


def test_sinonimos_unifican_terminos():
    assert tokenizar("reembolso") == tokenizar("devolver")
    assert tokenizar("delivery") == tokenizar("envío")


def test_jaccard_limites():
    assert jaccard(set(), {"a"}) == 0.0
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0


def test_base_valida():
    ids = [e["id"] for e in KB]
    assert len(ids) == len(set(ids)), "IDs duplicados en la base"
    for e in KB:
        assert e["respuesta"] and e["pregunta"] and e["fuente"]


@pytest.mark.parametrize("caso", [c for c in CASOS if c["esperado_id"]], ids=lambda c: c["id"])
def test_aceptacion_con_respuesta(indice, caso):
    r = indice.buscar(caso["pregunta"])
    assert r.entrada["id"] == caso["esperado_id"]
    assert r.score >= UMBRAL, f"score {r.score} bajo el umbral"


@pytest.mark.parametrize("caso", [c for c in CASOS if not c["esperado_id"]], ids=lambda c: c["id"])
def test_aceptacion_sin_respuesta(indice, caso):
    r = indice.buscar(caso["pregunta"])
    assert r.score < UMBRAL, f"falso positivo: {r.entrada['id']} con score {r.score}"


@pytest.mark.parametrize("pregunta,esperado", [
    ("orario de los sabados", "HOR-001"),
    ("garantia de una laptp", "GAR-001"),
    ("¿aseptan pago con qr?", "PAG-001"),
])
def test_tolerancia_errores_tipeo(indice, pregunta, esperado):
    # Con un error de tipeo el mejor candidato sigue siendo el correcto; el score
    # puede caer en la zona de "sugerencia" (el asistente pide confirmar).
    assert indice.buscar(pregunta).entrada["id"] == esperado


def test_pregunta_solo_stopwords(indice):
    r = indice.buscar("¿y qué es eso?")
    assert r.entrada is None and r.score == 0.0
