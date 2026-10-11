"""Helpers de composición HTML compartidos por las vistas."""
import re

def _html_plano(html):
    """HTML a sangre cero: st.markdown interpreta como código cualquier
    bloque con 4+ espacios de indentación."""
    return "\n".join(line.strip() for line in html.strip().splitlines())

def truncar_nombre(nombre, max_len=18):
    """Etiqueta corta para ejes de gráfica; el nombre completo se muestra
    en el tooltip y en la tabla, y en móvil un nombre largo aplasta el área
    útil de la gráfica."""
    nombre = str(nombre)
    return nombre if len(nombre) <= max_len else nombre[:max_len - 1].rstrip() + '…'

def hito_badge(resultado_hito, fase_alcanzada=''):
    """(clase_css, texto) del badge de hito de temporada, o (None, '')."""
    etiquetas = {
        'ascenso': 'ASCENSO',
        'campeon': 'CAMPEÓN',
        'permanencia': 'PERMANENCIA',
        'cancelada': 'CANCELADA',
        'en_curso': 'EN CURSO',
    }
    if resultado_hito == 'eliminado_playoff':
        m = re.search(r'1/\d+', fase_alcanzada or '')
        ronda = m.group(0) if m else 'FINAL'
        return f"hito-{resultado_hito}", f"ELIMINADO EN {ronda}"
    if resultado_hito in etiquetas:
        return f"hito-{resultado_hito}", etiquetas[resultado_hito]
    return None, ''
