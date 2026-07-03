# -*- coding: utf-8 -*-
"""Métricas (flujo por cruces, eventos de validez) y reproducibilidad por
semilla del aparato experimental multibaseline, sobre cruce-simple."""
import pytest

from conftest import CRUCE_CFG, hay_sumo

pytestmark = pytest.mark.skipif(not hay_sumo(), reason='SUMO no disponible')

PASOS = 150


def test_flujo_por_cruces_acotado_y_no_saturado():
    """El flujo debe medir CRUCES por ventana: acotado, y en un cruce simple
    con demanda media NUNCA el máximo teórico constante (el bug anterior
    saturaba el cap con un solo vehículo presente)."""
    import comparacion_multibaseline as M
    import comparacion_sumo as C
    from conector_sumo import traci

    M._iniciar(str(CRUCE_CFG), seed=3)
    try:
        C._forzar_tiempo_fijo(t_verde=30.0)
        info = C._mapear_semaforos()
        lanes = [l for d in info.values()
                 for g in d['fases_verdes'] for l in g['lanes']]
        medidor = C.ContadorCruces(lanes)
        assert medidor.flujo_veh_min(lanes) == 0.0   # sin datos -> 0, no cap
        muestras = []
        for i in range(PASOS):
            traci.simulationStep()
            medidor.actualizar()
            if i >= 60 and i % 10 == 0:
                muestras.append(medidor.flujo_veh_min(lanes))
    finally:
        traci.close()
    assert muestras and all(0.0 <= f <= 120.0 for f in muestras)
    assert sum(muestras) > 0.0            # con demanda media algo cruza
    assert len(set(round(f, 3) for f in muestras)) > 1, \
        'flujo constante: sugiere término saturado (bug regresado)'


def test_eventos_paso_devuelve_claves_de_validez():
    import comparacion_multibaseline as M
    import comparacion_sumo as C
    from conector_sumo import traci

    M._iniciar(str(CRUCE_CFG), seed=3)
    try:
        traci.simulationStep()
        ev = C._eventos_paso()
    finally:
        traci.close()
    assert set(ev) == {'teleports', 'backlog', 'departed'}
    assert all(v >= 0 for v in ev.values())


def test_misma_semilla_mismo_resultado():
    import comparacion_multibaseline as M
    r1 = M.ejecutar_estrategia(str(CRUCE_CFG), 7, PASOS, 'difuso')
    r2 = M.ejecutar_estrategia(str(CRUCE_CFG), 7, PASOS, 'difuso')
    for k in ('ICV_red', 'throughput', 'demora_media_veh_s',
              'vehiculos_insertados', 'teleports'):
        assert r1[k] == r2[k], f'{k} difiere entre corridas con la misma semilla'


def test_distinta_semilla_distinto_resultado():
    import comparacion_multibaseline as M
    r1 = M.ejecutar_estrategia(str(CRUCE_CFG), 7, PASOS, 'difuso')
    r2 = M.ejecutar_estrategia(str(CRUCE_CFG), 11, PASOS, 'difuso')
    assert any(r1[k] != r2[k]
               for k in ('ICV_red', 'demora_media_veh_s', 'Vavg_red'))


def test_metadatos_de_reproducibilidad():
    import comparacion_multibaseline as M
    r = M.ejecutar_estrategia(str(CRUCE_CFG), 5, 50, 'fijo')
    assert r['sumo_version'], 'la corrida debe registrar la versión de SUMO'
    assert isinstance(M._git_hash(), str)
    for k in ('teleports', 'backlog_medio', 'backlog_max',
              'demora_media_veh_s', 'vehiculos_insertados',
              'tviaje_p90_s', 'tviaje_p95_s'):
        assert k in r, f'métrica {k} ausente'
