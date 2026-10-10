#!/usr/bin/env python3
"""Migración P1.2 — reconciliación y QA de datos.

Comprueba la consistencia entre las tres fuentes de verdad de un partido:

  C1  cuartos.puntos_total == q1+q2+q3+q4+ot1+ot2      (campo derivado)
  C2  suma de cuartos por equipo  == marcador           (parciales vs resultado)
  C3  suma de puntos de jugadores == marcador           (acta vs resultado)
  C4  diferencia_puntos / resultado_benicarlo coherentes con el marcador
  C5  partidos jugados sin cuartos y/o sin acta de jugadores
  C6  filas de cuartos duplicadas por partido+equipo

--fix aplica ÚNICAMENTE correcciones deterministas (nunca inventa datos):
  - recalcula campos derivados (C1, C4);
  - en partidos con prórroga cuyos parciales no registran los puntos de la
    prórroga (empate al final del reglamento), los atribuye a ot1 y lo deja
    documentado en el informe (el desglose por prórroga solo puede obtenerse
    re-scrapeando con el parser actualizado);
  - marca partidos.qa_estado con el problema detectado (ok / descuadre_cuartos
    / descuadre_jugadores / sin_acta) para que la app los señale.

Los descuadres de actas (C3) NO se corrigen a mano: se marcan y se recomienda
re-scrape: `python scraper.py --seasons <códigos>`.

Uso:
    .venv/bin/python scripts/qa_reconcile.py            # solo informe
    .venv/bin/python scripts/qa_reconcile.py --fix      # aplica correcciones
"""

import argparse
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_utils import (  # noqa: E402
    DB_PATH,
    QA_DESCUADRE_CUARTOS,
    QA_DESCUADRE_JUGADORES,
    QA_OK,
    QA_SIN_ACTA,
    exportar_sqlite_a_archivos,
)

INFORME_PATH = os.path.join(os.path.dirname(DB_PATH), "informe_qa.csv")


def cargar(conn):
    partidos = {
        r[0]: r
        for r in conn.execute(
            "SELECT partido_id, temporada, fecha, equipo_local, equipo_visitante,"
            " puntos_local, puntos_visitante, puntos_benicarlo, puntos_rival,"
            " diferencia_puntos, resultado_benicarlo, jugado FROM partidos"
        )
    }
    cuartos = conn.execute(
        "SELECT id, partido_id, equipo, es_benicarlo, q1, q2, q3, q4, ot1, ot2, puntos_total FROM cuartos"
    ).fetchall()
    jugadores = conn.execute(
        "SELECT partido_id, equipo, es_benicarlo, jugador, minutos, puntos FROM jugadores_partido"
    ).fetchall()
    return partidos, cuartos, jugadores


def revisar(conn, aplicar_fix: bool) -> int:
    partidos, cuartos, jugadores = cargar(conn)
    incidencias = []  # (partido_id, temporada, check, detalle, diferencia, accion)
    fix_pendientes = []  # (sql, params)
    qa_estado = {pid: QA_OK for pid in partidos}

    # --- C1: campo derivado puntos_total -----------------------------------
    for id_, pid, equipo, es_beni, q1, q2, q3, q4, ot1, ot2, total in cuartos:
        calculado = (q1 or 0) + (q2 or 0) + (q3 or 0) + (q4 or 0) + (ot1 or 0) + (ot2 or 0)
        if calculado != (total or 0):
            temporada = partidos.get(pid, [None, "?"])[1]
            incidencias.append((pid, temporada, "C1_cuartos_total",
                                f"{equipo}: puntos_total={total} pero los periodos suman {calculado}",
                                calculado - (total or 0), "recalcular puntos_total"))
            fix_pendientes.append(("UPDATE cuartos SET puntos_total = ? WHERE id = ?", (calculado, id_)))

    # --- C2: parciales por equipo vs marcador -------------------------------
    suma_cuartos = {}
    for _, pid, equipo, es_beni, q1, q2, q3, q4, ot1, ot2, _total in cuartos:
        clave = (pid, es_beni)
        suma_cuartos.setdefault(clave, {"equipo": equipo, "reglamento": 0, "prorroga": 0})
        suma_cuartos[clave]["reglamento"] += (q1 or 0) + (q2 or 0) + (q3 or 0) + (q4 or 0)
        suma_cuartos[clave]["prorroga"] += (ot1 or 0) + (ot2 or 0)

    for pid, p in partidos.items():
        if (p[11] or 0) != 1:  # solo jugados
            continue
        marcador = {1: p[7] or 0, 0: p[8] or 0}  # es_benicarlo -> puntos
        for es_beni in (1, 0):
            datos = suma_cuartos.get((pid, es_beni))
            if datos is None:
                continue
            total_parciales = datos["reglamento"] + datos["prorroga"]
            dif = marcador[es_beni] - total_parciales
            if dif == 0:
                continue
            temporada = p[1]
            if dif > 0 and datos["prorroga"] == 0:
                # ¿empate al final del reglamento en ambos equipos? -> faltan prórrogas
                otro = suma_cuartos.get((pid, 1 - es_beni))
                if otro and otro["reglamento"] == datos["reglamento"] and otro["prorroga"] == 0:
                    incidencias.append((pid, temporada, "C2_prorroga_sin_registrar",
                                        f"{datos['equipo']}: faltan {dif} pts de prórroga (empate {datos['reglamento']}-{otro['reglamento']} en reglamento)",
                                        dif, "atribuir a ot1"))
                    fix_pendientes.append(
                        ("UPDATE cuartos SET ot1 = COALESCE(ot1,0) + ?, puntos_total = puntos_total + ? WHERE partido_id = ? AND es_benicarlo = ?",
                         (dif, dif, pid, es_beni))
                    )
                    continue
            incidencias.append((pid, temporada, "C2_cuartos_vs_marcador",
                                f"{datos['equipo']}: parciales suman {total_parciales}, marcador {marcador[es_beni]}",
                                -dif, "revisar/re-scrapear"))
            if pid in qa_estado and qa_estado[pid] == QA_OK:
                qa_estado[pid] = QA_DESCUADRE_CUARTOS

    # --- C3: puntos de jugadores vs marcador --------------------------------
    suma_jug = {}
    for pid, equipo, es_beni, jugador, minutos, puntos in jugadores:
        clave = (pid, es_beni)
        suma_jug.setdefault(clave, {"equipo": equipo, "puntos": 0, "n": 0})
        suma_jug[clave]["puntos"] += puntos or 0
        suma_jug[clave]["n"] += 1

    for pid, p in partidos.items():
        if (p[11] or 0) != 1:
            continue
        marcador = {1: p[7] or 0, 0: p[8] or 0}
        for es_beni in (1, 0):
            datos = suma_jug.get((pid, es_beni))
            if datos is None:
                continue
            dif = marcador[es_beni] - datos["puntos"]
            if dif != 0:
                incidencias.append((pid, p[1], "C3_acta_vs_marcador",
                                    f"{datos['equipo']}: acta suma {datos['puntos']} en {datos['n']} jugadores, marcador {marcador[es_beni]}",
                                    dif, "re-scrapear acta"))
                if qa_estado.get(pid) == QA_OK:
                    qa_estado[pid] = QA_DESCUADRE_JUGADORES

    # --- C4: campos derivados del partido -----------------------------------
    for pid, p in partidos.items():
        if (p[11] or 0) != 1:
            continue
        dif_calculada = (p[7] or 0) - (p[8] or 0)
        resultado = "Victoria" if dif_calculada > 0 else "Derrota"
        if p[9] != dif_calculada or p[10] != resultado:
            incidencias.append((pid, p[1], "C4_campos_derivados",
                                f"diferencia_puntos={p[9]} resultado={p[10]} (deberían ser {dif_calculada} / {resultado})",
                                dif_calculada, "recalcular"))
            fix_pendientes.append(
                ("UPDATE partidos SET diferencia_puntos = ?, resultado_benicarlo = ? WHERE partido_id = ?",
                 (dif_calculada, resultado, pid))
            )

    # --- C5: partidos jugados sin parciales y/o sin acta ----------------------
    con_cuartos = {c[1] for c in cuartos}
    con_jugadores = {j[0] for j in jugadores}
    for pid, p in partidos.items():
        if (p[11] or 0) != 1:
            continue
        faltan = []
        if pid not in con_cuartos:
            faltan.append("parciales")
        if pid not in con_jugadores:
            faltan.append("acta de jugadores")
        if faltan:
            incidencias.append((pid, p[1], "C5_sin_datos", "faltan: " + ", ".join(faltan), 0, "re-scrapear"))
            if qa_estado.get(pid) == QA_OK:
                qa_estado[pid] = QA_SIN_ACTA

    # --- C6: duplicados de cuartos ------------------------------------------
    vistos = set()
    for _, pid, equipo, es_beni, *_rest in cuartos:
        clave = (pid, es_beni)
        if clave in vistos:
            incidencias.append((pid, partidos.get(pid, [None, "?"])[1], "C6_duplicados",
                                f"más de una fila de cuartos para {equipo}", 0, "revisar"))
        vistos.add(clave)

    # --- C7/C8/C9: contexto de liga por temporada (P2 · punto 5) ------------
    temporadas_en_datos = sorted({p[1] for p in partidos.values()})
    try:
        ctx_rows = conn.execute(
            "SELECT temporada, balance_v, balance_d FROM temporadas"
        ).fetchall()
    except sqlite3.OperationalError:
        ctx_rows = []
    en_contexto = {t for (t, _bv, _bd) in ctx_rows}

    for temporada in temporadas_en_datos:
        if temporada not in en_contexto:
            incidencias.append((0, temporada, "C8_temporada_sin_contexto",
                                "falta la fila de contexto en la tabla 'temporadas'",
                                0, "ejecutar migrate_liga"))

    bal_real = {}
    for _pid, p in partidos.items():
        if (p[11] or 0) != 1:
            continue
        v, d = bal_real.get(p[1], (0, 0))
        bal_real[p[1]] = (v + 1, d) if p[10] == 'Victoria' else (v, d + 1)
    for temporada, bv, bd in ctx_rows:
        real = bal_real.get(temporada, (0, 0))
        if (bv or 0) != real[0] or (bd or 0) != real[1]:
            incidencias.append((0, temporada, "C7_temporada_balance",
                                f"temporadas dice {bv}-{bd}, los partidos {real[0]}-{real[1]}",
                                0, "re-ejecutar migrate_liga"))

    try:
        cl_rows = conn.execute(
            "SELECT DISTINCT temporada FROM clasificacion WHERE es_benicarlo = 1"
        ).fetchall()
    except sqlite3.OperationalError:
        cl_rows = []
    con_clasificacion = {t for (t,) in cl_rows}
    for temporada in temporadas_en_datos:
        if temporada not in con_clasificacion:
            incidencias.append((0, temporada, "C9_clasificacion_faltante",
                                "sin clasificación oficial para el Benicarló",
                                0, "scraper --solo-clasificacion"))

    # --- C10: fecha nula -> derivar de la fecha de la jornada ----------------
    # La jornada lleva su fecha nominal ("Jornada 25(11/04/2026)"), que NO
    # siempre coincide con la real del partido (la ficha puede moverse un día,
    # p. ej. 12/04/2026). Se usa como aproximación y se recomienda re-scrape:
    # el parser actual toma la fecha exacta de la etiqueta de la ficha.
    sin_fecha = conn.execute(
        "SELECT partido_id, temporada, jornada_nombre FROM partidos"
        " WHERE fecha IS NULL OR fecha = ''"
    ).fetchall()
    for pid, temporada, jornada in sin_fecha:
        m = re.search(r'\((\d{2})/(\d{2})/(\d{4})\)', jornada or '')
        if m:
            d, mo, y = m.groups()
            nueva_fecha = f"{y}-{mo}-{d}"
            incidencias.append((pid, temporada, "C10_fecha_nula",
                                f"fecha vacía; nominal de la jornada: {nueva_fecha} "
                                f"(la fecha exacta requiere re-scrape)",
                                0, "aproximación de jornada"))
            fix_pendientes.append(
                ("UPDATE partidos SET fecha = ? WHERE partido_id = ?", (nueva_fecha, pid))
            )
        else:
            incidencias.append((pid, temporada, "C10_fecha_nula",
                                "fecha vacía y la jornada no aporta fecha",
                                0, "re-scrapear"))

    # --- Informe ------------------------------------------------------------
    print(f"\nIncidencias encontradas: {len(incidencias)}")
    if incidencias:
        print(f"{'partido':>9} {'temporada':>9} {'check':<26} {'dif':>5}  detalle")
        for pid, temporada, check, detalle, dif, accion in incidencias:
            print(f"{pid:>9} {str(temporada):>9} {check:<26} {dif:>5}  {detalle}  [{accion}]")

    resumen_qa = {}
    for pid, estado in qa_estado.items():
        resumen_qa[estado] = resumen_qa.get(estado, 0) + 1
    print("\nqa_estado resultante por partido:")
    for estado, n in sorted(resumen_qa.items()):
        print(f"  {estado:22s}: {n}")

    if not aplicar_fix:
        print("\nSin --fix: no se escribe nada. Ejecuta con --fix para aplicar correcciones.")
        return len(incidencias)

    # --- Aplicar ------------------------------------------------------------
    for sql, params in fix_pendientes:
        conn.execute(sql, params)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS partidos_qa (partido_id INTEGER PRIMARY KEY, qa_estado TEXT)"
    )
    conn.execute("DELETE FROM partidos_qa")
    conn.executemany(
        "INSERT INTO partidos_qa (partido_id, qa_estado) VALUES (?, ?)",
        list(qa_estado.items()),
    )
    # Mantener también la copia desnormalizada en partidos
    cols = [r[1] for r in conn.execute("PRAGMA table_info(partidos)")]
    if "qa_estado" not in cols:
        conn.execute("ALTER TABLE partidos ADD COLUMN qa_estado TEXT DEFAULT 'ok'")
    conn.executemany(
        "UPDATE partidos SET qa_estado = ? WHERE partido_id = ?",
        [(estado, pid) for pid, estado in qa_estado.items()],
    )
    conn.commit()

    # Informe CSV
    with open(INFORME_PATH, "w", encoding="utf-8") as fh:
        fh.write("partido_id,temporada,check,diferencia,accion,detalle\n")
        for pid, temporada, check, detalle, dif, accion in incidencias:
            detalle_csv = '"' + str(detalle).replace('"', "'") + '"'
            fh.write(f"{pid},{temporada},{check},{dif},{accion},{detalle_csv}\n")
    print(f"\nCorrecciones aplicadas: {len(fix_pendientes)}")
    print(f"Informe guardado en: {INFORME_PATH}")
    return len(incidencias)


def main():
    ap = argparse.ArgumentParser(description="QA de reconciliación de datos")
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--fix", action="store_true", help="aplica correcciones deterministas")
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    try:
        revisar(conn, args.fix)
    finally:
        conn.close()
    if args.fix:
        exportar_sqlite_a_archivos(args.db)


if __name__ == "__main__":
    main()
