#!/usr/bin/env python
"""Cifra los parquet que consume app.py para subirlos al repositorio público.

Uso (lee la clave de .streamlit/secrets.toml si no se pasa por entorno):
    .venv/bin/python scripts/encrypt_data.py
    DATA_KEY="<clave>" .venv/bin/python scripts/encrypt_data.py   # alternativa

Generar una clave la primera vez:
    .venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

- Lee data/<nombre>.parquet y escribe data/enc/<nombre>.parquet.enc (Fernet).
- Idempotente: se puede relanzar tras cada actualización de datos.
- Los parquet en claro NO se suben (gitignore); el scraper y las migraciones
  siguen trabajando con ellos en local. El cifrado es el último paso antes
  de publicar.
- La clave vive en .streamlit/secrets.toml (local) o en Secrets de Streamlit
  Community Cloud. NUNCA en git.
"""
import os
import sys
import tomllib

from cryptography.fernet import Fernet

# Los parquet que lee app.py (los catálogos son opcionales en runtime,
# pero se cifran para que el despliegue sea completo).
PARQUETS = (
    "partidos",
    "cuartos",
    "jugadores",
    "jugadores_catalogo",
    "equipos_catalogo",
    "temporadas",
)


def _clave():
    """DATA_KEY del entorno o, en su defecto, de .streamlit/secrets.toml."""
    clave = os.environ.get("DATA_KEY")
    if clave:
        return clave
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        ".streamlit", "secrets.toml")
    if os.path.exists(ruta):
        with open(ruta, "rb") as fh:
            datos = tomllib.load(fh)
        return datos.get("DATA_KEY")
    return None


def main():
    clave = _clave()
    if not clave:
        sys.exit(
            "ERROR: no hay DATA_KEY ni en el entorno ni en .streamlit/secrets.toml.\n"
            "Genera una y guardala en secrets.toml (ver docstring)."
        )
    try:
        fernet = Fernet(clave)
    except Exception as e:
        sys.exit(f"ERROR: DATA_KEY no es una clave Fernet valida: {e}")

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base, "data")
    enc_dir = os.path.join(data_dir, "enc")
    os.makedirs(enc_dir, exist_ok=True)

    for nombre in PARQUETS:
        origen = os.path.join(data_dir, f"{nombre}.parquet")
        destino = os.path.join(enc_dir, f"{nombre}.parquet.enc")
        if not os.path.exists(origen):
            print(f"  ! {nombre}.parquet no existe, se omite")
            continue
        with open(origen, "rb") as fh:
            blob = fh.read()
        with open(destino, "wb") as fh:
            fh.write(fernet.encrypt(blob))
        print(f"  + {nombre}.parquet -> enc/{nombre}.parquet.enc ({len(blob):,} B)")

    print("\nOK. Recuerda:")
    print("  1. Los *.parquet/*.csv/*.db en claro NO se commitean (gitignore).")
    print("  2. Pegar DATA_KEY en Secrets de Streamlit Community Cloud.")


if __name__ == "__main__":
    main()
