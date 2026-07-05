# Despliegue en Raspberry Pi 4B (spec §37-§39)

**ESTADO HONESTO: IMPLEMENTED / REQUIRES HARDWARE (D-11).** La Pi 4B no
estuvo físicamente disponible durante el desarrollo: todo lo de este
documento está implementado y probado hasta donde Windows permite, pero NO
validado end-to-end en la Pi. Cuando exista el hardware, cada paso se
re-ejecuta y este doc se actualiza con evidencia.

## Reparto PC ↔ Pi (spec §37)

| PC (Windows) | Pi 4B |
|---|---|
| SUMO + HIL gateway, backend, MQTT broker, tests, video offline | Edge node, GPIO 12 LEDs, HIL client, telemetría |

## Layout en la Pi

```
/home/pi/nsb-node/          ← ruta ASCII deliberada (D-04): la "ñ" de
├── nucleo/                    "Diseño Software" no viaja; el layout
├── nsb/                       relativo se conserva y los imports no cambian
├── config/                 ← config/nsb/node.pi.yaml + pinout.yaml
├── certs/                  ← ca.crt + nsb-pi-01.crt/.key (0600), si MQTT
├── scripts/                ← install_pi.sh, run_node.sh, install_systemd.sh
├── requirements-nsb-pi.txt
└── .venv/                  ← creado por install_pi.sh
```

## Procedimiento

```powershell
# EN LA PC — 1. copiar todo por SSH/SCP (OpenSSH de Win11)
.\scripts\nsb\deploy_pi.ps1 -PiHost 192.168.1.50
#   -NodeId nsb-pi-01 por defecto; copia certs SOLO si existen (nunca ca.key)
```

```bash
# EN LA PI — 2. instalar (venv + dependencias mínimas desde piwheels)
cd /home/pi/nsb-node && ./scripts/install_pi.sh

# 3. corrida manual (GPIO; LEER gpio_wiring.md ANTES de conectar LEDs)
./scripts/run_node.sh                     # config/nsb/node.pi.yaml
./scripts/run_node.sh --mode advisory     # sin actuar

# 4. servicio systemd (opcional)
sudo ./scripts/install_systemd.sh
sudo systemctl start nsb-node
journalctl -u nsb-node -f
```

`requirements-nsb-pi.txt` es mínimo a propósito (spec §37: sin dependencias
Pi-only en la base): numpy, pydantic(+settings), PyYAML, psutil, paho-mqtt,
gpiozero(+lgpio). Nada de FastAPI/ultralytics/SUMO en la Pi.

## HIL desde la Pi

`node.pi.yaml` apunta `hil.host` a la IP de la PC (gateway con
`bind_host: 0.0.0.0` o la IP LAN en `gateway.yaml`). El protocolo y los
timeouts son idénticos a localhost (`hil_protocol.md`).

## systemd (spec §39)

`nsb-node.service`: `Restart=on-failure`, `RestartSec=3`, corre como `pi`
con `WorkingDirectory=/home/pi/nsb-node`.

> **systemd mejora la recuperación del PROCESO. NO constituye seguridad
> física independiente**: ante cuelgue del SO o fallo eléctrico, el estado
> seguro depende del Safety Kernel en software y, en un despliegue real, de
> un monitor de conflictos hardware que este prototipo NO tiene
> (`limitations.md`).

No hay watchdog systemd (`WatchdogSec`): exigiría `sd_notify` en el nodo y
sería seguridad aparente sin garantía real; se documenta como mejora futura
en lugar de fingirse.

## Métricas en la Pi (spec §31)

```bash
cd /home/pi/nsb-node && source .venv/bin/activate
python -m nsb bench --out bench_pi4b_aarch64.json
```

Los números de Windows NO se extrapolan; la tabla de la Pi se añadirá a
`experiments.md` cuando se mida en el hardware real.
