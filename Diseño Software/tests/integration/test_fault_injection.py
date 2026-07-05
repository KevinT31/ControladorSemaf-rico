"""Fault injection end-to-end (spec §32): los fallos inyectados deben ser
absorbidos por el guard, el TSC o el SafetyGate — jamás producir un estado
físico inseguro ni tumbar el nodo.

Cobertura de los 12 fallos de la spec:
  1 verde 200 s      → aquí (SabotagePipeline → CLAMP)
  2 verdes conflict. → aquí (gate) y unit test_authority_modes
  3 pérdida MQTT     → F3 (broker); diseño: telemetría nunca bloquea control
  4 pérdida HIL      → F2 (test_hil_localhost, timeout del gateway)
  5 NaN              → aquí (CorruptingSource → guard no_finito)
  6 infinito         → aquí
  7 mensaje vencido  → unit test_safety (stale) — transporte en F2
  8 seq duplicado    → aquí
  9 seq fuera orden  → aquí
 10 predictor caído  → aquí (PredictorRoto → fallback difuso)
 11 edge no disponible → unit test_tsc_emulator (silencio → CONFIG_SEGURA)
 12 EV incompatible  → unit test_tsc_emulator (secuencia segura)
"""
import pytest

from nsb.core.adapters import AdaptadorDifuso, AdaptadorICV
from nsb.core.pipeline import DecisionPipeline
from nsb.domain.enums import Mode, SourceKind, Verdict
from nsb.faults.injectors import (
    CorruptingSource,
    PredictorRoto,
    SabotagePipeline,
)
from nsb.faults.plan import FaultPlan
from nsb.config import NodeConfig
from nsb.node import NsbNode
from nsb.safety.conflict_matrix import ConflictMatrix
from nsb.sources.manual import ManualTestStateSource

from tests.conftest import make_state


def make_node(tmp_path, mode=Mode.TSC_EMULATED):
    cfg = NodeConfig(mode=mode, source=SourceKind.MANUAL,
                     telemetry={"jsonl_dir": str(tmp_path / "t")})
    return NsbNode.from_config(cfg, experiment_id="test-faults")


class TestEstadosCorruptos:
    def test_nan_inf_dup_ooo_absorbidos(self, tmp_path):
        plan = FaultPlan({
            3: ["nan_queue"],
            5: ["inf_speed"],
            7: ["duplicate"],
            9: ["out_of_order"],
            11: ["drop"],
            13: ["sensado_invalido"],
        })
        node = make_node(tmp_path)
        fuente = CorruptingSource(
            ManualTestStateSource(escenario="uniforme", pasos=20), plan)
        summary = node.run(fuente)
        actuator = node.authority._actuator
        node.shutdown()

        # 20 estados - 1 drop + 2 extra (duplicado y fuera-de-orden) = 21;
        # rechazos exactos: nan, inf, duplicado, fuera-de-orden, sensado = 5
        assert summary.estados == 21
        assert summary.verdicts.get("reject", 0) == 5
        assert summary.verdicts.get("accept", 0) == 16
        # Y JAMÁS un estado físico inseguro
        m = ConflictMatrix()
        assert all(m.es_segura(g) for g in actuator.historia)
        assert summary.violaciones_gate == 0

    def test_nodo_no_entra_en_safe_mode_por_fallos_aislados(self, tmp_path):
        # Fallos NO consecutivos: el ciclo de control se mantiene adaptativo
        plan = FaultPlan({4: ["nan_queue"], 9: ["duplicate"]})
        node = make_node(tmp_path)
        fuente = CorruptingSource(
            ManualTestStateSource(escenario="uniforme", pasos=15), plan)
        summary = node.run(fuente)
        node.shutdown()
        assert not summary.safe_mode_final


class TestSabotajeRecomendacion:
    def test_verde_200s_se_clampa(self, tmp_path):
        """DEMO 6: recomendación de 200 s → CLAMP a 120 s, trazable."""
        node = make_node(tmp_path)
        # Sabotear el pipeline interno de la autoridad
        node.authority._pipeline = SabotagePipeline(
            node.authority._pipeline, FaultPlan({2: ["verde_200"]}))
        decisiones = []
        for st in ManualTestStateSource(escenario="uniforme", pasos=5):
            _, d = node.process_one(st)
            decisiones.append(d)
        node.shutdown()

        d2 = decisiones[2]
        assert d2.verdict is Verdict.CLAMP
        assert d2.plan_aplicado.t_verde_ns == 120.0
        assert d2.corrections
        assert all(d.verdict is Verdict.ACCEPT
                   for i, d in enumerate(decisiones) if i != 2)


class TestPredictorCaido:
    def test_pipeline_sobrevive_predictor_roto(self):
        pipeline = DecisionPipeline(AdaptadorICV(), AdaptadorDifuso(),
                                    Mode.ADVISORY, predictor=PredictorRoto())
        rec = pipeline.recommend(make_state(seq=0))
        assert rec is not None
        assert rec.plan.t_verde_ns > 0
        assert rec.predictor.used is False   # jamás se usó la predicción
