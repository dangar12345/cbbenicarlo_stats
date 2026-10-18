import streamlit as st

from components import GLOSARIO, miles
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
    "Vistas del sistema", VISTAS, key="nav_side",
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style="font-size: 0.82rem; color: #CBD5E1; line-height: 1.6;">
    📊 <b>{miles(len(df_partidos))}</b> Partidos en la base de datos<br>
    🏀 <b>{miles(len(df_jugadores))}</b> Registros de jugadores<br>
    ⏱️ <b>{df_partidos['temporada'].nunique()}</b> Temporadas cubiertas
</div>
""", unsafe_allow_html=True)
with st.sidebar.expander("📖 Glosario de siglas"):
    st.markdown(GLOSARIO)

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
st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
st.markdown(f"""
<div style="text-align: center; font-size: 0.8rem; color: #94A3B8; border-top: 1px solid #1E293B; padding-top: 16px;">
    CB Benicarló Analytics Hub · Datos Oficiales FEB · Temporada {df_partidos['temporada'].max()}
</div>
""", unsafe_allow_html=True)
