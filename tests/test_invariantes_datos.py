"""Invariantes de integridad sobre las exportaciones (parquet) que consume la app.

Complementa a scripts/qa_reconcile.py (que trabaja sobre SQLite): aquí se
verifica que el EXPORT que lee la app conserva las invariantes.
"""
import os

import pandas as pd
import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@pytest.fixture(scope="module")
def datos():
    def leer(nombre):
        return pd.read_parquet(os.path.join(BASE, "data", f"{nombre}.parquet"))
    return {n: leer(n) for n in ("partidos", "cuartos", "jugadores",
                                 "equipos_catalogo", "jugadores_catalogo")}


class TestPartidos:
    def test_cobertura_conocida(self, datos):
        # 234 partidos (8 temporadas, 2019/2020 a 2026/2027)
        assert len(datos["partidos"]) == 234

    def test_ids_unicos(self, datos):
        assert datos["partidos"]["partido_id"].is_unique

    def test_estados_validos(self, datos):
        assert set(datos["partidos"]["estado"].unique()) <= {"jugado", "programado", "suspendido"}

    def test_marcador_coherente_con_condicion(self, datos):
        p = datos["partidos"]
        jugados = p[p["jugado"] == 1]
        es_local = jugados["es_benicarlo_local"] == 1
        assert (jugados.loc[es_local, "puntos_benicarlo"] == jugados.loc[es_local, "puntos_local"]).all()
        assert (jugados.loc[~es_local, "puntos_benicarlo"] == jugados.loc[~es_local, "puntos_visitante"]).all()

    def test_diferencia_y_resultado_consistentes(self, datos):
        p = datos["partidos"]
        jugados = p[p["jugado"] == 1]
        assert (jugados["diferencia_puntos"] == jugados["puntos_benicarlo"] - jugados["puntos_rival"]).all()
        v = jugados["diferencia_puntos"] > 0
        assert (jugados.loc[v, "resultado_benicarlo"] == "Victoria").all()
        assert (jugados.loc[~v, "resultado_benicarlo"] == "Derrota").all()

    def test_programados_sin_marcador(self, datos):
        prog = datos["partidos"][datos["partidos"]["estado"] == "programado"]
        assert (prog["jugado"] == 0).all()


class TestCuartos:
    def test_parciales_suman_total(self, datos):
        c = datos["cuartos"]
        suma = c[["q1", "q2", "q3", "q4"]].sum(axis=1) + c.get("ot1", 0) + c.get("ot2", 0)
        assert (suma == c["puntos_total"]).all()

    def test_cuartos_cuadran_con_marcador_en_partidos_ok(self, datos):
        c = datos["cuartos"].merge(
            datos["partidos"][["partido_id", "qa_estado"]], on="partido_id")
        ok = c[c["qa_estado"] == "ok"]
        assert not ok.empty
        totales = ok.groupby(["partido_id", "es_benicarlo"])["puntos_total"].sum().unstack()
        partidos = datos["partidos"].set_index("partido_id")
        for pid, fila in totales.iterrows():
            p = partidos.loc[pid]
            esperado = (p["puntos_benicarlo"], p["puntos_rival"])
            # es_benicarlo identifica al club sea local o visitante
            par = (fila.get(1, 0), fila.get(0, 0))
            assert par == esperado, f"partido {pid}: {par} != {esperado}"


class TestJugadores:
    def test_acta_suma_marcador_en_partidos_ok(self, datos):
        j = datos["jugadores"].merge(
            datos["partidos"][["partido_id", "qa_estado"]], on="partido_id")
        ok = j[j["qa_estado"] == "ok"]
        assert not ok.empty
        por_partido = ok[ok["es_benicarlo"] == 1].groupby("partido_id")["puntos"].sum()
        marcador = datos["partidos"].set_index("partido_id")["puntos_benicarlo"]
        for pid, suma in por_partido.items():
            assert suma == marcador.loc[pid], f"partido {pid}: acta {suma} != {marcador.loc[pid]}"

    def test_rebotes_totales_coherentes(self, datos):
        j = datos["jugadores"]
        assert (j["rebotes_totales"] == j["rebotes_ofensivos"] + j["rebotes_defensivos"]).all()

    def test_titulares_max_cinco_por_equipo(self, datos):
        # el acta FEB puede traer huecos, pero nunca más de 5 titulares
        por_partido = datos["jugadores"].groupby(["partido_id", "equipo"])["es_titular"].sum()
        assert (por_partido <= 5).all()

    def test_ids_canonicos_existen_en_catalogo(self, datos):
        ids_eq = set(datos["equipos_catalogo"]["equipo_id"])
        ids_jug = set(datos["jugadores_catalogo"]["jugador_id"])
        assert datos["jugadores"]["equipo_id"].isin(ids_eq).all()
        assert datos["jugadores"]["jugador_id"].isin(ids_jug).all()

    def test_el_club_tiene_id_canonico_unico(self, datos):
        beni = datos["jugadores"][datos["jugadores"]["es_benicarlo"] == 1]
        assert beni["equipo_id"].nunique() == 1
