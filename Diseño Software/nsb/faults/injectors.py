"""Inyectores de fallos (spec §32). SOLO para tests y demos.

- `CorruptingSource`: envuelve una fuente y corrompe/reordena/duplica los
  TrafficState según un FaultPlan. Los estados con NaN/inf se construyen con
  ``model_construct`` (sin validación) para simular datos que esquivaron la
  frontera — el MessageGuard debe atraparlos igualmente.
- `SabotagePipeline`: envuelve el pipeline y corrompe la recomendación
  (verde de 200 s) — el TSC debe CLAMP/REJECT.
- `PredictorRoto`: predictor que lanza — el pipeline debe seguir con difuso.
"""
from __future__ import annotations

import math
from typing import Iterator, Optional, Tuple

from nsb.core.pipeline import DecisionPipeline
from nsb.domain.contracts import (
    PlanSemaforico,
    PredictorInfo,
    QualityFlags,
    RecommendationEnvelope,
    TrafficState,
)
from nsb.domain.enums import Direction
from nsb.faults.plan import FaultPlan
from nsb.sources.base import TrafficStateSource


def _con_campo_corrupto(state: TrafficState, direccion: Direction,
                        campo: str, valor: float) -> TrafficState:
    """Copia un estado inyectando un valor NO FINITO sin pasar por la
    validación de Pydantic (simula un productor defectuoso)."""
    approaches = dict(state.approaches)
    ap = approaches[direccion]
    datos = ap.model_dump()
    datos[campo] = valor
    approaches[direccion] = type(ap).model_construct(**datos)
    datos_estado = state.model_dump()
    datos_estado["approaches"] = approaches
    datos_estado["source"] = state.source
    datos_estado["ev_event"] = state.ev_event
    datos_estado["quality"] = state.quality
    return TrafficState.model_construct(**datos_estado)


class CorruptingSource:
    """Fuente que aplica un FaultPlan sobre otra fuente."""

    def __init__(self, inner: TrafficStateSource, plan: FaultPlan):
        self._inner = inner
        self._plan = plan

    def __iter__(self) -> Iterator[TrafficState]:
        anterior: Optional[TrafficState] = None
        for state in self._inner:
            fallos = self._plan.en(state.seq)

            if "drop" in fallos:
                anterior = state
                continue

            emitir = state
            if "nan_queue" in fallos:
                emitir = _con_campo_corrupto(
                    emitir, Direction.NS, "queue_m", float("nan"))
            if "inf_speed" in fallos:
                emitir = _con_campo_corrupto(
                    emitir, Direction.EO, "speed_kmh", float("inf"))
            if "sensado_invalido" in fallos:
                emitir = emitir.model_copy(update={
                    "quality": QualityFlags(valid=False)})

            yield emitir

            if "duplicate" in fallos:
                yield emitir            # mismo seq otra vez
            if "out_of_order" in fallos and anterior is not None:
                yield anterior          # un seq viejo después de uno nuevo
            anterior = state

    def close(self) -> None:
        self._inner.close()


class SabotagePipeline:
    """Envuelve DecisionPipeline y sabotea la recomendación en seqs dados."""

    def __init__(self, inner: DecisionPipeline, plan: FaultPlan):
        self._inner = inner
        self._plan = plan

    def recommend(self, state: TrafficState) -> RecommendationEnvelope:
        rec = self._inner.recommend(state)
        if "verde_200" in self._plan.en(state.seq):
            rec = rec.model_copy(update={
                "plan": PlanSemaforico(t_verde_ns=200.0, t_verde_eo=30.0,
                                       t_ambar=rec.plan.t_ambar,
                                       t_todo_rojo=rec.plan.t_todo_rojo)})
        return rec


class PredictorRoto:
    """Predictor que siempre lanza (spec §32.10)."""

    enabled = True
    available = True

    def predict(self, state: TrafficState):
        raise RuntimeError("predictor saboteado")

    def info(self) -> PredictorInfo:
        return PredictorInfo(enabled=True, available=True, used=False,
                             fallback_reason="predictor_error")
