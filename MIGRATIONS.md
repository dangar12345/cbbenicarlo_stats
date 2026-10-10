# Migraciones y QA — Bloque P1 (integridad de datos)

Este bloque cubre cuatro puntos:

1. **Campo `estado`** en `partidos`: `jugado` | `programado` | `suspendido`.
2. **QA de reconciliación**: parciales y actas vs marcador oficial.
3. **Quinteto inicial** en el scraper (`es_titular`, vía `span.cincoInicial` de FEB).
4. **IDs canónicos** de equipos y jugadores con alias históricos.

## Requisitos

- Entorno virtual activo (`.venv`), con pandas + pyarrow (ya instalados).
- Recomendable: copia de seguridad antes de tocar datos:

```bash
cp -r data data.bak_$(date +%Y%m%d)
```

## Orden de ejecución

```bash
# 1) Estado de cada partido (jugado / programado / suspendido)
.venv/bin/python scripts/migrate_estado.py --dry-run   # vista previa
.venv/bin/python scripts/migrate_estado.py

# 2) IDs canónicos + tablas catálogo (equipos_catalogo / jugadores_catalogo)
.venv/bin/python scripts/migrate_ids.py --dry-run      # vista previa
.venv/bin/python scripts/migrate_ids.py

# 3) Reconciliación y correcciones deterministas
.venv/bin/python scripts/qa_reconcile.py               # solo informe
.venv/bin/python scripts/qa_reconcile.py --fix         # aplica correcciones

# 4) (opcional) Reparación de encoding si alguna tanda trae mojibake
.venv/bin/python scripts/fix_encoding.py
```

Cada script termina reexportando `data/*.parquet` y `data/*.csv` desde
`data/benicarlo.db` (la app lee los parquet). Los scripts son **idempotentes**:
se pueden reejecutar sin efectos adicionales.

> **Importante**: tras cualquier migración o `qa_reconcile.py --fix`, **reinicia
> Streamlit** (o vacía la caché del menú de la app). `st.cache_data` sirve los
> dataframes en memoria y seguiría mostrando los datos anteriores.

## Qué hace cada pieza

### scripts/migrate_estado.py

Deriva `partidos.estado`:

| condición | estado |
|---|---|
| `jugado == 1` | `jugado` |
| sin jugar y **fecha pasada** | `suspendido` (p. ej. los 9 de la 2019/2020 por el COVID) |
| sin jugar y fecha futura / sin fecha | `programado` |

Correcciones manuales: `data/estado_overrides.json`

```json
{ "2486982": "jugado" }
```

### scripts/migrate_ids.py

- Crea `equipos_catalogo(equipo_id, nombre_canonico, aliases)` y
  `jugadores_catalogo(jugador_id, nombre_canonico, aliases)`.
- Añade `equipo_local_id` / `equipo_visitante_id` / `equipo_rival_id` a
  `partidos`, `equipo_id` a `cuartos` y `equipo_id` / `jugador_id` a
  `jugadores_partido`.
- El ID es un slug del nombre normalizado (sin acentos ni puntuación), salvo
  que el nombre figure en los ficheros de alias.

Alias históricos (editar a mano cuando haga falta fusionar variantes):

- `data/alias_equipos.json` — ya incluye las 4 denominaciones de CB Benicarló
  (`C.B. BENICARLO`, `MI ARQUITECTO…`, `INTERMAQUINAS…`, `MADERAS SORLI…`)
  → `cb-benicarlo`, y la fusión automática `CB CORNELLA` / `CB. CORNELLÀ`.
- `data/alias_jugadores.json` — fusiones manuales de variantes de grafía.

### scripts/fix_encoding.py

Repara mojibake (UTF-8 decodificado como latin-1) en todas las columnas de
texto de forma idempotente. El scraper actual ya decodifica UTF-8 correctamente
(`fetch_html`), pero este script es la red de seguridad para tandas antiguas o
si FEB cambia cabeceras. Tras ejecutarlo conviene reejecutar
`scripts/migrate_ids.py` (los IDs se derivan de los nombres).

### scripts/qa_reconcile.py

Checks:

| check | descripción | con `--fix` |
|---|---|---|
| C1 | `cuartos.puntos_total` == suma de periodos | recalcula el campo derivado |
| C2 | parciales por equipo == marcador | si hay empate en reglamento y faltan los puntos de prórroga, los atribuye a `ot1` (queda documentado en el informe) |
| C3 | puntos del acta == marcador | **no toca nada**: marca `qa_estado` y recomienda re-scrape |
| C4 | `diferencia_puntos` / `resultado_benicarlo` coherentes | recalcula |
| C5 | partidos jugados sin parciales y/o sin acta | marca `qa_estado` |
| C6 | filas de cuartos duplicadas | solo informa |

Salidas:

- `data/informe_qa.csv` — todas las incidencias con diferencia y acción.
- `partidos.qa_estado` — `ok` / `descuadre_cuartos` / `descuadre_jugadores` /
  `sin_acta`. La app muestra ⚠ en el selector de partidos y una nota bajo el
  marcador para los partidos no `ok`.

**Nunca se inventan datos**: lo único que se corrige offline son campos
derivados y la atribución de puntos de prórroga cuando el empate en reglamento
la hace inequívoca.

## Re-scrape (opcional, para cerrar las incidencias de origen)

Los ~20 partidos con actas incompletas (`descuadre_jugadores` / `sin_acta`) solo
pueden corregirse volviendo a extraerlos de FEB. El scraper acepta temporadas
selectivas (códigos de `SEASON_MAP`):

```bash
# Backfill de quintetos iniciales + actas/parciales incompletos
.venv/bin/python scraper.py --seasons 2019 2020 2021 2022 2023 2024 2025
```

Notas:

- El scraper es **idempotente** (hace `INSERT OR REPLACE` y borra/reinserta
  parciales y actas por partido), pero aun así haz la copia de seguridad.
- Tras el re-scrape, ejecuta en cadena `scripts/fix_encoding.py` (por si FEB
  sirve alguna página con charset mal declarado), `scripts/migrate_ids.py`
  (refresca IDs canónicos desde los nombres) y `scripts/qa_reconcile.py --fix`
  (recalcula `qa_estado` y los exportables).
- El parser actual ya lee las prórrogas correctamente (parsing posicional de
  parciales) y detecta titulares reales (`<span class="cincoInicial">`); si FEB
  no marca ninguno, asume los 5 primeros (fallback documentado en el código).

## P2 · Punto 5 — Contexto de liga

Piezas:

- `data/temporadas_contexto.json` — narrativa curada por temporada
  (competición oficial, hito, resultado_hito). Único punto de edición humana.
- `scraper.py --solo-clasificacion` — extrae la clasificación oficial de
  `clasificacion.aspx` (P, Equipo, PJ, PG, PP, PF, PC, PTs) para cada
  temporada/grupo, tomando la instantánea de la última jornada disputada
  (con retroceso si la tabla sale vacía). `run()` normal también la ejecuta.
- `scripts/migrate_liga.py` — construye la tabla `temporadas` fusionando:
  derivados de partidos (balance, fase alcanzada) + clasificación oficial
  (posición del grupo) + contexto curado (tiene prioridad).
- QA ampliado: **C7** (balance de `temporadas` vs partidos), **C8**
  (temporadas sin fila de contexto), **C9** (temporadas sin clasificación
  oficial del Benicarló).

Orden de ejecución:

```bash
.venv/bin/python scraper.py --solo-clasificacion   # posiciones oficiales
.venv/bin/python scripts/migrate_liga.py           # tabla temporadas
.venv/bin/python scripts/qa_reconcile.py           # valida C7-C9
```

UI resultante: tira *Trayectoria por Temporada* en "Resumen & Trayectoria"
(posición, balance, hito y badge por temporada) y franja de contexto siempre
visible bajo el marcador en "Partidos & Boxscores" (fase, jornada, temporada,
clasificación de la temporada y badge de hito).

## Notas de modelo

- Se mantiene `partidos.jugado` (0/1) por compatibilidad; `estado` es la fuente
  de verdad para la lógica nueva.
- `ot1` acumula los puntos de prórroga cuando el desglose por prórroga no está
  disponible en datos históricos; `ot2` recoge prórrogas adicionales.
- Los IDs canónicos permiten agregar por jugador/equipo aunque cambie el
  patrocinador o la grafía; los nombres crudos se conservan en las columnas
  originales (`equipo`, `jugador`, …).
