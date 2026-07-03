"""
Módulo de IA predictiva (CNN-LSTM) del sistema semafórico.

Predice el ICV del PRÓXIMO intervalo de control por eje (NS/EO) a partir de
una ventana de estados reales de SUMO. La predicción NUNCA fija el verde:
solo se mezcla con el ICV actual antes del controlador difuso
(ICV_control = (1-beta)*actual + beta*predicho) y siempre con fallback al
difuso base (ver experimentos.controladores.ControladorDifusoPredictivo).

  secuencias.py    esquema de características + ventanas deslizantes + escalador
  modelo.py        arquitectura CNN-LSTM (PyTorch)
  entrenamiento.py entrena desde data/splits/ y guarda ia/artifacts/
  inferencia.py    PredictorICV: carga artefactos y predice en el lazo real
"""
