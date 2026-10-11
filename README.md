# 🏀 CB Benicarló · Analytics Hub

📊 Estadísticas oficiales del CB Benicarló en FEB: 234 partidos, boxscores
completos y analítica avanzada desde la temporada 2019/20 hasta hoy.

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
app.py                  # Entrada: config, tema, sidebar y dispatch (88 líneas)
theme.py                # CSS del tema oscuro
components.py           # Helpers de composición HTML (tarjetas, badges)
charts.py               # Estilo compartido de gráficas
data_loaders.py         # Carga: parquet cifrado (data/enc) + fallback local
views/                  # Una función render(ctx) por vista:
    resumen.py          #   Trayectoria, KPIs, split, H2H, narrativa, calendario
    partidos.py         #   Explorador de partidos, marcador, boxscores
    lideres.py          #   Rankings, Top 10, evolución interanual
    ficha.py            #   Ficha de jugador y comparador (radar)
    cuartos.py          #   Análisis por cuarto
data_utils.py           # Utilidades de datos derivados
tests/                  # Parsers del scraper, invariants de datos (pytest)
docs/DICCIONARIO_DATOS.md  # Esquema y significado de todas las tablas
scripts/                # Migraciones, QA (C1-C10), cifrado, actualizar.sh
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
Streamlit Community Cloud. El **scraper** (la herramienta que reconstruye el
dataset) tampoco se publica: vive en un repositorio privado de backup junto a
los datos sin encriptar. Las migraciones y el scraper se ejecutan en local con
los ficheros en claro (ignorados por `.gitignore`).
