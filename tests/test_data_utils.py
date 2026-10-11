"""Tests de data_utils: derivación de estado, alias y reparación de encoding."""
from datetime import date

from data_utils import derivar_estado, normalizar_nombre, reparar_texto, cargar_alias
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDerivarEstado:
    def test_jugado_manda_sobre_todo(self):
        # jugado aunque la fecha sea futura (datos anómalos): el acta manda
        assert derivar_estado(1, "2999-01-01") == "jugado"

    def test_sin_jugar_fecha_pasada_es_suspendido(self):
        # ej. los 9 partidos de 2019/2020 cancelados por COVID
        assert derivar_estado(0, "2020-03-01", hoy=date(2026, 10, 11)) == "suspendido"

    def test_sin_jugar_fecha_futura_es_programado(self):
        assert derivar_estado(0, "2999-01-01", hoy=date(2026, 10, 11)) == "programado"

    def test_sin_jugar_sin_fecha_es_programado(self):
        assert derivar_estado(0, None, hoy=date(2026, 10, 11)) == "programado"

    def test_jugado_otros_tipos(self):
        assert derivar_estado(True, None) == "jugado"
        assert derivar_estado("1", None) == "jugado"
        assert derivar_estado(None, None) == "programado"


class TestRepararTexto:
    def test_casos_reales_feb(self):
        assert reparar_texto("AMICS CASTELLÃ\x93") == "AMICS CASTELLÓ"

    def test_texto_sano_intacto(self):
        assert reparar_texto("CB Benicarló") == "CB Benicarló"
        assert reparar_texto("REINA PROTEÍNAS CLAVIJO") == "REINA PROTEÍNAS CLAVIJO"

    def test_no_string(self):
        assert reparar_texto(None) is None
        assert reparar_texto(42) == 42

    def test_idempotente(self):
        roto = "LA SALUD CARTAGENA C.B.Ã“"
        una_vez = reparar_texto(roto)
        assert reparar_texto(una_vez) == una_vez


class TestNormalizarNombre:
    def test_mayusculas_e_ignora_puntuacion(self):
        # puntos/comas -> espacios: 'C.B.' y 'CB' normalizan distinto, por eso
        # el catálogo guarda alias con ambas grafías
        assert normalizar_nombre("cb benicarlo") == "CB BENICARLO"
        assert normalizar_nombre("C.B.  BENICARLO") == "C B BENICARLO"

    def test_acentos_ignorados(self):
        assert normalizar_nombre("BENICARLÓ") == "BENICARLO"


class TestCargarAlias:
    def test_alias_reales_del_club(self):
        mapa = cargar_alias(os.path.join(BASE, "data", "alias_equipos.json"))
        assert mapa.get(normalizar_nombre("CB Benicarló")) == "cb-benicarlo"
        # Los 4 nombres históricos del club resuelven al mismo id
        ids = {mapa.get(normalizar_nombre(a))
               for a in ("C.B. BENICARLO", "MADERAS SORLI BENICARLO")}
        assert ids == {"cb-benicarlo"}

    def test_fichero_inexistente(self):
        assert cargar_alias("/no/existe.json") == {}

    def test_claves_internas_ignoradas(self, tmp_path):
        fichero = tmp_path / "alias.json"
        fichero.write_text(
            '{"_nota": "interno", "x1": {"nombre_canonico": "Equipo Uno"}}',
            encoding="utf-8")
        mapa = cargar_alias(str(fichero))
        assert normalizar_nombre("equipo uno") in mapa
        assert "_nota" not in mapa
