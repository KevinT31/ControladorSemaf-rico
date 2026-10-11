"""Separación de semillas y transiciones seguras del experimento de fase."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / 'integracion-sumo'))

from difuso_ia import ControladorDifusoIA, _estado_ambar, _fase_todo_rojo_tras
from ia.entrenamiento_fase import particion_fijada


def test_particion_fijada_rechaza_semillas_de_prueba():
    series = {'comparacion_101|tls|0': [[0.0]],
              'comparacion_media_203|tls|0': [[0.0]]}
    partes = particion_fijada(series)
    assert list(partes['train']) == ['comparacion_101|tls|0']
    assert list(partes['val']) == ['comparacion_media_203|tls|0']
    with pytest.raises(ValueError, match='fuera del protocolo'):
        particion_fijada({'comparacion_1|tls|0': [[0.0]]})


def test_ambar_sintetico_y_despeje():
    assert _estado_ambar('Grr', 'rGr') == 'yrr'
    logic = SimpleNamespace(phases=[SimpleNamespace(state=s) for s in
                                    ('Grr', 'yrr', 'rrr', 'rGr')])
    assert _fase_todo_rojo_tras(logic, 1) == 2


def test_guardia_acota_verde_y_ambar(monkeypatch):
    import difuso_ia
    monkeypatch.setattr(difuso_ia.traci.lane, 'getLinks', lambda lane: [])
    logic = SimpleNamespace(phases=[SimpleNamespace(state=s) for s in
                                    ('Gr', 'yr', 'rr', 'rG', 'ry', 'rr')])
    info = {'t': {'logic': logic, 'fases_verdes': [
        {'idx': 0, 'lanes': ['a']}, {'idx': 3, 'lanes': ['b']}]}}
    ctrl = ControladorDifusoIA(info, {'modo_ia': 'off', 't_ambar': 1,
                                      't_verde_max': 999})
    assert ctrl.t_min == 10
    assert ctrl.t_max == 120
    assert ctrl.p['t_ambar'] >= 3
    assert ctrl.p['t_todo_rojo'] >= 2
    assert ctrl.estado['t']['t'] == 10


def test_despeje_sintetico_si_programa_no_tiene_todo_rojo(monkeypatch):
    import difuso_ia
    monkeypatch.setattr(difuso_ia.traci.lane, 'getLinks', lambda lane: [])
    logic = SimpleNamespace(phases=[SimpleNamespace(state=s) for s in
                                    ('Gr', 'yr', 'rG', 'ry')])
    info = {'t': {'logic': logic, 'fases_verdes': [
        {'idx': 0, 'lanes': ['a']}, {'idx': 2, 'lanes': ['b']}]}}
    ctrl = ControladorDifusoIA(info, {'modo_ia': 'off', 't_todo_rojo': 0})
    pasos = []
    monkeypatch.setattr(ctrl, '_aplicar_transicion',
                        lambda tls, tipo, val, dur: pasos.append((tipo, val, dur)))
    ctrl._iniciar_transicion('t', info['t'], 0, 2, 20)
    assert pasos == [('fase', 1, 3.)]
    assert ctrl.estado['t']['trans'][0] == ('estado', 'rr', 2.)
    assert ctrl.estado['t']['trans'][1] == ('verde', 2, 20)


def test_renovacion_no_supera_120_segundos(monkeypatch):
    import difuso_ia
    monkeypatch.setattr(difuso_ia.traci.lane, 'getLinks', lambda lane: [])
    logic = SimpleNamespace(phases=[SimpleNamespace(state=s) for s in
                                    ('Gr', 'yr', 'rr', 'rG', 'ry', 'rr')])
    info = {'t': {'logic': logic, 'fases_verdes': [
        {'idx': 0, 'lanes': ['a']}, {'idx': 3, 'lanes': ['b']}]}}
    ctrl = ControladorDifusoIA(info, {'modo_ia': 'off'})
    ctrl.estado['t']['elapsed'] = 115
    monkeypatch.setattr(difuso_ia, '_medir_fase',
                        lambda lanes, stats=None: (1., 1., 0., 0.) if lanes == ['a'] else (0., 0., 0., 0.))
    monkeypatch.setattr(difuso_ia.C, '_demanda_fase', lambda lanes, calc: (0.5, 0.5))
    cambios = []
    monkeypatch.setattr(ctrl, '_iniciar_transicion',
                        lambda tls, data, actual, objetivo, dur: cambios.append((actual, objetivo, dur)))
    ctrl._decidir('t', info['t'], 115.)
    assert cambios and cambios[0][0:2] == (0, 3)
    assert 10 <= cambios[0][2] <= 120
