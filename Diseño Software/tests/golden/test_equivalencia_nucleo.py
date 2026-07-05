"""Golden master A (spec §20): equivalencia VIVA entre NSB y el núcleo
canónico. Sobre el corpus versionado, la ruta NSB (adaptadores/pipeline) debe
producir exactamente lo mismo que llamar al núcleo directamente — demuestra
que NSB no modificó silenciosamente el algoritmo científico.

Tolerancia 1e-9: misma instancia de código → debería ser bit-exact; la
tolerancia es solo robustez ante reordenamientos de suma en numpy.
"""
import json
from pathlib import Path

import pytest

from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6
from nucleo.indice_congestion import (
    CalculadorICV,
    ParametrosInterseccion as ParametrosICV,
)

from nsb.core.adapters import VEL_REF_KMH, AdaptadorDifuso, AdaptadorICV
from nsb.core.pipeline import DecisionPipeline
from nsb.domain.contracts import ApproachState
from nsb.domain.enums import Direction, Mode

from tests.conftest import make_state

DATA = Path(__file__).parent / "data"
TOL = 1e-9


def _corpus(kind):
    with open(DATA / "corpus.jsonl", encoding="utf-8") as f:
        for linea in f:
            reg = json.loads(linea)
            if reg["kind"] == kind:
                yield reg["in"]


@pytest.fixture(scope="module")
def canonico():
    return ControladorDifusoCapitulo6()


@pytest.fixture(scope="module")
def adaptador():
    return AdaptadorDifuso()


class TestEquivalenciaDifuso:
    def test_delta_y_reglas_identicos(self, canonico, adaptador):
        n = 0
        for caso in _corpus("fuzzy"):
            esperado = canonico.calcular_ajuste_verde(
                caso["icv"], caso["pi"], caso["ev"])
            # La ruta NSB usa el MISMO método vía calcular_control_completo;
            # se contrasta la inferencia de una dirección aislada.
            obtenido = adaptador.controlador.calcular_ajuste_verde(
                caso["icv"], caso["pi"], caso["ev"])
            assert obtenido['delta_t_porcentaje'] == pytest.approx(
                esperado['delta_t_porcentaje'], abs=TOL), caso
            assert ([r['descripcion'] for r in obtenido['reglas_disparadas']]
                    == [r['descripcion'] for r in esperado['reglas_disparadas']]), caso
            n += 1
        assert n > 1000   # el corpus completo se recorrió

    def test_plan_nsb_igual_a_control_completo_canonico(self, canonico, adaptador):
        casos = list(_corpus("fuzzy"))
        # Parejas (NS, EO) barajadas de forma determinista por zip inverso
        for caso_ns, caso_eo in zip(casos[:400], reversed(casos[:400])):
            esperado = canonico.calcular_control_completo(
                icv_ns=caso_ns["icv"], pi_ns=caso_ns["pi"], ev_ns=caso_ns["ev"],
                icv_eo=caso_eo["icv"], pi_eo=caso_eo["pi"], ev_eo=caso_eo["ev"])
            plan, control = adaptador.decidir_plan(
                icv_ns=caso_ns["icv"], pi_ns=caso_ns["pi"], ev_ns=caso_ns["ev"],
                icv_eo=caso_eo["icv"], pi_eo=caso_eo["pi"], ev_eo=caso_eo["ev"])
            assert plan.t_verde_ns == pytest.approx(
                esperado['NS']['T_verde'], abs=TOL)
            assert plan.t_verde_eo == pytest.approx(
                esperado['EO']['T_verde'], abs=TOL)


class TestEquivalenciaICV:
    def test_icv_identico(self):
        canonico = CalculadorICV(ParametrosICV())
        adaptador = AdaptadorICV()
        for caso in _corpus("state"):
            a = ApproachState(**caso)
            esperado = canonico.calcular(
                longitud_cola=caso["queue_m"],
                velocidad_promedio=caso["speed_kmh"],
                flujo_vehicular=caso["flow_veh_min"],
                num_vehiculos=caso["num_vehicles"])['icv']
            icv, pi = adaptador.indicadores(a)
            assert icv == pytest.approx(esperado, abs=TOL), caso
            assert 0.0 <= pi <= 1.0

    def test_pi_es_la_formula_de_los_resultados_de_tesis(self):
        """El PI de NSB replica _demanda_fase (D-D): 0.5·frac_mov + 0.5·v/50."""
        adaptador = AdaptadorICV()
        a = ApproachState(queue_m=10, speed_kmh=25, flow_veh_min=8,
                          num_vehicles=10, stopped_vehicles=4)
        _, pi = adaptador.indicadores(a)
        esperado = 0.5 * (6 / 10) + 0.5 * min(1.0, 25 / VEL_REF_KMH)
        assert pi == pytest.approx(esperado, abs=TOL)


class TestPipelineCompleto:
    def test_pipeline_reproduce_al_canonico(self):
        """End-to-end: TrafficState → pipeline NSB == cadena canónica manual."""
        pipeline = DecisionPipeline(AdaptadorICV(), AdaptadorDifuso(),
                                    Mode.ADVISORY)
        icv_canonico = CalculadorICV(ParametrosICV())
        difuso_canonico = ControladorDifusoCapitulo6()

        for k in range(20):
            st = make_state(seq=k, ev_ns=1.0 if k % 7 == 0 else 0.0)
            rec = pipeline.recommend(st)

            def indicadores(a):
                icv = icv_canonico.calcular(
                    longitud_cola=a.queue_m, velocidad_promedio=a.speed_kmh,
                    flujo_vehicular=a.flow_veh_min,
                    num_vehiculos=a.num_vehicles)['icv']
                moving = max(0, a.num_vehicles - a.stopped_vehicles)
                frac = (moving / a.num_vehicles) if a.num_vehicles else 1.0
                pi = 0.5 * frac + 0.5 * min(1.0, a.speed_kmh / VEL_REF_KMH)
                return icv, pi

            icv_ns, pi_ns = indicadores(st.approaches[Direction.NS])
            icv_eo, pi_eo = indicadores(st.approaches[Direction.EO])
            esperado = difuso_canonico.calcular_control_completo(
                icv_ns=icv_ns, pi_ns=pi_ns, ev_ns=st.ev_ns,
                icv_eo=icv_eo, pi_eo=pi_eo, ev_eo=st.ev_eo)

            assert rec.computed.icv_ns == pytest.approx(icv_ns, abs=TOL)
            assert rec.plan.t_verde_ns == pytest.approx(
                esperado['NS']['T_verde'], abs=TOL)
            assert rec.plan.t_verde_eo == pytest.approx(
                esperado['EO']['T_verde'], abs=TOL)
