"""El controlador difuso del Capítulo 6 admite puntos de pertenencia calibrables
sin alterar su comportamiento por defecto."""
import itertools
import json
from pathlib import Path

import pytest

from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6

RUTA_CALIBRADOS = (Path(__file__).resolve().parents[2] / "integracion-sumo"
                   / "resultados" / "parametros_difuso_calibrados.json")
MALLA = list(itertools.product([0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0],
                               [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]))


def test_puntos_por_defecto_equivalen_a_los_del_capitulo_6():
    base = ControladorDifusoCapitulo6()
    explicito = ControladorDifusoCapitulo6(puntos_icv=(0.2, 0.4, 0.7),
                                           puntos_pi=(0.3, 0.5, 0.8))
    for icv, pi in MALLA:
        a = base.calcular_ajuste_verde(icv, pi, 0.0)["delta_t_porcentaje"]
        b = explicito.calcular_ajuste_verde(icv, pi, 0.0)["delta_t_porcentaje"]
        assert a == b


@pytest.mark.parametrize("puntos", [(0.4, 0.2, 0.7), (0.2, 0.2, 0.7),
                                    (0.0, 0.4, 0.7), (0.2, 0.4, 1.0)])
def test_puntos_desordenados_o_fuera_de_rango_se_rechazan(puntos):
    with pytest.raises(ValueError):
        ControladorDifusoCapitulo6(puntos_icv=puntos)
    with pytest.raises(ValueError):
        ControladorDifusoCapitulo6(puntos_pi=puntos)


def test_puntos_distintos_modifican_la_inferencia_y_siguen_acotados():
    base = ControladorDifusoCapitulo6()
    otro = ControladorDifusoCapitulo6(puntos_icv=(0.15, 0.35, 0.6),
                                      puntos_pi=(0.25, 0.45, 0.7))
    difieren = False
    for icv, pi in MALLA:
        delta = otro.calcular_ajuste_verde(icv, pi, 0.0)["delta_t_porcentaje"]
        assert -30.0 <= delta <= 30.0
        difieren |= delta != base.calcular_ajuste_verde(icv, pi, 0.0)["delta_t_porcentaje"]
    assert difieren


@pytest.mark.skipif(not RUTA_CALIBRADOS.exists(),
                    reason="no se ha ejecutado la calibración")
def test_parametros_calibrados_son_validos_y_acotados():
    p = json.loads(RUTA_CALIBRADOS.read_text(encoding="utf-8"))["parametros"]
    assert 0.0 < p["alpha"] <= 1.0
    assert p["gamma"] >= 1.0
    ctrl = ControladorDifusoCapitulo6(puntos_icv=tuple(p["puntos_icv"]),
                                      puntos_pi=tuple(p["puntos_pi"]))
    for icv, pi in MALLA:
        assert -30.0 <= ctrl.calcular_ajuste_verde(icv, pi, 0.0)["delta_t_porcentaje"] <= 30.0
