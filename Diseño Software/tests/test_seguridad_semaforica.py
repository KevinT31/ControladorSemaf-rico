# -*- coding: utf-8 -*-
"""Invariantes de la capa central de seguridad funcional (sin SUMO)."""
import math

from nucleo.seguridad_semaforica import (LIMITES, ValidadorSeguridadSemaforica)

V = ValidadorSeguridadSemaforica()


def test_clamp_verde_recorta_a_limites():
    tiempos, corr = V.clamp_tiempos(t_verde_ns=200.0, t_verde_eo=5.0)
    assert tiempos['t_verde_ns'] == LIMITES.T_VERDE_MAX
    assert tiempos['t_verde_eo'] == LIMITES.T_VERDE_MIN
    assert len(corr) == 2  # ambas correcciones trazadas


def test_clamp_nan_cae_al_minimo_seguro():
    tiempos, corr = V.clamp_tiempos(t_verde_ns=float('nan'), t_verde_eo=30.0)
    assert tiempos['t_verde_ns'] == LIMITES.T_VERDE_MIN
    assert any(c['campo'] == 't_verde_ns' for c in corr)


def test_ambar_y_todo_rojo_minimos():
    ok, errores = V.validar_parametros_control({'t_ambar': 1.0,
                                                't_todo_rojo': 0.5})
    assert not ok
    assert any('amarillo' in e for e in errores)
    assert any('todo-rojo' in e for e in errores)
    tiempos, _ = V.clamp_tiempos(30.0, 30.0, t_ambar=1.0, t_todo_rojo=0.5)
    assert tiempos['t_ambar'] >= LIMITES.T_AMBAR_MIN
    assert tiempos['t_todo_rojo'] >= LIMITES.T_TODO_ROJO_MIN


def test_no_conflicto_de_fases():
    assert V.verificar_fases_no_conflictivas(True, False)
    assert V.verificar_fases_no_conflictivas(False, True)
    assert V.verificar_fases_no_conflictivas(False, False)
    assert not V.verificar_fases_no_conflictivas(True, True)


def test_modo_seguro_ante_estado_invalido():
    res = V.aplicar_con_seguridad({'t_verde_ns': 30, 't_verde_eo': 30},
                                  estado={'icv': float('nan')})
    assert res['modo_seguro'] is True
    t = res['tiempos']
    assert t['t_ambar'] >= LIMITES.T_AMBAR_MIN
    assert LIMITES.T_VERDE_MIN <= t['t_verde_ns'] <= LIMITES.T_VERDE_MAX


def test_modo_seguro_sin_salida_difusa():
    assert V.aplicar_con_seguridad(None)['modo_seguro'] is True
    assert V.aplicar_con_seguridad({})['modo_seguro'] is True
