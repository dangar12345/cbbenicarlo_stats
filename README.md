# 🏀 CB Benicarló · Analytics Hub

Dashboard de estadísticas del CB Benicarló con datos oficiales de la FEB
(2019/2020 – 2026/2027): 234 partidos, boxscores completos, análisis por
cuartos, head-to-head por rival y evolución interanual por jugador.

**Demo**: desplegada en Streamlit Community Cloud (ver link cuando esté activa).

## Funcionalidades

- **Resumen & Trayectoria**: KPIs históricos, victorias/derrotas por temporada,
  split local/visitante, head-to-head por rival (59 rivales canónicos),
  narrativa de partidos (cerrados, rachas, remontadas) y trayectoria por
  temporada con hitos.
- **Partidos & Boxscores**: explorador con filtros (temporada, fase, resultado)
  y acta completa por partido con analítica avanzada (TS%, eFG%, NetRtg).
- **Líderes & Jugadores**: rankings con cortes por minutos/partidos, Top 10
  anotadores, récords y evolución interanual por jugador.
- **Análisis de Cuartos**: puntos promedio y balance por periodo (1Q-4Q).

## Stack

Streamlit · Plotly · pandas/pyarrow · SQLite (scraper propio de FEB).

## Estructura

```
app.py                  # Aplicación Streamlit (4 vistas)
scraper.py              # Scraper idempotente de FEB (partidos, actas, clasificación)
data_utils.py           # Utilidades de datos derivados
scripts/                # Migraciones, QA de reconciliación (C1-C10), cifrado
data/enc/               # Datos cifrados (Fernet) — lo único que viaja al repo
MIGRATIONS.md           # Orden y detalle de migraciones/QA
ROADMAP.md              # Estado del proyecto y handoff
```

## Ejecución en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Los datos viajan **cifrados** en `data/enc/*.parquet.enc`; la clave `DATA_KEY`
vive fuera del repositorio (en `st.secrets` o variable de entorno). Para
desarrollar con los datos en claro, coloca los parquet en `data/` (la app los
usa como fallback) o configura `DATA_KEY` en `.streamlit/secrets.toml`
(plantilla: `.streamlit/secrets.toml.example`). Tras actualizar datos:

```bash
.venv/bin/python scripts/encrypt_data.py   # regenera data/enc/
```

## Protección de datos

El repositorio público no contiene estadísticas en claro: los datasets van
cifrados con Fernet y la clave de descifrado solo existe en los *Secrets* de
Streamlit Community Cloud. El scraper y las migraciones se ejecutan en local
con los ficheros en claro (ignorados por `.gitignore`).
