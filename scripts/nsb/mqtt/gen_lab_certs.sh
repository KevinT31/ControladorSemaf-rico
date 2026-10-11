#!/usr/bin/env bash
# Genera la PKI de LABORATORIO para MQTT+TLS (spec §28) — equivalente Linux/Pi
# de gen_lab_certs.ps1. SOLO PARA LABORATORIO; no commitear claves privadas.
#
# Uso:
#   ./gen_lab_certs.sh                                  # nodos por defecto
#   NODES="nsb-node-01" OBSERVERS="nsb-observer" SERVER_SANS="192.168.1.50" ./gen_lab_certs.sh
#   FORCE=1 ./gen_lab_certs.sh                          # rota la CA
set -euo pipefail
umask 077

NODES="${NODES:-nsb-node-01 nsb-pi-01}"
OBSERVERS="${OBSERVERS:-nsb-observer}"
SERVER_SANS="${SERVER_SANS:-}"
DIAS_CA="${DIAS_CA:-730}"
DIAS="${DIAS:-365}"

[[ "$DIAS_CA" =~ ^[1-9][0-9]*$ && "$DIAS" =~ ^[1-9][0-9]*$ ]] || {
    echo "ERROR: DIAS_CA y DIAS deben ser enteros >= 1" >&2; exit 1;
}
declare -A identidades_vistas=()
for identidad in $NODES $OBSERVERS; do
    [[ "$identidad" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ ]] || {
        echo "ERROR: identidad MQTT invalida: $identidad" >&2; exit 1;
    }
    [[ -z "${identidades_vistas[$identidad]:-}" ]] || {
        echo "ERROR: identidad MQTT duplicada: $identidad" >&2; exit 1;
    }
    identidades_vistas[$identidad]=1
done
(( ${#identidades_vistas[@]} > 0 )) || {
    echo "ERROR: declare al menos un nodo u observador" >&2; exit 1;
}

command -v openssl >/dev/null || { echo "ERROR: openssl no instalado" >&2; exit 1; }
# Un OPENSSL_CONF heredado roto tumba todo openssl
if [[ -n "${OPENSSL_CONF:-}" && ! -f "$OPENSSL_CONF" ]]; then unset OPENSSL_CONF; fi

raiz="$(cd "$(dirname "$0")/../../.." && pwd)"
dir="$raiz/config/nsb/mosquitto/certs"
mkdir -p "$dir"
cd "$dir"

# --- CA de laboratorio ------------------------------------------------------
if [[ -f ca.key && -f ca.crt && "${FORCE:-0}" != "1" ]]; then
    echo "CA existente conservada (FORCE=1 para rotarla)."
else
    [[ -f ca.key ]] && echo "ROTACION: regenerando CA — certs previos dejan de valer."
    openssl genrsa -out ca.key 2048
    openssl req -x509 -new -key ca.key -sha256 -days "$DIAS_CA" -out ca.crt \
        -subj "/CN=nsb-lab-ca"
    echo "CA de laboratorio: ca.crt (valida $DIAS_CA dias)"
fi

# --- Certificado del broker -------------------------------------------------
san="DNS:localhost,IP:127.0.0.1"
for extra in $SERVER_SANS; do
    if [[ "$extra" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        san="$san,IP:$extra"
    else
        san="$san,DNS:$extra"
    fi
done
printf 'subjectAltName=%s\nextendedKeyUsage=serverAuth\n' "$san" > server_ext.cnf
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=localhost"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days "$DIAS" -sha256 -extfile server_ext.cnf
echo "Broker: server.crt (SAN: $san)"

# --- Certificados de cliente por nodo ---------------------------------------
printf 'extendedKeyUsage=clientAuth\n' > client_ext.cnf
for nodo in $NODES $OBSERVERS; do
    openssl genrsa -out "$nodo.key" 2048
    openssl req -new -key "$nodo.key" -out "$nodo.csr" -subj "/CN=$nodo"
    openssl x509 -req -in "$nodo.csr" -CA ca.crt -CAkey ca.key -CAcreateserial \
        -out "$nodo.crt" -days "$DIAS" -sha256 -extfile client_ext.cnf
    echo "Cliente: $nodo.crt (CN=$nodo)"
done

# ACL fail-closed: escritores enumerados; observadores sin write heredado.
acl="$dir/../acl.conf"
{
    echo "# Generado por scripts/nsb/mqtt/gen_lab_certs.sh"
    echo "# Nodos: escritura solo en su prefijo; observadores: lectura global."
    for nodo in $NODES; do
        printf '\nuser %s\ntopic write nsb/%s/#\n' "$nodo" "$nodo"
    done
    for observador in $OBSERVERS; do
        printf '\nuser %s\ntopic read nsb/#\n' "$observador"
    done
} > "$acl"

rm -f ./*.csr server_ext.cnf client_ext.cnf
echo ""
echo "Certificados en: $dir"
echo "Para la Pi copie SOLO: ca.crt + <nodo>.crt + <nodo>.key"
