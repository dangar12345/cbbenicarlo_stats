import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import re

from data_utils import derivar_estado

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="CB Benicarló | Analytics Hub",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- SECRETOS (despliegue público) ---
# La app es pública; lo que se protege son los FICHEROS del repo: los parquet
# viajan cifrados (data/enc/) y la clave DATA_KEY solo vive en Secrets (Cloud)
# o en el secrets.toml local. Nadie puede descargar los datos desde GitHub.
def _secreto(nombre):
    """Lee un secreto de st.secrets (Cloud) o del entorno (local)."""
    try:
        if nombre in st.secrets:
            return st.secrets[nombre]
    except Exception:
        pass  # sin secrets.toml configurado
    return os.environ.get(nombre)

# --- CUSTOM CSS (HIGH CONTRAST & IMPECCABLE CRAFT) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Chivo:ital,wght@0,300..900;1,300..900&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, .stApp {
        font-family: 'Chivo', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #F8FAFC;
    }

    .stMarkdown, .stMarkdown p, label {
        font-family: 'Chivo', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #F8FAFC !important;
    }

    /* Preserve Streamlit icon fonts */
    [data-testid="stIconMaterial"], .material-symbols-rounded, .material-symbols-outlined, [class*="material-symbols"] {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
        font-weight: normal !important;
    }

    .stApp {
        background-color: #080D1A;
    }

    /* Clean top header: eliminate black mismatch, hide unnecessary deploy button */
    header[data-testid="stHeader"] {
        background-color: #080D1A !important;
        border-bottom: 1px solid #1E293B !important;
    }

    .stDeployButton,
    div[data-testid="stAppDeployButton"] {
        display: none !important;
    }

    /* High-contrast three-dots menu popup */
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[data-baseweb="menu"] {
        background-color: #0F172A !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="menu"] li, div[data-baseweb="menu"] div, div[data-baseweb="menu"] span {
        color: #F8FAFC !important;
    }
    div[data-baseweb="menu"] li:hover {
        background-color: #1E293B !important;
    }

    /* Headings */
    h1, h2, h3, h4 {
        font-family: 'Chivo', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
        color: #FFFFFF !important;
    }

    /* Subtitles and captions with high contrast */
    .stCaption, caption {
        color: #CBD5E1 !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
    }

    /* High-contrast Metric Cards */
    .metric-container {
        background: #111A2E;
        border: 1px solid #233554;
        border-radius: 8px;
        padding: 18px 20px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
        height: 100%;
    }
    /* Para que height:100% funcione, toda la cadena de ancestros dentro de la
       fila de columnas debe tener altura definida (el DOM de Streamlit monta
       4-5 wrappers por elemento). */
    div[data-testid="stHorizontalBlock"] > div:has(.metric-container),
    div[data-testid="stHorizontalBlock"] > div:has(.metric-container) *:has(.metric-container) {
        height: 100%;
    }

    /* Fila de tarjetas con altura igualada (flex propio, sin wrappers) */
    .cards-row {
        display: flex;
        align-items: stretch;
        gap: 24px;
    }
    .cards-row .metric-container {
        flex: 1 1 0;
        height: auto; /* el height:100% base bloquea el stretch de flex */
    }
    .cards-row .scheduled-card {
        flex: 1 1 0;
    }
    @media (max-width: 720px) {
        .cards-row {
            flex-direction: column;
        }
    }
    .metric-label {
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #93C5FD;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 900;
        color: #FFFFFF;
        line-height: 1.1;
        font-feature-settings: "tnum" 1;
    }
    .metric-sub {
        font-size: 0.85rem;
        color: #E2E8F0;
        margin-top: 6px;
        font-weight: 500;
        font-feature-settings: "tnum" 1;
    }

    /* Scoreboard display */
    .scoreboard {
        background: #0F172A;
        border: 1px solid #3B82F6;
        border-radius: 12px;
        padding: 26px;
        margin-bottom: 24px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
    }
    .team-name {
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        color: #FFFFFF;
        min-width: 0;
        overflow-wrap: break-word;
        text-wrap: balance;
    }
    .team-score {
        font-size: 3.2rem;
        font-weight: 900;
        color: #FFFFFF;
        font-feature-settings: "tnum" 1;
    }
    /* Marcador en grid de filas fijas: los dos nombres comparten fila y los dos
       marcadores otra, así un nombre largo (3 líneas) no desplaza su cifra. */
    .sb-grid {
        display: grid;
        grid-template-columns: 1fr auto 1fr;
        grid-template-areas:
            "nameL dash nameR"
            "scoreL dash scoreR";
        column-gap: 12px;
        align-items: start;
        text-align: center;
    }
    .sb-name-l { grid-area: nameL; }
    .sb-name-r { grid-area: nameR; }
    .sb-score-l { grid-area: scoreL; }
    .sb-score-r { grid-area: scoreR; }
    .sb-dash {
        grid-area: dash;
        align-self: center;
        font-size: 2rem;
        font-weight: 300;
        color: #64748B;
        padding: 0 8px;
    }

    /* High-contrast Badges */
    .badge-win {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 6px;
        background: #047857;
        color: #ECFDF5 !important;
        font-size: 0.82rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-loss {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 6px;
        background: #B91C1C;
        color: #FEF2F2 !important;
        font-size: 0.82rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-pending {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 6px;
        background: #1D4ED8;
        color: #EFF6FF !important;
        font-size: 0.82rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Scheduled Match Card */
    .scheduled-card {
        background: #111A2E;
        border: 1px solid #2563EB;
        border-radius: 8px;
        padding: 16px;
        min-height: 145px;
    }
    .scheduled-jornada {
        font-size: 0.78rem;
        font-weight: 800;
        color: #60A5FA;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .scheduled-rival {
        font-size: 1.05rem;
        font-weight: 800;
        color: #FFFFFF;
        margin: 8px 0;
    }
    .scheduled-info {
        font-size: 0.85rem;
        color: #E2E8F0;
        font-weight: 500;
    }

    /* Dataframe high-contrast */
    div[data-testid="stDataFrame"] {
        border: 1px solid #334155;
        border-radius: 8px;
        background: #0F172A;
    }

    /* Sidebar customization */
    section[data-testid="stSidebar"] {
        background-color: #0A101F;
        border-right: 1px solid #1E293B;
    }
    section[data-testid="stSidebar"] hr {
        margin: 0.5rem 0 1rem 0;
    }

    /* Selectbox, Inputs, Radio */
    .stSelectbox label, .stTextInput label, .stRadio label {
        color: #F8FAFC !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
    }

    /* Form controls: consistent dark surface + visible hover/focus */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    textarea[data-testid="stTextInput"] {
        background-color: #0F172A !important;
        border: 1px solid #233554 !important;
        border-radius: 8px !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="input"] > div:hover,
    textarea[data-testid="stTextInput"]:hover {
        border-color: #3B82F6 !important;
    }
    div[data-baseweb="select"]:focus-within > div,
    div[data-baseweb="input"]:focus-within > div,
    textarea[data-testid="stTextInput"]:focus {
        border-color: #60A5FA !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25) !important;
    }
    div[data-baseweb="select"] svg {
        fill: #93C5FD !important;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        background: transparent !important;
        border-radius: 8px 8px 0 0 !important;
    }
    button[data-baseweb="tab"]:hover p {
        color: #93C5FD !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #60A5FA !important;
    }
    div[data-baseweb="tab-border"] {
        background-color: #2563EB !important;
    }

    /* Dataframe: dark surface, tight edges */
    div[data-testid="stDataFrame"] {
        overflow: hidden;
    }

    /* Plotly hover tooltips: readable regardless of theme merging */
    .hoverlayer .hovertext rect {
        fill: #0F172A !important;
        stroke: #3B82F6 !important;
    }
    .hoverlayer .hovertext text {
        fill: #F8FAFC !important;
        font-family: 'Chivo', sans-serif !important;
    }

    /* Browser surfaces: selection, caret, scrollbars, focus */
    ::selection {
        background: #2563EB;
        color: #FFFFFF;
    }
    input, textarea {
        caret-color: #60A5FA;
    }
    :focus-visible {
        outline: 2px solid #60A5FA;
        outline-offset: 2px;
    }
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #0A101F;
    }
    ::-webkit-scrollbar-thumb {
        background: #24344F;
        border-radius: 6px;
        border: 2px solid #0A101F;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #33507F;
    }
    html {
        scrollbar-color: #24344F #0A101F;
        scrollbar-width: thin;
    }

    /* Footer link-ish affordances */
    a {
        color: #60A5FA;
        text-underline-offset: 3px;
    }
    a:hover {
        color: #93C5FD;
    }

    /* P2 · Contexto de liga: tira de trayectoria por temporada */
    .tray-wrap {
        overflow-x: auto;
    }
    table.tray-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }
    .tray-table th {
        text-align: left;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        color: #93C5FD;
        font-weight: 800;
        padding: 8px 12px;
        border-top: none;
        border-left: none;
        border-right: none;
        border-bottom: 1px solid #233554;
    }
    .tray-table td {
        padding: 11px 12px;
        border-top: none;
        border-left: none;
        border-right: none;
        border-bottom: 1px solid #16233D;
        color: #CBD5E1;
        font-size: 0.875rem;
        vertical-align: middle;
    }
    .tray-table tbody tr:hover td {
        background: #0F172A;
    }
    .tray-table .c-temp {
        color: #FFFFFF;
        font-weight: 800;
        font-feature-settings: "tnum" 1;
    }
    .tray-table .c-meta {
        color: #94A3B8;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .tray-table .c-pos {
        color: #60A5FA;
        font-weight: 800;
        font-size: 1.05rem;
        text-align: right;
        font-feature-settings: "tnum" 1;
    }
    .tray-table .c-bal {
        text-align: right;
        font-feature-settings: "tnum" 1;
    }
    .tray-table .c-hito {
        color: #CBD5E1;
    }
    .tray-table .c-badge {
        text-align: right;
    }
    .tray-table .c-badge .hito-badge {
        white-space: nowrap;
    }
    .tray-table th.c-pos,
    .tray-table th.c-bal,
    .tray-table th.c-badge {
        text-align: right;
    }
    @media (max-width: 720px) {
        /* Filas como tarjetas: la tabla con anchos fijos no cabe en móvil.
           Ojo: el CSS de Streamlit fija display:table en <table>; sin
           !important los hijos bloque se envuelven en celdas anónimas y el
           layout colapsa. */
        .tray-table thead {
            display: none !important;
        }
        .tray-table,
        .tray-table tbody,
        .tray-table tr {
            display: block !important;
            width: 100% !important;
        }
        .tray-table tr {
            border: 1px solid #1E293B;
            border-radius: 8px;
            margin-bottom: 10px;
            padding: 8px 4px;
            box-sizing: border-box;
        }
        .tray-table tbody tr:hover td {
            background: transparent;
        }
        .tray-table td {
            display: flex !important;
            width: auto !important;
            border-bottom: none;
            padding: 4px 12px;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            text-align: right;
            font-size: 0.84rem;
        }
        .tray-table td::before {
            content: attr(data-label);
            color: #93C5FD;
            font-size: 0.68rem;
            letter-spacing: 0.05em;
            font-weight: 800;
            text-transform: uppercase;
            text-align: left;
            flex: 0 0 auto;
        }
        .tray-table td.c-temp {
            justify-content: flex-start;
            font-size: 1rem;
        }
        .tray-table td.c-temp::before {
            display: none;
        }
        .tray-table .c-meta {
            display: flex;
            white-space: normal;
        }
        .tray-table .c-badge {
            justify-content: space-between;
        }
    }
    .hito-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        white-space: nowrap;
    }
    .hito-ascenso, .hito-campeon {
        background: #047857;
        color: #ECFDF5;
    }
    .hito-eliminado_playoff {
        background: #1D4ED8;
        color: #EFF6FF;
    }
    .hito-permanencia {
        background: #B45309;
        color: #FFFBEB;
    }
    .hito-cancelada {
        background: #334155;
        color: #E2E8F0;
    }
    .hito-en_curso {
        background: rgba(37, 99, 235, 0.12);
        border: 1px solid #2563EB;
        color: #93C5FD;
    }

    /* Franja de contexto de liga bajo el marcador */
    .match-context {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        margin: 10px 0 4px 0;
        color: #94A3B8;
        font-size: 0.85rem;
    }
    .match-context .ctx-fase {
        color: #93C5FD;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.78rem;
    }
    /* Cada parte lleva su separador como sufijo con espacio irrompible: el
       "·" viaja con el texto y nunca empieza una línea al envolver. */
    .match-context .ctx-item {
        min-width: 0;
    }

    /* Móvil: sin anclas de título ni modebar de Plotly (táctil, sin hover) */
    @media (max-width: 720px) {
        .stHeadingAnchor {
            display: none !important;
        }
        .modebar-container {
            display: none !important;
        }
        .team-name {
            font-size: 1.05rem;
        }
        .team-score {
            font-size: 2.5rem;
        }
        .scoreboard {
            padding: 18px 14px;
        }
        /* Columnas apiladas: aire real entre tarjetas (el gap por defecto de
           16px es menor que el padding interno y las cajas se ven pegadas) */
        div[data-testid="stHorizontalBlock"] {
            gap: 24px !important;
            row-gap: 24px !important;
        }
    }

    /* Tablet / ventanas estrechas: sin este mínimo, las filas de 4-5 tarjetas
       se aplastan en columnas de ~105-150px. Con mínimo de 280px envuelven a
       2 por fila y las filas de gráficas [3,2] mantienen su proporción. */
    @media (min-width: 641px) and (max-width: 1023px) {
        div[data-testid="stColumn"] {
            min-width: 280px !important;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 24px !important;
            row-gap: 24px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- DATA LOADERS ---
def _leer_parquet(nombre, data_dir):
    """Lee data/enc/<nombre>.parquet.enc (despliegue público, Fernet) o el
    parquet en claro (desarrollo local). El descifrado es en memoria: el repo
    nunca contiene los datos en claro y la clave vive solo en secrets/env."""
    ruta_enc = os.path.join(data_dir, "enc", f"{nombre}.parquet.enc")
    ruta_plano = os.path.join(data_dir, f"{nombre}.parquet")
    if os.path.exists(ruta_enc):
        clave = _secreto("DATA_KEY")
        if clave:
            import io
            from cryptography.fernet import Fernet
            with open(ruta_enc, "rb") as fh:
                blob = fh.read()
            return pd.read_parquet(io.BytesIO(Fernet(clave).decrypt(blob)))
        if os.path.exists(ruta_plano):
            return pd.read_parquet(ruta_plano)  # dev local sin secrets
        raise RuntimeError(
            "Los datos están cifrados (data/enc/) pero falta DATA_KEY. "
            "Configúralo en .streamlit/secrets.toml (local) o en Secrets "
            "(Community Cloud), o consulta scripts/encrypt_data.py."
        )
    return pd.read_parquet(ruta_plano)

@st.cache_data
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")

    partidos = _leer_parquet("partidos", data_dir)
    cuartos = _leer_parquet("cuartos", data_dir)
    jugadores = _leer_parquet("jugadores", data_dir)

    # Preprocessing
    partidos['fecha'] = pd.to_datetime(partidos['fecha'], errors='coerce')
    partidos['temporada_orden'] = partidos['temporada'].apply(lambda x: int(x.split('/')[0]))

    # Campo estado (P1): se deriva si la exportación aún no lo incluye
    if 'estado' not in partidos.columns:
        partidos['estado'] = [
            derivar_estado(j, f) for j, f in zip(partidos['jugado'], partidos['fecha'])
        ]
    if 'qa_estado' not in partidos.columns:
        partidos['qa_estado'] = 'ok'

    # Catálogos canónicos (opcionales hasta ejecutar scripts/migrate_ids.py)
    def _catalogo(nombre):
        try:
            return _leer_parquet(nombre, data_dir)
        except FileNotFoundError:
            return None

    cat_jugadores = _catalogo("jugadores_catalogo")
    cat_equipos = _catalogo("equipos_catalogo")
    df_temporadas = _catalogo("temporadas")

    # Nombres canónicos de jugador (fusiona alias/históricos en una sola ficha)
    if cat_jugadores is not None and 'jugador_id' in jugadores.columns:
        mapa = dict(zip(cat_jugadores['jugador_id'], cat_jugadores['nombre_canonico']))
        jugadores['jugador'] = jugadores['jugador_id'].map(mapa).fillna(jugadores['jugador'])

    return partidos, cuartos, jugadores, cat_jugadores, cat_equipos, df_temporadas

try:
    df_partidos, df_cuartos, df_jugadores, cat_jugadores, cat_equipos, df_temporadas = load_data()
except Exception as e:
    st.error(f"Error al cargar los datos desde 'data/': {e}")
    st.stop()

# --- SHARED CHART STYLING ---
HOVERLABEL = dict(
    bgcolor="#0F172A",
    bordercolor="#3B82F6",
    font=dict(family="Chivo", color="#F8FAFC", size=13),
)

def style_fig(fig, height=340, hovermode=None):
    """Dark transparent canvas + readable hover tooltips for every chart."""
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Chivo", color="#F8FAFC"),
        hoverlabel=HOVERLABEL,
        height=height,
    )
    if hovermode:
        fig.update_layout(hovermode=hovermode)
    return fig

def chart_kwargs():
    """Keep the figure's own dark template instead of Streamlit's light one."""
    return dict(theme=None, width="stretch")

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

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("""
<div style="padding: 12px 0 20px 0;">
    <div style="font-size: 1.45rem; font-weight: 900; color: #FFFFFF; letter-spacing: -0.02em;">
        CB BENICARLÓ
    </div>
    <div style="font-size: 0.8rem; font-weight: 700; color: #60A5FA; letter-spacing: 0.05em; text-transform: uppercase;">
        Analytics Hub · FEB (2019 - 2027)
    </div>
</div>
""", unsafe_allow_html=True)

nav_option = st.sidebar.radio(
    "Vistas del sistema",
    [
        "Resumen & Trayectoria",
        "Partidos & Boxscores",
        "Líderes & Jugadores",
        "Ficha & Comparador",
        "Análisis de Cuartos"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style="font-size: 0.82rem; color: #CBD5E1; line-height: 1.6;">
    📊 <b>{len(df_partidos):,}</b> Partidos en la base de datos<br>
    🏀 <b>{len(df_jugadores):,}</b> Registros de jugadores<br>
    ⏱️ <b>{df_partidos['temporada'].nunique()}</b> Temporadas cubiertas
</div>
""".replace(",", "."), unsafe_allow_html=True)

# ==============================================================================
# VIEW 1: RESUMEN & TRAYECTORIA
# ==============================================================================
if nav_option == "Resumen & Trayectoria":
    st.markdown("## Trayectoria Histórica del CB Benicarló")
    st.caption("Evolución de resultados, anotación y balance competitivo en Segunda FEB y LEB Plata.")

    partidos_played = df_partidos[df_partidos['estado'] == 'jugado'].copy()
    total_games = len(partidos_played)
    wins = len(partidos_played[partidos_played['resultado_benicarlo'] == 'Victoria'])
    losses = len(partidos_played[partidos_played['resultado_benicarlo'] == 'Derrota'])
    win_pct = (wins / total_games * 100) if total_games > 0 else 0
    
    pts_scored = partidos_played['puntos_benicarlo'].sum()
    pts_allowed = partidos_played['puntos_rival'].sum()
    avg_scored = (pts_scored / total_games) if total_games > 0 else 0
    avg_allowed = (pts_allowed / total_games) if total_games > 0 else 0
    diff_pts = pts_scored - pts_allowed
    pending_current = len(df_partidos[df_partidos['estado'] == 'programado'])

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    with kpi1:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Partidos Oficiales</div>
            <div class="metric-value">{total_games}</div>
            <div class="metric-sub">{pending_current} por jugar en 2026/2027</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi2:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Balance W / L</div>
            <div class="metric-value">{wins} - {losses}</div>
            <div class="metric-sub" style="color: #6EE7B7; font-weight: 700;">{win_pct:.1f}% de victorias</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi3:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Puntos a Favor (PPP)</div>
            <div class="metric-value">{avg_scored:.1f}</div>
            <div class="metric-sub">{pts_scored:,} puntos anotados</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi4:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Puntos en Contra (PPP)</div>
            <div class="metric-value">{avg_allowed:.1f}</div>
            <div class="metric-sub">{pts_allowed:,} puntos recibidos</div>
        </div>
        """, unsafe_allow_html=True)
    with kpi5:
        diff_color = "#34D399" if diff_pts >= 0 else "#F87171"
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Diferencial Neto</div>
            <div class="metric-value" style="color: {diff_color};">{diff_pts:+d}</div>
            <div class="metric-sub">{(diff_pts / total_games if total_games else 0):+.1f} pts / partido</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    col_graph1, col_graph2 = st.columns([3, 2])

    with col_graph1:
        st.markdown("### Victorias y Derrotas por Temporada")
        
        season_summary = partidos_played.groupby('temporada').agg(
            Victorias=('resultado_benicarlo', lambda x: (x == 'Victoria').sum()),
            Derrotas=('resultado_benicarlo', lambda x: (x == 'Derrota').sum()),
            Total=('partido_id', 'count')
        ).reset_index()

        fig_wl = go.Figure()
        fig_wl.add_trace(go.Bar(
            name='Victorias',
            x=season_summary['temporada'],
            y=season_summary['Victorias'],
            marker_color='#2563EB',
            text=season_summary['Victorias'],
            textposition='auto',
            textfont=dict(color='#FFFFFF'),
            hovertemplate='%{x}<br>Victorias: <b>%{y}</b><extra></extra>',
        ))
        fig_wl.add_trace(go.Bar(
            name='Derrotas',
            x=season_summary['temporada'],
            y=season_summary['Derrotas'],
            marker_color='#64748B',
            text=season_summary['Derrotas'],
            textposition='auto',
            textfont=dict(color='#FFFFFF'),
            hovertemplate='%{x}<br>Derrotas: <b>%{y}</b><extra></extra>',
        ))

        style_fig(fig_wl)
        fig_wl.update_layout(
            barmode='group',
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
            xaxis=dict(showgrid=False, tickfont=dict(color="#E2E8F0")),
            yaxis=dict(gridcolor="#1E293B", gridwidth=1, tickfont=dict(color="#E2E8F0")),
        )
        st.plotly_chart(fig_wl, **chart_kwargs())

    with col_graph2:
        st.markdown("### Anotación Promedio: Favor vs Contra")
        
        season_pts = partidos_played.groupby('temporada').agg(
            Puntos_Favor=('puntos_benicarlo', 'mean'),
            Puntos_Contra=('puntos_rival', 'mean')
        ).reset_index()
        season_pts['temporada_corta'] = season_pts['temporada'].str[2:4] + '/' + season_pts['temporada'].str[7:9]

        fig_pts = go.Figure()
        fig_pts.add_trace(go.Scatter(
            x=season_pts['temporada_corta'],
            y=season_pts['Puntos_Favor'],
            name='Puntos Favor',
            line=dict(color='#38BDF8', width=3),
            mode='lines+markers',
            customdata=season_pts['temporada'],
            hovertemplate='%{customdata}<br>Favor: <b>%{y:.1f}</b> pts<extra></extra>',
        ))
        fig_pts.add_trace(go.Scatter(
            x=season_pts['temporada_corta'],
            y=season_pts['Puntos_Contra'],
            name='Puntos Contra',
            line=dict(color='#F43F5E', width=2, dash='dot'),
            mode='lines+markers',
            customdata=season_pts['temporada'],
            hovertemplate='%{customdata}<br>Contra: <b>%{y:.1f}</b> pts<extra></extra>',
        ))

        style_fig(fig_pts, hovermode='x unified')
        fig_pts.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
            xaxis=dict(showgrid=False, tickfont=dict(color="#E2E8F0"), tickangle=0),
            yaxis=dict(gridcolor="#1E293B", gridwidth=1, tickfont=dict(color="#E2E8F0")),
        )
        st.plotly_chart(fig_pts, **chart_kwargs())

    # RENDIMIENTO LOCAL vs VISITANTE (P2 · split de condición)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("### Rendimiento Local vs Visitante")
    st.caption("Balance, anotación y diferencial según se juegue en casa o fuera.")

    split_seasons = ["Todas las temporadas"] + sorted(partidos_played['temporada'].unique().tolist(), reverse=True)
    sel_split = st.selectbox("Temporada", split_seasons, index=0, key="split_season")

    base_split = partidos_played
    if sel_split != "Todas las temporadas":
        base_split = base_split[base_split['temporada'] == sel_split]

    if base_split.empty:
        st.info(f"Sin partidos jugados en {sel_split}.")
    else:
        def _tarjeta_venue(df_venue, titulo):
            n = len(df_venue)
            v = int((df_venue['resultado_benicarlo'] == 'Victoria').sum())
            d = n - v
            pct = (v / n * 100) if n else 0.0
            pf = df_venue['puntos_benicarlo'].mean() if n else 0.0
            pc = df_venue['puntos_rival'].mean() if n else 0.0
            dif = pf - pc
            color = '#34D399' if dif >= 0 else '#F87171'
            return f"""
            <div class="metric-container">
                <div class="metric-label">{titulo} · {n} partidos</div>
                <div class="metric-value">{v} - {d} <span style="font-size: 1.1rem; color: #93C5FD;">{pct:.1f}% victorias</span></div>
                <div class="metric-sub">PPP a favor <b>{pf:.1f}</b> · PPP en contra <b>{pc:.1f}</b></div>
                <div class="metric-sub" style="color: {color}; font-weight: 700;">Diferencial: {dif:+.1f} pts / partido</div>
            </div>
            """

        casa_df = base_split[base_split['es_benicarlo_local'] == 1]
        fuera_df = base_split[base_split['es_benicarlo_local'] == 0]

        col_casa, col_fuera = st.columns(2)
        with col_casa:
            st.markdown(_tarjeta_venue(casa_df, "CASA"), unsafe_allow_html=True)
        with col_fuera:
            st.markdown(_tarjeta_venue(fuera_df, "FUERA"), unsafe_allow_html=True)

        # Narrativa: la ventaja de campo medida en puntos porcentuales
        if not casa_df.empty and not fuera_df.empty:
            pct_casa = (casa_df['resultado_benicarlo'] == 'Victoria').mean() * 100
            pct_fuera = (fuera_df['resultado_benicarlo'] == 'Victoria').mean() * 100
            delta = pct_casa - pct_fuera
            if abs(delta) < 1:
                txt = "Sin ventaja de campo apreciable: el porcentaje de victorias es prácticamente igual en casa y fuera."
            elif delta > 0:
                txt = (f"Ventaja de campo: {delta:.1f} puntos porcentuales más de victorias en casa "
                       f"({pct_casa:.1f}% en casa vs {pct_fuera:.1f}% fuera).")
            else:
                txt = (f"Ventaja de campo invertida: {abs(delta):.1f} puntos porcentuales más de victorias fuera "
                       f"({pct_fuera:.1f}% fuera vs {pct_casa:.1f}% en casa).")
            st.caption(txt)

    # ENFRENTAMIENTOS DIRECTOS (P2 · head-to-head por rival)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("### Enfrentamientos Directos")
    st.caption("Historial completo contra cada rival: balance, medias anotadoras y últimos cruces.")

    h2h_base = partidos_played.copy()
    if 'equipo_rival_id' in h2h_base.columns:
        h2h_base['_rival_id'] = h2h_base['equipo_rival_id'].fillna('')
    else:
        h2h_base['_rival_id'] = h2h_base['equipo_rival']
    # Nombre visible: la variante más frecuente del rival canónico
    nombres_rival = (h2h_base.groupby('_rival_id')['equipo_rival']
                     .agg(lambda s: s.value_counts().index[0]))
    h2h_base['_rival'] = h2h_base['_rival_id'].map(nombres_rival)

    conteo_rivales = h2h_base['_rival'].value_counts()
    opciones_rivales = sorted(h2h_base['_rival'].dropna().unique())
    sel_rival = st.selectbox(
        "Rival",
        opciones_rivales,
        index=opciones_rivales.index(conteo_rivales.index[0]),
        key="h2h_rival",
    )

    h2h = h2h_base[h2h_base['_rival'] == sel_rival].sort_values('fecha', ascending=False)
    if h2h.empty:
        st.info(f"No hay enfrentamientos registrados contra {sel_rival}.")
    else:
        n_h2h = len(h2h)
        v_h2h = int((h2h['resultado_benicarlo'] == 'Victoria').sum())
        d_h2h = n_h2h - v_h2h
        pct_h2h = v_h2h / n_h2h * 100
        pf_h2h = h2h['puntos_benicarlo'].mean()
        pc_h2h = h2h['puntos_rival'].mean()
        dif_h2h = pf_h2h - pc_h2h
        color_h2h = '#34D399' if dif_h2h >= 0 else '#F87171'
        ultimo = h2h.iloc[0]
        ult_fecha = ultimo['fecha'].strftime('%d/%m/%Y') if pd.notnull(ultimo['fecha']) else 'S/F'
        ult_txt = (f"{ult_fecha} · "
                   f"{int(ultimo['puntos_benicarlo'])}-{int(ultimo['puntos_rival'])} "
                   f"({ultimo['resultado_benicarlo'].lower()})")

        col_h2h_card, col_h2h_tabla = st.columns([2, 3])
        with col_h2h_card:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Historial vs {sel_rival}</div>
                <div class="metric-value">{v_h2h} - {d_h2h} <span style="font-size: 1.1rem; color: #93C5FD;">{pct_h2h:.1f}% victorias</span></div>
                <div class="metric-sub">PPP a favor <b>{pf_h2h:.1f}</b> · PPP en contra <b>{pc_h2h:.1f}</b></div>
                <div class="metric-sub" style="color: {color_h2h}; font-weight: 700;">Diferencial: {dif_h2h:+.1f} pts / partido</div>
                <div class="metric-sub">Último cruce: {ult_txt}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_h2h_tabla:
            st.markdown("### Últimos cruces")
            ultimos_h2h = h2h.head(8)
            tabla_h2h = pd.DataFrame({
                'Fecha': ultimos_h2h['fecha'].dt.strftime('%d/%m/%Y').fillna('S/F'),
                'Temporada': ultimos_h2h['temporada'],
                'Condición': np.where(ultimos_h2h['es_benicarlo_local'] == 1, 'Casa', 'Fuera'),
                'Marcador': ultimos_h2h.apply(
                    lambda r: f"{int(r['puntos_benicarlo'])} - {int(r['puntos_rival'])}", axis=1),
                'Resultado': ultimos_h2h['resultado_benicarlo'],
            })
            st.dataframe(tabla_h2h, hide_index=True, width="stretch")

    # NARRATIVA DE PARTIDO (P2 · cerrados, rachas y remontadas)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("### Narrativa de Partido")
    st.caption("Los partidos que se definen al final: cerrados (±5 pts), rachas y remontadas al descanso.")

    narr = partidos_played.sort_values(['fecha', 'partido_id']).copy()

    def _fmt_fecha(f):
        return f.strftime('%d/%m/%Y') if pd.notnull(f) else 'S/F'

    # --- Partidos cerrados (margen <= 5) ---
    cerrados = narr[narr['diferencia_puntos'].abs() <= 5]
    n_cer = len(cerrados)
    v_cer = int((cerrados['resultado_benicarlo'] == 'Victoria').sum())
    d_cer = n_cer - v_cer
    pct_cer = (v_cer / n_cer * 100) if n_cer else 0.0
    pf_cer = cerrados['puntos_benicarlo'].mean() if n_cer else 0.0
    pc_cer = cerrados['puntos_rival'].mean() if n_cer else 0.0
    dif_cer = pf_cer - pc_cer
    color_cer = '#34D399' if dif_cer >= 0 else '#F87171'

    # --- Rachas (resultados consecutivos por fecha) ---
    res_n = narr['resultado_benicarlo'].tolist()
    fechas_n = narr['fecha'].tolist()

    def _mejor_racha(tipo):
        mejor = act = fin = 0
        for i, r in enumerate(res_n):
            if r == tipo:
                act += 1
                if act > mejor:
                    mejor, fin = act, i
            else:
                act = 0
        return mejor, fin

    racha_v, fin_v = _mejor_racha('Victoria')
    racha_d, fin_d = _mejor_racha('Derrota')
    act_tipo = res_n[-1] if res_n else ''
    act_n = 0
    for r in reversed(res_n):
        if r == act_tipo:
            act_n += 1
        else:
            break
    act_desde = _fmt_fecha(fechas_n[len(fechas_n) - act_n]) if act_n else 'S/F'

    # --- Remontadas: victoria tras ir perdiendo al descanso ---
    beni_q = df_cuartos[df_cuartos['es_benicarlo'] == 1].set_index('partido_id')
    riv_q = df_cuartos[df_cuartos['es_benicarlo'] == 0].set_index('partido_id')
    descanso = pd.DataFrame({
        'desc_beni': beni_q['q1'] + beni_q['q2'],
        'desc_riv': riv_q['q1'] + riv_q['q2'],
    })
    narr_ix = narr.set_index('partido_id').join(descanso)
    remontadas = narr_ix[(narr_ix['resultado_benicarlo'] == 'Victoria') &
                         (narr_ix['desc_beni'] < narr_ix['desc_riv'])].copy()
    remontadas['desventaja'] = remontadas['desc_riv'] - remontadas['desc_beni']
    n_rem = len(remontadas)
    n_vic = int((narr['resultado_benicarlo'] == 'Victoria').sum())
    pct_rem = (n_rem / n_vic * 100) if n_vic else 0.0

    tipo_actual = 'victoria' if act_tipo == 'Victoria' else 'derrota'
    if act_n != 1:
        tipo_actual += 's'
    mayor_rem = remontadas.sort_values('desventaja', ascending=False).iloc[0] if n_rem else None
    ultima_rem = remontadas.sort_values('fecha', ascending=False).iloc[0] if n_rem else None
    linea_mayor = (f"Mayor: -{int(mayor_rem['desventaja'])} al descanso → "
                   f"{int(mayor_rem['puntos_benicarlo'])}-{int(mayor_rem['puntos_rival'])} vs {mayor_rem['equipo_rival']}"
                   if n_rem else 'Sin remontadas registradas')
    linea_ultima = (f"Última: {_fmt_fecha(ultima_rem['fecha'])} vs {ultima_rem['equipo_rival']}"
                    if n_rem else '')

    # Fila flex propia: iguala alturas de forma fiable (los wrappers de
    # st.columns no estiran el contenido de las tarjetas)
    st.markdown(_html_plano(f"""
    <div class="cards-row">
        <div class="metric-container">
            <div class="metric-label">Partidos cerrados (±5)</div>
            <div class="metric-value">{v_cer} - {d_cer} <span style="font-size: 1.1rem; color: #93C5FD;">{pct_cer:.1f}% victorias</span></div>
            <div class="metric-sub">{n_cer} de {len(narr)} partidos ({n_cer / len(narr) * 100:.1f}%)</div>
            <div class="metric-sub">PPP a favor <b>{pf_cer:.1f}</b> · PPP en contra <b>{pc_cer:.1f}</b></div>
            <div class="metric-sub" style="color: {color_cer}; font-weight: 700;">Diferencial: {dif_cer:+.1f} pts / partido</div>
        </div>
        <div class="metric-container">
            <div class="metric-label">Mayor racha de victorias</div>
            <div class="metric-value">{racha_v} seguidas</div>
            <div class="metric-sub">hasta el {_fmt_fecha(fechas_n[fin_v])}</div>
            <div class="metric-sub">Racha actual: <b>{act_n} {tipo_actual}</b> desde el {act_desde}</div>
            <div class="metric-sub" style="color: #F87171; font-weight: 700;">Mayor racha de derrotas: {racha_d} (hasta el {_fmt_fecha(fechas_n[fin_d])})</div>
        </div>
        <div class="metric-container">
            <div class="metric-label">Remontadas al descanso</div>
            <div class="metric-value">{n_rem} <span style="font-size: 1.1rem; color: #93C5FD;">{pct_rem:.1f}% de las victorias</span></div>
            <div class="metric-sub">{linea_mayor}</div>
            <div class="metric-sub">{linea_ultima}</div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    if n_rem:
        st.markdown("### Mayores Remontadas")
        top_rem = remontadas.sort_values('desventaja', ascending=False).head(5)
        tabla_rem = pd.DataFrame({
            'Fecha': top_rem['fecha'].apply(_fmt_fecha),
            'Rival': top_rem['equipo_rival'],
            'Condición': np.where(top_rem['es_benicarlo_local'] == 1, 'Casa', 'Fuera'),
            'Al descanso': top_rem.apply(
                lambda r: f"{int(r['desc_beni'])} - {int(r['desc_riv'])} (-{int(r['desventaja'])})", axis=1),
            'Final': top_rem.apply(
                lambda r: f"{int(r['puntos_benicarlo'])} - {int(r['puntos_rival'])}", axis=1),
        })
        st.dataframe(tabla_rem, hide_index=True, width="stretch")

    # TRAYECTORIA POR TEMPORADA (P2 · punto 5: contexto de liga)
    if df_temporadas is not None and not df_temporadas.empty:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("### Trayectoria por Temporada")

        filas = []
        for _, t in df_temporadas.sort_values('temporada', ascending=False).iterrows():
            clase, texto = hito_badge(t.get('resultado_hito'), t.get('fase_alcanzada', ''))
            badge = (f'<span class="hito-badge {clase}">{texto}</span>' if clase
                     else '<span style="color:#475569;">—</span>')
            pos = f"{int(t['posicion_grupo'])}º" if pd.notnull(t.get('posicion_grupo')) else '—'
            fase = t.get('fase_alcanzada') or ''
            narrativa = t.get('hito') or (fase if fase not in ('', 'Liga Regular') else '—')
            filas.append(_html_plano(f"""
            <tr>
                <td class="c-temp" data-label="Temporada">{t['temporada']}</td>
                <td class="c-meta" data-label="Competición">{t.get('competicion') or ''} · {t.get('grupo') or ''}</td>
                <td class="c-pos" data-label="Pos">{pos}</td>
                <td class="c-bal" data-label="Balance">{int(t['balance_v'])}-{int(t['balance_d'])}</td>
                <td class="c-hito" data-label="Hito">{narrativa}</td>
                <td class="c-badge" data-label="Estado">{badge}</td>
            </tr>
            """))
        st.markdown(_html_plano(f"""
        <div class="tray-wrap">
        <table class="tray-table">
            <colgroup>
                <col style="width: 12%">
                <col style="width: 27%">
                <col style="width: 7%">
                <col style="width: 10%">
                <col style="width: 29%">
                <col style="width: 15%">
            </colgroup>
            <thead>
                <tr>
                    <th>TEMPORADA</th>
                    <th class="c-meta">COMPETICIÓN · GRUPO</th>
                    <th class="c-pos">POS</th>
                    <th class="c-bal">BALANCE</th>
                    <th class="c-hito">HITO</th>
                    <th class="c-badge">ESTADO</th>
                </tr>
            </thead>
            <tbody>
            {''.join(filas)}
            </tbody>
        </table>
        </div>
        """), unsafe_allow_html=True)

    # CALENDARIO DE PRÓXIMOS PARTIDOS: Strictly temporada actual 2026/2027
    upcoming_2026 = df_partidos[
        (df_partidos['temporada'] == '2026/2027') & 
        (df_partidos['estado'] == 'programado')
    ].sort_values('fecha').head(6)

    if not upcoming_2026.empty:
        st.markdown("### Calendario de Próximos Partidos (Segunda FEB · 2026/2027)")
        # Fila flex propia (patrón de la Narrativa): en móvil las tarjetas se
        # apilan con gap real, sin el contacto borde con borde de st.columns.
        tarjetas = []
        for _, row in upcoming_2026.iterrows():
            date_str = row['fecha'].strftime('%d/%m/%Y') if pd.notnull(row['fecha']) else 'S/F'
            is_home = row['es_benicarlo_local'] == 1
            cond = "CASA" if is_home else "FUERA"
            tarjetas.append(_html_plano(f"""
            <div class="scheduled-card">
                <div class="scheduled-jornada">{row['jornada_nombre'].split('(')[0]} · {cond}</div>
                <div class="scheduled-rival">vs {row['equipo_rival']}</div>
                <div class="scheduled-info">📅 {date_str}</div>
                <div class="scheduled-info" style="color: #93C5FD;">⏰ {row['hora'] or '18:00'}</div>
            </div>
            """))
        st.markdown(_html_plano(f"""
        <div class="cards-row">
            {''.join(tarjetas)}
        </div>
        """), unsafe_allow_html=True)

# ==============================================================================
# VIEW 2: PARTIDOS & BOXSCORES
# ==============================================================================
elif nav_option == "Partidos & Boxscores":
    st.markdown("## Explorador de Partidos & Boxscores")
    st.caption("Consulta cualquier partido de la historia del club desde 2019/2020 hasta hoy con su acta completa.")

    partidos_disponibles = df_partidos[df_partidos['estado'] == 'jugado'].sort_values('fecha', ascending=False).copy()
    
    # Filter Controls
    f_col1, f_col2, f_col3 = st.columns([2, 2, 2])
    
    with f_col1:
        temporadas_list = ["Todas las temporadas"] + sorted(partidos_disponibles['temporada'].unique().tolist(), reverse=True)
        sel_temporada = st.selectbox("Temporada", temporadas_list, index=0)

    if sel_temporada != "Todas las temporadas":
        partidos_disponibles = partidos_disponibles[partidos_disponibles['temporada'] == sel_temporada]

    with f_col2:
        fases_list = ["Todas las fases"] + sorted(partidos_disponibles['fase_tipo'].unique().tolist())
        sel_fase = st.selectbox("Fase / Competición", fases_list, index=0)
        if sel_fase != "Todas las fases":
            partidos_disponibles = partidos_disponibles[partidos_disponibles['fase_tipo'] == sel_fase]

    with f_col3:
        filtro_resultado = st.selectbox("Resultado", ["Todos", "Solo Victorias", "Solo Derrotas", "Cerrados (±5)"])
        if filtro_resultado == "Solo Victorias":
            partidos_disponibles = partidos_disponibles[partidos_disponibles['resultado_benicarlo'] == 'Victoria']
        elif filtro_resultado == "Solo Derrotas":
            partidos_disponibles = partidos_disponibles[partidos_disponibles['resultado_benicarlo'] == 'Derrota']
        elif filtro_resultado == "Cerrados (±5)":
            partidos_disponibles = partidos_disponibles[partidos_disponibles['diferencia_puntos'].abs() <= 5]

    if partidos_disponibles.empty:
        st.warning("No hay partidos con los filtros seleccionados.")
        st.stop()

    # Match Dropdown with Clear Labels
    match_options = {}
    for _, row in partidos_disponibles.iterrows():
        fecha_fmt = row['fecha'].strftime('%d/%m/%Y') if pd.notnull(row['fecha']) else 'S/F'
        jornada_clean = row['jornada_nombre'].split('(')[0].strip()
        icon = "🟢" if row['resultado_benicarlo'] == 'Victoria' else "🔴"
        aviso = "⚠ " if row.get('qa_estado', 'ok') != 'ok' else ""
        label = f"{aviso}{icon} [{row['temporada']} · {jornada_clean}] {fecha_fmt} | {row['nombre_benicarlo']} {row['puntos_benicarlo']} - {row['puntos_rival']} {row['equipo_rival']}"
        match_options[label] = row['partido_id']

    sel_label = st.selectbox(
        f"Seleccionar Partido ({len(partidos_disponibles)} encontrados):",
        list(match_options.keys()),
        index=0
    )
    sel_partido_id = match_options[sel_label]
    match_row = df_partidos[df_partidos['partido_id'] == sel_partido_id].iloc[0]
    
    # Scoreboard
    is_win = match_row['resultado_benicarlo'] == 'Victoria'
    badge_class = "badge-win" if is_win else "badge-loss"
    
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="scoreboard">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px 12px; margin-bottom: 14px;">
            <div style="font-size: 0.95rem; color: #93C5FD; font-weight: 700; text-transform: uppercase; min-width: 0;">
                {match_row['temporada']}\u00A0·\u00A0{match_row['grupo_nombre']}\u00A0·\u00A0{match_row['jornada_nombre']}
            </div>
            <span class="{badge_class}">{match_row['resultado_benicarlo']}</span>
        </div>
        <div class="sb-grid">
            <div class="team-name sb-name-l" style="color: {'#38BDF8' if match_row['es_benicarlo_local'] else '#FFFFFF'};">
                {match_row['equipo_local']}
            </div>
            <div class="team-score sb-score-l">{match_row['puntos_local']}</div>
            <div class="sb-dash">-</div>
            <div class="team-name sb-name-r" style="color: {'#38BDF8' if not match_row['es_benicarlo_local'] else '#FFFFFF'};">
                {match_row['equipo_visitante']}
            </div>
            <div class="team-score sb-score-r">{match_row['puntos_visitante']}</div>
        </div>
        <div style="text-align: center; margin-top: 18px; font-size: 0.9rem; color: #E2E8F0;">
            📍 <b>Campo:</b> {match_row['cancha'] or 'Pabellón Municipal de Benicarló'}&nbsp;| 👨‍⚖️&nbsp;<b>Árbitros:</b> {match_row['arbitros'] or 'N/D'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Franja de contexto de liga bajo el marcador (P2 · punto 5)
    jornada_txt = match_row['jornada_nombre'].split('(')[0].strip()
    if match_row['fase_tipo'] == 'Playoff':
        fase_txt = f"Playoff de ascenso\u00A0·\u00A0{jornada_txt}"
    else:
        fase_txt = f"{jornada_txt}\u00A0·\u00A0{match_row['grupo_nombre']}"
    partes_ctx = [f'<span class="ctx-fase">{fase_txt}</span>',
                  f"Temporada {match_row['temporada']}"]
    if df_temporadas is not None and not df_temporadas.empty:
        ctx = df_temporadas[df_temporadas['temporada'] == match_row['temporada']]
        if not ctx.empty:
            t = ctx.iloc[0]
            if pd.notnull(t.get('posicion_grupo')):
                etiqueta_pos = 'Clasificación actual' if t.get('resultado_hito') == 'en_curso' else 'Clasificación final'
                partes_ctx.append(f"{etiqueta_pos}: {int(t['posicion_grupo'])}º ({int(t['balance_v'])}-{int(t['balance_d'])})")
            clase_ctx, texto_ctx = hito_badge(t.get('resultado_hito'), t.get('fase_alcanzada', ''))
            if clase_ctx:
                partes_ctx.append(f'<span class="hito-badge {clase_ctx}">{texto_ctx}</span>')
    # Separador como sufijo irrompible de cada parte: al envolver en móvil el
    # "·" queda al final de línea y nunca la empieza.
    sep_ctx = '\u00A0·'
    ctx_html = ''.join(f'<span class="ctx-item">{p}{sep_ctx}</span>' for p in partes_ctx[:-1])
    ctx_html += f'<span class="ctx-item">{partes_ctx[-1]}</span>'
    st.markdown(f'<div class="match-context">{ctx_html}</div>', unsafe_allow_html=True)

    # Aviso de calidad de datos (bloque P1): el marcador oficial es fiable,
    # pero los parciales o el acta pueden venir incompletos de origen.
    avisos_qa = {
        'descuadre_jugadores': "El acta de jugadores no suma el marcador oficial (datos incompletos de origen).",
        'descuadre_cuartos': "Los parciales por cuarto no suman el marcador oficial.",
        'sin_acta': "Faltan parciales o acta de jugadores para este partido.",
    }
    qa_estado = match_row.get('qa_estado', 'ok')
    if qa_estado in avisos_qa:
        st.caption(f"⚠ Datos con reservas: {avisos_qa[qa_estado]}")

    # Quarters
    match_cuartos = df_cuartos[df_cuartos['partido_id'] == sel_partido_id]
    if not match_cuartos.empty:
        col_q_table, col_q_chart = st.columns([1, 1])
        with col_q_table:
            st.markdown("### Parciales por Cuarto")
            q_display = match_cuartos[['equipo', 'q1', 'q2', 'q3', 'q4', 'ot1', 'ot2', 'puntos_total']].copy()
            q_display.columns = ['Equipo', '1Q', '2Q', '3Q', '4Q', '1OT', '2OT', 'Total']
            if q_display['1OT'].sum() == 0:
                q_display = q_display.drop(columns=['1OT', '2OT'])
            st.dataframe(q_display, hide_index=True, width="stretch")

        with col_q_chart:
            st.markdown("### Evolución de Anotación")
            q_cols = ['1Q', '2Q', '3Q', '4Q']
            if '1OT' in q_display.columns:
                q_cols.append('1OT')
            
            fig_q = go.Figure()
            for _, r_eq in match_cuartos.iterrows():
                eq_color = '#2563EB' if r_eq['es_benicarlo'] == 1 else '#94A3B8'
                y_vals = [r_eq['q1'], r_eq['q2'], r_eq['q3'], r_eq['q4']]
                if r_eq['ot1'] > 0:
                    y_vals.append(r_eq['ot1'])
                fig_q.add_trace(go.Bar(
                    name=r_eq['equipo'],
                    x=q_cols[:len(y_vals)],
                    y=y_vals,
                    marker_color=eq_color,
                    text=y_vals,
                    textposition='auto',
                    textfont=dict(color='#FFFFFF'),
                    hovertemplate='%{x}<br>' + r_eq['equipo'] + ': <b>%{y}</b> pts<extra></extra>',
                ))
            style_fig(fig_q, height=210)
            fig_q.update_layout(
                barmode='group',
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
                yaxis=dict(showgrid=False, tickfont=dict(color="#E2E8F0")),
                xaxis=dict(tickfont=dict(color="#E2E8F0")),
            )
            st.plotly_chart(fig_q, **chart_kwargs())

    # Boxscores
    st.markdown("### Acta y Estadísticas de Jugadores")
    match_players = df_jugadores[df_jugadores['partido_id'] == sel_partido_id].copy()

    def format_boxscore(df_sub):
        df_sub = df_sub.sort_values(['es_titular', 'minutos', 'puntos'], ascending=[False, False, False])
        
        # Advanced stats per game
        ts_denom = 2 * (df_sub['tc_intentados'] + 0.44 * df_sub['tl_intentados'])
        ts_vals = np.where(ts_denom > 0, (df_sub['puntos'] / ts_denom * 100).round(1), 0.0)
        net_rtg_vals = np.where(df_sub['minutos'] > 0, ((df_sub['mas_menos'] / df_sub['minutos']) * 53.3).round(1), 0.0)

        display_df = pd.DataFrame({
            'T': df_sub['es_titular'].apply(lambda x: '★' if x == 1 else ''),
            'D': df_sub['dorsal'],
            'Jugador': df_sub['jugador'],
            'MIN': df_sub['minutos'],
            'PTS': df_sub['puntos'],
            'TS%': [f"{v:.1f}%" if v > 0 else "-" for v in ts_vals],
            'NetRtg': [f"{v:+.1f}" if m > 0 else "-" for v, m in zip(net_rtg_vals, df_sub['minutos'])],
            'T2': df_sub.apply(lambda r: f"{r['t2_anotados']}/{r['t2_intentados']} ({r['t2_pct']:.0f}%)", axis=1),
            'T3': df_sub.apply(lambda r: f"{r['t3_anotados']}/{r['t3_intentados']} ({r['t3_pct']:.0f}%)", axis=1),
            'TL': df_sub.apply(lambda r: f"{r['tl_anotados']}/{r['tl_intentados']} ({r['tl_pct']:.0f}%)", axis=1),
            'REB': df_sub['rebotes_totales'],
            'AST': df_sub['asistencias'],
            'ROB': df_sub['recuperaciones'],
            'PER': df_sub['perdidas'],
            'TAP': df_sub['tapones_favor'],
            'FAL': df_sub['faltas_cometidas'],
            'VAL': df_sub['valoracion'],
            '+/-': df_sub['mas_menos']
        })
        if df_sub['es_titular'].sum() == 0:
            display_df = display_df.drop(columns=['T'])
        return display_df

    tab_beni, tab_rival = st.tabs(["CB Benicarló", f"Rival: {match_row['equipo_rival']}"])
    with tab_beni:
        beni_players = match_players[match_players['es_benicarlo'] == 1]
        if not beni_players.empty:
            st.dataframe(format_boxscore(beni_players), hide_index=True, width="stretch")
        else:
            st.info("No hay datos de jugadores para este partido.")

    with tab_rival:
        rival_players = match_players[match_players['es_benicarlo'] == 0]
        if not rival_players.empty:
            st.dataframe(format_boxscore(rival_players), hide_index=True, width="stretch")
        else:
            st.info("No hay datos de jugadores para el equipo rival.")

# ==============================================================================
# VIEW 3: LÍDERES & JUGADORES
# ==============================================================================
elif nav_option == "Líderes & Jugadores":
    st.markdown("## Rendimiento de Jugadores & Récords Históricos")
    st.caption("Rankings individuales, máximos anotadores y estadísticas acumuladas.")

    # Temporada filter
    seasons_avail = ["Histórico Completo (Todas)"] + sorted(df_partidos['temporada'].unique().tolist(), reverse=True)
    sel_player_season = st.selectbox("Seleccionar Temporada:", seasons_avail, index=0)

    if sel_player_season != "Histórico Completo (Todas)":
        beni_all = df_jugadores[(df_jugadores['temporada'] == sel_player_season) & (df_jugadores['es_benicarlo'] == 1)].copy()
    else:
        beni_all = df_jugadores[df_jugadores['es_benicarlo'] == 1].copy()

    if beni_all.empty:
        st.warning("No hay datos de jugadores para la selección.")
        st.stop()

    # Aggregate by player
    player_agg = beni_all.groupby('jugador').agg(
        Partidos=('partido_id', 'nunique'),
        Minutos=('minutos', 'sum'),
        Puntos=('puntos', 'sum'),
        Puntos_Media=('puntos', 'mean'),
        TC_Anotados=('tc_anotados', 'sum'),
        TC_Intentados=('tc_intentados', 'sum'),
        T3_Anotados=('t3_anotados', 'sum'),
        T3_Intentados=('t3_intentados', 'sum'),
        TL_Anotados=('tl_anotados', 'sum'),
        TL_Intentados=('tl_intentados', 'sum'),
        Rebotes=('rebotes_totales', 'sum'),
        Rebotes_Media=('rebotes_totales', 'mean'),
        Asistencias=('asistencias', 'sum'),
        Asistencias_Media=('asistencias', 'mean'),
        Robos=('recuperaciones', 'sum'),
        Valoracion=('valoracion', 'sum'),
        Valoracion_Media=('valoracion', 'mean'),
        Mas_Menos=('mas_menos', 'sum'),
        Max_Puntos=('puntos', 'max')
    ).reset_index()

    player_agg['T3_Pct'] = np.where(
        player_agg['T3_Intentados'] > 0,
        round(player_agg['T3_Anotados'] / player_agg['T3_Intentados'] * 100, 1),
        0.0
    )
    
    # Advanced: True Shooting % = PTS / (2 * (FGA + 0.44 * FTA)) * 100
    ts_denom = 2 * (player_agg['TC_Intentados'] + 0.44 * player_agg['TL_Intentados'])
    player_agg['TS_Pct'] = np.where(
        ts_denom > 0,
        (player_agg['Puntos'] / ts_denom * 100).round(1),
        0.0
    )

    # Advanced: Effective Field Goal % = (FGM + 0.5 * 3PM) / FGA * 100
    player_agg['eFG_Pct'] = np.where(
        player_agg['TC_Intentados'] > 0,
        ((player_agg['TC_Anotados'] + 0.5 * player_agg['T3_Anotados']) / player_agg['TC_Intentados'] * 100).round(1),
        0.0
    )

    # Advanced: Net Rating (per 100 possessions)
    player_agg['Net_Rating'] = np.where(
        player_agg['Minutos'] > 0,
        ((player_agg['Mas_Menos'] / player_agg['Minutos']) * 53.3).round(1),
        0.0
    )

    player_agg['Puntos_Media'] = player_agg['Puntos_Media'].round(1)
    player_agg['Rebotes_Media'] = player_agg['Rebotes_Media'].round(1)
    player_agg['Asistencias_Media'] = player_agg['Asistencias_Media'].round(1)
    player_agg['Valoracion_Media'] = player_agg['Valoracion_Media'].round(1)

    # FILTROS DE CORTE EN RANKINGS (P2 · umbrales mínimos)
    # Un jugador con 1 partido puede liderar un promedio por azar; el corte
    # limita quién entra en cards, gráfica y tabla.
    max_partidos_corte = int(player_agg['Partidos'].max()) if not player_agg.empty else 1
    max_minutos_corte = int(player_agg['Minutos'].max()) if not player_agg.empty else 1

    corte_col1, corte_col2, corte_col3 = st.columns([2, 2, 3])
    with corte_col1:
        sel_min_partidos = st.slider("Partidos mínimos", 0, max(max_partidos_corte, 1), 0)
    with corte_col2:
        sel_min_minutos = st.slider("Minutos mínimos", 0, max(max_minutos_corte, 1), 0, step=50)
    with corte_col3:
        st.markdown("<div style='height: 26px;'></div>", unsafe_allow_html=True)
        st.caption("Corte mínimo para entrar en los rankings: evita sesgos en promedios (PPP, TS%, eFG%, NetRtg).")

    player_rank = player_agg[
        (player_agg['Partidos'] >= sel_min_partidos) &
        (player_agg['Minutos'] >= sel_min_minutos)
    ]
    if sel_min_partidos > 0 or sel_min_minutos > 0:
        st.caption(f"{len(player_rank)} de {len(player_agg)} jugadores cumplen el corte.")
    if player_rank.empty:
        st.warning("Ningún jugador cumple el corte seleccionado. Reduce los umbrales.")
        st.stop()

    # Top Leaders Row
    col_lead1, col_lead2, col_lead3, col_lead4 = st.columns(4)
    top_scorer = player_rank.sort_values('Puntos', ascending=False).iloc[0]
    top_ast = player_rank.sort_values('Asistencias', ascending=False).iloc[0]
    top_reb = player_rank.sort_values('Rebotes', ascending=False).iloc[0]
    top_val = player_rank.sort_values('Valoracion', ascending=False).iloc[0]

    with col_lead1:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Máximo Anotador</div>
            <div class="metric-value">{top_scorer['Puntos']} <span style="font-size: 1.1rem; color: #93C5FD;">PTS</span></div>
            <div style="font-weight: 800; color: #FFFFFF; font-size: 1rem; margin-top: 4px;">{top_scorer['jugador']}</div>
            <div class="metric-sub">{top_scorer['Puntos_Media']} PPP · {top_scorer['Partidos']} partidos</div>
        </div>
        """, unsafe_allow_html=True)

    with col_lead2:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Líder Asistencias</div>
            <div class="metric-value">{top_ast['Asistencias']} <span style="font-size: 1.1rem; color: #93C5FD;">AST</span></div>
            <div style="font-weight: 800; color: #FFFFFF; font-size: 1rem; margin-top: 4px;">{top_ast['jugador']}</div>
            <div class="metric-sub">{top_ast['Asistencias_Media']} APP · {top_ast['Partidos']} partidos</div>
        </div>
        """, unsafe_allow_html=True)

    with col_lead3:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Líder Rebotes</div>
            <div class="metric-value">{top_reb['Rebotes']} <span style="font-size: 1.1rem; color: #93C5FD;">REB</span></div>
            <div style="font-weight: 800; color: #FFFFFF; font-size: 1rem; margin-top: 4px;">{top_reb['jugador']}</div>
            <div class="metric-sub">{top_reb['Rebotes_Media']} RPP · {top_reb['Partidos']} partidos</div>
        </div>
        """, unsafe_allow_html=True)

    with col_lead4:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Líder Valoración</div>
            <div class="metric-value">{top_val['Valoracion']} <span style="font-size: 1.1rem; color: #93C5FD;">VAL</span></div>
            <div style="font-weight: 800; color: #FFFFFF; font-size: 1rem; margin-top: 4px;">{top_val['jugador']}</div>
            <div class="metric-sub">{top_val['Valoracion_Media']} VPP · {top_val['Partidos']} partidos</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    col_chart_scorers, col_records = st.columns([3, 2])

    with col_chart_scorers:
        st.markdown("### Top 10 Anotadores")
        top10 = player_rank.sort_values('Puntos', ascending=False).head(10).copy()
        top10['jugador_corto'] = top10['jugador'].apply(truncar_nombre)
        fig_scorers = px.bar(
            top10,
            x='Puntos',
            y='jugador_corto',
            orientation='h',
            text='Puntos',
            color='Puntos',
            color_continuous_scale=['#1E40AF', '#38BDF8'],
            custom_data=['Puntos_Media', 'Partidos', 'jugador'],
        )
        fig_scorers.update_traces(
            textposition='outside',
            textfont=dict(color='#F8FAFC'),
            hovertemplate='%{customdata[2]}<br><b>%{x}</b> puntos · %{customdata[0]:.1f} PPP · %{customdata[1]} partidos<extra></extra>',
        )
        style_fig(fig_scorers, height=380)
        fig_scorers.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            coloraxis_showscale=False,
            yaxis=dict(autorange="reversed", title=None, tickfont=dict(color="#FFFFFF", size=11)),
            xaxis=dict(showgrid=False, title=None, tickfont=dict(color="#E2E8F0"), range=[0, top10['Puntos'].max() * 1.22]),
        )
        st.plotly_chart(fig_scorers, **chart_kwargs())

    with col_records:
        st.markdown("### Récords en un Solo Partido")
        rec_pts = beni_all.sort_values('puntos', ascending=False).iloc[0]
        rec_val = beni_all.sort_values('valoracion', ascending=False).iloc[0]
        rec_triples = beni_all.sort_values('t3_anotados', ascending=False).iloc[0]
        rec_reb = beni_all.sort_values('rebotes_totales', ascending=False).iloc[0]

        records_data = pd.DataFrame([
            {"Récord": "Más Puntos", "Marca": f"{rec_pts['puntos']} pts", "Jugador": rec_pts['jugador'], "Temporada": rec_pts['temporada']},
            {"Récord": "Mayor Valoración", "Marca": f"{rec_val['valoracion']} val", "Jugador": rec_val['jugador'], "Temporada": rec_val['temporada']},
            {"Récord": "Más Triples", "Marca": f"{rec_triples['t3_anotados']} T3", "Jugador": rec_triples['jugador'], "Temporada": rec_triples['temporada']},
            {"Récord": "Más Rebotes", "Marca": f"{rec_reb['rebotes_totales']} reb", "Jugador": rec_reb['jugador'], "Temporada": rec_reb['temporada']},
        ])
        st.dataframe(records_data, hide_index=True, width="stretch")

    # Full Player Table with Direct Search (NO SLIDER)
    st.markdown("### Tabla Completa de Jugadores")
    st.caption("Incluye estadísticas tradicionales y analítica avanzada: **TS%** (True Shooting %), **eFG%** (Tiro efectivo) y **NetRtg** (Balance neto por 100 posesiones).")
    
    search_query = st.text_input("🔍 Buscar jugador por nombre:", placeholder="Escribe para filtrar (ej. Libroia, Ruesga, Orlov, Lafuente...)")
    
    table_src = player_rank.sort_values('Puntos', ascending=False).copy()
    if search_query:
        table_src = table_src[table_src['jugador'].str.contains(search_query, case=False, na=False)]

    table_src['TS%'] = table_src['TS_Pct'].apply(lambda x: f"{x:.1f}%")
    table_src['eFG%'] = table_src['eFG_Pct'].apply(lambda x: f"{x:.1f}%")
    table_src['NetRtg'] = table_src['Net_Rating'].apply(lambda x: f"{x:+.1f}")

    table_display = table_src[[
        'jugador', 'Partidos', 'Minutos', 'Puntos', 'Puntos_Media',
        'TS%', 'eFG%', 'NetRtg',
        'T3_Anotados', 'T3_Pct', 'Rebotes', 'Rebotes_Media',
        'Asistencias', 'Asistencias_Media', 'Valoracion', 'Max_Puntos'
    ]].copy()
    table_display.columns = [
        'Jugador', 'PJ', 'MIN', 'PTS', 'PPP',
        'TS%', 'eFG%', 'NetRtg',
        'T3 Conv', 'T3 %', 'REB', 'RPP',
        'AST', 'APP', 'VAL', 'Máx PTS'
    ]
    st.dataframe(table_display, hide_index=True, width="stretch")

    # EVOLUCIÓN INTERANUAL POR JUGADOR (P2 · vista temporal año a año)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("### Evolución Interanual por Jugador")
    st.caption("Trayectoria año a año con el CB Benicarló: producción, eficiencia y participación.")

    beni_hist = df_jugadores[df_jugadores['es_benicarlo'] == 1].copy()
    jugadores_hist = sorted(beni_hist['jugador'].dropna().unique())
    default_jugador = (player_rank.sort_values('Puntos', ascending=False).iloc[0]['jugador']
                       if not player_rank.empty else jugadores_hist[0])
    sel_jugador = st.selectbox(
        "Jugador",
        jugadores_hist,
        index=jugadores_hist.index(default_jugador) if default_jugador in jugadores_hist else 0,
        key="evo_jugador",
    )

    jrows = beni_hist[beni_hist['jugador'] == sel_jugador]
    g_j = jrows.groupby('temporada')
    evo = pd.DataFrame({
        'PJ': g_j['partido_id'].nunique(),
        'MIN': g_j['minutos'].sum(),
        'PTS': g_j['puntos'].sum(),
        'PPP': g_j['puntos'].mean().round(1),
        'REB': g_j['rebotes_totales'].sum(),
        'RPP': g_j['rebotes_totales'].mean().round(1),
        'AST': g_j['asistencias'].sum(),
        'APP': g_j['asistencias'].mean().round(1),
        'VAL': g_j['valoracion'].sum(),
        'VPP': g_j['valoracion'].mean().round(1),
    }).reset_index().sort_values('temporada').reset_index(drop=True)

    # Ratios por temporada (mismas fórmulas que los rankings históricos)
    ts_den = (2 * (g_j['tc_intentados'].sum() + 0.44 * g_j['tl_intentados'].sum())).values
    efg_den = g_j['tc_intentados'].sum().values
    min_den = g_j['minutos'].sum().values
    evo['TS%'] = np.where(ts_den > 0, np.round(evo['PTS'].values / np.where(ts_den == 0, 1, ts_den) * 100, 1), 0.0)
    evo['eFG%'] = np.where(efg_den > 0, np.round(
        (g_j['tc_anotados'].sum().values + 0.5 * g_j['t3_anotados'].sum().values) /
        np.where(efg_den == 0, 1, efg_den) * 100, 1), 0.0)
    evo['NetRtg'] = np.where(min_den > 0, np.round(
        g_j['mas_menos'].sum().values / np.where(min_den == 0, 1, min_den) * 53.3, 1), 0.0)

    fig_evo = go.Figure()
    for serie, color, ancho in (('PPP', '#38BDF8', 3), ('RPP', '#F43F5E', 2), ('APP', '#34D399', 2)):
        fig_evo.add_trace(go.Scatter(
            x=evo['temporada'], y=evo[serie], name=serie,
            mode='lines+markers',
            line=dict(color=color, width=ancho),
            hovertemplate='%{x}<br>' + serie + ': <b>%{y:.1f}</b> por partido<extra></extra>',
        ))
    style_fig(fig_evo, height=300, hovermode='x unified')
    fig_evo.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
        xaxis=dict(tickfont=dict(color="#E2E8F0"), tickangle=0),
        yaxis=dict(gridcolor="#1E293B", tickfont=dict(color="#E2E8F0"), title='Por partido'),
    )
    st.plotly_chart(fig_evo, **chart_kwargs())

    if len(evo) >= 3:
        pendiente = np.polyfit(np.arange(len(evo)), evo['PPP'].values, 1)[0]
        tendencia = ("estable" if abs(pendiente) < 0.05
                     else f"{pendiente:+.1f} PPP por temporada")
        st.caption(f"{len(evo)} temporadas con el club · Tendencia de anotación: {tendencia}.")
    else:
        st.caption(f"{len(evo)} temporada(s) con el club.")

    tabla_evo = evo[['temporada', 'PJ', 'MIN', 'PTS', 'PPP', 'REB', 'RPP', 'AST', 'APP',
                     'VAL', 'TS%', 'eFG%', 'NetRtg']].copy()
    for col in ('PPP', 'RPP', 'APP'):
        tabla_evo[col] = tabla_evo[col].apply(lambda x: f"{x:.1f}")
    tabla_evo['TS%'] = tabla_evo['TS%'].apply(lambda x: f"{x:.1f}%")
    tabla_evo['eFG%'] = tabla_evo['eFG%'].apply(lambda x: f"{x:.1f}%")
    tabla_evo['NetRtg'] = tabla_evo['NetRtg'].apply(lambda x: f"{x:+.1f}")
    tabla_evo.columns = ['Temporada', 'PJ', 'MIN', 'PTS', 'PPP', 'REB', 'RPP', 'AST', 'APP',
                         'VAL', 'TS%', 'eFG%', 'NetRtg']
    st.dataframe(tabla_evo, hide_index=True, width="stretch")

# ==============================================================================
# VIEW 3B: FICHA & COMPARADOR DE JUGADORES (P3)
# ==============================================================================
elif nav_option == "Ficha & Comparador":
    st.markdown("## Ficha & Comparador de Jugadores")
    st.caption("Ficha individual por temporada y comparación lado a lado entre jugadores del club.")

    def _serie_temporada(jrows):
        """Agregados por temporada de un jugador (mismas fórmulas que los rankings).

        Las métricas derivadas se calculan con el índice de temporada intacto
        (antes del reset_index) para que las Series se alineen por temporada;
        hacerlo después provoca la unión de índices y NaN.
        """
        g = jrows.groupby('temporada')
        s = pd.DataFrame({
            'PJ': g['partido_id'].nunique(),
            'MIN': g['minutos'].sum(),
            'PTS': g['puntos'].sum(),
            'PPP': g['puntos'].mean().round(1),
            'REB': g['rebotes_totales'].sum(),
            'RPP': g['rebotes_totales'].mean().round(1),
            'AST': g['asistencias'].sum(),
            'APP': g['asistencias'].mean().round(1),
            'VAL': g['valoracion'].sum(),
            'VPP': g['valoracion'].mean().round(1),
        })
        ts_den = 2 * (g['tc_intentados'].sum() + 0.44 * g['tl_intentados'].sum())
        efg_den = g['tc_intentados'].sum()
        efg_num = g['tc_anotados'].sum() + 0.5 * g['t3_anotados'].sum()
        min_den = g['minutos'].sum()
        s['TS%'] = np.where(ts_den > 0, (s['PTS'] / ts_den.replace(0, np.nan) * 100).round(1), 0.0)
        s['eFG%'] = np.where(efg_den > 0, (efg_num / efg_den.replace(0, np.nan) * 100).round(1), 0.0)
        s['NetRtg'] = np.where(min_den > 0, (g['mas_menos'].sum() / min_den.replace(0, np.nan) * 53.3).round(1), 0.0)
        return s.reset_index().sort_values('temporada').reset_index(drop=True)

    def _agg_carrera(jrows):
        """Agregados de carrera en un dict por partido (para el comparador)."""
        pj = jrows['partido_id'].nunique()
        if pj == 0:
            return None
        pts, minu = jrows['puntos'].sum(), jrows['minutos'].sum()
        ts_den = 2 * (jrows['tc_intentados'].sum() + 0.44 * jrows['tl_intentados'].sum())
        efg_den = jrows['tc_intentados'].sum()
        return {
            'PJ': pj,
            'MIN': round(minu / pj, 1),
            'PPP': round(pts / pj, 1),
            'RPP': round(jrows['rebotes_totales'].sum() / pj, 1),
            'APP': round(jrows['asistencias'].sum() / pj, 1),
            'ROB': round(jrows['recuperaciones'].sum() / pj, 1),
            'TAP': round(jrows['tapones_favor'].sum() / pj, 1),
            'T3P': round(jrows['t3_anotados'].sum() / pj, 1),
            'VPP': round(jrows['valoracion'].sum() / pj, 1),
            'TS%': round(pts / ts_den * 100, 1) if ts_den > 0 else 0.0,
            'eFG%': round((jrows['tc_anotados'].sum() + 0.5 * jrows['t3_anotados'].sum()) / efg_den * 100, 1) if efg_den > 0 else 0.0,
        }

    beni_jug = df_jugadores[df_jugadores['es_benicarlo'] == 1].copy()
    # Ordena el selector por relevancia (puntos totales en el club)
    relevancia = beni_jug.groupby('jugador')['puntos'].sum().sort_values(ascending=False)
    lista_jugadores = relevancia.index.tolist()

    modo_jug = st.radio("Modo", ["Ficha individual", "Comparador"],
                        horizontal=True, label_visibility="collapsed")

    # ------------------------------------------------------------------ FICHA
    if modo_jug == "Ficha individual":
        if not lista_jugadores:
            st.warning("No hay registros de jugadores del club.")
            st.stop()
        sel_ficha = st.selectbox("Jugador", lista_jugadores, key="ficha_jugador")
        jrows = beni_jug[beni_jug['jugador'] == sel_ficha]
        serie = _serie_temporada(jrows)
        pj_total = int(serie['PJ'].sum())

        st.markdown(f"### {sel_ficha}")
        st.caption(f"{serie.shape[0]} temporadas · {pj_total} partidos")

        # KPIs de carrera
        titulares = int(jrows['es_titular'].sum())
        pct_titular = (titulares / pj_total * 100) if pj_total else 0.0
        ts_carrera = _agg_carrera(jrows)
        kpis = [
            ("Puntos por partido", f"{ts_carrera['PPP']}", f"{int(jrows['puntos'].sum())} puntos en total"),
            ("Rebotes por partido", f"{ts_carrera['RPP']}", f"{int(jrows['rebotes_totales'].sum())} rebotes"),
            ("Asistencias por partido", f"{ts_carrera['APP']}", f"{int(jrows['asistencias'].sum())} asistencias"),
            ("Valoración por partido", f"{ts_carrera['VPP']}", f"{int(jrows['valoracion'].sum())} valoración total"),
            ("Titularidad", f"{pct_titular:.0f}%", f"TS% carrera: {ts_carrera['TS%']:.1f}%"),
        ]
        tarjetas = []
        for etiqueta, valor, sub in kpis:
            tarjetas.append(_html_plano(f"""
            <div class="metric-container">
                <div class="metric-label">{etiqueta}</div>
                <div class="metric-value">{valor}</div>
                <div class="metric-sub">{sub}</div>
            </div>
            """))
        st.markdown(_html_plano(f"""
        <div class="cards-row">
            {''.join(tarjetas)}
        </div>
        """), unsafe_allow_html=True)
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        col_ficha_chart, col_ficha_split = st.columns([3, 2])
        with col_ficha_chart:
            st.markdown("#### Trayectoria por Temporada")
            fig_tray = go.Figure()
            for serie_nombre, color in (('PPP', '#38BDF8'), ('RPP', '#F43F5E'),
                                        ('APP', '#34D399'), ('VPP', '#FBBF24')):
                fig_tray.add_trace(go.Scatter(
                    x=serie['temporada'], y=serie[serie_nombre], name=serie_nombre,
                    mode='lines+markers', line=dict(color=color, width=2),
                    hovertemplate='%{x}<br>' + serie_nombre + ': <b>%{y:.1f}</b><extra></extra>',
                ))
            style_fig(fig_tray, height=320, hovermode='x unified')
            fig_tray.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
                xaxis=dict(tickfont=dict(color="#E2E8F0"), tickangle=0),
                yaxis=dict(gridcolor="#1E293B", tickfont=dict(color="#E2E8F0"), title='Por partido'),
            )
            st.plotly_chart(fig_tray, **chart_kwargs())

        with col_ficha_split:
            st.markdown("#### Titular vs Suplente")
            jrows_cp = jrows.copy()
            jrows_cp['rol'] = np.where(jrows_cp['es_titular'] == 1, 'Titular', 'Suplente')
            g_rol = jrows_cp.groupby('rol')
            tabla_rol = pd.DataFrame({
                'PJ': g_rol['partido_id'].nunique(),
                'PPP': g_rol['puntos'].mean().round(1),
                'RPP': g_rol['rebotes_totales'].mean().round(1),
                'APP': g_rol['asistencias'].mean().round(1),
                'VPP': g_rol['valoracion'].mean().round(1),
            }).reset_index().rename(columns={'rol': 'Rol'})
            st.dataframe(tabla_rol, hide_index=True, width="stretch")

        # Tabla por temporada
        tabla_ficha = serie.copy()
        for col in ('PPP', 'RPP', 'APP', 'VPP'):
            tabla_ficha[col] = tabla_ficha[col].apply(lambda x: f"{x:.1f}")
        tabla_ficha['TS%'] = tabla_ficha['TS%'].apply(lambda x: f"{x:.1f}%")
        tabla_ficha['eFG%'] = tabla_ficha['eFG%'].apply(lambda x: f"{x:.1f}%")
        tabla_ficha['NetRtg'] = tabla_ficha['NetRtg'].apply(lambda x: f"{x:+.1f}")
        tabla_ficha.columns = ['Temporada', 'PJ', 'MIN', 'PTS', 'PPP', 'REB', 'RPP',
                               'AST', 'APP', 'VAL', 'VPP', 'TS%', 'eFG%', 'NetRtg']
        st.markdown("#### Temporada a Temporada")
        st.dataframe(tabla_ficha, hide_index=True, width="stretch")

        # Últimos partidos (bitácora)
        partidos_info = df_partidos[['partido_id', 'fecha', 'equipo_rival',
                                     'es_benicarlo_local', 'resultado_benicarlo', 'estado']]
        log = jrows.merge(partidos_info, on='partido_id')
        log = log[log['estado'] == 'jugado'].sort_values('fecha', ascending=False).head(10)
        if not log.empty:
            st.markdown("#### Últimos Partidos")
            tabla_log = pd.DataFrame({
                'Fecha': log['fecha'].dt.strftime('%d/%m/%y'),
                'Rival': log['equipo_rival'].apply(truncar_nombre),
                'Sede': np.where(log['es_benicarlo_local'] == 1, 'Casa', 'Fuera'),
                'Res': log['resultado_benicarlo'].str[0],
                'MIN': log['minutos'],
                'PTS': log['puntos'],
                'T3': log['t3_anotados'],
                'REB': log['rebotes_totales'],
                'AST': log['asistencias'],
                'VAL': log['valoracion'],
                '+/-': log['mas_menos'],
            })
            st.dataframe(tabla_log, hide_index=True, width="stretch")

    # ------------------------------------------------------------- COMPARADOR
    else:
        c_cmp_a, c_cmp_b = st.columns(2)
        with c_cmp_a:
            jugador_a = st.selectbox("Jugador A", lista_jugadores, key="cmp_a")
        with c_cmp_b:
            idx_b = 1 if len(lista_jugadores) > 1 else 0
            jugador_b = st.selectbox("Jugador B", lista_jugadores, index=idx_b, key="cmp_b")

        temporadas_cmp = ["Toda la carrera"] + sorted(
            beni_jug['temporada'].unique().tolist(), reverse=True)
        alcance = st.selectbox("Alcance", temporadas_cmp, key="cmp_temporada")

        def _filas(jugador):
            f = beni_jug[beni_jug['jugador'] == jugador]
            if alcance != "Toda la carrera":
                f = f[f['temporada'] == alcance]
            return f

        filas_a, filas_b = _filas(jugador_a), _filas(jugador_b)
        agg_a, agg_b = _agg_carrera(filas_a), _agg_carrera(filas_b)

        if agg_a is None or agg_b is None:
            st.warning("No hay partidos con los filtros seleccionados.")
            st.stop()

        st.markdown(f"### {truncar_nombre(jugador_a, 28)} vs {truncar_nombre(jugador_b, 28)}")
        st.caption(f"Alcance: {alcance} · {agg_a['PJ']} vs {agg_b['PJ']} partidos")

        # Radar normalizado al máximo de ambos en cada eje
        ejes = ['PPP', 'RPP', 'APP', 'ROB', 'TAP', 'VPP']
        fig_cmp = go.Figure()
        for nombre, agg, color in ((truncar_nombre(jugador_a, 20), agg_a, '#38BDF8'),
                                   (truncar_nombre(jugador_b, 20), agg_b, '#F43F5E')):
            fig_cmp.add_trace(go.Scatterpolar(
                r=[agg[e] for e in ejes], theta=ejes, fill='toself', name=nombre,
                line=dict(color=color),
                hovertemplate='%{theta}: <b>%{r:.1f}</b><extra>' + nombre + '</extra>',
            ))
        maximo = max(max(agg_a[e], agg_b[e]) for e in ejes) or 1
        style_fig(fig_cmp, height=400)
        fig_cmp.update_layout(
            polar=dict(radialaxis=dict(range=[0, maximo * 1.1], gridcolor="#1E293B",
                                       tickfont=dict(color="#E2E8F0"), showticklabels=False),
                       bgcolor='rgba(0,0,0,0)'),
            margin=dict(l=40, r=40, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
        )
        st.plotly_chart(fig_cmp, **chart_kwargs())

        # Tabla comparativa
        filas_tabla = []
        for metrica, formato in (('PJ', 'd'), ('MIN', '.1f'), ('PPP', '.1f'), ('RPP', '.1f'),
                                 ('APP', '.1f'), ('ROB', '.1f'), ('TAP', '.1f'), ('T3P', '.1f'),
                                 ('VPP', '.1f'), ('TS%', '.1f'), ('eFG%', '.1f')):
            va, vb = agg_a[metrica], agg_b[metrica]
            mejor_a = va > vb
            filas_tabla.append({
                'Métrica': metrica,
                jugador_a[:20]: f"{va:{formato}}" if formato != 'd' else str(va),
                jugador_b[:20]: f"{vb:{formato}}" if formato != 'd' else str(vb),
                'Ventaja': truncar_nombre(jugador_a, 16) if mejor_a else truncar_nombre(jugador_b, 16),
            })
        st.dataframe(pd.DataFrame(filas_tabla), hide_index=True, width="stretch")

# ==============================================================================
# VIEW 4: ANÁLISIS DE CUARTOS
# ==============================================================================
elif nav_option == "Análisis de Cuartos":
    st.markdown("## Análisis de Rendimiento por Cuarto")
    st.caption("Desglose táctico de fortaleza y vulnerabilidad en 1Q, 2Q, 3Q y 4Q.")

    temporadas_q = ["Todas las temporadas"] + sorted(df_partidos['temporada'].unique().tolist(), reverse=True)
    sel_q_season = st.selectbox("Temporada", temporadas_q, index=0)

    if sel_q_season != "Todas las temporadas":
        partidos_q_ids = df_partidos.loc[df_partidos['temporada'] == sel_q_season, 'partido_id']
    else:
        partidos_q_ids = df_partidos['partido_id']

    cuartos_beni = df_cuartos[(df_cuartos['es_benicarlo'] == 1) & (df_cuartos['partido_id'].isin(partidos_q_ids))].copy()
    cuartos_rival = df_cuartos[(df_cuartos['es_benicarlo'] == 0) & (df_cuartos['partido_id'].isin(partidos_q_ids))].copy()

    merged_q = pd.merge(
        cuartos_beni,
        cuartos_rival,
        on='partido_id',
        suffixes=('_beni', '_rival')
    )

    if merged_q.empty:
        scope = f"la temporada {sel_q_season}" if sel_q_season != "Todas las temporadas" else "la selección actual"
        st.warning(f"No hay datos de parciales para {scope}.")
        st.stop()

    st.caption(f"Basado en {len(merged_q)} partidos jugados.")

    merged_q['diff_q1'] = merged_q['q1_beni'] - merged_q['q1_rival']
    merged_q['diff_q2'] = merged_q['q2_beni'] - merged_q['q2_rival']
    merged_q['diff_q3'] = merged_q['q3_beni'] - merged_q['q3_rival']
    merged_q['diff_q4'] = merged_q['q4_beni'] - merged_q['q4_rival']

    avg_q1_beni = merged_q['q1_beni'].mean()
    avg_q1_rival = merged_q['q1_rival'].mean()
    avg_q2_beni = merged_q['q2_beni'].mean()
    avg_q2_rival = merged_q['q2_rival'].mean()
    avg_q3_beni = merged_q['q3_beni'].mean()
    avg_q3_rival = merged_q['q3_rival'].mean()
    avg_q4_beni = merged_q['q4_beni'].mean()
    avg_q4_rival = merged_q['q4_rival'].mean()

    qc1, qc2, qc3, qc4 = st.columns(4)
    with qc1:
        diff_1 = avg_q1_beni - avg_q1_rival
        color_1 = "#34D399" if diff_1 >= 0 else "#F87171"
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Primer Cuarto (1Q)</div>
            <div class="metric-value">{avg_q1_beni:.1f} <span style="font-size: 1.1rem; color: #93C5FD;">vs {avg_q1_rival:.1f}</span></div>
            <div class="metric-sub" style="color: {color_1}; font-weight: 700;">Diferencial: {diff_1:+.2f} pts</div>
        </div>
        """, unsafe_allow_html=True)

    with qc2:
        diff_2 = avg_q2_beni - avg_q2_rival
        color_2 = "#34D399" if diff_2 >= 0 else "#F87171"
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Segundo Cuarto (2Q)</div>
            <div class="metric-value">{avg_q2_beni:.1f} <span style="font-size: 1.1rem; color: #93C5FD;">vs {avg_q2_rival:.1f}</span></div>
            <div class="metric-sub" style="color: {color_2}; font-weight: 700;">Diferencial: {diff_2:+.2f} pts</div>
        </div>
        """, unsafe_allow_html=True)

    with qc3:
        diff_3 = avg_q3_beni - avg_q3_rival
        color_3 = "#34D399" if diff_3 >= 0 else "#F87171"
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Tercer Cuarto (3Q)</div>
            <div class="metric-value">{avg_q3_beni:.1f} <span style="font-size: 1.1rem; color: #93C5FD;">vs {avg_q3_rival:.1f}</span></div>
            <div class="metric-sub" style="color: {color_3}; font-weight: 700;">Diferencial: {diff_3:+.2f} pts</div>
        </div>
        """, unsafe_allow_html=True)

    with qc4:
        diff_4 = avg_q4_beni - avg_q4_rival
        color_4 = "#34D399" if diff_4 >= 0 else "#F87171"
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Último Cuarto (4Q)</div>
            <div class="metric-value">{avg_q4_beni:.1f} <span style="font-size: 1.1rem; color: #93C5FD;">vs {avg_q4_rival:.1f}</span></div>
            <div class="metric-sub" style="color: {color_4}; font-weight: 700;">Diferencial: {diff_4:+.2f} pts</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    col_q_chart_main, col_q_wins = st.columns([3, 2])

    with col_q_chart_main:
        st.markdown("### Promedio de Puntos por Periodo")
        fig_q_comp = go.Figure()
        fig_q_comp.add_trace(go.Bar(
            name='CB Benicarló',
            x=['1Q', '2Q', '3Q', '4Q'],
            y=[avg_q1_beni, avg_q2_beni, avg_q3_beni, avg_q4_beni],
            marker_color='#2563EB',
            text=[f"{v:.1f}" for v in [avg_q1_beni, avg_q2_beni, avg_q3_beni, avg_q4_beni]],
            textposition='auto',
            textfont=dict(color='#FFFFFF'),
            hovertemplate='%{x}<br>CB Benicarló: <b>%{y:.1f}</b> pts<extra></extra>',
        ))
        fig_q_comp.add_trace(go.Bar(
            name='Rivales',
            x=['1Q', '2Q', '3Q', '4Q'],
            y=[avg_q1_rival, avg_q2_rival, avg_q3_rival, avg_q4_rival],
            marker_color='#64748B',
            text=[f"{v:.1f}" for v in [avg_q1_rival, avg_q2_rival, avg_q3_rival, avg_q4_rival]],
            textposition='auto',
            textfont=dict(color='#FFFFFF'),
            hovertemplate='%{x}<br>Rivales: <b>%{y:.1f}</b> pts<extra></extra>',
        ))
        style_fig(fig_q_comp)
        fig_q_comp.update_layout(
            barmode='group',
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(color="#F8FAFC", size=11)),
            xaxis=dict(tickfont=dict(color="#E2E8F0")),
            yaxis=dict(gridcolor="#1E293B", tickfont=dict(color="#E2E8F0"), title='Puntos promedio'),
        )
        st.plotly_chart(fig_q_comp, **chart_kwargs())

    with col_q_wins:
        st.markdown("### Balance de Cuartos")
        q_wins = [
            (merged_q['diff_q1'] > 0).sum(),
            (merged_q['diff_q2'] > 0).sum(),
            (merged_q['diff_q3'] > 0).sum(),
            (merged_q['diff_q4'] > 0).sum()
        ]
        q_losses = [
            (merged_q['diff_q1'] < 0).sum(),
            (merged_q['diff_q2'] < 0).sum(),
            (merged_q['diff_q3'] < 0).sum(),
            (merged_q['diff_q4'] < 0).sum()
        ]
        q_ties = [
            (merged_q['diff_q1'] == 0).sum(),
            (merged_q['diff_q2'] == 0).sum(),
            (merged_q['diff_q3'] == 0).sum(),
            (merged_q['diff_q4'] == 0).sum()
        ]
        df_q_stats = pd.DataFrame({
            'Cuarto': ['1Q', '2Q', '3Q', '4Q'],
            'Ganados': q_wins,
            'Perdidos': q_losses,
            'Empatados': q_ties,
            '% Victoria': [f"{(w / len(merged_q) * 100):.1f}%" for w in q_wins]
        })
        st.dataframe(df_q_stats, hide_index=True, width="stretch")

# Footer
st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; font-size: 0.8rem; color: #94A3B8; border-top: 1px solid #1E293B; padding-top: 16px;">
    CB Benicarló Analytics Hub · Datos Oficiales FEB · Temporada 2026/2027
</div>
""", unsafe_allow_html=True)
