#!/usr/bin/env python3
"""Utilidades compartidas de datos — bloque P1 (integridad de datos).

Contiene:
- Identidad canónica de equipos y jugadores (IDs estables + alias históricos).
- Derivación del estado de un partido (jugado / programado / suspendido).
- Exportación consistente SQLite -> Parquet/CSV.

Lo usan scraper.py y los scripts de migración/QA para que no haya lógica duplicada.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from datetime import date, datetime
from typing import Dict, Optional

# --- Rutas -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "benicarlo.db")
ALIAS_EQUIPOS_PATH = os.path.join(DATA_DIR, "alias_equipos.json")
ALIAS_JUGADORES_PATH = os.path.join(DATA_DIR, "alias_jugadores.json")
ESTADO_OVERRIDES_PATH = os.path.join(DATA_DIR, "estado_overrides.json")

# --- Estados de partido ------------------------------------------------------
ESTADO_JUGADO = "jugado"
ESTADO_PROGRAMADO = "programado"
ESTADO_SUSPENDIDO = "suspendido"
ESTADOS = (ESTADO_JUGADO, ESTADO_PROGRAMADO, ESTADO_SUSPENDIDO)

# --- Estados QA (columna partidos.qa_estado) ---------------------------------
QA_OK = "ok"
QA_DESCUADRE_CUARTOS = "descuadre_cuartos"
QA_DESCUADRE_JUGADORES = "descuadre_jugadores"
QA_SIN_ACTA = "sin_acta"


# --- Identidad ---------------------------------------------------------------
def normalizar_nombre(nombre) -> str:
    """Mayúsculas sin acentos ni puntuación y con espacios simples.

    'LÓPEZ SANCHEZ, JOSÉ A.' -> 'LOPEZ SANCHEZ JOSE A'
    """
    if nombre is None:
        return ""
    s = unicodedata.normalize("NFD", str(nombre))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip().upper()


def slug_id(nombre) -> str:
    """ID estable y legible a partir del nombre: 'CB BENICARLÓ' -> 'cb-benicarlo'."""
    s = normalizar_nombre(nombre).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


MOJIBAKE_RE = re.compile(r"Ã.|â.|Â.")


def reparar_texto(valor):
    """Repara mojibake clásico (UTF-8 decodificado como latin-1/cp1252).

    'AMICS CASTELLÃ\x93' -> 'AMICS CASTELLÓ'. Idempotente: los textos sanos
    se devuelven sin cambios.
    """
    if not isinstance(valor, str) or not MOJIBAKE_RE.search(valor):
        return valor
    for codificacion in ("latin-1", "cp1252"):
        try:
            reparado = valor.encode(codificacion).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if reparado != valor:
            return reparado
    return valor


def cargar_alias(ruta: str) -> Dict[str, str]:
    """Carga un fichero de alias y devuelve {nombre_normalizado: id_canónico}.

    Formato del JSON (las claves que empiezan por '_' se ignoran):
    {
      "cb-benicarlo": {
        "nombre_canonico": "CB Benicarló",
        "alias": ["C.B. BENICARLO", "MADERAS SORLI BENICARLO"]
      }
    }
    """
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8") as fh:
        contenido = json.load(fh)
    mapa: Dict[str, str] = {}
    for canonico_id, info in contenido.items():
        if canonico_id.startswith("_"):
            continue
        if not isinstance(info, dict):
            continue
        nombres = [info.get("nombre_canonico", "")] + list(info.get("alias", []))
        for nombre in nombres:
            if nombre:
                mapa[normalizar_nombre(nombre)] = canonico_id
    return mapa


def id_equipo(nombre, alias_map: Optional[Dict[str, str]] = None) -> str:
    if alias_map is None:
        alias_map = cargar_alias(ALIAS_EQUIPOS_PATH)
    return alias_map.get(normalizar_nombre(nombre), slug_id(nombre))


def id_jugador(nombre, alias_map: Optional[Dict[str, str]] = None) -> str:
    if alias_map is None:
        alias_map = cargar_alias(ALIAS_JUGADORES_PATH)
    return alias_map.get(normalizar_nombre(nombre), slug_id(nombre))


# --- Estado de partido -------------------------------------------------------
def _parse_fecha(fecha) -> Optional[date]:
    if fecha is None:
        return None
    if isinstance(fecha, datetime):
        return fecha.date()
    if isinstance(fecha, date):
        return fecha
    s = str(fecha).strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except ValueError:
            return None


def derivar_estado(jugado, fecha, hoy: Optional[date] = None) -> str:
    """jugado/programado/suspendido.

    Reglas:
    - jugado == 1                          -> 'jugado'
    - sin jugar y fecha pasada             -> 'suspendido'  (ej. COVID 2019/2020)
    - sin jugar y fecha futura/sin fecha   -> 'programado'
    """
    hoy = hoy or date.today()
    try:
        jugado_int = int(jugado or 0)
    except (TypeError, ValueError):
        jugado_int = 0
    if jugado_int == 1:
        return ESTADO_JUGADO
    f = _parse_fecha(fecha)
    if f is not None and f < hoy:
        return ESTADO_SUSPENDIDO
    return ESTADO_PROGRAMADO


def cargar_estado_overrides() -> Dict[int, str]:
    """Overrides manuales {partido_id: estado} desde data/estado_overrides.json."""
    if not os.path.exists(ESTADO_OVERRIDES_PATH):
        return {}
    with open(ESTADO_OVERRIDES_PATH, encoding="utf-8") as fh:
        contenido = json.load(fh)
    overrides = {}
    for k, v in contenido.items():
        if k.startswith("_"):
            continue
        if v in ESTADOS:
            overrides[int(k)] = v
    return overrides


# --- Exportación SQLite -> Parquet/CSV ---------------------------------------
def exportar_sqlite_a_archivos(db_path: str = DB_PATH) -> None:
    """Vuelca las tablas del SQLite a data/*.parquet y data/*.csv.

    Debe ejecutarse tras cualquier migración para que la app (que lee parquet)
    vea los mismos datos que la base de datos.
    """
    import pandas as pd

    data_dir = os.path.dirname(db_path)
    conn = sqlite3.connect(db_path)
    tablas = {
        "partidos": "partidos",
        "cuartos": "cuartos",
        "jugadores_partido": "jugadores",
        "equipos_catalogo": "equipos_catalogo",
        "jugadores_catalogo": "jugadores_catalogo",
        "clasificacion": "clasificacion",
        "temporadas": "temporadas",
    }
    for tabla, prefijo in tablas.items():
        try:
            df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
        except (pd.errors.DatabaseError, sqlite3.OperationalError):
            continue  # tabla aún no creada
        df.to_parquet(os.path.join(data_dir, f"{prefijo}.parquet"), index=False)
        df.to_csv(os.path.join(data_dir, f"{prefijo}.csv"), index=False)
    conn.close()
    print(f"Exportación a Parquet/CSV actualizada en '{data_dir}/'.")
