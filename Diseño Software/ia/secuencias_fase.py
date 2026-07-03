"""
Esquema y secuencias del predictor de COLA POR FASE (redes multi-intersección).

A diferencia de ia.secuencias (intersección aislada NS/EO de cruce-simple),
aquí cada serie es UNA fase de UN semáforo, muestreada en rejilla fija
(difuso_ia.GRID_S). Las características ya vienen normalizadas a [0,1] por
diseño (ver difuso_ia.CARACTERISTICAS_FASE), por lo que NO se necesita
escalador. El objetivo es la cola normalizada en el siguiente tick de rejilla.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

#: debe coincidir con difuso_ia.CARACTERISTICAS_FASE (orden incluido)
CARACTERISTICAS_FASE: List[str] = ['cola_n', 'nveh_n', 'ocupacion', 'vel_n',
                                   'verde_activa', 'espera_fase_n']
OBJETIVO = 'cola_n'          # cola normalizada del tick siguiente
VENTANA_DEFECTO = 8
HORIZONTE = 1                # ticks de rejilla (15 s por defecto)

#: Constantes de normalización de las características de fase. FUENTE ÚNICA:
#: difuso_ia normaliza el sensado con estas constantes al recolectar Y al
#: inferir, y entrenamiento_fase las persiste en artifacts_fase/config.json.
#: PredictorFase valida en carga que coincidan: si alguien las cambia sin
#: re-entrenar, la inferencia queda desalineada del entrenamiento y el modelo
#: se desactiva con error explícito (no silenciosamente).
NORMALIZACION_FASE: Dict[str, float] = {
    'cola_veh': 30.0,      # vehículos en cola (cola_n = cola/30)
    'nveh': 40.0,          # vehículos presentes (nveh_n = n/40)
    'vel_kmh': 50.0,       # velocidad (vel_n = v/50)
    'espera_s': 120.0,     # espera de la fase (espera_fase_n = e/120)
}


def _a_float(v) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def leer_series(ruta_csv: Path) -> Dict[str, List[List[float]]]:
    """serie_id -> lista ordenada por t de vectores de características."""
    series: Dict[str, List[Tuple[float, List[float]]]] = {}
    with open(ruta_csv, newline='', encoding='utf-8') as f:
        for fila in csv.DictReader(f):
            vec = [_a_float(fila[c]) for c in CARACTERISTICAS_FASE]
            series.setdefault(fila['serie_id'], []).append(
                (_a_float(fila['t']), vec))
    return {sid: [v for _, v in sorted(pares)]
            for sid, pares in series.items()}


def construir_secuencias(series: Dict[str, List[List[float]]],
                         ventana: int = VENTANA_DEFECTO,
                         horizonte: int = HORIZONTE
                         ) -> Tuple[List[List[List[float]]], List[List[float]]]:
    """Ventanas (X) y cola futura (y) SIN cruzar series (fase/semáforo/corrida)."""
    idx_obj = CARACTERISTICAS_FASE.index(OBJETIVO)
    X: List[List[List[float]]] = []
    y: List[List[float]] = []
    for _, serie in sorted(series.items()):
        for fin in range(ventana, len(serie) - horizonte + 1):
            X.append(serie[fin - ventana:fin])
            y.append([serie[fin + horizonte - 1][idx_obj]])
    return X, y


def particionar_series(series: Dict[str, List[List[float]]],
                       frac: Tuple[float, float, float] = (0.8, 0.1, 0.1),
                       semilla: int = 20260701) -> Dict[str, Dict]:
    """Split POR SEMILLA de corrida (prefijo del serie_id): sin fuga."""
    import random
    prefijos = sorted({sid.split('|')[0] for sid in series})
    rng = random.Random(semilla)
    rng.shuffle(prefijos)
    n = len(prefijos)
    n_tr = max(1, round(n * frac[0]))
    n_va = max(1, round(n * frac[1])) if n - n_tr >= 2 else 0
    grupos = {'train': set(prefijos[:n_tr]),
              'val': set(prefijos[n_tr:n_tr + n_va]),
              'test': set(prefijos[n_tr + n_va:])}
    return {k: {sid: s for sid, s in series.items()
                if sid.split('|')[0] in g}
            for k, g in grupos.items()}
