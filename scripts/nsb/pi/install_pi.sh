#!/usr/bin/env bash
# Instala el nodo NSB en la Raspberry Pi (ejecutar EN la Pi, desde
# /home/pi/nsb-node tras deploy_pi.ps1). Crea venv e instala dependencias
# mínimas desde piwheels (Pi OS Bookworm, Python 3.11).
#
# ESTADO HONESTO: IMPLEMENTED / REQUIRES HARDWARE (D-11) — no validado sin Pi.
set -euo pipefail

base="$(cd "$(dirname "$0")/.." && pwd)"
cd "$base"

if [[ ! -f requirements-nsb-pi.txt || ! -d nsb || ! -d nucleo ]]; then
    echo "ERROR: layout incompleto en $base (¿corrió deploy_pi.ps1?)" >&2
    exit 1
fi

pyver="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
echo "Python detectado: $pyver (piso de sintaxis del proyecto: 3.11 — D-E)"

if [[ ! -d .venv ]]; then
    echo "Creando venv en $base/.venv ..."
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-nsb-pi.txt

echo ""
echo "Verificación mínima (sin hardware):"
python -m nsb --version
python - <<'EOF'
from nsb.actuation.gpio import cargar_pinout
pinout = cargar_pinout("config/nsb/pinout.yaml")
print(f"pinout OK: {sum(len(v) for v in pinout.values())} pines definidos")
EOF

echo ""
echo "Instalación completa. Corrida manual:  ./scripts/run_node.sh"
echo "LEA docs gpio_wiring ANTES de conectar los LEDs."
