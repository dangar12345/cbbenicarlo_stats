#!/usr/bin/env python3
"""Migración P2 · punto 5 — contexto de liga (tabla 'temporadas').

Construye una fila por temporada fusionando tres fuentes, de menor a mayor
prioridad:

  1. Derivado de partidos: balance V/D, fase alcanzada (Liga Regular / Playoff
     de ascenso / Permanencia / Cancelada), grupo de la última fase regular.
  2. Clasificación oficial (tabla 'clasificacion', scrapeada de FEB):
     posición final del Benicarló en su grupo.
  3. Curado en data/temporadas_contexto.json: competición oficial y narrativa
     (hito / resultado_hito). Tiene la última palabra.

Uso:
    .venv/bin/python scripts/migrate_liga.py [--dry-run]

Requiere haber ejecutado antes (o después, con re-ejecución de esta):
    .venv/bin/python scraper.py --solo-clasificacion
"""

import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_utils import (  # noqa: E402
    DB_PATH,
    exportar_sqlite_a_archivos,
    normalizar_nombre,
)

CONTEXTO_PATH = os.path.join(os.path.dirname(DB_PATH), "temporadas_contexto.json")

# Orden de rondas de playoff: menor = ronda más avanzada
RONDAS_PLAYOFF = (("1/8", 8), ("1/4", 4), ("1/2", 2), ("FINAL", 1))


def fase_alcanzada(rows):
    """Deriva la fase más avanzada disputada por el Benicarló en la temporada."""
    fases = {r['fase_tipo'] for r in rows}
    if 'Playoff' in fases:
        mejor_num, mejor_nombre = 99, 'Playoff'
        for r in rows:
            if r['fase_tipo'] != 'Playoff':
                continue
            grupo_up = (r['grupo_nombre'] or '').upper()
            # Ojo: los nombres traen "Final" como palabra ("1/8 Final"); la
            # ronda se decide primero por la fracción (1/8, 1/4, 1/2).
            num = None
            for etiqueta, n in RONDAS_PLAYOFF[:-1]:
                if etiqueta in grupo_up:
                    num = n
                    break
            if num is None and 'FINAL' in grupo_up:
                num = 1
            if num is not None and num < mejor_num:
                mejor_num = num
                mejor_nombre = ('Playoff de ascenso (Final)' if num == 1
                                else f'Playoff de ascenso (1/{num} de final)')
        return mejor_nombre
    if 'Permanencia' in fases:
        return 'Permanencia'
    return 'Liga Regular'


def cargar_contexto():
    if not os.path.exists(CONTEXTO_PATH):
        return {}
    with open(CONTEXTO_PATH, encoding='utf-8') as fh:
        contenido = json.load(fh)
    return {k: v for k, v in contenido.items() if not k.startswith('_')}


def posicion_en_clasificacion(conn, temporada, grupo):
    """Posición del Benicarló en la clasificación oficial de su grupo."""
    filas = conn.execute(
        "SELECT grupo, posicion FROM clasificacion WHERE temporada = ? AND es_benicarlo = 1",
        (temporada,)
    ).fetchall()
    if not filas:
        return None, None
    # Coincidencia exacta con el grupo derivado; si no, el grupo de liga regular
    grupo_norm = normalizar_nombre(grupo) if grupo else ''
    for g, pos in filas:
        if normalizar_nombre(g) == grupo_norm:
            return pos, g
    for g, pos in filas:
        if 'LIGA REGULAR' in g.upper():
            return pos, g
    return filas[0][1], filas[0][0]


def migrar(db_path: str = DB_PATH, dry_run: bool = False) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    partidos = conn.execute(
        "SELECT temporada, grupo_nombre, fase_tipo, estado, fecha, resultado_benicarlo"
        " FROM partidos ORDER BY temporada, fecha"
    ).fetchall()
    contexto = cargar_contexto()

    por_temporada = {}
    for r in partidos:
        por_temporada.setdefault(r['temporada'], []).append(r)

    filas = []
    for temporada in sorted(por_temporada):
        rows = por_temporada[temporada]
        jugados = [r for r in rows if r['estado'] == 'jugado']
        suspendidos = sum(1 for r in rows if r['estado'] == 'suspendido')
        programados = sum(1 for r in rows if r['estado'] == 'programado')

        balance_v = sum(1 for r in jugados if r['resultado_benicarlo'] == 'Victoria')
        balance_d = sum(1 for r in jugados if r['resultado_benicarlo'] == 'Derrota')
        fase = fase_alcanzada(rows)

        # Grupo de la última fase disputada (la 'temporada' de referencia)
        grupo = jugados[-1]['grupo_nombre'] if jugados else (rows[-1]['grupo_nombre'] if rows else None)

        # Derivado del desenlace, salvo que el curado diga otra cosa
        if suspendidos > 0:
            resultado_hito = 'cancelada'
        elif 'Playoff' in fase:
            resultado_hito = 'eliminado_playoff'
        elif programados > 0:
            resultado_hito = 'en_curso'
        else:
            resultado_hito = 'sin_hito'
        hito = ''

        pos, grupo_clasif = posicion_en_clasificacion(conn, temporada, grupo)
        fuente = 'feb' if pos is not None else 'manual'

        curado = contexto.get(temporada, {})
        competicion = curado.get('competicion')
        hito = curado.get('hito', hito)
        resultado_hito = curado.get('resultado_hito', resultado_hito)
        if curado:
            fuente = 'feb+manual' if fuente == 'feb' else 'manual'

        filas.append({
            'temporada': temporada,
            'competicion': competicion,
            'grupo': grupo_clasif or grupo,
            'fase_alcanzada': fase,
            'posicion_grupo': pos,
            'hito': hito,
            'resultado_hito': resultado_hito,
            'balance_v': balance_v,
            'balance_d': balance_d,
            'fuente': fuente,
        })

    # --- Vista previa ------------------------------------------------------
    print(f"{'temporada':>9} {'competición':<12} {'grupo':<28} {'pos':>4} {'bal.':>7} {'fase':<28} {'hito'}")
    for f in filas:
        print(f"{f['temporada']:>9} {str(f['competicion']):<12} {str(f['grupo'])[:28]:<28} "
              f"{str(f['posicion_grupo'] or '-'):>4} {f['balance_v']}-{f['balance_d']:<4} "
              f"{f['fase_alcanzada'][:28]:<28} {f['hito']}")

    if dry_run:
        print("\n--dry-run: no se escriben cambios.")
        conn.close()
        return

    conn.execute("DELETE FROM temporadas")
    conn.executemany("""
        INSERT INTO temporadas (
            temporada, competicion, grupo, fase_alcanzada, posicion_grupo,
            hito, resultado_hito, balance_v, balance_d, fuente
        ) VALUES (
            :temporada, :competicion, :grupo, :fase_alcanzada, :posicion_grupo,
            :hito, :resultado_hito, :balance_v, :balance_d, :fuente
        )
    """, filas)
    conn.commit()
    conn.close()
    exportar_sqlite_a_archivos(db_path)
    print(f"\nTabla 'temporadas' escrita con {len(filas)} filas.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Construye el contexto de liga por temporada")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    migrar(args.db, args.dry_run)
