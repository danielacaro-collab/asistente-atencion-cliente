"""
Motor de búsqueda por similitud de texto (100 % Python estándar, sin IA gestionada).

Pipeline:
  1. Normalización: minúsculas, sin tildes, sin signos, sinónimos de dominio.
  2. Tokenización + eliminación de palabras vacías (stopwords) en español.
  3. Lematización ligera (stemming por sufijos + truncado).
  4. Vectores TF-IDF y similitud de coseno contra cada entrada de la base.
  5. Jaccard sobre trigramas de caracteres (tolerancia a errores de tipeo).
  6. Factor de cobertura: penaliza preguntas con muchas palabras que no
     existen en la documentación (evita falsos positivos).

Puntaje final en [0, 1]:
  score = (0.55 * coseno_mejor_variante + 0.25 * coseno_entrada
           + 0.20 * jaccard_trigramas) * factor_cobertura
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

STOPWORDS = set("""
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun cada como con
contra cual cuales cualquier cuando cuanto cuanta cuantos cuantas de del desde donde
dos e el ella ellas ellos en entre era eres es esa esas ese eso esos esta estas este
esto estos estoy estan estar fue ha hay hace hacer hasta la las le les lo los mas me
mi mis mucho muy nada ni no nos nosotros o os otra otro para pero poco por porque puedo
puede pueden que quien quienes se sea ser si sin sobre son su sus tal tambien tan te
tengo tiene tienen tu tus un una unas uno unos usted ustedes vosotros y ya yo
quiero quisiera necesito saber favor hola buenas buenos tardes noches gracias
debo deberia podria podrian seria hago tener tienes cuanto cuantos
""".split())

# Sinónimos de dominio -> término canónico (antes del stemming).
SINONIMOS = {
    "devolver": "devolucion", "devuelvo": "devolucion", "devolverlo": "devolucion",
    "reembolso": "devolucion", "reembolsar": "devolucion", "regresar": "devolucion",
    "abren": "horario", "abre": "horario", "cierran": "horario", "cierra": "horario",
    "atienden": "horario", "atencion": "horario", "hora": "horario", "horas": "horario",
    "abierto": "horario", "abiertos": "horario",
    "pagar": "pago", "pagos": "pago", "pago": "pago", "abonar": "pago",
    "tarjeta": "pago", "qr": "pago",
    "envio": "envio", "envios": "envio", "enviar": "envio", "entrega": "envio",
    "entregas": "envio", "delivery": "envio", "despacho": "envio", "llega": "envio",
    "demora": "plazo", "tarda": "plazo", "tardan": "plazo", "tiempo": "plazo",
    "dias": "plazo",
    "garantia": "garantia", "garantias": "garantia",
    "factura": "factura", "facturas": "factura", "nit": "factura",
    "precio": "precio", "precios": "precio", "cuesta": "precio", "costo": "precio",
    "vale": "precio",
    "sucursal": "sucursal", "sucursales": "sucursal", "tienda": "sucursal",
    "tiendas": "sucursal", "local": "sucursal", "ubicados": "sucursal",
    "ubicacion": "sucursal", "direccion": "sucursal",
    "contacto": "contacto", "telefono": "contacto", "whatsapp": "contacto",
    "correo": "contacto", "email": "contacto", "llamar": "contacto",
    "reclamo": "reclamo", "queja": "reclamo", "quejas": "reclamo", "reclamar": "reclamo",
    "cuotas": "credito", "financiamiento": "credito", "plazos": "credito",
    "cancelar": "cancelacion", "anular": "cancelacion",
    "pedido": "pedido", "pedidos": "pedido", "compra": "pedido", "orden": "pedido",
    "mandan": "envio", "mandar": "envio", "envian": "envio", "mandar": "envio",
    "plata": "dinero", "platita": "dinero",
    "interes": "intereses",
    "rastrear": "seguimiento", "rastreo": "seguimiento",
    "parqueo": "estacionamiento", "parquear": "estacionamiento", "estacionar": "estacionamiento",
}

SUFIJOS = (
    "aciones", "iciones", "uciones", "amiento", "imiento", "mente",
    "acion", "icion", "ucion", "ancia", "encia", "ables", "ibles",
    "able", "ible", "ador", "edor", "idor", "ando", "iendo",
    "ados", "idos", "adas", "idas", "ado", "ido", "ada", "ida",
    "ar", "er", "ir", "es", "s",
)
LONGITUD_RAIZ = 7


def quitar_tildes(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def raiz(palabra: str) -> str:
    """Stemming ligero para español: quita un sufijo y trunca la raíz."""
    for suf in SUFIJOS:
        if palabra.endswith(suf) and len(palabra) - len(suf) >= 4:
            palabra = palabra[: -len(suf)]
            break
    return palabra[:LONGITUD_RAIZ]


def tokenizar(texto: str) -> list[str]:
    texto = quitar_tildes((texto or "").lower())
    palabras = re.findall(r"[a-z0-9]+", texto)
    tokens = []
    for p in palabras:
        if p in STOPWORDS or (len(p) < 2 and not p.isdigit()):
            continue
        p = SINONIMOS.get(p, p)
        tokens.append(raiz(p))
    return tokens


def trigramas(texto: str) -> set[str]:
    limpio = " ".join(quitar_tildes((texto or "").lower()).split())
    limpio = re.sub(r"[^a-z0-9 ]", "", limpio)
    limpio = f"  {limpio} "
    return {limpio[i : i + 3] for i in range(len(limpio) - 2)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def coseno(v1: dict, v2: dict) -> float:
    if not v1 or not v2:
        return 0.0
    comunes = set(v1) & set(v2)
    num = sum(v1[t] * v2[t] for t in comunes)
    n1 = math.sqrt(sum(x * x for x in v1.values()))
    n2 = math.sqrt(sum(x * x for x in v2.values()))
    return num / (n1 * n2) if n1 and n2 else 0.0


@dataclass
class Resultado:
    entrada: dict | None
    score: float
    detalle: dict = field(default_factory=dict)
    candidatos: list = field(default_factory=list)


class IndiceSimilitud:
    """Índice TF-IDF en memoria construido a partir de la base de conocimiento."""

    W_VARIANTE, W_ENTRADA, W_TRIGRAMA = 0.55, 0.25, 0.20

    def __init__(self, entradas: list[dict]):
        self.entradas = entradas
        self._docs_entrada: list[list[str]] = []
        self._docs_variantes: list[list[list[str]]] = []
        self._trigramas_variantes: list[list[set]] = []

        for e in entradas:
            variantes = [e.get("pregunta", "")] + list(e.get("variantes", []))
            toks_var = [tokenizar(v) for v in variantes]
            claves = " ".join(e.get("palabras_clave", []))
            # El documento de la entrada incluye la respuesta: amplía el recall.
            doc = tokenizar(" ".join(variantes) + " " + claves + " " + e.get("respuesta", ""))
            self._docs_variantes.append(toks_var)
            self._docs_entrada.append(doc)
            self._trigramas_variantes.append([trigramas(v) for v in variantes])

        n = len(entradas) or 1
        df = Counter()
        for doc in self._docs_entrada:
            df.update(set(doc))
        self.vocabulario = set(df)
        self.idf = {t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()}
        self.idf_max = max(self.idf.values(), default=1.0)

        self._vec_entrada = [self._tfidf(d) for d in self._docs_entrada]
        self._vec_variantes = [[self._tfidf(v) for v in vs] for vs in self._docs_variantes]

    def _tfidf(self, tokens: list[str]) -> dict:
        tf = Counter(tokens)
        total = sum(tf.values()) or 1
        return {t: (c / total) * self.idf.get(t, 1.0) for t, c in tf.items()}

    def buscar(self, pregunta: str, top_k: int = 3) -> Resultado:
        tokens = tokenizar(pregunta)
        if not tokens or not self.entradas:
            return Resultado(None, 0.0, {"motivo": "sin_terminos_utiles", "tokens": tokens})

        vq = self._tfidf(tokens)
        tq = trigramas(pregunta)
        # Cobertura ponderada por IDF: una palabra desconocida (p. ej. "wifi")
        # pesa como la más rara del vocabulario, así que penaliza más que una
        # palabra frecuente conocida.
        peso_desconocida = self.idf_max
        masa_total = sum(self.idf.get(t, peso_desconocida) for t in tokens)
        masa_conocida = sum(self.idf[t] for t in tokens if t in self.idf)
        cobertura = masa_conocida / masa_total if masa_total else 0.0
        factor = 0.3 + 0.7 * cobertura  # 1.0 si todas las palabras existen en la base

        puntajes = []
        for i, e in enumerate(self.entradas):
            cos_var = max((coseno(vq, vv) for vv in self._vec_variantes[i]), default=0.0)
            cos_ent = coseno(vq, self._vec_entrada[i])
            jac = max((jaccard(tq, tv) for tv in self._trigramas_variantes[i]), default=0.0)
            base = self.W_VARIANTE * cos_var + self.W_ENTRADA * cos_ent + self.W_TRIGRAMA * jac
            puntajes.append((round(base * factor, 4), i, cos_var, cos_ent, jac))

        puntajes.sort(reverse=True)
        mejor = puntajes[0]
        candidatos = [
            {"id": self.entradas[i]["id"], "pregunta": self.entradas[i]["pregunta"], "score": s}
            for s, i, *_ in puntajes[:top_k]
        ]
        detalle = {
            "tokens": tokens,
            "cobertura": round(cobertura, 3),
            "coseno_variante": round(mejor[2], 4),
            "coseno_entrada": round(mejor[3], 4),
            "jaccard_trigramas": round(mejor[4], 4),
        }
        return Resultado(self.entradas[mejor[1]], mejor[0], detalle, candidatos)
