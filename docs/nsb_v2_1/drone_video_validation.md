# Validación con video real de dron (spec §15-§17)

**ESTADO: NOT RUN — llega en F4.** Este documento fija el diseño y los
criterios ANTES de implementar, para que la validación no se acomode a los
resultados. Se actualizará con evidencia real cuando F4 se ejecute.

## Qué será (F4)

- `VideoStateSource`: produce `TrafficState` desde el pipeline de visión
  YOLOv8 **ya existente** en el repo (`vision_computadora/`) — no se
  reimplementa detección.
- **Solo ADVISORY** (spec §15): el video jamás actúa sobre semáforos; se
  registran recomendaciones para comparación offline.
- Ground truth: muestreo de frames (`gt-sample`) etiquetado a mano,
  contra el que se mide la detección (spec §17).

## Limitaciones ya conocidas del video de dron (spec §16)

- Perspectiva/oclusión: conteos y velocidades estimadas, no verdad absoluta.
- FPS de procesamiento ≠ FPS de captura; se reporta el medido, no el nominal.
- La calidad depende de altura/ángulo/luz del vuelo original.
- Un video ≠ validación de campo: es evidencia de viabilidad, no
  certificación.

## Criterios de aceptación (fijados por adelantado)

1. `TrafficState` de video pasa la MISMA validación estricta que las demás
   fuentes (NaN/inf rechazados, calidad marcada).
2. Métricas de visión (precision/recall de conteo por acceso) reportadas
   contra ground truth etiquetado, con tamaño de muestra explícito.
3. Latencia y FPS medidos y versionados como los del bench (spec §31).
4. Demo 11 (shadow mode con video) ejecutable end-to-end en Windows.
