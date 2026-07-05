# MQTT + TLS de laboratorio (spec §28)

Broker **Mosquitto local** en la PC de desarrollo con TLS y mTLS. Estado:
**VERIFIED en Windows** (broker real, 2026-07-05). No sustituye una
validación contra Azure IoT Hub u otro broker gestionado (ver
`limitations.md`).

## Separación de planos (D-02)

| Plano | Transporte | Por qué |
|---|---|---|
| HIL data plane | TCP JSON-lines dedicado (`nsb/hil`) | latencia, orden estricto request→response |
| Telemetría | **MQTT** (este doc) + JSONL local + HTTP opcional | best-effort, tolerante a pérdida |
| Command/control | API FastAPI existente (JWT+RBAC) | no duplicar autenticación (spec §29) |

MQTT **no** transporta comandos hacia el nodo: el sink no suscribe ningún
tópico y ninguna vía remota puede elevar el modo de autoridad (D-H).

## Tópicos

```
nsb/{node_id}/heartbeat              retained; online/offline + Last Will
nsb/{node_id}/telemetry/decision     un mensaje por decisión
nsb/{node_id}/events/{event}         node_start, node_stop, mode_change, ...
```

## Garantía "la telemetría jamás bloquea el control"

`nsb/comms/mqtt_telemetry.py` (`MqttTelemetrySink`):

- `connect_async` + hilo de red de paho: el lazo de control nunca espera red.
- QoS 0 best-effort: sin broker los eventos se **descartan y se cuentan**
  (`dropped`); el JSONL local sigue siendo la fuente de verdad (D-F).
- Reconexión automática con backoff (1→30 s).
- Dos esperas acotadas FUERA del lazo de control: 2 s al arrancar (conexión
  inicial) y 2 s al cerrar (drenado de la cola); sin ellas las corridas
  cortas pierden los primeros/últimos eventos.
- Config TLS inválida → falla al **arrancar** el nodo, nunca en runtime.
- paho-mqtt se importa perezosamente: `mqtt_enabled=false` no lo requiere.

Demo de pérdida: `python -m nsb demo --id 8` (broker inaccesible a propósito;
el control termina con 10/10 accept y `dropped > 0`).

## Seguridad

- **TLS** con CA de laboratorio propia (no hay claves reales en el repo;
  `config/nsb/mosquitto/certs/` está en `.gitignore`).
- **mTLS**: `require_certificate true` — el cliente debe presentar cert
  firmado por la CA. `use_identity_as_username true` convierte el CN del
  cert (= `node_id`) en el usuario de la ACL.
- **ACL por tópico** (`config/nsb/mosquitto/acl.conf`):
  - `pattern write nsb/%u/#` — cada nodo solo escribe bajo su prefijo.
  - `nsb-observer` — única identidad con `read nsb/#`.
  - Nadie tiene write global; no existen tópicos de comando.
- **Identidad por nodo**: un par cert/clave por `node_id`
  (`nsb-node-01`, `nsb-pi-01`, `nsb-observer`).

## Procedimiento (Windows)

```powershell
# 1. Generar PKI de laboratorio (CA + broker + clientes)
.\scripts\nsb\mqtt\gen_lab_certs.ps1
#    con IP LAN para que la Pi valide el hostname del broker:
.\scripts\nsb\mqtt\gen_lab_certs.ps1 -ServerSans 192.168.1.100

# 2. Levantar el broker TLS (8883)
.\scripts\nsb\mqtt\run_mqtt_broker.ps1 -Tls

# 3. Correr el nodo con telemetría MQTT
cd "Diseño Software"
$certs = "..\config\nsb\mosquitto\certs"
$env:NSB_TELEMETRY__MQTT_ENABLED = "true"
$env:NSB_TELEMETRY__MQTT_CA_CERT = "$certs\ca.crt"
$env:NSB_TELEMETRY__MQTT_CLIENT_CERT = "$certs\nsb-node-01.crt"
$env:NSB_TELEMETRY__MQTT_CLIENT_KEY = "$certs\nsb-node-01.key"
python -m nsb run --source manual --mode advisory --pasos 5

# 4. Observar (otra consola)
& "C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -p 8883 `
    --cafile $certs\ca.crt --cert $certs\nsb-observer.crt `
    --key $certs\nsb-observer.key -t "nsb/#" -v
```

Test de integración opt-in (requiere broker corriendo):

```powershell
$env:NSB_TEST_MQTT = "1"; $env:NSB_TEST_MQTT_TLS = "1"
# + variables NSB_TEST_MQTT_CA/CERT/KEY/SUB_CERT/SUB_KEY (ver el test)
python -m pytest tests/integration/test_mqtt_local.py -q
```

## Rotación de certificados

1. `.\scripts\nsb\mqtt\gen_lab_certs.ps1 -Force` regenera la CA: **todos**
   los certs anteriores dejan de valer (revocación por sustitución de CA —
   suficiente para laboratorio; no hay CRL/OCSP).
2. Redistribuir a la Pi con `deploy_pi.ps1` (copia solo `ca.crt` +
   `<node>.crt/.key`, jamás `ca.key`).
3. Reiniciar broker y nodos. Vigencias por defecto: CA 730 días, hojas 365.

## Limitaciones honestas

- CA de laboratorio ≠ PKI gestionada; sin CRL/OCSP ni HSM.
- Mosquitto local ≠ Azure IoT Hub: la validación cloud real queda fuera de
  esta fase (spec §28 permite empezar local).
- QoS 0: pérdida de telemetría bajo desconexión es **por diseño**; para
  auditoría usar el JSONL local (siempre completo).
