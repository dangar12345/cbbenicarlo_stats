#!/usr/bin/env python3
"""Reparación de encoding (mojibake) en los datos.

FEB no siempre declara el charset de sus páginas; scraping antiguo dejó
valores como 'AMICS CASTELLÃ\\x93' en lugar de 'AMICS CASTELLÓ'. Este script
repara todas las columnas de texto de las tablas de datos de forma
determinista e idempotente (los textos sanos no cambian).

Casos especiales documentados:
- partidos.arbitros: si el prefijo 'Árbitros ' quedó pegado por el mojibake,
  se elimina tras la reparación (el resto de filas ya no lo llevan).

Uso:
    .venv/bin/python scripts/fix_encoding.py [--dry-run]

Es seguro reejecutarlo tras cualquier scrape. El scraper actual ya decodifica
UTF-8 correctamente (fetch_html), así que es una red de seguridad.
"""

import argparse
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_utils import DB_PATH, exportar_sqlite_a_archivos, reparar_texto  # noqa: E402

TABLAS = ("partidos", "cuartos", "jugadores_partido", "equipos_catalogo", "jugadores_catalogo")


def reparar(db_path: str = DB_PATH, dry_run: bool = False) -> None:
    conn = sqlite3.connect(db_path)
    total = 0

    for tabla in TABLAS:
        try:
            cols = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
        except sqlite3.OperationalError:
            continue
        if not cols:
            continue
        pk = next((c[1] for c in cols if c[5]), None)  # columna PK
        text_cols = [c[1] for c in cols if c[2].upper() in ("TEXT", "")]
        if pk is None or not text_cols:
            continue

        filas = conn.execute(
            f"SELECT {pk}, {', '.join(text_cols)} FROM {tabla}"
        ).fetchall()

        for fila in filas:
            id_valor = fila[0]
            cambios = {}
            for col, valor in zip(text_cols, fila[1:]):
                if not isinstance(valor, str):
                    continue
                reparado = reparar_texto(valor)
                if tabla == "partidos" and col == "arbitros":
                    reparado = re.sub(r'^\s*Á?rbitros\s+', '', reparado, flags=re.I)
                if reparado != valor:
                    cambios[col] = (valor, reparado)
            if cambios:
                total += len(cambios)
                marca = "[dry-run] " if dry_run else ""
                for col, (viejo, nuevo) in cambios.items():
                    print(f"{marca}{tabla}.{col} (id={id_valor}): {viejo!r} -> {nuevo!r}")
                if not dry_run:
                    sets = ", ".join(f"{col} = ?" for col in cambios)
                    conn.execute(
                        f"UPDATE {tabla} SET {sets} WHERE {pk} = ?",
                        [nuevo for _viejo, nuevo in cambios.values()] + [id_valor],
                    )

    if not dry_run:
        conn.commit()
    conn.close()
    print(f"\nValores reparados: {total}")
    if not dry_run:
        exportar_sqlite_a_archivos(db_path)
    else:
        print("--dry-run: no se escriben cambios.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Repara mojibake en los datos")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    reparar(args.db, args.dry_run)
