# -*- coding: utf-8 -*-
"""Degradación ordenada de la CNN-LSTM: el controlador NUNCA depende de la IA.

Sin SUMO corriendo: se instancia ControladorDifusoIA con info vacío (no toca
TraCI) y se verifican los caminos de fallo del predictor.
"""
import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip('sumolib')
import difuso_ia as D  # noqa: E402

ARTIFACTS_REALES = Path(D.__file__).resolve().parent.parent \
    / 'ia' / 'artifacts_fase'


def test_modelo_ausente_no_detiene_el_controlador():
    ctrl = D.ControladorDifusoIA({}, {'modo_ia': 'guardia',
                                      'ruta_artefactos': 'no_existe_dir'})
    assert ctrl.ia_activa is False
    assert ctrl._error_ia and 'FileNotFoundError' in ctrl._error_ia
    # el lazo sigue operable: un paso no lanza excepción con info vacío
    ctrl.paso(0)
    assert ctrl.resumen_ia()['ia_activa'] is False


def test_modo_off_no_carga_predictor():
    ctrl = D.ControladorDifusoIA({}, {'modo_ia': 'off',
                                      'ruta_artefactos': 'no_existe_dir'})
    # en 'off' ni siquiera se intenta cargar: sin error y sin IA
    assert ctrl.ia_activa is False
    assert ctrl._error_ia is None
    assert ctrl._predecir_colas('x', {'fases_verdes': []}) is None


def test_parametros_de_seguridad_se_fuerzan():
    ctrl = D.ControladorDifusoIA({}, {'modo_ia': 'off', 't_ambar': 0.5,
                                      't_todo_rojo': 0.1})
    from nucleo.seguridad_semaforica import LIMITES
    assert ctrl.p['t_ambar'] >= LIMITES.T_AMBAR_MIN
    assert ctrl.p['t_todo_rojo'] >= LIMITES.T_TODO_ROJO_MIN


@pytest.mark.skipif(not (ARTIFACTS_REALES / 'modelo_fase.pt').exists(),
                    reason='sin artefactos entrenados')
def test_normalizacion_desalineada_desactiva_ia(tmp_path):
    pytest.importorskip('torch')
    # artefactos con constantes de normalización DISTINTAS a las del código:
    # la IA debe desactivarse con error explícito (no operar desalineada)
    shutil.copy(ARTIFACTS_REALES / 'modelo_fase.pt', tmp_path / 'modelo_fase.pt')
    cfg = json.loads((ARTIFACTS_REALES / 'config.json').read_text(encoding='utf-8'))
    cfg['normalizacion'] = {'cola_veh': 99.0, 'nveh': 40.0,
                            'vel_kmh': 50.0, 'espera_s': 120.0}
    (tmp_path / 'config.json').write_text(json.dumps(cfg), encoding='utf-8')

    ctrl = D.ControladorDifusoIA({}, {'modo_ia': 'guardia',
                                      'ruta_artefactos': str(tmp_path)})
    assert ctrl.ia_activa is False
    assert 'normalizacion_desalineada' in (ctrl._error_ia or '')


@pytest.mark.skipif(not (ARTIFACTS_REALES / 'modelo_fase.pt').exists(),
                    reason='sin artefactos entrenados')
def test_normalizacion_correcta_carga_ia():
    pytest.importorskip('torch')
    ctrl = D.ControladorDifusoIA({}, {'modo_ia': 'guardia'})
    assert ctrl.ia_activa is True
    assert ctrl._error_ia is None
