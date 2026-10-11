"""Tests unitarios de las funciones puras del scraper y del saneado de texto."""
import scraper
from bs4 import BeautifulSoup


class TestCleanText:
    def test_none_y_vacio(self):
        assert scraper.clean_text(None) == ""
        assert scraper.clean_text("") == ""
        assert scraper.clean_text("   ") == ""

    def test_espacios_irrompibles_y_multiples(self):
        assert scraper.clean_text("AMICS\xa0\xa0CASTELLÓ") == "AMICS CASTELLÓ"
        assert scraper.clean_text("  a   b  ") == "a b"

    def test_mojibake_reparado(self):
        # UTF-8 real decodificado como latin-1 (bug histórico de FEB)
        assert scraper.clean_text("AMICS CASTELLÃ\x93") == "AMICS CASTELLÓ"

    def test_idempotente_con_texto_sano(self):
        sano = "MADERAS SORLI BENICARLÓ"
        assert scraper.clean_text(sano) == sano


class TestParseShot:
    def test_formato_acta(self):
        assert scraper.parse_shot("3/5 60%") == (3, 5, 60.0)

    def test_cero_intentos(self):
        assert scraper.parse_shot("0/0 0%") == (0, 0, 0.0)

    def test_sin_formato(self):
        assert scraper.parse_shot("—") == (0, 0, 0.0)
        assert scraper.parse_shot("") == (0, 0, 0.0)

    def test_redondeo_un_decimal(self):
        made, att, pct = scraper.parse_shot("2/3 66.7%")
        assert (made, att) == (2, 3)
        assert pct == round(2 / 3 * 100, 1)


class TestParseInt:
    def test_basico(self):
        assert scraper.parse_int("24") == 24
        assert scraper.parse_int("+3") == 3
        assert scraper.parse_int(" 7 ") == 7

    def test_default(self):
        assert scraper.parse_int("N/D") == 0
        assert scraper.parse_int("", default=-1) == -1


class TestGetPostData:
    def test_formulario_aspnet(self):
        html = """
        <html><form>
          <input id="__VIEWSTATE" value="VS123">
          <input id="__VIEWSTATEGENERATOR" value="GEN456">
          <input id="__EVENTVALIDATION" value="EV789">
        </form></html>
        """
        data = scraper.get_post_data(BeautifulSoup(html, "html.parser"),
                                     "_ctl0$jornadasDropDownList",
                                     {"_ctl0:temporadasDropDownList": "2025"})
        assert data["__EVENTTARGET"] == "_ctl0$jornadasDropDownList"
        assert data["__VIEWSTATE"] == "VS123"
        assert data["__EVENTVALIDATION"] == "EV789"
        assert data["_ctl0:temporadasDropDownList"] == "2025"

    def test_formulario_sin_campos_ocultos(self):
        data = scraper.get_post_data(BeautifulSoup("<html></html>", "html.parser"),
                                     "target", {})
        assert data["__VIEWSTATE"] == ""


class TestFetchHtml:
    """El bug P1: FEB sirve UTF-8 sin declarar charset y requests cae a latin-1."""

    class _Respuesta:
        def __init__(self, contenido: bytes, text_latin: str):
            self.content = contenido
            self.text = text_latin

    class _Sesion:
        def __init__(self, respuesta):
            self._r = respuesta

        def get(self, url, timeout=30):
            return self._r

    def test_utf8_valido_se_decodifica_como_utf8(self):
        bytes_html = "MADERAS SORLI BENICARLÓ".encode("utf-8")
        # Si requests decodificara como latin-1, daría mojibake: lo simulamos
        resp = self._Respuesta(bytes_html, bytes_html.decode("latin-1"))
        assert scraper.fetch_html(self._Sesion(resp), "http://x") == "MADERAS SORLI BENICARLÓ"

    def test_fallback_a_text_si_no_es_utf8(self):
        bytes_html = "año".encode("latin-1")  # no válido como UTF-8
        resp = self._Respuesta(bytes_html, "año")
        assert scraper.fetch_html(self._Sesion(resp), "http://x") == "año"
