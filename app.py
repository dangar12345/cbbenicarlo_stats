import streamlit as st

from components import GLOSARIO_HTML, miles
from data_loaders import load_data
from theme import CSS
from views import cuartos, ficha, lideres, partidos, resumen

VISTAS = ["Resumen", "Partidos", "Líderes", "Ficha", "Cuartos"]
SLUGS = {"Resumen": "resumen", "Partidos": "partidos", "Líderes": "lideres",
         "Ficha": "ficha", "Cuartos": "cuartos"}

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="CB Benicarló | Analytics Hub",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS, unsafe_allow_html=True)


# --- CARGA DE DATOS ---
try:
    df_partidos, df_cuartos, df_jugadores, cat_jugadores, cat_equipos, df_temporadas = load_data()
except Exception as e:
    st.error(f"Error al cargar los datos desde 'data/': {e}")
    st.stop()


# --- NAVEGACIÓN ---
_param_vista = st.query_params.get("vista")
_vista_titulo = next((v for v, s in SLUGS.items() if s == _param_vista), None)
if _vista_titulo and "nav_side" not in st.session_state:
    st.session_state["nav_side"] = _vista_titulo

st.sidebar.markdown("""
<div class="sidebar-brand-box">
    <div class="sidebar-brand-icon">🏀</div>
    <div>
        <div class="sidebar-brand-title">CB BENICARLÓ</div>
        <div class="sidebar-brand-sub">Analytics Hub · FEB</div>
    </div>
</div>
""", unsafe_allow_html=True)

nav_option = st.sidebar.radio(
    "Vistas del sistema", VISTAS, key="nav_side",
    label_visibility="collapsed"
)

st.sidebar.markdown(f"""
<div class="sidebar-meta-card">
    <div class="sidebar-meta-header">
        <span>📊</span> Cobertura de Datos
    </div>
    <div class="sidebar-meta-row">
        <span class="sidebar-meta-label">Partidos en BD</span>
        <span class="sidebar-meta-val">{miles(len(df_partidos))}</span>
    </div>
    <div class="sidebar-meta-row">
        <span class="sidebar-meta-label">Registros jugadores</span>
        <span class="sidebar-meta-val">{miles(len(df_jugadores))}</span>
    </div>
    <div class="sidebar-meta-row">
        <span class="sidebar-meta-label">Temporadas</span>
        <span class="sidebar-meta-val">{df_partidos['temporada'].nunique()}</span>
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar.expander("📖 Glosario de siglas"):
    st.markdown(GLOSARIO_HTML, unsafe_allow_html=True)

ctx = {
    'df_partidos': df_partidos,
    'df_cuartos': df_cuartos,
    'df_jugadores': df_jugadores,
    'cat_jugadores': cat_jugadores,
    'cat_equipos': cat_equipos,
    'df_temporadas': df_temporadas,
}

if nav_option == "Resumen":
    resumen.render(ctx)
elif nav_option == "Partidos":
    partidos.render(ctx)
elif nav_option == "Líderes":
    lideres.render(ctx)
elif nav_option == "Ficha":
    ficha.render(ctx)
elif nav_option == "Cuartos":
    cuartos.render(ctx)


# Footer
st.markdown("<div style='height: 48px;'></div>", unsafe_allow_html=True)
st.markdown(f"""
<div class="app-footer">
    <span>🏀 <b>CB Benicarló Analytics Hub</b></span>
    <span class="footer-sep">·</span>
    <span>Datos Oficiales FEB</span>
    <span class="footer-sep">·</span>
    <span>Temporada {df_partidos['temporada'].max()}</span>
</div>
""", unsafe_allow_html=True)
