# Plataforma de experimentación reproducible (SUMO + difuso + IA)

Plataforma de investigación para comparar estrategias de control semafórico
sobre SUMO con **trazabilidad completa** y **estadística pareada**. Todo dato
proviene de simulación real (libsumo); no hay flujos sintéticos.

## Arquitectura (capas)

```
base.py              contratos: EstadoEje / EstadoInterseccion / AccionControl / ControladorTrafico
entorno.py           sys.path + motor (libsumo>traci) + directorios de artefactos
interseccion_sumo.py adaptador: sensa/actúa sobre UN semáforo (ejes NS/EO por geometría)
seguridad.py         envoltura de seguridad funcional (nucleo.seguridad_semaforica)
controladores.py     fixed | fuzzy (Mamdani Cap.6) | fuzzy_predictive_ai (CNN-LSTM asistido)
runner.py            una corrida: simula, decide cada intervalo, registra TODO
campania.py          matriz {controlador}×{demanda}×{semilla} + t pareada/Wilcoxon/IC95%
dataset.py           consolida corridas -> dataset temporal + splits SIN FUGA (por corrida)
../../ia/            secuencias, modelo CNN-LSTM, entrenamiento, inferencia (PredictorICV)
```

**Principio rector:** la IA NUNCA fija el verde. La cadena siempre es
`estado real -> (predicción opcional) -> difuso Mamdani -> seguridad -> SUMO`,
con `ICV_control = (1-β)·ICV_actual + β·ICV_predicho` y fallback trazado al
difuso base ante cualquier anomalía (modelo ausente, buffer incompleto, NaN,
fuera de rango, discrepancia > 0.35).

## Flujo completo (desde `integracion-sumo/`)

```bash
# 0) Red del escenario (si falta cruce.net.xml; requiere SUMO_HOME)
python escenarios/cruce-simple/generar_red.py

# 1) Una corrida trazada (results/runs/<run_id>/: intervals.csv, decisions.csv,
#    safety_events.csv, resumen.json + SQLite base-datos/experimentos.db)
python -m experimentos.runner --controlador fuzzy --demanda punta --semilla 7

# 2) Campaña con estadística (results/control_comparison/<campania_id>/)
python -m experimentos.campania --controladores fixed fuzzy \
    --demandas baja media alta punta --semillas 1 2 3 4 5 6 7 8 9 10

# 3) Dataset para la IA (data/processed/ + data/splits/, split POR corrida)
python -m experimentos.dataset

# 4) Entrenar la CNN-LSTM (desde 'Diseño Software/'; ia/artifacts/)
python -m ia.entrenamiento --epocas 150 --paciencia 20

# 5) Control asistido por IA (evaluar con semillas NO usadas al entrenar)
python -m experimentos.campania --controladores fuzzy fuzzy_predictive_ai \
    --demandas baja media alta punta --semillas 11 12 13 14 15 16 17 18 19 20 \
    --linea-base fuzzy
```

## Decisiones metodológicas defendibles

- **Comparación pareada:** misma semilla y demanda para todos los
  controladores; los contrastes son t pareada + Wilcoxon con IC95%.
- **Sin fuga de datos:** el split train/val/test se hace POR corrida
  (estratificado por demanda×controlador); una secuencia jamás cruza splits.
- **Línea base de persistencia:** la CNN-LSTM se reporta contra
  `ICV_{t+1}=ICV_t`; si no la supera, no aporta.
- **Evaluación con semillas frescas:** el control con IA se evalúa con
  semillas jamás vistas en el entrenamiento.
- **Seguridad primero:** ninguna acción llega a SUMO sin pasar por
  `nucleo.seguridad_semaforica` (verde 10–120 s, no-conflicto, modo seguro);
  cada corrección queda en `safety_events.csv`.
- **Trazabilidad total:** cada decisión registra ICV actual/predicho, β,
  reglas difusas disparadas, verdes solicitados vs aplicados y motivo de
  fallback (`decisions.csv` + SQLite).
