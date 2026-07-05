"""Genera el corpus del golden master (spec §20). SE EJECUTA UNA VEZ y sus
salidas (data/corpus.jsonl, data/snapshot.jsonl) se VERSIONAN en git.

    python tests/golden/generar_corpus.py

Corpus:
- ``fuzzy``: tripletas (icv, pi, ev) — grid con paso 0.05 sobre [0,1]²,
  bordes exactos y 200 casos aleatorios con seed fija 20260705.
- ``state``: ApproachState aleatorios (misma seed) + bordes (vacío, saturado)
  para el pipeline completo (ICV+PI+difuso).

Snapshot: la salida del NÚCLEO CANÓNICO para cada caso (delta NS/EO, verdes,
reglas). Si alguien modifica el núcleo científico, el snapshot deja de
coincidir y el test lo denuncia (ese es el objetivo, no un fallo espurio:
regenerar SOLO si el cambio del núcleo es deliberado y justificado).
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

_AQUI = Path(__file__).resolve()
sys.path.insert(0, str(_AQUI.parents[2]))   # raíz "Diseño Software"

from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6
from nucleo.indice_congestion import (
    CalculadorICV,
    ParametrosInterseccion as ParametrosICV,
)

SEED = 20260705
DATA = _AQUI.parent / "data"


def casos_fuzzy() -> list:
    casos = []
    # Grid 0.05 (21×21×2 = 882 casos)
    pasos = [round(i * 0.05, 2) for i in range(21)]
    for icv in pasos:
        for pi in pasos:
            for ev in (0.0, 1.0):
                casos.append({"icv": icv, "pi": pi, "ev": ev})
    # Bordes de las funciones de pertenencia (quiebres exactos)
    for icv in (0.2, 0.4, 0.7):
        for pi in (0.3, 0.5, 0.8):
            for ev in (0.0, 0.5, 1.0):
                casos.append({"icv": icv, "pi": pi, "ev": ev})
    # Aleatorios con seed fija
    rng = random.Random(SEED)
    for _ in range(200):
        casos.append({"icv": round(rng.random(), 6),
                      "pi": round(rng.random(), 6),
                      "ev": rng.choice([0.0, 1.0])})
    return casos


def casos_state() -> list:
    rng = random.Random(SEED + 1)
    casos = []
    # Bordes
    casos.append({"queue_m": 0, "speed_kmh": 0, "flow_veh_min": 0,
                  "num_vehicles": 0, "stopped_vehicles": 0})
    casos.append({"queue_m": 500, "speed_kmh": 0.1, "flow_veh_min": 30,
                  "num_vehicles": 60, "stopped_vehicles": 60})
    for _ in range(200):
        n = rng.randint(0, 50)
        casos.append({
            "queue_m": round(rng.uniform(0, 300), 3),
            "speed_kmh": round(rng.uniform(0, 80), 3),
            "flow_veh_min": round(rng.uniform(0, 40), 3),
            "num_vehicles": n,
            "stopped_vehicles": rng.randint(0, n) if n else 0,
        })
    return casos


def snapshot_fuzzy(difuso: ControladorDifusoCapitulo6, caso: dict) -> dict:
    r = difuso.calcular_ajuste_verde(caso["icv"], caso["pi"], caso["ev"])
    t_verde = difuso.calcular_tiempo_verde_ajustado(
        difuso.T_base_NS, r['delta_t_porcentaje'])
    return {
        "delta_t_porcentaje": r['delta_t_porcentaje'],
        "t_verde": t_verde,
        "reglas": [x['descripcion'] for x in r['reglas_disparadas']],
    }


def snapshot_state(calc: CalculadorICV, caso: dict) -> dict:
    r = calc.calcular(
        longitud_cola=caso["queue_m"],
        velocidad_promedio=caso["speed_kmh"],
        flujo_vehicular=caso["flow_veh_min"],
        num_vehiculos=caso["num_vehicles"],
    )
    return {"icv": r['icv'], "clasificacion": r['clasificacion']}


def main() -> None:
    DATA.mkdir(exist_ok=True)
    difuso = ControladorDifusoCapitulo6()          # defaults canónicos
    calc = CalculadorICV(ParametrosICV())

    with open(DATA / "corpus.jsonl", "w", encoding="utf-8") as fc, \
         open(DATA / "snapshot.jsonl", "w", encoding="utf-8") as fs:
        for caso in casos_fuzzy():
            fc.write(json.dumps({"kind": "fuzzy", "in": caso}) + "\n")
            fs.write(json.dumps({"kind": "fuzzy", "in": caso,
                                 "out": snapshot_fuzzy(difuso, caso)}) + "\n")
        for caso in casos_state():
            fc.write(json.dumps({"kind": "state", "in": caso}) + "\n")
            fs.write(json.dumps({"kind": "state", "in": caso,
                                 "out": snapshot_state(calc, caso)}) + "\n")

    n_f = len(casos_fuzzy())
    n_s = len(casos_state())
    print(f"corpus: {n_f} casos fuzzy + {n_s} casos state -> {DATA}")


if __name__ == "__main__":
    main()
