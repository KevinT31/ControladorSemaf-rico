"""Tests de replay (writer/reader/digest) y del actuador simulado."""

import pytest

from nsb.actuation.simulated import SimulatedActuator
from nsb.domain.enums import SignalColor, SignalGroup
from nsb.safety.gate import TODO_ROJO
from nsb.sources.manual import ManualTestStateSource
from nsb.sources.replay import (
    ReplayStateSource,
    ReplayWriter,
    digest_decisiones,
)

from tests.conftest import make_state


class TestReplayRoundtrip:
    def test_states_sobreviven_roundtrip(self, tmp_path):
        path = tmp_path / "r.jsonl"
        w = ReplayWriter(path)
        originales = [make_state(seq=k) for k in range(5)]
        for st in originales:
            w.write_state(st)
        w.close()

        leidos = list(ReplayStateSource(path))
        assert len(leidos) == 5
        assert leidos == originales   # igualdad estructural pydantic

    def test_fuente_manual_es_determinista(self):
        a = list(ManualTestStateSource("congestion_ns", pasos=10))
        b = list(ManualTestStateSource("congestion_ns", pasos=10))
        assert a == b

    def test_archivo_corrupto_falla_ruidosamente(self, tmp_path):
        path = tmp_path / "c.jsonl"
        path.write_text('{"kind": "state", "data": {"seq": "no"}}\n',
                        encoding="utf-8")
        with pytest.raises(ValueError, match="inválido"):
            list(ReplayStateSource(path))

    def test_replay_inexistente(self):
        with pytest.raises(FileNotFoundError):
            ReplayStateSource("no_existe.jsonl")

    def test_digest_ignora_mediciones(self, tmp_path):
        """Dos corridas con processing_ms distinto ⇒ mismo digest."""
        from nsb.domain.contracts import (AppliedPhase, DecisionEnvelope,
                                          PlanSemaforico)
        from nsb.domain.enums import Mode, PhaseId, Verdict

        def decision(ms):
            return DecisionEnvelope(
                experiment_id="e", seq=0, verdict=Verdict.ACCEPT,
                processing_ms=ms, mode=Mode.TSC_EMULATED,
                applied_phase=AppliedPhase(
                    phase_id=PhaseId.NS_VERDE, since_s=0.0,
                    signal_groups={SignalGroup.NORTE: SignalColor.VERDE,
                                   SignalGroup.SUR: SignalColor.VERDE,
                                   SignalGroup.ESTE: SignalColor.ROJO,
                                   SignalGroup.OESTE: SignalColor.ROJO},
                    plan_en_vigor=PlanSemaforico(t_verde_ns=30, t_verde_eo=30)))

        p1, p2 = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
        for p, ms in ((p1, 1.0), (p2, 99.0)):
            w = ReplayWriter(p)
            w.write_decision(decision(ms))
            w.close()
        assert digest_decisiones(p1) == digest_decisiones(p2)


class TestSimulatedActuator:
    def test_estado_inicial_todo_rojo(self):
        a = SimulatedActuator()
        assert a.state() == TODO_ROJO

    def test_apply_y_state(self):
        a = SimulatedActuator()
        g = dict(TODO_ROJO)
        g[SignalGroup.NORTE] = SignalColor.VERDE
        g[SignalGroup.SUR] = SignalColor.VERDE
        a.apply(g)
        assert a.state() == g
        assert a.applies == 1
        assert a.historia == [g]

    def test_shutdown_es_todo_rojo(self):
        a = SimulatedActuator()
        g = dict(TODO_ROJO)
        g[SignalGroup.ESTE] = SignalColor.VERDE
        g[SignalGroup.OESTE] = SignalColor.VERDE
        a.apply(g)
        a.shutdown()
        assert a.state() == TODO_ROJO
