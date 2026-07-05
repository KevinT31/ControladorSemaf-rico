"""TSC Emulator (spec §25): la autoridad que dictamina recomendaciones.

Pipeline de veredicto, en orden:

1. Razones de rechazo aguas arriba (MessageGuard sobre el TrafficState) →
   REJECT sin evaluar el plan.
2. `validador_seguridad.validar_parametros_control` (núcleo canónico):
   - valores no finitos → REJECT (los contratos ya los bloquean; defensa);
   - fuera de rango → según política: ``clamp`` (default, coherente con el
     lazo SUMO existente) recorta con `clamp_tiempos` → CLAMP con las
     correcciones trazables; ``strict`` → REJECT.
3. Preempción EV activa y plan sin relación → DEFER (el plan se pospone
   hasta que la secuencia de emergencia termine).
4. Plan programado en la FSM (se aplica en frontera de verde) → ACCEPT.

Fail-safe de silencio (spec §26-G): tras `max_silence_cycles` ciclos sin
recomendación aceptada, se programa CONFIG_SEGURA y se marca safe_mode
hasta la próxima aceptación.
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional

from nsb.domain.contracts import (
    DecisionEnvelope,
    PlanSemaforico,
    RecommendationEnvelope,
)
from nsb.domain.enums import Mode, Verdict
from nsb.safety.limits import CONFIG_SEGURA, validador_seguridad
from nsb.tsc.fsm import PhaseFSM

logger = logging.getLogger(__name__)

PLAN_SEGURO = PlanSemaforico(
    t_verde_ns=CONFIG_SEGURA['t_verde_ns'],
    t_verde_eo=CONFIG_SEGURA['t_verde_eo'],
    t_ambar=CONFIG_SEGURA['t_ambar'],
    t_todo_rojo=CONFIG_SEGURA['t_todo_rojo'],
)


class TscEmulator:
    """Autoridad semafórica emulada sobre una PhaseFSM."""

    def __init__(self, fsm: PhaseFSM, mode: Mode,
                 clamp_policy: str = "clamp",
                 max_silence_cycles: int = 3,
                 defer_during_preempt: bool = True):
        if clamp_policy not in ("clamp", "strict"):
            raise ValueError(f"clamp_policy desconocida: {clamp_policy!r}")
        self._fsm = fsm
        self._mode = mode
        self._clamp_policy = clamp_policy
        self._max_silence = max_silence_cycles
        # TSC_EMULATED pospone planes durante una preempción EV (DEFER);
        # AUTOMATED_DIRECT_LAB los programa igualmente (la FSM los aplicará
        # al terminar la secuencia de emergencia) — el veto es del emulador,
        # la seguridad es de la FSM+gate y es idéntica en ambos modos.
        self._defer_during_preempt = defer_during_preempt
        self._silence_count = 0
        self._safe_mode = False
        self._safe_mode_reason: Optional[str] = None

    @property
    def safe_mode(self) -> bool:
        return self._safe_mode

    @property
    def fsm(self) -> PhaseFSM:
        return self._fsm

    # ------------------------------------------------------------------ #
    def process(self, rec: Optional[RecommendationEnvelope],
                experiment_id: str, seq: int,
                reject_reasons: Optional[List[str]] = None
                ) -> DecisionEnvelope:
        """Dictamina una recomendación (o su ausencia) para el punto de
        control `seq` y devuelve la decisión con la fase aplicada actual."""
        t0 = time.perf_counter()

        if reject_reasons:
            decision = self._rechazar(rec, experiment_id, seq, reject_reasons)
        elif rec is None:
            decision = self._sin_recomendacion(experiment_id, seq)
        else:
            decision = self._evaluar(rec)

        self._fsm.tick()
        processing_ms = (time.perf_counter() - t0) * 1000.0
        return decision.model_copy(update={
            "applied_phase": self._fsm.applied_phase(),
            "processing_ms": processing_ms,
        })

    # ------------------------------------------------------------------ #
    def _registrar_silencio(self) -> None:
        self._silence_count += 1
        if self._silence_count >= self._max_silence and not self._safe_mode:
            self._safe_mode = True
            self._safe_mode_reason = (
                f"sin recomendacion valida en {self._silence_count} ciclos")
            self._fsm.request_plan(PLAN_SEGURO)
            logger.warning("TSC: MODO SEGURO programado (%s)",
                           self._safe_mode_reason)

    def enter_safe_mode(self, reason: str) -> None:
        """Entrada EXPLÍCITA a modo seguro (p. ej. pérdida del enlace HIL,
        spec §26-B). Programa CONFIG_SEGURA; se sale con la próxima
        recomendación aceptada."""
        self._safe_mode = True
        self._safe_mode_reason = reason
        self._fsm.request_plan(PLAN_SEGURO)
        logger.warning("TSC: MODO SEGURO explícito (%s)", reason)

    def _salir_de_safe_mode(self) -> None:
        self._silence_count = 0
        if self._safe_mode:
            logger.info("TSC: salida de modo seguro (recomendacion aceptada)")
        self._safe_mode = False
        self._safe_mode_reason = None

    def _base(self, experiment_id: str, seq: int, **kw) -> DecisionEnvelope:
        return DecisionEnvelope(
            experiment_id=experiment_id, seq=seq, mode=self._mode,
            safe_mode=self._safe_mode, safe_mode_reason=self._safe_mode_reason,
            applied_phase=self._fsm.applied_phase(), **kw)

    def _rechazar(self, rec: Optional[RecommendationEnvelope],
                  experiment_id: str, seq: int,
                  reasons: List[str]) -> DecisionEnvelope:
        self._registrar_silencio()
        return self._base(
            experiment_id, seq,
            recommendation_id=rec.recommendation_id if rec else None,
            verdict=Verdict.REJECT, reasons=list(reasons))

    def _sin_recomendacion(self, experiment_id: str, seq: int) -> DecisionEnvelope:
        self._registrar_silencio()
        return self._base(
            experiment_id, seq, recommendation_id=None,
            verdict=Verdict.REJECT, reasons=["sin_recomendacion"])

    # ------------------------------------------------------------------ #
    def _evaluar(self, rec: RecommendationEnvelope) -> DecisionEnvelope:
        plan = rec.plan
        params = {
            't_verde_ns': plan.t_verde_ns,
            't_verde_eo': plan.t_verde_eo,
            't_ambar': plan.t_ambar,
            't_todo_rojo': plan.t_todo_rojo,
        }
        ok, errores = validador_seguridad.validar_parametros_control(params)

        corrections: List[dict] = []
        if not ok:
            if self._clamp_policy == "strict":
                return self._rechazar(rec, rec.experiment_id, rec.seq,
                                      [f"plan_inseguro:{e}" for e in errores])
            tiempos, corrections = validador_seguridad.clamp_tiempos(
                plan.t_verde_ns, plan.t_verde_eo, plan.t_ambar, plan.t_todo_rojo)
            plan = PlanSemaforico(
                t_verde_ns=tiempos['t_verde_ns'],
                t_verde_eo=tiempos['t_verde_eo'],
                t_ambar=tiempos['t_ambar'],
                t_todo_rojo=tiempos['t_todo_rojo'],
            )

        # Preempción EV: la transición segura la ejecuta la FSM.
        if rec.ev_preempt is not None:
            self._fsm.request_preempt(rec.ev_preempt)
        elif (self._fsm.preempt_activo is not None
              and self._defer_during_preempt):
            # Hay una preempción en curso y esta recomendación no la trae:
            # el plan se pospone hasta completar la secuencia de emergencia.
            # NO cuenta como silencio: es comportamiento normal durante EV.
            return self._base(
                rec.experiment_id, rec.seq,
                recommendation_id=rec.recommendation_id,
                verdict=Verdict.DEFER,
                reasons=["ev_preempt_activo"])

        self._fsm.request_plan(plan)
        self._salir_de_safe_mode()

        verdict = Verdict.CLAMP if corrections else Verdict.ACCEPT
        reasons = ([f"clamp:{c['campo']}:{c['motivo']}" for c in corrections]
                   if corrections else [])
        return self._base(
            rec.experiment_id, rec.seq,
            recommendation_id=rec.recommendation_id,
            verdict=verdict, reasons=reasons,
            corrections=corrections, plan_aplicado=plan)
