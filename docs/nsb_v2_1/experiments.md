# Experimentos y demos (spec §43, §45)

Estados posibles: **VERIFIED** (ejecutado con éxito en esta máquina),
**IMPLEMENTED** (código completo, no ejecutado end-to-end),
**REQUIRES HARDWARE** (falta Pi/LEDs), **NOT RUN**, **BLOCKED**.
Jamás se marca VERIFIED algo no ejecutado (spec §50).

## Tabla de demos

| # | Demo | Comando (desde `Diseño Software/`) | Estado |
|---|---|---|---|
| 1 | ADVISORY + replay | `python -m nsb demo --id 1` | VERIFIED (Windows) |
| 2 | TSC_EMULATED + SimulatedActuator | `python -m nsb demo --id 2` | VERIFIED (Windows) |
| 3 | HIL SUMO ↔ nodo | ver procedimiento abajo | VERIFIED (Windows, localhost; Pi pendiente) |
| 4 | TSC_EMULATED + LEDs físicos | `./scripts/run_node.sh` en la Pi | IMPLEMENTED / REQUIRES HARDWARE |
| 5 | AUTOMATED_DIRECT_LAB (simulado) | `python -m nsb demo --id 5` | VERIFIED (Windows; con LEDs: REQUIRES HARDWARE) |
| 6 | verde solicitado = 200 s | `python -m nsb demo --id 6` | VERIFIED (Windows) |
| 7 | doble verde conflictivo | `python -m nsb demo --id 7` | VERIFIED (Windows) |
| 8 | pérdida MQTT | `python -m nsb demo --id 8` | VERIFIED (Windows, 2026-07-05) |
| 9 | pérdida HIL / silencio | `python -m nsb demo --id 9` | VERIFIED (Windows) |
| 10 | EV en fase incompatible | `python -m nsb demo --id 10` | VERIFIED (Windows) |
| 11 | video real shadow mode | ver `drone_video_validation.md` | IMPLEMENTED / NOT RUN (sin video ni pesos en el repo) |
| 12 | replay determinista | `python -m nsb demo --id 12` | VERIFIED (Windows) |

## Experimento A — HIL con SUMO real (escenario `nsb-cruz`)

```powershell
# Consola 1: gateway (SUMO + servidor TCP step-sync)
.\scripts\nsb\run_hil_gateway.ps1

# Consola 2: nodo
.\scripts\nsb\run_node_hil.ps1
```

Última corrida verificada (F2, 2026-07-05): 28 puntos de control,
0 timeouts, digest determinista. Con la Pi: mismo procedimiento, nodo en la
Pi (`hil.host` = IP de la PC) — REQUIRES HARDWARE.

## Experimento B — video de dron

Implementado (solo ADVISORY, spec §15): `--source video` + `gt-sample` +
`gt-eval`. Comandos exactos y estado honesto en `drone_video_validation.md`.
Sin video real ni pesos YOLO en el repo: NOT RUN hasta tenerlos.

## Experimento C — replay reproducible

Ver `replay.md`. `python -m nsb demo --id 12`.

## Benchmark de latencias (spec §31)

```powershell
python -m nsb bench --out ..\docs\nsb_v2_1\resultados\bench.json
```

Medido en **Windows AMD64, Python 3.12** (2026-07-05,
`resultados/bench_windows_amd64.json`):

| Métrica | n | p50 (ms) | p95 (ms) |
|---|---|---|---|
| ICV+PI por acceso | 1010 | 0.032 | 0.057 |
| Inferencia difusa | 255 | 1.300 | 2.272 |
| Pipeline completo | 500 | 1.852 | 3.026 |

**No extrapolable a la Pi 4B**: el mismo bench se re-ejecuta en la Pi cuando
exista el hardware (D-11) y se versiona como `bench_pi4b_aarch64.json`.

## Verificación integral

```powershell
.\scripts\nsb\verify_all.ps1   # imports + pytest + demos 6,7,8,10,12 + replay CLI
```

Suite actual: 155 passed, 2 skipped (hardware Pi) + 1 test MQTT opt-in
(requiere broker; ver `mqtt_tls.md`).
