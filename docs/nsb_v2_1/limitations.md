# Limitaciones honestas del prototipo (spec §42)

Lista viva. Si algo de aquí se resuelve, se mueve al doc correspondiente con
su evidencia; nada se borra silenciosamente.

## Alcance del prototipo

1. **NO es un controlador vial certificado.** Prototipo de laboratorio con
   LEDs de baja potencia; sin validación de campo, sin normativa (NEMA/CE),
   sin redundancia física.
2. **Sin monitor de conflictos hardware.** La prevención de verdes
   conflictivos es 100 % software (matriz + gate + FSM). Un despliegue real
   exige un conflict monitor independiente del procesador (spec §27).
3. **systemd no es seguridad física** (spec §39): reinicia el proceso, nada
   más. Sin watchdog `sd_notify` (se documenta en vez de fingirse).

## Plataforma y hardware

4. **Pi 4B ausente durante el desarrollo (D-11).** Todo lo específico de Pi
   (GPIO físico, systemd en Bookworm, `deploy_pi.ps1` end-to-end, bench en
   ARM) está IMPLEMENTED / REQUIRES HARDWARE, no VERIFIED.
5. **El bench versionado es de Windows AMD64** — no extrapolable a la Pi.
6. La Pi 4B **no es el target final de la tesis**; sus números se
   etiquetarán como Pi 4B sin extrapolar (nota en `node.pi.yaml`).

## Núcleo científico

7. **CNN-LSTM no existe en el repo (D-01).** Solo hay interfaz
   `PredictorBackend` + `DisabledPredictor`; `predictor_enabled=False`
   siempre en producción. No se inventó un predictor.
8. **PI tiene tres variantes en el repo (D-D).** NSB usa la de
   `comparacion_sumo._demanda_fase` (la que generó los resultados
   multibaseline versionados). Las otras dos siguen en el código heredado.
9. El golden master garantiza equivalencia con ESA variante, no con "todas
   las formas de calcular PI" del repo.

## Comunicaciones

10. **Mosquitto local ≠ broker gestionado.** La validación MQTT es contra
    Mosquitto en la PC (TLS+mTLS+ACL verificados); Azure IoT Hub u otro
    broker cloud queda fuera de esta fase.
11. **Telemetría MQTT QoS 0:** pérdida bajo desconexión es por diseño;
    la fuente de verdad auditable es el JSONL local (D-F).
12. **PKI de laboratorio:** CA propia sin CRL/OCSP ni HSM; revocación =
    rotación completa (`gen_lab_certs.ps1 -Force`).
13. Los primeros/últimos eventos de una corrida dependen de esperas
    acotadas (2 s) de conexión/drenado; con broker caído esas esperas se
    pagan una vez por proceso.

## Backend preexistente (D-10 — riesgos NO introducidos por NSB)

14. `SECRET_KEY` con default inseguro en el backend FastAPI existente.
15. WebSocket del dashboard sin autenticación.
16. Sin rate limiting en la API. — Su corrección es deuda separada de NSB;
    NSB no amplió la superficie (telemetría HTTP es saliente y opcional).

## Visión y datos

17. **Visión sin ejecutar con video real:** F4 está implementado y testeado
    con proveedores sintéticos, pero el repo no contiene videos de dron ni
    pesos YOLO (gitignored, ausentes): demo 11 y las métricas de conteo
    quedan NOT RUN (`drone_video_validation.md`). El proveedor dual-ROI
    carga el modelo YOLO dos veces (una por ROI) — costo de RAM aceptado
    para procesamiento offline (D-J).
18. Los escenarios lima-* usan estructuras de fase OSM arbitrarias; el HIL
    usa el cruce dedicado `nsb-cruz` (D-12). Extrapolar de un cruce único a
    una red real no está soportado por esta evidencia.

## Testing

19. **Property-based sin Hypothesis (D-09):** fuzz sembrado propio; menor
    poder de shrinking que Hypothesis (mejora opcional futura).
20. Tests `hardware` y MQTT-broker son opt-in/skip: la suite estándar no
    los ejecuta (los skips son visibles, jamás PASS silencioso).
