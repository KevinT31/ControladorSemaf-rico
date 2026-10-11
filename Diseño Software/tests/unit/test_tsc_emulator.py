"""Tests del TSC Emulator: veredictos ACCEPT/CLAMP/DEFER/REJECT y fail-safe
de silencio."""

from nsb.core.adapters import AdaptadorDifuso, AdaptadorICV
from nsb.core.pipeline import DecisionPipeline
from nsb.domain.contracts import PlanSemaforico
from nsb.domain.enums import Direction, Mode, PhaseId, Verdict
from nsb.safety.limits import CONFIG_SEGURA
from nsb.tsc.clock import ManualClock
from nsb.tsc.emulator import TscEmulator
from nsb.tsc.fsm import PhaseFSM

from tests.conftest import make_state


def make_tsc(clock=None, **kw):
    clock = clock or ManualClock()
    fsm = PhaseFSM(clock=clock,
                   plan_inicial=PlanSemaforico(t_verde_ns=30, t_verde_eo=30))
    return TscEmulator(fsm=fsm, mode=Mode.TSC_EMULATED, **kw), clock


def make_rec(seq=0, *, plan=None, ev_preempt=None, state=None):
    """Recomendación real (vía pipeline) con plan opcionalmente sobrescrito."""
    pipeline = DecisionPipeline(AdaptadorICV(), AdaptadorDifuso(),
                                Mode.TSC_EMULATED)
    rec = pipeline.recommend(state or make_state(seq=seq))
    update = {}
    if plan is not None:
        update["plan"] = plan
    if ev_preempt is not None:
        update["ev_preempt"] = ev_preempt
    return rec.model_copy(update=update) if update else rec


class TestVeredictos:
    def test_plan_valido_accept(self):
        tsc, _ = make_tsc()
        d = tsc.process(make_rec(0), "exp-test", 0)
        assert d.verdict is Verdict.ACCEPT
        assert d.plan_aplicado is not None
        assert not d.safe_mode

    def test_verde_200s_clamp_con_correcciones(self):
        tsc, _ = make_tsc()
        rec = make_rec(0, plan=PlanSemaforico(t_verde_ns=200, t_verde_eo=30))
        d = tsc.process(rec, "exp-test", 0)
        assert d.verdict is Verdict.CLAMP
        assert d.plan_aplicado.t_verde_ns == 120.0   # T_VERDE_MAX
        assert d.corrections and d.corrections[0]['campo'] == 't_verde_ns'

    def test_verde_200s_strict_reject(self):
        tsc, _ = make_tsc(clamp_policy="strict")
        rec = make_rec(0, plan=PlanSemaforico(t_verde_ns=200, t_verde_eo=30))
        d = tsc.process(rec, "exp-test", 0)
        assert d.verdict is Verdict.REJECT
        assert d.plan_aplicado is None

    def test_razones_de_guard_reject(self):
        tsc, _ = make_tsc()
        d = tsc.process(make_rec(0), "exp-test", 0,
                        reject_reasons=["duplicate_seq:3"])
        assert d.verdict is Verdict.REJECT
        assert "duplicate_seq:3" in d.reasons

    def test_defer_durante_preempcion(self):
        tsc, clock = make_tsc()
        # 1) rec con preempción EV hacia EO
        d1 = tsc.process(make_rec(0, ev_preempt=Direction.EO), "exp-test", 0)
        assert d1.verdict is Verdict.ACCEPT
        assert tsc.fsm.preempt_activo is Direction.EO
        # 2) siguiente rec sin EV mientras la preempción sigue activa → DEFER
        d2 = tsc.process(make_rec(1), "exp-test", 1)
        assert d2.verdict is Verdict.DEFER
        assert "ev_preempt_activo" in d2.reasons

    def test_direct_lab_no_defer(self):
        clock = ManualClock()
        fsm = PhaseFSM(clock=clock,
                       plan_inicial=PlanSemaforico(t_verde_ns=30, t_verde_eo=30))
        tsc = TscEmulator(fsm=fsm, mode=Mode.AUTOMATED_DIRECT_LAB,
                          defer_during_preempt=False)
        tsc.process(make_rec(0, ev_preempt=Direction.EO), "exp-test", 0)
        d = tsc.process(make_rec(1), "exp-test", 1)
        assert d.verdict is Verdict.ACCEPT   # sin veto de emulador


class TestFailSafeSilencio:
    def test_silencio_activa_config_segura(self):
        tsc, clock = make_tsc(max_silence_cycles=3)
        for k in range(3):
            d = tsc.process(None, "exp-test", k)
            assert d.verdict is Verdict.REJECT
        assert tsc.safe_mode
        assert d.safe_mode
        # El plan seguro quedó programado (pendiente o ya vigente)
        plan = tsc.fsm.plan_pendiente or tsc.fsm.plan_vigente
        assert plan.t_verde_ns == CONFIG_SEGURA['t_verde_ns']

    def test_recomendacion_valida_sale_de_safe_mode(self):
        tsc, _ = make_tsc(max_silence_cycles=2)
        tsc.process(None, "exp-test", 0)
        tsc.process(None, "exp-test", 1)
        assert tsc.safe_mode
        d = tsc.process(make_rec(2), "exp-test", 2)
        assert d.verdict is Verdict.ACCEPT
        assert not tsc.safe_mode

    def test_fsm_sigue_avanzando_sin_recomendaciones(self):
        # Spec §26-G: edge muerto, TSC vivo → el ciclo continúa
        tsc, clock = make_tsc()
        fase_inicial = tsc.fsm.fase
        clock.advance(40.0)
        tsc.process(None, "exp-test", 0)
        assert tsc.fsm.fase is not fase_inicial


class TestPreempcionEVCompleta:
    def test_ev_en_fase_incompatible_secuencia_segura(self):
        """DEMO 10 (spec §43): EV en dirección EO con NS en verde debe
        producir: recorte a mínimo → ámbar → todo-rojo → verde EO."""
        tsc, clock = make_tsc()
        transiciones = [tsc.fsm.fase]
        tsc.fsm._on_transition = lambda a, b: transiciones.append(b)

        clock.advance(2.0)
        tsc.process(make_rec(0, ev_preempt=Direction.EO), "exp-test", 0)
        # Avanzar hasta ver el verde EO
        for _ in range(30):
            clock.advance(1.0)
            tsc.fsm.tick()
            if tsc.fsm.fase is PhaseId.EO_VERDE:
                break
        assert tsc.fsm.fase is PhaseId.EO_VERDE
        assert PhaseId.NS_AMBAR in transiciones
        assert PhaseId.TODO_ROJO_1 in transiciones
        from nsb.tsc.fsm import secuencia_es_segura
        assert secuencia_es_segura(transiciones)
