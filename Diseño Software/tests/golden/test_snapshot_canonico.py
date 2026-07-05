"""Golden master B (spec §20): el núcleo canónico contra su snapshot
VERSIONADO. Si este test falla, alguien modificó el algoritmo científico
(reglas difusas, funciones de pertenencia, pesos, fórmulas) — exactamente lo
que la spec prohíbe hacer en silencio (§7.4).

Si el cambio del núcleo fue deliberado y está justificado/documentado,
regenerar con: python tests/golden/generar_corpus.py
"""
import json
from pathlib import Path

import pytest

from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6
from nucleo.indice_congestion import (
    CalculadorICV,
    ParametrosInterseccion as ParametrosICV,
)

DATA = Path(__file__).parent / "data"
TOL = 1e-9

MENSAJE = ("EL NÚCLEO CIENTÍFICO CAMBIÓ respecto al snapshot versionado. "
           "Si fue deliberado, documentarlo y regenerar con "
           "generar_corpus.py; si no, revertir el cambio.")


def _snapshot(kind):
    with open(DATA / "snapshot.jsonl", encoding="utf-8") as f:
        for linea in f:
            reg = json.loads(linea)
            if reg["kind"] == kind:
                yield reg["in"], reg["out"]


def test_difuso_coincide_con_snapshot():
    difuso = ControladorDifusoCapitulo6()
    n = 0
    for entrada, esperado in _snapshot("fuzzy"):
        r = difuso.calcular_ajuste_verde(entrada["icv"], entrada["pi"],
                                         entrada["ev"])
        assert r['delta_t_porcentaje'] == pytest.approx(
            esperado["delta_t_porcentaje"], abs=TOL), (MENSAJE, entrada)
        t_verde = difuso.calcular_tiempo_verde_ajustado(
            difuso.T_base_NS, r['delta_t_porcentaje'])
        assert t_verde == pytest.approx(esperado["t_verde"], abs=TOL), (
            MENSAJE, entrada)
        assert [x['descripcion'] for x in r['reglas_disparadas']] == \
            esperado["reglas"], (MENSAJE, entrada)
        n += 1
    assert n > 1000


def test_icv_coincide_con_snapshot():
    calc = CalculadorICV(ParametrosICV())
    n = 0
    for entrada, esperado in _snapshot("state"):
        r = calc.calcular(
            longitud_cola=entrada["queue_m"],
            velocidad_promedio=entrada["speed_kmh"],
            flujo_vehicular=entrada["flow_veh_min"],
            num_vehiculos=entrada["num_vehicles"])
        assert r['icv'] == pytest.approx(esperado["icv"], abs=TOL), (
            MENSAJE, entrada)
        assert r['clasificacion'] == esperado["clasificacion"], (
            MENSAJE, entrada)
        n += 1
    assert n >= 200
