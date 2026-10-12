# Archivos de resultados

Todas las campañas usan la red y la demanda versionadas en
`escenarios/lima-centro/` y SUMO 1.24.0; cada JSON guarda sus huellas SHA-256.

## Resultados vigentes (los que cita la tesis)

| Archivo | Contenido |
|---|---|
| `completo_ALTA30.json`, `completo_MEDIA10.json` | Nueve estrategias en las semillas de prueba (1-30 alta, 1-10 media), con la métrica `tiempo_red_por_veh_s`. `difuso_fase_cal` es `difuso_fase` con `params_fase_calibrado.json`. |
| `analisis_completo_*.json` | Resumen, contrastes pareados con Holm, Friedman, Wilcoxon y ablaciones. |
| `robustez_1800_ALTA10.json`, `analisis_robustez_1800_ALTA10.json` | Horizonte de 1800 s, demanda alta, semillas 1-10. |
| `multibaseline_ALTA30.json`, `multibaseline_MEDIA10.json` | Campaña de siete estrategias (sin el controlador de fase); sus métricas coinciden con las de `completo_*`. |

## Calibración y protocolo

| Archivo | Contenido |
|---|---|
| `parametros_difuso_calibrados.json` | Calibración del difuso del Capítulo 6 (`difuso_opt`). |
| `calibracion_fase.json`, `params_fase_calibrado.json` | Calibración del controlador de fase. |
| `calibracion_fase_ia.json`, `params_ia_calibrado.json` | Variantes con predictor (no adoptadas). |
| `difuso_fase_*_desarrollo.json`, `difuso_ia*_validacion.json` | Entrenamiento y validación del controlador de fase y del predictor. |
| `params_recoleccion.json`, `params_ia_abierta.json` | Parámetros de recolección de series y de la IA con compuertas abiertas. |

## Intermedios del experimento

`prueba_*`, `experimento_*` y `experimento2_*` son las ejecuciones de prueba
del controlador de fase (por defecto, calibrado y con IA) antes de reunir todo
en `completo_*`. Se conservan para trazabilidad; sus métricas coinciden.

`historico_jun2026/` contiene la campaña de junio de 2026, no repetible.
