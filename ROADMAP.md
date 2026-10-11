# CB Benicarló Analytics Hub — Resumen, pendientes y retomada de sesión

> **Qué es este documento**: handoff para retomar el proyecto en una sesión nueva.
> Generado el 10/10/2026. Estado: **P1, P2, versión móvil y protección de datos
> completados; repos GitHub creados (app con historial fresco + backup privado con
> datos en claro, ver §3)**. Pendiente: bloque P3 y el deploy en Streamlit
> Community Cloud (pegar DATA_KEY en Secrets).

---

## 0. Retomar la sesión en 2 minutos

```bash
cd ~/benicarloStats
.venv/bin/streamlit run app.py --server.headless true --server.port 8501
```

- **App**: `app.py` (Streamlit, 4 vistas en el sidebar). Lee `data/*.parquet`
  (o los descifra de `data/enc/*.enc` con `DATA_KEY`, ver §3).
- **Datos**: `data/benicarlo.db` (SQLite = fuente de verdad) → exportados a
  parquet/CSV. **Tras cualquier migración/QA, reiniciar Streamlit** (`st.cache_data`
  sirve datos en memoria) y relanzar `scripts/encrypt_data.py` para regenerar los
  `.enc` que van al repo.
- **Scraper FEB**: `scraper.py` (partidos, actas, parciales, titulares, clasificación).
  Idempotente. `--seasons 2025` para selectivo, `--solo-clasificacion` para tablas.
- **Migraciones/QA**: `scripts/` (`migrate_estado`, `migrate_ids`, `migrate_liga`,
  `qa_reconcile`, `fix_encoding`). Orden y detalles en **`MIGRATIONS.md`**.
- **Contexto curado**: `data/temporadas_contexto.json` (hitos), `data/alias_*.json`
  (IDs canónicos), `data/estado_overrides.json`.
- **Conviene saber**: flujo de trabajo con validación Playwright por ronda
  (desktop 1440x900 + móvil 390x844) y detector de diseño
  (`.opencode/skills/impeccable/scripts/impeccable detect --json app.py`).
  Patrón útil ya probado: cambiar de vista en desktop y luego redimensionar a
  móvil (el radio del sidebar no responde en viewport táctil).

**Commits** (rama `main`):

| Commit | Contenido |
|---|---|
| `c6d1b1a` | **Móvil**: gráficas legibles, tarjetas con espaciado, marcador alineado |
| `a4ac37e` | Tooltips legibles, tema oscuro unificado, Deploy oculto |
| `7757685` | **P1**: estado de partido, QA C1-C10, titulares, IDs canónicos, encoding |
| `21762f0` | **P2.5**: contexto de liga (clasificación oficial + hitos) |
| `8b2c860` | **P2**: split local/visitante |
| `67fc219` | **P2**: head-to-head + cortes de rankings + fechas exactas |
| `090308b` | **P2**: evolución interanual por jugador |
| `4b4addc` | **P2**: narrativa de partido (cerrados, rachas, remontadas) |

---

## 1. Resumen de todo lo hecho

### UI / UX (base, commit `a4ac37e`)
- Tooltips de gráficas ilegibles (blanco sobre blanco) → template oscuro propio +
  `hoverlabel` + red de seguridad CSS; `hovertemplate` con contexto en las 5 gráficas.
- Tema Streamlit oscuro unificado (`.streamlit/config.toml`) para selectores,
  tablas y pestañas; botón Deploy ocultado; scrollbars/selección/foco con la paleta.
- Ejes de la gráfica de anotación (`19/20 … 25/26`), leyendas fuera del modo,
  cifras tabulares, tablas alineadas.

### P1 — Integridad de datos (commit `7757685`)
- **`estado`** en `partidos`: `jugado` / `programado` / `suspendido` (los 9 de la
  2019/2020 por COVID) + overrides manuales.
- **QA de reconciliación** (`qa_reconcile.py`): checks **C1-C10** (parciales y actas
  vs marcador, campos derivados, cobertura, duplicados, contexto de temporada,
  fechas nulas). Nunca inventa datos; informe en `data/informe_qa.csv`.
- **Titulares reales** (`es_titular` vía `span.cincoInicial` de FEB) — 1.885 en 189
  partidos — y parsing posicional de parciales (las prórrogas se perdían).
- **IDs canónicos** de equipos/jugadores + alias históricos (4 nombres de
  Benicarló → `cb-benicarlo`; tablas catálogo `*_catalogo`).
- **Encoding**: mojibake de FEB corregido en 3 capas (`fetch_html`, `reparar_texto`,
  `fix_encoding.py`).
- **Fechas exactas 234/234** desde la ficha oficial (la fecha nominal de jornada NO
  vale: hay partidos movidos un día).

### P2 — Narrativa deportiva (commits `21762f0` → `4b4addc`)
1. **Contexto de liga**: clasificación oficial scrapeada (`clasificacion.aspx`),
   tabla `temporadas` con hitos y badges (`ELIMINADO EN 1/8`, `CANCELADA`, `EN CURSO`),
   tira *Trayectoria por Temporada* (tabla desktop → tarjetas móvil) y franja de
   contexto bajo cada marcador.
2. **Split Local/Visitante**: CASA 57.6% vs FUERA 36.0% de victorias, con narrativa
   de ventaja de campo por temporada (el 14-0 en casa de 2021/2022).
3. **Head-to-head por rival**: historial, medias, últimos cruces (59 rivales
   canónicos; CB PRAT 1-9 es el bestia negro).
4. **Cortes en rankings**: sliders de partidos/minutos mínimos contra el sesgo de
   promedios.
5. **Evolución interanual por jugador**: gráfica + tabla por temporada + tendencia
   (Libroia +1.0 PPP/temporada en 4 años).
6. **Narrativa de partido**: cerrados (±5): 24-38 en 62 partidos; rachas (9 V, 10 D);
   remontadas al descanso: 19, la mayor un -11 remontado a 68-65 en FIBWI PALMA;
   filtro "Cerrados (±5)" en el explorador de partidos.

---

## 2. COMPLETADO — Versión móvil (10/10/2026)

Problemas confirmados con Playwright a **390×844** y corregidos. Resumen de lo aplicado:

### 2.1 Gráficas ilegibles (Top 10 Anotadores y similares) ✅
- **Etiquetas de categoría**: `truncar_nombre()` corta a 18 chars con "…" en el eje Y
  de `fig_scorers`; el nombre completo vive en el tooltip (`custom_data`) y en la tabla.
- **Etiquetas de valor**: `textposition='outside'` con holgura de rango ×1.22 — las 10
  etiquetas (1325…334) se ven completas, sin recorte.
- **Leyendas centradas** (`xanchor="center", x=0.5`, size 11) en las 5 gráficas — medidas
  en móvil: caben completas en 358px sin cortarse por la derecha.
- **Altura**: `fig_scorers` a 380px para que 10 barras no se estrujen.
- **Modebar** de Plotly y anclas de título ocultos en ≤720px (CSS).

### 2.2 "Calendario de Próximos Partidos" sin espaciado ✅
- Las 6 tarjetas pasan de `st.columns(6)` (gap 0px medido, wrappers con `margin -16px`)
  al patrón `cards-row` de la Narrativa: **24px** de separación vertical medida.

### 2.3 Marcador descuadrado con nombres de equipo largos ✅
- `.sb-grid`: grid de filas fijas (nombres en fila 1, marcadores en fila 2) — los dos
  marcadores comparten top aunque el nombre ocupe 1 o 3 líneas (verificado: 217px =
  217px, antes 35px de desfase).
- `.team-name` con `text-wrap: balance` + `overflow-wrap: break-word`; tamaños de fuente
  del marcador reducidos en ≤720px.
- **Separadores irrompibles** (`\u00A0·` como sufijo de cada parte) en la franja
  `.match-context`, la cabecera del marcador y la línea Campo/Árbitros: el "·" y el "|"
  viajan con el texto y **nunca empiezan línea** (verificado desglosando el DOM línea a
  línea).

### 2.4 Extras + retos añadidos por el usuario ✅
- **Tarjetas apiladas "pegadas" en todas las secciones** (KPIs, líderes, cuartos): el gap
  de columnas apiladas pasa de 16px a **24px** en ≤720px.
- **Tablet / ventanas estrechas (641-1023px)**: las filas de 4-5 tarjetas se aplastaban
  en columnas de 105-150px → `min-width: 280px` fuerza envolver a 2 por fila; las filas
  de gráficas [3,2] conservan su proporción. Desktop (≥1024) intacto.
- Icono 🔗 de anclaje de títulos oculto en móvil.
- Tablas (`st.dataframe`) con scroll horizontal ✅ comportamiento esperado.
- Verificado a 360, 390, 414, 700, 800, 1023 y 1440px.

### Checklist de verificación móvil (ejecutada)
```bash
# Playwright: por cada vista en 390/414/360 (y tablet 700-1023, desktop 1440):
#  - Resumen: KPIs, gráficas, split, H2H, narrativa, trayectoria, calendario
#  - Partidos: marcador (con rival de nombre largo), parciales, acta
#  - Líderes: Top 10 (recortes), tabla completa, evolución
#  - Cuartos: tarjetas, gráfica, tabla
# detector: .opencode/skills/impeccable/scripts/impeccable detect --json app.py → []
```

---

## 3. COMPLETADO — Protección de datos para despliegue público (10/10/2026)

**Decisión del usuario**: la app es **pública** (sin contraseña de acceso). Lo que se
protege son los **ficheros del repo**: nadie debe poder descargar los datos crudos
desde GitHub. Se aplicó la **opción A** (cifrado Fernet con clave fuera de git); la
opción C (puerta de contraseña) se llegó a implementar y se desmontó por decisión del
usuario.

### Lo aplicado
- **`scripts/encrypt_data.py`**: cifra los 6 parquet que lee la app (partidos, cuartos,
  jugadores, jugadores_catalogo, equipos_catalogo, temporadas) a `data/enc/*.parquet.enc`
  con Fernet. Idempotente; relanzar tras cada actualización de datos:
  `DATA_KEY="<clave>" .venv/bin/python scripts/encrypt_data.py`.
- **`app.py`**: `_leer_parquet()` prefiere `data/enc/` (descifra **en memoria** con
  `DATA_KEY`) y cae al parquet en claro para desarrollo local sin secrets. `_secreto()`
  lee de `st.secrets` (Cloud) o de variable de entorno (local). Si hay `.enc` sin clave
  y sin parquet en claro, el error explica cómo configurar `DATA_KEY`.
- **`.gitignore`** (nuevo): `data/*.parquet`, `data/*.csv`, `data/*.db`,
  `.streamlit/secrets.toml`, `data.bak_*/`, `__pycache__/`, `.playwright-cli/`. Los datos
  en claro fueron des-trackeados con `git rm --cached` (17 ficheros).
- **`requirements.txt`** (nuevo) con versiones fijadas: streamlit 1.65.0, pandas 3.0.6,
  pyarrow 25.0.1, plotly 7.1.0, cryptography 50.0.2.
- **`.streamlit/secrets.toml.example`**: plantilla documentada (el real vive en
  `.gitignore`; contiene la DATA_KEY real en local).
- En git solo quedan de `data/`: los 4 JSON de contexto (alias canónicos,
  estado_overrides, temporadas_contexto): nombres e hitos públicos de FEB, sin
  estadísticas de partidos; necesarios para scraper/migraciones en local.

### Verificación (simulación de Cloud)
- Parquet en claro apartados temporalmente → la app sirvió datos solo desde `.enc`
  (234 partidos cargados, gráficas y tablas correctas).
- Tras restaurar los parquet en claro (flujo scraper/migraciones en local), la app
  sigue funcionando: usa `.enc` si hay clave; fallback a claro si no la hay.

### Historial de git y datos en claro (RESUELTO 10/10/2026)
Los commits anteriores trackeaban `data/*.parquet`, `*.csv` y `benicarlo.db` en claro:
los blobs siguen en el historial **local**, pero el repo público se publicó con
historial fresco (ver Repositorios) y el historial completo quedó preservado en el
repo privado de backup. El `.gitignore` protege los commits futuros. Resumen de
opciones aplicadas:

1. **Repo público con historial fresco** (recomendada; no toca el repo local):
   ```bash
   git checkout --orphan publico
   git add -A
   git commit -m "CB Benicarlo Analytics Hub (historial fresco, datos cifrados)"
   git push https://github.com/<usuario>/<repo>.git publico:main
   # El main local conserva el historial completo de desarrollo
   ```
2. **Reescribir el historial en sitio**: `git filter-repo --path data/ --invert-paths`
   (destructivo: rompe los hashes referenciados en este documento; backup antes).

Honestidad sobre el modelo de amenazas: la app pública SIEMPRE revela los agregados
que muestra (alguien con la URL puede transcribir la UI); lo que no puede hacer es
descargarse la base de datos cruda. Si el dato llegara a ser realmente sensible, el
siguiente escalón es la opción B (bucket privado) o limitar la visibilidad.

### Repositorios en GitHub (10/10/2026)

| Repo | Visibilidad | Contenido |
|---|---|---|
| `dangar12345/cbbenicarlo_stats` | privado* | **Repo de la app**: historial fresco (1 commit, `a8e2618`), datos solo cifrados en `data/enc/`. Listo para hacerlo público o desplegar en Cloud. |
| `dangar12345/cbbenicarlo_stats_datos` | privado | **Backup "por si acaso"**: rama `main` = datos SIN encriptar en la raíz (parquet, CSV, `benicarlo.db`, `secrets.toml` con la DATA_KEY) + rama `historial` = historial completo de desarrollo. |

*Privado de momento; puede pasarse a público en cualquier momento sin riesgo
porque el historial no contiene datos en claro.

**Remotes locales**: `origin` → `cbbenicarlo_stats` (SSH alias
`github.com-personal`), `backup` → `cbbenicarlo_stats_datos`.

**Flujo de trabajo (importante)**: el desarrollo sigue en `main` local
(historial completo). El repo público recibe **historial fresco**, nunca `main`
directo (arrastraría el historial con datos en claro). Para publicar cambios:

```bash
# 1. Terminar el trabajo en main y commitear
git checkout publico
git rm -rq .
git restore --source=main --staged --worktree .
git commit -m "sync desde main"
git push origin publico:main
git checkout main
```

Y si los datos cambiaron: `scripts/encrypt_data.py` ANTES del sync (los `.enc`
son lo que viaja al repo público).

Para refrescar el backup de datos en claro (repo privado, rama `main`):

```bash
export GIT_INDEX_FILE=/tmp/opencode/idx-backup
git read-tree main
git add -f data/*.parquet data/*.csv data/benicarlo.db .streamlit/secrets.toml
COMMIT=$(git commit-tree $(git write-tree) -p main -m "Backup: datos en claro")
unset GIT_INDEX_FILE
git branch -f backup-main $COMMIT && git push backup backup-main:main
```

### Checklist de despliegue en Community Cloud
- [x] `requirements.txt` con versiones fijadas
- [x] `.gitignore` aplicado y `git rm --cached` de los datos en claro
- [x] `.streamlit/secrets.toml` no commiteado (en `.gitignore`)
- [x] Simulación local: app sirviendo desde `data/enc/` con `DATA_KEY` en secrets
- [x] Repo con **historial fresco** subido a GitHub (verificado: `data/` solo
      contiene `.enc` + JSONs de contexto; 1 commit)
- [x] Backup privado con datos en claro + historial completo creado y subido
- [ ] En Cloud: *New app* → repo `dangar12345/cbbenicarlo_stats` → *Advanced
      settings → Secrets*, pegar `DATA_KEY = "..."`
- [ ] Tras el primer deploy: comprobar que la app carga con datos (234 partidos)

## 4. P3 — hecho y pendiente (11/10/2026)

### Completado
- **Ficha & Comparador de Jugadores** (5ª vista): ficha individual con KPIs de
  carrera (PPP/RPP/APP/VPP, % titularidad, TS%), trayectoria por temporada,
  split titular/suplente, temporada a temporada y bitácora de últimos 10
  partidos; comparador con radar normalizado (PPP/RPP/APP/ROB/TAP/VPP),
  filtro de temporada y tabla con la ventaja de cada métrica.
- **Tests**: 41 en `tests/` (parsers del scraper y saneado de encoding,
  `derivar_estado`/alias de `data_utils`, invariantes de las exportaciones:
  marcadores, cuartos, acta vs marcador, IDs canónicos). `pytest tests/`.
- **Diccionario de datos**: `docs/DICCIONARIO_DATOS.md` (esquema SQLite completo,
  parquet, métricas derivadas, estados QA, ficheros de contexto).
- **`scripts/actualizar.sh`**: actualización en un comando — scraper (omisible
  con `--sin-scraper`) → QA `--fix` → cifrado → backup de datos en claro →
  sync del repo público. Verificado de punta a punta.

### Pendiente (P3, opcional)
- Exportaciones (CSV/PNG) desde la UI — hoy deliberadamente no hay, por la
  protección de datos.
- Clasificación completa del grupo como vista propia (ahora vive en el contexto
  de temporada y la franja del marcador).
- Watermarking de datos si algún día se comparten ficheros fuera del club.
