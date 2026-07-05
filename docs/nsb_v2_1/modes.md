# Modos de autoridad (spec §10)

Tres modos, con garantías decrecientes de pasividad. El modo se resuelve UNA
vez al construir el proceso (config + CLI + entorno) y en runtime **solo puede
degradarse** (direct-lab → tsc → advisory); ninguna vía remota (MQTT/HTTP)
puede elevarlo (D-H, spec §29).

## ADVISORY (default)

- El pipeline calcula ICV/PI/EV y la recomendación difusa, y **solo
  registra** (telemetría/JSONL). No hay actuador.
- Garantía: cero efecto sobre semáforos reales o simulados.
- Uso: shadow mode, validación de visión (F4), comparaciones offline.

## TSC_EMULATED

- Un **TscEmulator** local (emulador de controlador de tránsito) es quien
  decide: recibe la recomendación como *input*, la valida contra el Safety
  Kernel y programa la FSM de fases.
- La recomendación puede ser aceptada (`accept`), recortada (`clamp`),
  rechazada (`reject`) o diferida (`defer` durante preempción EV).
- Cambio de plan: solo al entrar al verde correspondiente o en frontera de
  ciclo (`TODO_ROJO_2 → NS_VERDE`); jamás acorta la fase en curso por debajo
  de los mínimos.
- Silencio prolongado (`max_silence_cycles`, default 3) → CONFIG_SEGURA.

## AUTOMATED_DIRECT_LAB (experimental, laboratorio)

- El nodo aplica su propia decisión al actuador **de laboratorio** (12 LEDs).
- **Triple compuerta** (spec §10.3) — las tres son obligatorias:
  1. `allow_direct_lab: true` en `node.yaml`;
  2. flag CLI explícito `--mode automated-direct-lab`;
  3. variable de entorno `NSB_CONFIRM_DIRECT_LAB` = `node_id` exacto.
- Su activación emite un evento `direct_lab_activated` con severidad
  CRITICAL (spec §40).
- Mismo Safety Kernel que TSC_EMULATED: límites, matriz de conflictos,
  secuencia verde→ámbar→todo-rojo. `defer_during_preempt` se desactiva
  (el nodo gestiona su propia preempción EV).

## Qué NO cambia entre modos

El pipeline científico es idéntico; los tres modos producen la misma
`RecommendationEnvelope` ante el mismo `TrafficState` (verificado por el
golden master). Cambia únicamente **quién tiene autoridad para actuar**.

## Verificación

- `tests/unit/test_authority_modes.py` — advisory jamás actúa; direct-lab
  exige triple compuerta; degradación permitida, elevación imposible.
- Demos: 1 (advisory+replay), 2 (tsc+simulado), 5 (direct-lab simulado).
