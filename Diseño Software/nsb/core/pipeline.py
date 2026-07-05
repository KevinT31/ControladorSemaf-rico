"""Pipeline de decisión del nodo: TrafficState → RecommendationEnvelope.

Función pura respecto al estado de entrada: dado el mismo TrafficState y la
misma configuración, produce la misma recomendación (base del replay
determinista y del golden master). `processing_ms` es una MEDICIÓN adjunta,
nunca un insumo de la decisión.

El pipeline NO valida seguridad ni aplica nada: recomienda. La autoridad
(TSC Emulator / Direct Lab) valida, veta y actúa.
"""
from __future__ import annotations

import time
from typing import Optional

from nsb.core.adapters import AdaptadorDifuso, AdaptadorICV
from nsb.core.predictor import DisabledPredictor, PredictorBackend
from nsb.domain.contracts import (
    ComputedIndicators,
    RecommendationEnvelope,
    TrafficState,
)
from nsb.domain.enums import Direction, Mode


class DecisionPipeline:
    """ICV+PI (canónicos) → difuso Cap. 6 → RecommendationEnvelope."""

    def __init__(self, icv: AdaptadorICV, difuso: AdaptadorDifuso,
                 mode: Mode, predictor: Optional[PredictorBackend] = None):
        self._icv = icv
        self._difuso = difuso
        self._mode = mode
        self._predictor = predictor if predictor is not None else DisabledPredictor()

    def recommend(self, state: TrafficState) -> RecommendationEnvelope:
        """Calcula la recomendación para un TrafficState YA validado por el
        MessageGuard (la validación de frontera no se repite aquí)."""
        t0 = time.perf_counter()

        icv_ns, pi_ns = self._icv.indicadores(state.approaches[Direction.NS])
        icv_eo, pi_eo = self._icv.indicadores(state.approaches[Direction.EO])

        # Predictor opcional: hoy siempre None (D-01). Si algún día existe,
        # su salida podrá enriquecer las entradas SIN saltarse el difuso.
        prediccion = None
        try:
            prediccion = self._predictor.predict(state)
        except Exception:
            prediccion = None  # el predictor jamás tumba el pipeline
        predictor_info = self._predictor.info()
        if prediccion is not None:
            predictor_info = predictor_info.model_copy(update={"used": True})

        plan, control = self._difuso.decidir_plan(
            icv_ns=icv_ns, pi_ns=pi_ns, ev_ns=state.ev_ns,
            icv_eo=icv_eo, pi_eo=pi_eo, ev_eo=state.ev_eo,
        )

        # Preempción EV explícita: solo si hay evento estructurado. Los
        # niveles ev_ns/ev_eo ya influyeron en el difuso (reglas R1-R3).
        ev_preempt = state.ev_event.approach if state.ev_event else None

        processing_ms = (time.perf_counter() - t0) * 1000.0

        return RecommendationEnvelope(
            experiment_id=state.experiment_id,
            intersection_id=state.intersection_id,
            seq=state.seq,
            sim_time_s=state.sim_time_s,
            recommendation_id=f"{state.experiment_id}/{state.seq}",
            computed=ComputedIndicators(
                icv_ns=icv_ns, pi_ns=pi_ns, ev_ns=state.ev_ns,
                icv_eo=icv_eo, pi_eo=pi_eo, ev_eo=state.ev_eo,
            ),
            plan=plan,
            delta_pct_ns=control['NS']['delta_t_porcentaje'],
            delta_pct_eo=control['EO']['delta_t_porcentaje'],
            reglas_disparadas=AdaptadorDifuso.reglas_como_texto(control),
            ev_preempt=ev_preempt,
            predictor=predictor_info,
            processing_ms=processing_ms,
            mode=self._mode,
        )
