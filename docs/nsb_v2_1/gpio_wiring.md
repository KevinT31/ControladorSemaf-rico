# Cableado GPIO — 12 LEDs (LEER ANTES DE CONECTAR)

Maqueta de laboratorio: 4 accesos (N/S/E/O) × 3 LEDs (rojo/ámbar/verde),
ánodo al GPIO a través de resistencia, cátodo a GND (`active_high: true`).
Numeración **BCM** (la de gpiozero), no el pin físico del header.

> ⚠ PROTOTIPO DE LABORATORIO. LEDs indicadores de baja potencia únicamente.
> Nada de relés, lámparas ni cargas inductivas en estos pines.

## Pinout (config/nsb/pinout.yaml)

| Grupo | Rojo (BCM/físico) | Ámbar (BCM/físico) | Verde (BCM/físico) |
|---|---|---|---|
| Norte | 17 / 11 | 27 / 13 | 22 / 15 |
| Sur | 5 / 29 | 6 / 31 | 13 / 33 |
| Este | 23 / 16 | 24 / 18 | 25 / 22 |
| Oeste | 16 / 36 | 20 / 38 | 21 / 40 |

GND disponibles: físicos 6, 9, 14, 20, 25, 30, 34, 39. El pinout es un
borrador razonable: **verificar contra el cableado real antes de energizar**
(el YAML valida 12 pines únicos y completos al cargar).

## Resistencias — CALCULADAS, no asumidas

Datos: GPIO en alto = 3.3 V. Límites del BCM2711 (Pi 4B): ~16 mA máximo
recomendado por pin y ~50 mA agregado del rail GPIO. Tensiones directas
típicas de LED indicador de 5 mm: rojo/ámbar (AlGaInP) V_f ≈ 2.0 V; verde
clásico V_f ≈ 2.1 V; verde brillante (InGaN) V_f ≈ 3.0 V.

Con **R = 330 Ω** en serie por LED:

| LED | I = (3.3 − V_f) / 330 | ¿Dentro de límites? |
|---|---|---|
| Rojo (V_f 2.0 V) | (3.3−2.0)/330 = **3.9 mA** | ✓ ≪ 16 mA |
| Ámbar (V_f 2.0 V) | **3.9 mA** | ✓ |
| Verde AlGaInP (V_f 2.1 V) | (3.3−2.1)/330 = **3.6 mA** | ✓ |
| Verde InGaN (V_f 3.0 V) | (3.3−3.0)/330 = **0.9 mA** | ✓ (tenue; ver nota) |

Presupuesto agregado:

- Operación normal: máx. 4 LEDs encendidos (un color por acceso; p. ej.
  todo-rojo) → 4 × 3.9 ≈ **15.6 mA** ≪ 50 mA ✓
- **Peor caso absoluto** (bug enciende los 12): 12 × 3.9 ≈ **47 mA** < 50 mA ✓
  — esta es la razón para elegir 330 Ω y no 220 Ω: con 220 Ω el peor caso
  daría 12 × 5.9 ≈ 71 mA, fuera de presupuesto. La seguridad no debe
  depender de que el software nunca falle.

Nota verde InGaN: si a 0.9 mA resulta demasiado tenue, usar verde AlGaInP o
bajar solo las tres R de verdes InGaN a 150 Ω ((3.3−3.0)/150 = 2 mA; peor
caso absoluto quedaría 9×3.9 + 3×2 = 41 mA ✓).

## Comportamiento del software

- `GPIOActuator` (gpiozero, import perezoso — spec §23) arranca con **todo
  apagado** y al cerrar deja **todo-rojo y luego apaga** (apagado ordenado).
- La matriz de conflictos impide verdes NS×EO simultáneos antes de llegar
  al actuador; el peor caso de corriente es defensa en profundidad, no el
  modo de operación.
- `tick_mode: control_only` (default): los LEDs reflejan puntos de control,
  no cada segundo de SUMO (D-B).

## Checklist antes de energizar

1. Continuidad y polaridad de cada LED (ánodo→resistencia→GPIO).
2. Ninguna resistencia < 330 Ω instalada (o 150 Ω solo en verdes InGaN).
3. Cátodos a GND común de la Pi.
4. Pi apagada durante el cableado.
5. Primer arranque en `--mode advisory` (no actúa) y luego demo con
   `tsc_emulated` observando secuencia verde→ámbar→todo-rojo.

**ESTADO: IMPLEMENTED / REQUIRES HARDWARE** — cableado no realizado aún
(D-11); `tests/hardware/test_gpio_pi.py` corre solo en la Pi.
