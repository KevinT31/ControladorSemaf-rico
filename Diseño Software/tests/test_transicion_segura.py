# -*- coding: utf-8 -*-
"""Helpers de transición segura (ámbar sintético, todo-rojo del programa).

Puros sobre strings/objetos falsos; requieren importar comparacion_sumo,
que a su vez necesita sumolib instalado (no una simulación corriendo).
"""
import pytest

pytest.importorskip('sumolib')
import comparacion_sumo as C  # noqa: E402


class _Fase:
    def __init__(self, state, duration=3.0):
        self.state = state
        self.duration = duration


class _Logic:
    def __init__(self, estados):
        self.phases = [_Fase(s) for s in estados]


def test_estado_ambar_senales_que_pierden_verde():
    # señales 0-3 pierden el verde -> 'y'; 4-7 lo ganan -> conservan su color
    assert C._estado_ambar('GGGgrrrr', 'rrrrGGGg') == 'yyyyrrrr'


def test_estado_ambar_senal_que_conserva_verde_no_cambia():
    # la señal 0 sigue en verde en el objetivo: no debe pasar a ámbar
    assert C._estado_ambar('GGrr', 'Grrr') == 'Gyrr'


def test_estado_ambar_nunca_produce_verde_nuevo():
    amb = C._estado_ambar('GGGgrrrr', 'rrrrGGGg')
    # ninguna señal roja del estado actual aparece verde en el ámbar
    assert all(a not in 'Gg' for a, c in zip(amb, 'GGGgrrrr') if c == 'r')


def test_fase_todo_rojo_tras_ambar_detectada():
    # programa tipo cruce-simple: G, y, todo-rojo, G, y, todo-rojo
    logic = _Logic(['GGGgrrrr', 'yyyyrrrr', 'rrrrrrrr',
                    'rrrrGGGg', 'rrrryyyy', 'rrrrrrrr'])
    assert C._fase_todo_rojo_tras(logic, 1) == 2
    assert C._fase_todo_rojo_tras(logic, 4) == 5


def test_fase_todo_rojo_ausente_devuelve_none():
    logic = _Logic(['GGrr', 'yyrr', 'rrGG', 'rryy'])   # sin fase de despeje
    assert C._fase_todo_rojo_tras(logic, 1) is None
