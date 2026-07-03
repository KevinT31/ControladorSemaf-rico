"""
Esquema de características y construcción de secuencias temporales.

CARACTERISTICAS define el ORDEN CANÓNICO del vector de entrada. Debe coincidir
1:1 con ControladorDifusoPredictivo._vector_caracteristicas (lazo en vivo) y
con las columnas de intervals.csv (entrenamiento offline). Si se cambia aquí,
cambiar allá y re-entrenar.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence, Tuple

#: columnas de intervals.csv que forman el vector de entrada (orden canónico)
CARACTERISTICAS: List[str] = [
    'icv_ns', 'icv_ew', 'pi_ns', 'pi_ew',
    'queue_ns', 'queue_ew', 'waiting_ns', 'waiting_ew',
    'speed_ns', 'speed_ew', 'flow_ns', 'flow_ew',
    'occupancy_ns', 'occupancy_ew', 'green_ns', 'green_ew',
]

#: variables objetivo: ICV del intervalo FUTURO por eje
OBJETIVOS: List[str] = ['icv_ns', 'icv_ew']

VENTANA_DEFECTO = 8   # W intervalos de historia
HORIZONTE = 1         # se predice el intervalo siguiente


def _a_float(v) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def filas_a_series(filas: Iterable[Dict]) -> Dict[str, List[Dict[str, float]]]:
    """Agrupa filas del dataset por corrida y las ordena por tiempo."""
    series: Dict[str, List[Dict[str, float]]] = {}
    for f in filas:
        series.setdefault(f['run_id'], []).append(f)
    for run_id in series:
        series[run_id].sort(key=lambda f: _a_float(f['time_step']))
    return series


def construir_secuencias(filas: Iterable[Dict],
                         ventana: int = VENTANA_DEFECTO,
                         horizonte: int = HORIZONTE
                         ) -> Tuple[List[List[List[float]]], List[List[float]]]:
    """Ventanas deslizantes (X) y objetivos futuros (y), SIN cruzar corridas.

    X[i] tiene forma (ventana, len(CARACTERISTICAS)); y[i] es el ICV NS/EO
    `horizonte` intervalos después del cierre de la ventana.
    """
    X: List[List[List[float]]] = []
    y: List[List[float]] = []
    for _, serie in sorted(filas_a_series(filas).items()):
        vectores = [[_a_float(f[c]) for c in CARACTERISTICAS] for f in serie]
        objetivos = [[_a_float(f[c]) for c in OBJETIVOS] for f in serie]
        for fin in range(ventana, len(serie) - horizonte + 1):
            X.append(vectores[fin - ventana:fin])
            y.append(objetivos[fin + horizonte - 1])
    return X, y


class EscaladorMinMax:
    """Escalador min-max por característica, serializable a dict/JSON.

    Sin dependencia de sklearn: en inferencia solo se necesita stdlib.
    """

    def __init__(self, minimos: Sequence[float] = (), maximos: Sequence[float] = ()):
        self.minimos = list(minimos)
        self.maximos = list(maximos)

    def ajustar(self, X: List[List[List[float]]]) -> 'EscaladorMinMax':
        n = len(CARACTERISTICAS)
        self.minimos = [float('inf')] * n
        self.maximos = [float('-inf')] * n
        for ventana in X:
            for vector in ventana:
                for j, v in enumerate(vector):
                    if v < self.minimos[j]:
                        self.minimos[j] = v
                    if v > self.maximos[j]:
                        self.maximos[j] = v
        for j in range(n):
            if not math.isfinite(self.minimos[j]):
                self.minimos[j], self.maximos[j] = 0.0, 1.0
        return self

    def transformar_vector(self, vector: Sequence[float]) -> List[float]:
        out = []
        for j, v in enumerate(vector):
            rango = self.maximos[j] - self.minimos[j]
            out.append((float(v) - self.minimos[j]) / rango if rango > 0 else 0.0)
        return out

    def transformar(self, X: List[List[List[float]]]) -> List[List[List[float]]]:
        return [[self.transformar_vector(vec) for vec in ventana] for ventana in X]

    def como_dict(self) -> Dict:
        return {'caracteristicas': CARACTERISTICAS,
                'minimos': self.minimos, 'maximos': self.maximos}

    @classmethod
    def desde_dict(cls, d: Dict) -> 'EscaladorMinMax':
        if d.get('caracteristicas') != CARACTERISTICAS:
            raise ValueError(
                'El escalador fue ajustado con OTRA lista de características; '
                're-entrenar el modelo (ia.entrenamiento).')
        return cls(d['minimos'], d['maximos'])
