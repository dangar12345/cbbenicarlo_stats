#!/usr/bin/env python3
"""Migración P1.4 — IDs canónicos de equipos y jugadores.

Crea las tablas catálogo y añade claves foráneas naturales a las tablas de
hechos:

    equipos_catalogo(equipo_id, nombre_canonico, aliases)
    jugadores_catalogo(jugador_id, nombre_canonico, aliases)

    partidos.equipo_local_id / equipo_visitante_id / equipo_rival_id
    cuartos.equipo_id
    jugadores_partido.equipo_id / jugador_id

El ID se deriva del nombre normalizado (slug), salvo que el nombre figure en
data/alias_equipos.json o data/alias_jugadores.json, en cuyo caso se usa el ID
canónico declarado allí (así las 4 denominaciones históricas de CB Benicarló
convergen en 'cb-benicarlo').

Uso:
    .venv/bin/python scripts/migrate_ids.py [--dry-run]
"""

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_utils import (  # noqa: E402
    ALIAS_EQUIPOS_PATH,
    ALIAS_JUGADORES_PATH,
    DB_PATH,
    cargar_alias,
    exportar_sqlite_a_archivos,
    id_equipo,
    id_jugador,
    normalizar_nombre,
    slug_id,
)

COLUMNAS_NUEVAS = {
    "partidos": ["equipo_local_id", "equipo_visitante_id", "equipo_rival_id"],
    "cuartos": ["equipo_id"],
    "jugadores_partido": ["equipo_id", "jugador_id"],
}

DDL_CATALOGOS = """
CREATE TABLE IF NOT EXISTS equipos_catalogo (
    equipo_id TEXT PRIMARY KEY,
    nombre_canonico TEXT,
    aliases TEXT
)
"""

DDL_CATALOGOS_JUG = """
CREATE TABLE IF NOT EXISTS jugadores_catalogo (
    jugador_id TEXT PRIMARY KEY,
    nombre_canonico TEXT,
    aliases TEXT
)
"""


def asegurar_esquema(conn: sqlite3.Connection, dry_run: bool = False) -> None:
    for tabla, columnas in COLUMNAS_NUEVAS.items():
        existentes = [r[1] for r in conn.execute(f"PRAGMA table_info({tabla})")]
        for col in columnas:
            if col not in existentes:
                if dry_run:
                    print(f"[dry-run] se añadiría la columna '{tabla}.{col}'.")
                    continue
                conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} TEXT")
                print(f"Columna '{tabla}.{col}' añadida.")
    if not dry_run:
        conn.execute(DDL_CATALOGOS)
        conn.execute(DDL_CATALOGOS_JUG)
        conn.commit()


def resolver_alias(ruta_alias: str):
    """Devuelve (mapa_nombre_a_id, mapa_id_a_nombre_canónico)."""
    with open(ruta_alias, encoding="utf-8") as fh:
        contenido = json.load(fh)
    nombre_a_id = cargar_alias(ruta_alias)
    id_a_canonico = {}
    for canonico_id, info in contenido.items():
        if canonico_id.startswith("_") or not isinstance(info, dict):
            continue
        id_a_canonico[canonico_id] = info.get("nombre_canonico", canonico_id)
    return nombre_a_id, id_a_canonico


def catalogo_desde_nombres(nombres, nombre_a_id, id_a_canonico):
    """Agrupa nombres crudos por ID canónico y monta las filas de catálogo.

    nombre_canonico: el declarado en el alias; si no hay, la variante más
    frecuente. 'aliases' recoge todas las variantes vistas.
    """
    por_id = defaultdict(lambda: {"variantes": defaultdict(int)})
    for nombre in nombres:
        if not nombre:
            continue
        cid = nombre_a_id.get(normalizar_nombre(nombre), slug_id(nombre))
        por_id[cid]["variantes"][nombre] += 1

    filas = []
    for cid, info in por_id.items():
        variantes = sorted(info["variantes"], key=lambda n: (-info["variantes"][n], n))
        canonico = id_a_canonico.get(cid, variantes[0])
        filas.append((cid, canonico, json.dumps(variantes, ensure_ascii=False)))
    return filas


def migrar(db_path: str = DB_PATH, dry_run: bool = False) -> None:
    conn = sqlite3.connect(db_path)
    asegurar_esquema(conn, dry_run=dry_run)

    alias_equipos, canon_equipos = resolver_alias(ALIAS_EQUIPOS_PATH)
    alias_jugadores, canon_jugadores = resolver_alias(ALIAS_JUGADORES_PATH)

    # --- Equipos: nombre -> id en las tres tablas de hechos ------------------
    nombres_equipos = []
    for col in ("equipo_local", "equipo_visitante", "nombre_benicarlo", "equipo_rival"):
        nombres_equipos += [r[0] for r in conn.execute(f"SELECT DISTINCT {col} FROM partidos")]
    nombres_equipos += [r[0] for r in conn.execute("SELECT DISTINCT equipo FROM cuartos")]
    nombres_equipos += [r[0] for r in conn.execute("SELECT DISTINCT equipo FROM jugadores_partido")]

    # --- Jugadores ----------------------------------------------------------
    nombres_jugadores = [r[0] for r in conn.execute("SELECT DISTINCT jugador FROM jugadores_partido")]

    cat_equipos = catalogo_desde_nombres(nombres_equipos, alias_equipos, canon_equipos)
    cat_jugadores = catalogo_desde_nombres(nombres_jugadores, alias_jugadores, canon_jugadores)

    print(f"Equipos únicos: {len(cat_equipos)} | Jugadores únicos: {len(cat_jugadores)}")

    # Colisiones interesantes: varios nombres crudos -> mismo ID
    fusionados = [(cid, json.loads(als)) for cid, _, als in cat_equipos if len(json.loads(als)) > 1]
    if fusionados:
        print("\nEquipos con variantes fusionadas:")
        for cid, variantes in sorted(fusionados):
            print(f"  {cid}: {variantes}")
    fusionados_j = [(cid, json.loads(als)) for cid, _, als in cat_jugadores if len(json.loads(als)) > 1]
    if fusionados_j:
        print(f"\nJugadores con variantes fusionadas: {len(fusionados_j)}")
        for cid, variantes in sorted(fusionados_j)[:20]:
            print(f"  {cid}: {variantes}")

    if dry_run:
        print("\n--dry-run: no se escriben cambios.")
        conn.close()
        return

    # --- Escritura ----------------------------------------------------------
    # Los catálogos se reconstruyen por completo desde las tablas de hechos
    # (evita IDs huérfanos tras reparaciones de encoding o renombres).
    conn.execute("DELETE FROM equipos_catalogo")
    conn.execute("DELETE FROM jugadores_catalogo")
    conn.executemany(
        "INSERT OR REPLACE INTO equipos_catalogo (equipo_id, nombre_canonico, aliases) VALUES (?, ?, ?)",
        cat_equipos,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO jugadores_catalogo (jugador_id, nombre_canonico, aliases) VALUES (?, ?, ?)",
        cat_jugadores,
    )

    mapa_eq = {}
    for cid, canonico, als in cat_equipos:
        for variante in json.loads(als):
            mapa_eq[variante] = cid
    mapa_jug = {}
    for cid, canonico, als in cat_jugadores:
        for variante in json.loads(als):
            mapa_jug[variante] = cid

    for col, origen in (
        ("equipo_local_id", "equipo_local"),
        ("equipo_visitante_id", "equipo_visitante"),
        ("equipo_rival_id", "equipo_rival"),
    ):
        for variante, cid in mapa_eq.items():
            conn.execute(f"UPDATE partidos SET {col} = ? WHERE {origen} = ?", (cid, variante))

    for variante, cid in mapa_eq.items():
        conn.execute("UPDATE cuartos SET equipo_id = ? WHERE equipo = ?", (cid, variante))
        conn.execute("UPDATE jugadores_partido SET equipo_id = ? WHERE equipo = ?", (cid, variante))
    for variante, cid in mapa_jug.items():
        conn.execute("UPDATE jugadores_partido SET jugador_id = ? WHERE jugador = ?", (cid, variante))

    conn.commit()
    conn.close()
    exportar_sqlite_a_archivos(db_path)
    print("Migración de IDs canónicos completada.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Migra IDs canónicos de equipos y jugadores")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    migrar(args.db, args.dry_run)
