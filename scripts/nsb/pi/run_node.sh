#!/usr/bin/env bash
# Arranca el nodo NSB en la Pi con la config de Pi (GPIO + HIL hacia la PC).
# Uso: ./scripts/run_node.sh [args extra de `python -m nsb run`]
#   p. ej.: ./scripts/run_node.sh --mode advisory
set -euo pipefail

base="$(cd "$(dirname "$0")/.." && pwd)"
cd "$base"                       # cwd = raíz del layout: rutas relativas de config
# shellcheck disable=SC1091
source .venv/bin/activate
exec python -m nsb run --config config/nsb/node.pi.yaml "$@"
