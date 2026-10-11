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

# deploy_pi.ps1 admite User/Dest personalizados. Inferir ambos aquí evita
# instalar una unidad que siga apuntando al /home/pi hardcodeado del template.
usuario="${SUDO_USER:-}"
if [[ -z "$usuario" || "$usuario" == "root" ]]; then
    usuario="$(stat -c '%U' "$base")"
fi
[[ "$usuario" =~ ^[a-z_][a-z0-9_-]{0,31}$ && "$usuario" != "root" ]] || {
    echo "ERROR: no se pudo inferir un usuario no-root valido ($usuario)" >&2
    exit 1
}
[[ "$base" =~ ^/[A-Za-z0-9._/-]+$ ]] || {
    echo "ERROR: ruta de instalacion no soportada por la unidad: $base" >&2
    exit 1
}

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
sed -e "s|^User=.*|User=$usuario|" \
    -e "s|^WorkingDirectory=.*|WorkingDirectory=$base|" \
    -e "s|^ExecStart=.*|ExecStart=$base/.venv/bin/python -m nsb run --config config/nsb/node.pi.yaml|" \
    "$unidad" > "$tmp"
install -m 644 "$tmp" /etc/systemd/system/nsb-node.service
systemctl daemon-reload
systemctl enable nsb-node.service
echo "Unidad instalada y habilitada. Comandos útiles:"
echo "  sudo systemctl start nsb-node      # arrancar ahora"
echo "  systemctl status nsb-node          # estado"
echo "  journalctl -u nsb-node -f          # logs en vivo"
