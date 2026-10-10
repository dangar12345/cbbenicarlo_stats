#!/usr/bin/env python3
"""Migración P1.1 — campo `estado` en la tabla partidos.

Añade la columna `estado` ('jugado' | 'programado' | 'suspendido') y la rellena
para todos los partidos existentes:

- jugado == 1                       -> 'jugado'
- sin jugar y fecha pasada          -> 'suspendido' (p. ej. los 9 partidos de la
                                        2019/2020 suspendidos por el COVID)
- sin jugar y fecha futura/sin fecha-> 'programado'

Respete data/estado_overrides.json para correcciones manuales.

Uso:
    .venv/bin/python scripts/migrate_estado.py [--dry-run]
"""

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_utils import (  # noqa: E402
    DB_PATH,
    ESTADOS,
    cargar_estado_overrides,
    derivar_estado,
    exportar_sqlite_a_archivos,
)


def asegurar_columna(conn: sqlite3.Connection, dry_run: bool = False) -> None:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(partidos)")]
    if "estado" not in cols:
        if dry_run:
            print("[dry-run] se añadiría la columna 'estado' a la tabla partidos.")
            return
        conn.execute("ALTER TABLE partidos ADD COLUMN estado TEXT")
        conn.commit()
        print("Columna 'estado' añadida a la tabla partidos.")


def migrar(db_path: str = DB_PATH, dry_run: bool = False) -> None:
    conn = sqlite3.connect(db_path)
    asegurar_columna(conn, dry_run=dry_run)

    overrides = cargar_estado_overrides()
    filas = conn.execute(
        "SELECT partido_id, jugado, fecha, temporada FROM partidos"
    ).fetchall()

    cambios = {}
    resumen = {estado: 0 for estado in ESTADOS}
    for partido_id, jugado, fecha, temporada in filas:
        estado = overrides.get(partido_id) or derivar_estado(jugado, fecha)
        resumen[estado] = resumen.get(estado, 0) + 1
        cambios[partido_id] = estado

    print("\nResumen de estados derivados:")
    for estado, n in sorted(resumen.items()):
        print(f"  {estado:12s}: {n}")
    if overrides:
        print(f"  (overrides manuales aplicados: {len(overrides)})")

    # Detalle de los suspendidos: suelen necesitar revisión manual
    suspendidos = [
        (pid, fecha, temporada)
        for (pid, jugado, fecha, temporada) in filas
        if cambios[pid] == "suspendido"
    ]
    if suspendidos:
        print("\nPartidos marcados como 'suspendido':")
        for pid, fecha, temporada in suspendidos:
            origen = "override" if pid in overrides else "regla automática"
            print(f"  {pid} | {temporada} | {fecha} | ({origen})")

    if dry_run:
        print("\n--dry-run: no se escriben cambios.")
        conn.close()
        return

    conn.executemany(
        "UPDATE partidos SET estado = ? WHERE partido_id = ?",
        [(estado, pid) for pid, estado in cambios.items()],
    )
    conn.commit()
    conn.close()
    exportar_sqlite_a_archivos(db_path)
    print("Migración de 'estado' completada.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Migra el campo estado de partidos")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    migrar(args.db, args.dry_run)
