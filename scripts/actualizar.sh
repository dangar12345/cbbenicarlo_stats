#!/usr/bin/env bash
# Actualización completa del proyecto en un solo comando.
#
# Uso:
#   .venv/bin/sh scripts/actualizar.sh                 # flujo completo (scraping incluido)
#   .venv/bin/bash scripts/actualizar.sh --sin-scraper # solo QA + cifrado + repos
#   scripts/actualizar.sh --seasons 2026               # args se pasan al scraper
#
# Pasos:
#   1. Scraper FEB (SQLite) + export a parquet/CSV  [omisible con --sin-scraper]
#   2. QA de reconciliación con correcciones deterministas (--fix) + re-export
#   3. Cifrado de parquet a data/enc/ (clave de .streamlit/secrets.toml)
#   4. Refresco del snapshot de datos en claro en el repo privado (backup)
#   5. Sincronización del repo público (historial fresco)
#
# Requisitos: main limpio (sin cambios sin commitear) y remotes configurados:
#   origin -> cbbenicarlo_stats       backup -> cbbenicarlo_stats_datos
set -euo pipefail
cd "$(dirname "$0")/.."

SCRAPER_ARGS=()
SIN_SCRAPER=0
for arg in "$@"; do
    if [[ "$arg" == "--sin-scraper" ]]; then SIN_SCRAPER=1; else SCRAPER_ARGS+=("$arg"); fi
done

PY=.venv/bin/python
[ -x "$PY" ] || PY=python3

# --- 0. Precondiciones -------------------------------------------------------
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "ERROR: main tiene cambios sin commitear. Comitea o descarta antes de"
    echo "actualizar datos (el sync del repo público publica el árbol commiteado)."
    git status --short | grep -v '^??' | head -5
    exit 1
fi
git rev-parse --verify -q publico >/dev/null || { echo "ERROR: falta la rama publico (git checkout --orphan publico)"; exit 1; }
git remote get-url backup >/dev/null 2>&1 || { echo "ERROR: falta el remote backup (repo privado)"; exit 1; }

if [[ $SIN_SCRAPER -eq 0 ]]; then
    echo "== 1/5 Scraper FEB =="
    $PY scraper.py "${SCRAPER_ARGS[@]+"${SCRAPER_ARGS[@]}"}"
else
    echo "== 1/5 Scraper FEB — OMITIDO (--sin-scraper) =="
fi

echo "== 2/5 QA de reconciliación (--fix) =="
$PY scripts/qa_reconcile.py --fix

echo "== 3/5 Cifrado de parquet =="
$PY scripts/encrypt_data.py

echo "== 4/5 Backup de datos en claro (repo privado) =="
export GIT_INDEX_FILE="$(mktemp /tmp/opencode/idx-backup.XXXX)"
git read-tree main
git add -f data/ .streamlit/secrets.toml
TREE=$(git write-tree)
unset GIT_INDEX_FILE
PARENT=$(git rev-parse -q --verify backup-main >/dev/null && git rev-parse backup-main || git rev-parse main)
if [ "$TREE" = "$(git rev-parse "$PARENT^{tree}")" ]; then
    echo "   sin cambios respecto al snapshot anterior; no se genera commit"
else
    COMMIT=$(git commit-tree "$TREE" -p "$PARENT" -m "Backup: datos sin encriptar ($(date +%Y-%m-%d))")
    git branch -f backup-main "$COMMIT"
    git push backup backup-main:main
fi

echo "== 5/5 Sync del repo público =="
git checkout -q publico
git rm -rq . >/dev/null 2>&1 || true
git restore --source=main --staged --worktree .
if git diff --quiet && git diff --cached --quiet; then
    echo "   repo público ya sincronizado"
else
    git commit -q -m "sync desde main ($(date +%Y-%m-%d))"
    git push origin publico:main
fi
git checkout -q main

echo ""
echo "OK. Datos actualizados, cifrados y publicados; backup refrescado."
