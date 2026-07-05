"""Integración: fuente → nodo → actuador simulado, con determinismo
verificable por digest (DEMO 1, 2 y 12 de la spec §43)."""
import pytest

from nsb.config import NodeConfig
from nsb.domain.enums import Mode, SourceKind
from nsb.node import NsbNode
from nsb.safety.conflict_matrix import ConflictMatrix
from nsb.sources.manual import ManualTestStateSource
from nsb.sources.replay import ReplayStateSource, ReplayWriter, digest_decisiones


def make_node(tmp_path, mode=Mode.TSC_EMULATED):
    cfg = NodeConfig(
        mode=mode, source=SourceKind.MANUAL,
        telemetry={"jsonl_dir": str(tmp_path / "telemetria")})
    return NsbNode.from_config(cfg, experiment_id="test-integ")


def correr(tmp_path, nombre, escenario="congestion_ns", pasos=30,
           mode=Mode.TSC_EMULATED):
    node = make_node(tmp_path / nombre, mode=mode)
    writer = ReplayWriter(tmp_path / f"{nombre}.jsonl")
    fuente = ManualTestStateSource(escenario=escenario, pasos=pasos)
    summary = node.run(fuente, writer=writer)
    node.shutdown()
    return summary, tmp_path / f"{nombre}.jsonl"


class TestDeterminismo:
    def test_dos_corridas_mismo_digest(self, tmp_path):
        """DEMO 12: replay determinista — misma entrada ⇒ mismas decisiones."""
        _, p1 = correr(tmp_path, "corrida1")
        _, p2 = correr(tmp_path, "corrida2")
        assert digest_decisiones(p1) == digest_decisiones(p2)

    def test_replay_de_grabacion_reproduce_decisiones(self, tmp_path):
        """Grabar una corrida y re-decidir desde el JSONL produce el mismo
        digest (la ruta replay no altera la decisión)."""
        _, p1 = correr(tmp_path, "original")

        node = make_node(tmp_path / "replay")
        writer = ReplayWriter(tmp_path / "replay.jsonl")
        summary = node.run(ReplayStateSource(p1), writer=writer)
        node.shutdown()
        assert summary.estados == 30
        assert digest_decisiones(p1) == digest_decisiones(
            tmp_path / "replay.jsonl")


class TestModos:
    def test_advisory_no_actua_y_registra(self, tmp_path):
        """DEMO 1: ADVISORY + replay — recomendaciones sin actuación."""
        summary, path = correr(tmp_path, "advisory", mode=Mode.ADVISORY)
        assert summary.estados == 30
        assert summary.verdicts.get("accept") == 30
        assert summary.violaciones_gate == 0
        # Las decisiones de advisory jamás llevan plan aplicado
        from nsb.sources.replay import leer_decisiones
        assert all(d.plan_aplicado is None for d in leer_decisiones(path))

    def test_tsc_emulated_actua_seguro(self, tmp_path):
        """DEMO 2: TSC_EMULATED + SimulatedActuator, sin conflictos."""
        node = make_node(tmp_path, mode=Mode.TSC_EMULATED)
        fuente = ManualTestStateSource(escenario="emergencia_ns", pasos=30)
        summary = node.run(fuente)
        actuator = node.authority._actuator
        m = ConflictMatrix()
        assert actuator.applies == 30
        assert all(m.es_segura(g) for g in actuator.historia)
        assert summary.violaciones_gate == 0
        node.shutdown()

    def test_emergencia_dispara_reglas_ev(self, tmp_path):
        """El escenario de emergencia activa las reglas R1-R3 del difuso."""
        node = make_node(tmp_path, mode=Mode.ADVISORY)
        fuente = ManualTestStateSource(escenario="emergencia_ns", pasos=20)
        recs = []
        for st in fuente:
            rec, _ = node.process_one(st)
            recs.append(rec)
        node.shutdown()
        con_ev = [r for r in recs if r and r.computed.ev_ns > 0]
        assert con_ev, "el escenario debe traer estados con EV"
        assert any(any(regla.startswith("NS:R1") or regla.startswith("NS:R2")
                       or regla.startswith("NS:R3")
                       for regla in r.reglas_disparadas)
                   for r in con_ev)
