# Grabación y replay determinista (spec §18)

Toda corrida puede grabarse y reproducirse **bit a bit**: misma secuencia de
`TrafficState` ⇒ mismas decisiones ⇒ mismo digest.

## Formato de grabación

JSONL (`ReplayWriter`): una línea por objeto, en orden de ocurrencia:

```
{"kind": "state", ...TrafficState...}
{"kind": "recommendation", ...RecommendationEnvelope...}   # si hubo
{"kind": "decision", ...DecisionEnvelope...}
```

Graban tanto el nodo (`--record`) como el gateway (`record_jsonl:` en
`gateway.yaml`).

## Digest determinista

`digest_decisiones(jsonl)` = SHA-256 sobre los campos decisionales
normalizados (excluye timestamps de pared y rutas). Dos corridas equivalentes
⇒ digests idénticos. Es el mecanismo del golden master y de la demo 12.

## Por qué es determinista

- Reloj inyectable (D-B): en replay se usa el `sim_time_s` grabado, jamás
  el reloj de pared.
- Monohilo sin asyncio (D-03): no hay carreras de scheduling.
- El difuso canónico es determinista; el fuzz sembrado usa `random.Random(seed)`.
- Validación estricta de entradas (D-G): NaN/inf no entran al pipeline.

## Comandos exactos (Windows)

```powershell
cd "Diseño Software"

# Grabar una fuente manual (sin decidir)
python -m nsb record --escenario congestion_ns --pasos 25 --out corrida.jsonl

# Reproducir decidiendo, grabando las decisiones
python -m nsb run --source replay --input corrida.jsonl --mode tsc-emulated --record decidido.jsonl

# Digest (repetir la corrida debe dar el MISMO hash)
python -m nsb digest decidido.jsonl
```

Demo automatizada: `python -m nsb demo --id 12` (dos corridas ⇒ digests
idénticos). Verificación adicional: `tests/integration/test_pipeline_replay.py`
y `tests/golden/`.
