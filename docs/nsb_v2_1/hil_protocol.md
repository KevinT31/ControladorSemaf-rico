# Protocolo HIL (spec §13-§14)

HIL **step-synchronous**: SUMO no avanza hasta recibir la decisión del nodo
(o agotar el timeout). Transporte: **TCP JSON-lines** dedicado, sockets
síncronos stdlib (D-03). MQTT no participa en este plano (D-02).

## Topología

1 gateway (PC: SUMO + traci) ↔ 1 nodo (PC u otra máquina/Pi) — D-A.
El envelope transporta `intersection_id` para multi-nodo futuro.

## Framing

- Una línea JSON UTF-8 terminada en `\n` por mensaje (`nsb/domain/wire.py`).
- `MAX_LINE_BYTES = 1 MiB`: líneas mayores son error de protocolo.
- `TCP_NODELAY` activado (mensajes pequeños, uno a uno).
- Envelope con `schema_version`; extras se ignoran (forward-compat, D-G).

## Secuencia

```
nodo → hello      {node_id, modes_supported, resume?}
gw   → hello_ack  {experiment_id, control_interval_s, seed,
                   scenario_digest, next_seq}
[por cada punto de control:]
gw   → state      {TrafficState con seq y sim_time_s}
nodo → decision   {DecisionEnvelope con seq espejado}
[al terminar la corrida:]
gw   → bye        {resumen}
```

Errores de protocolo → mensaje `type=error` y cierre de sesión.

## Ciclo por punto de control (spec §13)

1. SUMO avanza hasta el próximo punto de control (`control_interval_s`,
   canónico 25 s — D-07).
2. El gateway extrae `TrafficState` (mapeo de fases EXPLÍCITO declarado en
   `gateway.yaml` — D-12) y asigna `seq`.
3. Envía al nodo; el nodo procesa (guard → pipeline → autoridad → gate).
4. El nodo devuelve `DecisionEnvelope`.
5. El gateway valida y aplica la fase resultante en SUMO
   (`setProgramLogic` preservando fase, patrón de `comparacion_sumo`).
6. Continúa la simulación.

## Fallos y política de timeout (D-C, §26-B)

| Situación | Comportamiento |
|---|---|
| Timeout del nodo (`node_timeout_s`) | según `timeout_policy` |
| `fallback` (demos) | mantiene plan vigente; tras `max_consecutive_timeouts` → plan seguro |
| `fail_fast` (campañas de métricas) | aborta la corrida (un timeout contamina el determinismo) |
| Desconexión del nodo | el gateway espera reconexión hasta `max_wait_reconnect_s`; `resume` con `next_seq` |
| seq viejo/duplicado | descartado y contado (`stale_descartados`) |

## Configuración

`config/nsb/gateway.yaml` (gateway) y sección `hil:` de `node.yaml`
(cliente). Escenario dedicado reproducible: `nsb-cruz` (netgenerate +
randomTrips con seed — D-12).

## Verificación

- `tests/integration/test_hil_localhost.py` — gateway y nodo reales por
  sockets locales (sin SUMO).
- `tests/sumo/` — con SUMO real (se salta si no está instalado).
- Corrida real F2 (2026-07-05): 28 puntos de control, 0 timeouts —
  ver `resultados/` y `experiments.md`.
