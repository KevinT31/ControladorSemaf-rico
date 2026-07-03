# -*- coding: utf-8 -*-
"""Invariantes de transición del controlador canónico sobre SUMO real
(cruce-simple): nunca verde->rojo sin ámbar, ámbar >= 3 s, todo-rojo del
programa servido, verdes dentro de [t_min, t_max].
"""
import pytest

from conftest import CRUCE_CFG, hay_sumo

pytestmark = pytest.mark.skipif(not hay_sumo(), reason='SUMO no disponible')

PASOS = 260


def _correr_con_estados(params_ia):
    """Corre difuso_ia sobre cruce-simple registrando el estado RYG por paso."""
    import comparacion_multibaseline as M
    import comparacion_sumo as C
    import difuso_ia as D
    from conector_sumo import traci

    M._iniciar(str(CRUCE_CFG), seed=7)
    try:
        C._forzar_tiempo_fijo(t_verde=30.0)
        info = C._mapear_semaforos()
        ctrl = D.ControladorDifusoIA(info, params_ia)
        estados = {tls: [] for tls in ctrl.info}
        for i in range(PASOS):
            traci.simulationStep()
            ctrl.paso(i)
            for tls in estados:
                estados[tls].append(
                    traci.trafficlight.getRedYellowGreenState(tls))
        resumen = ctrl.resumen_ia()
        ctrl.cerrar()
    finally:
        traci.close()
    return estados, resumen


@pytest.fixture(scope='module')
def corrida():
    return _correr_con_estados({'modo_ia': 'off'})


def test_sin_errores_de_paso(corrida):
    _, resumen = corrida
    assert resumen['errores_paso'] == 0


def test_nunca_verde_a_rojo_sin_ambar(corrida):
    estados, _ = corrida
    for tls, secuencia in estados.items():
        for s1, s2 in zip(secuencia, secuencia[1:]):
            for i, (a, b) in enumerate(zip(s1, s2)):
                assert not (a in 'Gg' and b in 'rs'), (
                    f'{tls}: señal {i} pasó de verde a rojo sin ámbar '
                    f'({s1} -> {s2})')


def test_ambar_dura_al_menos_3s(corrida):
    estados, _ = corrida
    for tls, secuencia in estados.items():
        rachas = []
        n = 0
        for s in secuencia:
            if 'y' in s.lower():
                n += 1
            elif n:
                rachas.append(n)
                n = 0
        # toda transición servida completa debe exhibir >= 3 muestras de ámbar
        assert rachas, f'{tls}: no se observó ningún ámbar en {PASOS} pasos'
        assert min(rachas) >= 3, f'{tls}: ámbar de {min(rachas)} s (< 3 s)'


def test_todo_rojo_del_programa_se_sirve(corrida):
    # cruce-simple define fases de despeje (todo-rojo, 2 s) tras cada ámbar;
    # antes se saltaban con setPhase directo (bug corregido)
    estados, _ = corrida
    for tls, secuencia in estados.items():
        allred = [s for s in secuencia if set(s.lower()) == {'r'}]
        assert allred, f'{tls}: ninguna fase todo-rojo servida en {PASOS} pasos'


def test_verde_minimo_respetado(corrida):
    estados, _ = corrida
    for tls, secuencia in estados.items():
        rachas = []
        n = 0
        for s in secuencia:
            if any(c in 'Gg' for c in s) and 'y' not in s.lower():
                n += 1
            elif n:
                rachas.append(n)
                n = 0
        # los verdes completos (no truncados por el fin de la corrida) deben
        # durar al menos t_verde_min = 10 s
        completos = rachas[1:] if rachas else []
        assert all(r >= 10 for r in completos), \
            f'{tls}: verde de {min(completos)} s (< 10 s)'
