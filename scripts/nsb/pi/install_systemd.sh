#!/usr/bin/env bash
# Instala la unidad systemd del nodo NSB (ejecutar EN la Pi con sudo).
#   sudo ./scripts/install_systemd.sh
#
# systemd reinicia el PROCESO ante fallo; NO es seguridad física (spec §39).
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: ejecutar con sudo" >&2
    exit 1
fi

base="$(cd "$(dirname "$0")/.." && pwd)"
unidad="$base/scripts/systemd/nsb-node.service"
if [[ ! -f "$unidad" ]]; then
    echo "ERROR: no existe $unidad" >&2
    exit 1
fi

install -m 644 "$unidad" /etc/systemd/system/nsb-node.service
systemctl daemon-reload
systemctl enable nsb-node.service
echo "Unidad instalada y habilitada. Comandos útiles:"
echo "  sudo systemctl start nsb-node      # arrancar ahora"
echo "  systemctl status nsb-node          # estado"
echo "  journalctl -u nsb-node -f          # logs en vivo"
