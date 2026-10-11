"""Carga de datos: parquet cifrado (data/enc) con fallback en claro."""
import os

import pandas as pd
import streamlit as st

from data_utils import derivar_estado

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

