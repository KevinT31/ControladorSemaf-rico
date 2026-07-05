# Inyección de fallos (spec §32)

Módulo separado (`nsb/faults/`): los fallos se **declaran** en un `FaultPlan`
(qué fallo, en qué `seq`) y los inyectores envuelven componentes reales sin
tocarlos. Nada de esto vive en el código de producción del pipeline.

## Fallos soportados

| Fallo | Qué hace | Quién debe atajarlo |
|---|---|---|
| `nan_queue` | `queue_m = NaN` puenteando la validación | MessageGuard (entrada no finita) |
| `inf_speed` | `speed_kmh = inf` | MessageGuard |
| `duplicate` | re-emite el `seq` anterior | MessageGuard (seq duplicado) |
| `out_of_order` | emite un `seq` viejo | MessageGuard (orden) |
| `drop` | no emite el estado (pérdida) | TSC: silencio → CONFIG_SEGURA |
| `stale` | estado con edad excesiva | MessageGuard (frescura) |
| `sensado_invalido` | `quality.valid = False` | MessageGuard (calidad) |
| `verde_200` | recomendación con verde de 200 s | SafetyGate (límites → clamp/reject) |
| `conflicto_verde` | salida con verdes NS y EO simultáneos | Matriz de conflictos (reject + evento) |
| `predictor_roto` | predictor que lanza excepción | Pipeline: fallback, `predictor_used=False` |

## Inyectores

- `CorruptingSource(inner, plan)` — envuelve cualquier `TrafficStateSource`
  y corrompe/duplica/pierde estados según el plan.
- `SabotagePipeline(inner, plan)` — envuelve el `DecisionPipeline` real y
  sabotea la *recomendación* (p. ej. `verde_200`, `conflicto_verde`).
- `PredictorRoto` — backend de predictor que explota al usarse (D-01).

## Invariantes verificadas bajo fallo

1. El proceso **no muere**: todo fallo produce `reject`/`clamp`/fallback y
   un evento correlacionable (spec §40), jamás una excepción no atrapada.
2. **Cero verdes conflictivos** aplicados (violaciones_gate == 0 salvo test
   que las cuenta a propósito).
3. Silencio efectivo prolongado (N ciclos sin recomendación válida) →
   CONFIG_SEGURA (demo 9).
4. El replay de una corrida con fallos es igual de determinista.

## Cómo ejercitarlos

```powershell
cd "Diseño Software"
python -m nsb demo --id 6    # verde 200 s → clamp/reject
python -m nsb demo --id 7    # doble verde conflictivo → reject
python -m nsb demo --id 9    # silencio → CONFIG_SEGURA
python -m pytest tests/integration/test_fault_injection.py -q
```
