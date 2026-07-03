"""
Plataforma de experimentación reproducible de control semafórico sobre SUMO.

Arquitectura (capas):
  base.py              -> contratos: EstadoEje / EstadoInterseccion / AccionControl / ControladorTrafico
  interseccion_sumo.py -> adaptador de infraestructura: sensa y actúa sobre UN semáforo de SUMO
  seguridad.py         -> envoltura de seguridad funcional (usa nucleo.seguridad_semaforica)
  controladores.py     -> FixedTime / Fuzzy (Mamdani Cap.6) / FuzzyPredictive (CNN-LSTM asistido)
  runner.py            -> lazo experimental: simula, decide cada intervalo, registra TODO
  campania.py          -> campañas multi-semilla + estadística (Wilcoxon / t pareada)
  dataset.py           -> generación del dataset temporal para IA (una fila por intervalo)

Principio rector: la IA NUNCA fija el verde directamente. La cadena SIEMPRE es
  estado real -> (predicción opcional) -> controlador difuso -> envoltura de seguridad -> SUMO
y toda decisión queda trazada (CSV + SQLite) con su procedencia (source_type).
"""
