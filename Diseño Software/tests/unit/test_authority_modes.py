"""Tests de los modos de autoridad y la triple compuerta de direct-lab."""
import pytest

from nsb.actuation.simulated import SimulatedActuator
from nsb.authority.direct_lab_gate import (
    ENV_CONFIRM,
    DirectLabDenied,
    resolve_mode,
)
from nsb.authority.modes import Authority
from nsb.core.adapters import AdaptadorDifuso, AdaptadorICV
from nsb.core.pipeline import DecisionPipeline
from nsb.domain.contracts import PlanSemaforico
from nsb.domain.enums import Mode, SignalColor, SignalGroup, Verdict
from nsb.safety.message_guard import MessageGuard
from nsb.tsc.clock import ManualClock
from nsb.tsc.emulator import TscEmulator
from nsb.tsc.fsm import PhaseFSM

from tests.conftest import make_state


def make_authority(mode, clock=None, actuator=None):
    clock = clock or ManualClock()
    pipeline = DecisionPipeline(AdaptadorICV(), AdaptadorDifuso(), mode)
    fsm = PhaseFSM(clock=clock,
                   plan_inicial=PlanSemaforico(t_verde_ns=30, t_verde_eo=30))
    tsc = TscEmulator(fsm=fsm, mode=mode)
    if actuator is None and mode is not Mode.ADVISORY:
        actuator = SimulatedActuator()
    return Authority(mode=mode, pipeline=pipeline, tsc=tsc,
                     guard=MessageGuard(), actuator=actuator), actuator


class TestAdvisory:
    def test_jamas_actua(self):
        actuator = SimulatedActuator()
        authority, _ = make_authority(Mode.ADVISORY, actuator=actuator)
        for k in range(10):
            rec, decision = authority.process_state(make_state(seq=k))
            assert rec is not None
            assert decision.plan_aplicado is None
        assert actuator.applies == 0   # NUNCA se llamó apply()

    def test_decision_es_solo_registro(self):
        authority, _ = make_authority(Mode.ADVISORY)
        rec, decision = authority.process_state(make_state(seq=0))
        assert decision.verdict is Verdict.ACCEPT
        assert "advisory:solo_registro" in decision.reasons

    def test_guard_rechaza_y_lo_reporta(self):
        authority, _ = make_authority(Mode.ADVISORY)
        authority.process_state(make_state(seq=5))
        rec, decision = authority.process_state(make_state(seq=5))  # dup
        assert rec is None
        assert decision.verdict is Verdict.REJECT


class TestTscEmulated:
    def test_actua_tras_gate(self):
        authority, actuator = make_authority(Mode.TSC_EMULATED)
        rec, decision = authority.process_state(make_state(seq=0))
        assert decision.verdict is Verdict.ACCEPT
        assert actuator.applies == 1
        # Lo aplicado coincide con la fase de la decisión
        assert actuator.state() == decision.applied_phase.signal_groups

    def test_historial_sin_conflictos(self):
        authority, actuator = make_authority(Mode.TSC_EMULATED)
        for k in range(20):
            authority.process_state(make_state(seq=k))
        from nsb.safety.conflict_matrix import ConflictMatrix
        m = ConflictMatrix()
        assert all(m.es_segura(g) for g in actuator.historia)

    def test_estado_rechazado_no_puede_avanzar_reloj(self):
        clock = ManualClock()
        authority, _ = make_authority(Mode.TSC_EMULATED, clock=clock)
        authority.process_state(make_state(seq=0, sim_time_s=0.0))

        _, decision = authority.process_state(
            make_state(seq=0, sim_time_s=36.0),  # duplicado con tiempo futuro
            on_state_accepted=lambda: clock.set(36.0),
        )

        assert decision.verdict is Verdict.REJECT
        assert clock.now() == 0.0
        assert decision.applied_phase.phase_id.value == "ns_verde"

    def test_requiere_actuador(self):
        clock = ManualClock()
        pipeline = DecisionPipeline(AdaptadorICV(), AdaptadorDifuso(),
                                    Mode.TSC_EMULATED)
        fsm = PhaseFSM(clock=clock, plan_inicial=PlanSemaforico(
            t_verde_ns=30, t_verde_eo=30))
        with pytest.raises(ValueError, match="requiere un actuador"):
            Authority(mode=Mode.TSC_EMULATED, pipeline=pipeline,
                      tsc=TscEmulator(fsm=fsm, mode=Mode.TSC_EMULATED),
                      guard=MessageGuard(), actuator=None)


class TestSafetyGateEnAutoridad:
    def test_conflicto_inyectado_se_bloquea(self):
        """DEMO 7: si algo (fault injection) produjera verdes conflictivos,
        el gate fuerza todo-rojo antes del actuador."""
        authority, actuator = make_authority(Mode.TSC_EMULATED)
        _, decision = authority.process_state(make_state(seq=0))

        # Simular corrupción del estado de la FSM (bypass hipotético):
        conflicto = {SignalGroup.NORTE: SignalColor.VERDE,
                     SignalGroup.SUR: SignalColor.VERDE,
                     SignalGroup.ESTE: SignalColor.VERDE,
                     SignalGroup.OESTE: SignalColor.ROJO}
        decision_corrupta = decision.model_copy(update={
            "applied_phase": decision.applied_phase.model_copy(
                update={"signal_groups": conflicto})})
        resultado = authority._actuar(decision_corrupta)
        assert resultado.safe_mode
        assert "safety_gate:todo_rojo_forzado" == resultado.safe_mode_reason
        from nsb.safety.gate import TODO_ROJO
        assert actuator.state() == TODO_ROJO


class TestTripleCompuerta:
    NODE = "nodo-test"

    def test_modos_normales_sin_compuertas(self, monkeypatch):
        monkeypatch.delenv(ENV_CONFIRM, raising=False)
        assert resolve_mode(Mode.ADVISORY, False, None, self.NODE) is Mode.ADVISORY
        assert resolve_mode(Mode.TSC_EMULATED, False, None,
                            self.NODE) is Mode.TSC_EMULATED

    def test_solo_config_denegado(self, monkeypatch):
        monkeypatch.delenv(ENV_CONFIRM, raising=False)
        with pytest.raises(DirectLabDenied, match="CLI"):
            resolve_mode(Mode.AUTOMATED_DIRECT_LAB, True, None, self.NODE)

    def test_solo_cli_denegado(self, monkeypatch):
        monkeypatch.delenv(ENV_CONFIRM, raising=False)
        with pytest.raises(DirectLabDenied, match="allow_direct_lab"):
            resolve_mode(Mode.TSC_EMULATED, False,
                         Mode.AUTOMATED_DIRECT_LAB, self.NODE)

    def test_sin_env_denegado(self, monkeypatch):
        monkeypatch.delenv(ENV_CONFIRM, raising=False)
        with pytest.raises(DirectLabDenied, match=ENV_CONFIRM):
            resolve_mode(Mode.AUTOMATED_DIRECT_LAB, True,
                         Mode.AUTOMATED_DIRECT_LAB, self.NODE)

    def test_env_con_node_id_equivocado_denegado(self, monkeypatch):
        monkeypatch.setenv(ENV_CONFIRM, "otro-nodo")
        with pytest.raises(DirectLabDenied):
            resolve_mode(Mode.AUTOMATED_DIRECT_LAB, True,
                         Mode.AUTOMATED_DIRECT_LAB, self.NODE)

    def test_tres_compuertas_activa(self, monkeypatch):
        monkeypatch.setenv(ENV_CONFIRM, self.NODE)
        mode = resolve_mode(Mode.AUTOMATED_DIRECT_LAB, True,
                            Mode.AUTOMATED_DIRECT_LAB, self.NODE)
        assert mode is Mode.AUTOMATED_DIRECT_LAB

    def test_cli_degrada_sin_compuertas(self, monkeypatch):
        # Degradar (direct-lab en config → advisory por CLI) NO exige nada
        monkeypatch.delenv(ENV_CONFIRM, raising=False)
        mode = resolve_mode(Mode.AUTOMATED_DIRECT_LAB, True, Mode.ADVISORY,
                            self.NODE)
        assert mode is Mode.ADVISORY
