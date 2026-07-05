# Red team F3+F4 (spec §46) — 2026-07-05

Revisión adversarial del código nuevo de F3 (MQTT/PKI/Pi) y F4 (video/GT).
Contexto: F0–F2 tuvieron revisión adversarial en una sesión previa; para
F3/F4 no hubo revisor adicional disponible — la revisión la hizo el autor
contra la checklist completa de §46, con verificación empírica de cada
sospecha.

## Hallazgos corregidos

| # | Hallazgo | Evidencia | Fix | Retest |
|---|---|---|---|---|
| 1 | `inf` del pipeline de visión atraviesa `max(0.0, x)` y revienta el contrato a mitad de corrida (un frame degenerado tumba todo el video) | `max(0.0, inf) == inf` verificado en REPL | `_finito()` en `nsb/vision/provider.py`: no-finito o negativo → 0.0 + warning | `test_metricas_no_finitas_se_sanean_a_cero` PASS |
| 2 | `cv2.imwrite` falla silenciosamente con rutas no-ASCII en Windows — gt-sample NUNCA funcionaría bajo "Diseño Software" | `imwrite(...ñ...) == False` verificado en REPL | `imencode('.png')+tofile()` en `ground_truth.py` | `test_sample_frames_video_sintetico` (out dir con "ñ") PASS |
| 3 | Carrera de arranque/cierre del sink MQTT: eventos QoS 0 perdidos en corridas cortas y Last Will disparado pese a cierre limpio | corrida real: solo heartbeats llegaron al broker | esperas acotadas (2 s) de conexión y drenado FUERA del lazo de control (D-I) | corrida real: online→node_start→5 decisiones→node_stop→offline ✓ |
| 4 | Heartbeat retained hacía frágil el test de integración (llega el `offline` viejo antes del `online` fresco) | fallo real del test | aserción por contenido (`"online" in heart`), no por orden | `test_mqtt_local` PASS con broker real |

## Verificado sin hallazgo (checklist §46)

- **Verdes conflictivos / bypass Safety Kernel**: sin cambios en F3/F4 al
  kernel; fuente video solo ADVISORY (CLI lo fuerza); demo 7 y gate tests PASS.
- **Activación remota de Direct Lab**: el sink MQTT no ejecuta `subscribe()`
  (solo publica); triple compuerta intacta (D-H).
- **Carreras en el sink**: estado compartido = `threading.Event` +
  contadores solo tocados por el hilo de control; `client.publish` es
  thread-safe en paho.
- **Stale/duplicados/out-of-order/NaN/timeout/reconexión**: sin cambios
  (MessageGuard/gateway F1-F2); suite de fault injection PASS.
- **Secretos**: `git ls-files` sin `.key/.pem/certs/`; `.gitignore` cubre
  `config/nsb/mosquitto/certs/`; deploy jamás copia `ca.key`.
- **Imports Pi-only/pesados en Windows**: `nsb.vision.provider` y
  `nsb.comms.mqtt_telemetry` importan perezosamente (tests de import PASS).
- **Rutas rígidas**: destino Pi parametrizado (`-Dest`); rutas de certs por
  config; fallbacks a `Program Files` solo tras `Get-Command`.
- **Mocks de producción**: ninguno; los fakes viven solo en tests.
- **Claims**: tabla de estados en `experiments.md` distingue
  VERIFIED / IMPLEMENTED / REQUIRES HARDWARE / NOT RUN.

Suite tras el red team: **176 passed, 3 skipped** (2 hardware Pi, 1 broker
opt-in) + `verify_all.ps1` OK.
