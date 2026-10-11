import streamlit as st

from data_loaders import load_data
from theme import CSS
from views import cuartos, ficha, lideres, partidos, resumen

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



ctx = {
    'df_partidos': df_partidos,
    'df_cuartos': df_cuartos,
    'df_jugadores': df_jugadores,
    'cat_jugadores': cat_jugadores,
    'cat_equipos': cat_equipos,
    'df_temporadas': df_temporadas,
}

if nav_option == "Resumen & Trayectoria":
    resumen.render(ctx)
elif nav_option == "Partidos & Boxscores":
    partidos.render(ctx)
elif nav_option == "Líderes & Jugadores":
    lideres.render(ctx)
elif nav_option == "Ficha & Comparador":
    ficha.render(ctx)
elif nav_option == "Análisis de Cuartos":
    cuartos.render(ctx)


# Footer
st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; font-size: 0.8rem; color: #94A3B8; border-top: 1px solid #1E293B; padding-top: 16px;">
    CB Benicarló Analytics Hub · Datos Oficiales FEB · Temporada 2026/2027
</div>
""", unsafe_allow_html=True)
