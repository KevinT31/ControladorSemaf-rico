# Validación con video real de dron (spec §15-§17)

**ESTADO: IMPLEMENTED / NOT RUN con video real.** El código de F4 está
completo y verificado con proveedores sintéticos (20 tests), pero el
repositorio **no contiene ningún video de dron ni pesos YOLO** (ambos
gitignored y ausentes localmente): ninguna cifra de visión se reporta hasta
procesar un video real (spec §17: "NO generar cifras hasta ejecutar").

## Qué hay implementado (F4)

- `nsb/sources/video.py` — `VideoStateSource`: agrega frames por ventana de
  `control_interval_s` (media por ventana; ventana vacía ⇒
  `quality.valid=False` y el guard la rechaza). `sim_time_s` = tiempo de
  video ⇒ replay determinista.
- `nsb/vision/provider.py` — `DualRoiVideoProvider`: UN decodificado del
  video alimenta dos `ProcesadorVideo` **existentes** (YOLO + ByteTrack +
  colas, `vision_computadora/`) con ROI NS y ROI EO (D-J). No se
  reimplementa detección.
- **Solo ADVISORY** (spec §15): la CLI rechaza cualquier otro modo con
  `--source video`.
- EV: la confianza máxima del detector de emergencias existente entra como
  `ev_ns/ev_eo`; evento EV solo con confianza ≥ 0.5 (igual, solo ADVISORY).
- Ground truth: `nsb gt-sample` (frames + manifest para anotar A MANO) y
  `nsb gt-eval` (MAE/RMSE de conteo por acceso). SUMO **no** es ground
  truth de video real (spec §15).

## Comandos exactos (cuando exista un video)

```powershell
cd "Diseño Software"

# 1. Correr en shadow mode grabando estados y decisiones
python -m nsb run --source video --mode advisory `
    --input datos\videos-prueba\dron.mp4 `
    --roi-ns "0,0,960,540" --roi-eo "0,540,960,540" `
    --stride 15 --px-per-m 15 --record video_run.jsonl
#   dron móvil: añadir --camera-moving (marca velocidades no confiables)

# 2. Muestrear frames para ground truth y anotar count_ns/count_eo a mano
python -m nsb gt-sample --input datos\videos-prueba\dron.mp4 --out gt_dron --every-s 5

# 3. Evaluar conteos anotados vs. estados grabados
python -m nsb gt-eval --manifest gt_dron\manifest.csv --states video_run.jsonl
```

## Limitaciones ya conocidas del video de dron (spec §16)

- Perspectiva/oclusión: conteos y velocidades estimadas, no verdad absoluta.
- FPS de procesamiento ≠ FPS de captura; se reporta el medido, no el nominal.
- La calidad depende de altura/ángulo/luz del vuelo original.
- Un video ≠ validación de campo: es evidencia de viabilidad, no
  certificación.

## Criterios de aceptación (fijados por adelantado)

1. `TrafficState` de video pasa la MISMA validación estricta que las demás
   fuentes (NaN/inf rechazados, calidad marcada). — CUMPLIDO (mismos
   contratos pydantic; verificado en tests).
2. Métricas de conteo (MAE/RMSE por acceso) reportadas contra ground truth
   anotado a mano, con tamaño de muestra explícito. — Tooling listo
   (`gt-eval` reporta `n_emparejadas/n_anotaciones`); PENDIENTE de video.
3. Latencia y FPS medidos y versionados como los del bench (spec §31). —
   PENDIENTE de video.
4. Demo 11 (shadow mode con video) ejecutable end-to-end en Windows. —
   comandos arriba; PENDIENTE de video y pesos YOLO.

Los flags de calidad (`camera_moving`, `calibrated`) los declara el
operador: no se inventan detecciones de movimiento de cámara ni
calibraciones (spec §16, "No inventar calibraciones").
