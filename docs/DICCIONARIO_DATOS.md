# Diccionario de datos — CB Benicarló Analytics Hub

> Fuente de verdad: `data/benicarlo.db` (SQLite, alimentado por `scraper.py`).
> De ahí se exportan `data/*.parquet` y `data/*.csv` (`data_utils.exportar_sqlite_a_archivos`),
> y de los parquet se cifran `data/enc/*.parquet.enc` para el repo público
> (`scripts/encrypt_data.py`). Última revisión: 11/10/2026.

## Arquitectura del dato

```
FEB (web) ──scraper.py──► benicarlo.db ──exportar_sqlite_a_archivos──► *.parquet / *.csv
                              │                                              │
                              └── qa_reconcile.py (checks C1-C10, --fix)      └── encrypt_data.py ──► data/enc/
```

- **Los parquet son la única entrada de `app.py`** (nunca lee el SQLite).
- `estado` y `qa_estado` se deriva/guarden en la exportación; si faltan, `app.py`
  los regenera al vuelo (`derivar_estado`).

## Tablas SQLite

### `partidos` (234 filas) — un registro por partido del club
| Columna | Tipo | Descripción |
|---|---|---|
| `partido_id` | INTEGER PK | ID interno (autonumérico; no es el de FEB) |
| `temporada` | TEXT | `AAAA/BBBB` (ej. `2025/2026`) |
| `grupo_id`, `grupo_nombre` | INT, TEXT | Grupo de competición (ej. Liga Regular "ESTE") |
| `fase_tipo` | TEXT | `Liga Regular` / `Playoff` |
| `jornada_id`, `jornada_nombre` | INT, TEXT | Jornada; el nombre puede incluir fase (`J26(18/04/2026)`) |
| `fecha`, `hora` | TEXT | Fecha real de la ficha oficial (no la nominal de jornada; puede diferir ±1 día). `hora` puede ser NULL |
| `equipo_local`, `equipo_visitante` | TEXT | Nombres según FEB |
| `puntos_local`, `puntos_visitante` | INT | Marcador oficial |
| `es_benicarlo_local` | INT (0/1) | Condición del club |
| `nombre_benicarlo`, `equipo_rival` | TEXT | Nombre del club según FEB y rival canónico |
| `puntos_benicarlo`, `puntos_rival`, `diferencia_puntos` | INT | Marcador desde la óptica del club (deriva del oficial) |
| `resultado_benicarlo` | TEXT | `Victoria` / `Derrota` / vacío si no jugado |
| `jugado` | INT (0/1) | 1 = con marcador final |
| `arbitros`, `cancha` | TEXT | De la ficha oficial; pueden ser NULL (→ 'N/D' en la app) |
| `estado` | TEXT | `jugado` / `programado` / `suspendido` (los 9 de 2019/2020 por COVID; override manual en `data/estado_overrides.json`) |
| `equipo_local_id`, `equipo_visitante_id`, `equipo_rival_id` | TEXT | IDs canónicos de catálogo |
| `qa_estado` | TEXT | `ok` / `descuadre_jugadores` / `descuadre_cuartos` / `sin_acta` |

### `jugadores_partido` (3.842 filas) — una fila por jugador y partido (acta)
| Columna | Descripción |
|---|---|
| `id` INTEGER PK, `partido_id` FK → partidos | |
| `temporada`, `equipo`, `es_benicarlo` (0/1) | Contexto de la ficha |
| `es_titular` (0/1) | Real, desde `span.cincoInicial` de FEB (P1); 1.885 titulares en 189 partidos |
| `dorsal` | Dorsal en esa ficha |
| `jugador` | Nombre según FEB (sin normalizar; usar `jugador_id` para agrupar) |
| `jugador_id` | **ID canónico** (`jugadores_catalogo`): la clave para agrupar alias e históricos |
| `minutos`, `puntos` | Carga y anotación |
| `t2/t3/tc/tl_*` | `anotados`, `intentados`, `pct` por tipo de tiro |
| `rebotes_ofensivos/defensivos/totales` | |
| `asistencias`, `recuperaciones`, `perdidas` | |
| `tapones_favor/contra`, `mates` | |
| `faltas_cometidas/recibidas` | |
| `valoracion` | Valoración FEB de la acta |
| `mas_menos` | +/- mientras en pista (fuente: acta FEB) |
| `equipo_id` | ID canónico de equipo |

### `cuartos` (398 filas) — parciales por periodo
`partido_id` FK, `equipo`, `es_benicarlo`, `q1..q4`, `ot1`, `ot2`, `puntos_total`, `equipo_id`.
Prórrogas en columnas separadas (parsing posicional corregido en P1; antes se perdían).

### `clasificacion` (220 filas) — clasificación oficial scrapeada
`temporada`, `grupo`, `jornada_id/nombre` (instante del scrape), `posicion`, `equipo`,
`equipo_id`, `es_benicarlo`, `pj/pg/pp/pf/pc`, `puntos`, `racha`.
Alimenta la tabla `temporadas` y la franja de contexto de la vista Partidos.

### `temporadas` (8 filas) — una fila por temporada, contexto curado
`temporada`, `competicion`, `grupo`, `fase_alcanzada`, `posicion_grupo`,
`hito` (narrativa), `resultado_hito` (`ascenso`/`campeon`/`permanencia`/
`eliminado_playoff`/`cancelada`/`en_curso`), `balance_v/d`, `fuente`.

### Catálogos canónicos (P1)
- `equipos_catalogo` (117): `equipo_id` → `nombre_canonico` + `aliases`.
  Los 4 nombres históricos del club resuelven a `cb-benicarlo`.
- `jugadores_catalogo` (807): `jugador_id` → `nombre_canonico` + `aliases`.

### `partidos_qa` (234) — espejo del `qa_estado` por partido.
`sqlite_sequence` — interna de SQLite (autonuméricos).

## Métricas derivadas (fórmulas de la app)

| Métrica | Fórmula |
|---|---|
| TS% | `PTS / (2 × (TCI + 0.44 × TLI)) × 100` |
| eFG% | `(TCA + 0.5 × T3A) / TCI × 100` |
| NetRtg (por partido) | `+/- / MIN × 53.3` (estimación por minuto escalada a 100 posesiones) |
| Valoración | La que publica el acta FEB (no recalculada) |

## Estados y calidad (`qa_estado`)

| Valor | Significado | Comportamiento en la app |
|---|---|---|
| `ok` | Acta y parciales cuadran con el marcador oficial | Sin aviso |
| `descuadre_jugadores` | El acta no suma el marcador oficial (origen FEB incompleto) | Aviso ⚠ bajo el marcador |
| `descuadre_cuartos` | Los parciales no suman el marcador | Aviso ⚠ |
| `sin_acta` | Faltan parciales o acta | Aviso ⚠; el marcador oficial manda siempre |

Los checks C1-C10 y su detalle viven en `scripts/qa_reconcile.py`; el informe
corriente se escribe en `data/informe_qa.csv` (no versionado).

## Ficheros de contexto (versionados en git)

| Fichero | Contenido |
|---|---|
| `data/alias_equipos.json` | Alias → `equipo_id` canónico |
| `data/alias_jugadores.json` | Alias → `jugador_id` canónico |
| `data/estado_overrides.json` | Overrides manuales de `estado` (COVID 2019/2020) |
| `data/temporadas_contexto.json` | Hitos curados por temporada (fuente de `temporadas`) |

## No versionado (local / backup privado)

`data/*.parquet`, `data/*.csv`, `data/*.db`, `data/informe_qa.csv` (en claro),
`data/enc/*.parquet.enc` (en el repo público), `.streamlit/secrets.toml` (DATA_KEY).
Snapshot en claro actualizado en `cbbenicarlo_stats_datos` (rama `main`).
