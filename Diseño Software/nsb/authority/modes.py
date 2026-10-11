"""Autoridad semafórica: composición guard → pipeline → TSC → gate → actuador
según el modo (spec §10).

- ADVISORY: calcula y registra; JAMÁS llama a `actuator.apply()` ni programa
  planes. La FSM interna corre pasiva con el plan base (referencia de fase
  para telemetría), sin actuación.
- TSC_EMULATED: el TscEmulator dictamina (ACCEPT/CLAMP/DEFER/REJECT) y la
  salida pasa por SafetyGate antes del actuador.
- AUTOMATED_DIRECT_LAB: sin veto de emulador (no hay DEFER), pero con las
  MISMAS etapas de seguridad obligatorias: guard → clamp → FSM → SafetyGate
  → actuador. Activable solo por triple compuerta (direct_lab_gate).

El modo se fija al construir y NO existe API para elevarlo en runtime (D-H).
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional, Tuple

from nsb.actuation.base import ActuatorBackend
from nsb.core.pipeline import DecisionPipeline
from nsb.domain.contracts import (
    AppliedPhase,
    DecisionEnvelope,
    RecommendationEnvelope,
    TrafficState,
)
from nsb.domain.enums import Mode, Verdict
from nsb.safety.gate import SafetyGate
from nsb.safety.message_guard import MessageGuard
from nsb.tsc.emulator import TscEmulator

logger = logging.getLogger(__name__)


class Authority:
    """Procesa TrafficState → (Recommendation opcional, Decision) y actúa."""

    def __init__(self, mode: Mode, pipeline: DecisionPipeline,
                 tsc: TscEmulator, guard: MessageGuard,
                 actuator: Optional[ActuatorBackend]):
        if mode is not Mode.ADVISORY and actuator is None:
            raise ValueError(f"el modo {mode.value} requiere un actuador")
        self._mode = mode
        self._pipeline = pipeline
        self._tsc = tsc
        self._guard = guard
        self._actuator = actuator
        # Gate propio, no inyectable: nadie puede sustituirlo por uno nulo.
        self._gate = SafetyGate()

    @property
    def mode(self) -> Mode:
        return self._mode

    @property
    def gate(self) -> SafetyGate:
        return self._gate

    @property
    def tsc(self) -> TscEmulator:
        return self._tsc

    # ------------------------------------------------------------------ #
    def process_state(self, state: TrafficState,
                      edad_s: Optional[float] = None,
                      on_state_accepted: Optional[Callable[[], None]] = None,
                      ) -> Tuple[Optional[RecommendationEnvelope],
                                 DecisionEnvelope]:
        """Ciclo completo de un punto de control.

        ``on_state_accepted`` se ejecuta después del guard y antes de decidir.
        Permite avanzar el reloj de simulación sin que un mensaje rechazado
        pueda modificar la FSM.
        """
        verdict = self._guard.check_state(state, edad_s=edad_s)

        rec: Optional[RecommendationEnvelope] = None
        if verdict.ok:
            if on_state_accepted is not None:
                on_state_accepted()
            rec = self._pipeline.recommend(state)

        if self._mode is Mode.ADVISORY:
            return rec, self._decision_advisory(state, rec, verdict.reasons)

        decision = self._tsc.process(
            rec, state.experiment_id, state.seq,
            reject_reasons=verdict.reasons if not verdict.ok else None)
        decision = self._actuar(decision)
        return rec, decision

    # ------------------------------------------------------------------ #
    def _decision_advisory(self, state: TrafficState,
                           rec: Optional[RecommendationEnvelope],
                           guard_reasons: list) -> DecisionEnvelope:
        """ADVISORY: registro sin autoridad. plan_aplicado SIEMPRE None;
        la FSM avanza pasiva con su plan base (nunca recibe planes)."""
        self._tsc.fsm.tick()
        if rec is not None:
            verdict, reasons = Verdict.ACCEPT, ["advisory:solo_registro"]
        else:
            verdict, reasons = Verdict.REJECT, list(guard_reasons)
        return DecisionEnvelope(
            experiment_id=state.experiment_id,
            seq=state.seq,
            recommendation_id=rec.recommendation_id if rec else None,
            verdict=verdict,
            reasons=reasons,
            plan_aplicado=None,
            applied_phase=self._tsc.fsm.applied_phase(),
            mode=self._mode,
        )

    def _actuar(self, decision: DecisionEnvelope) -> DecisionEnvelope:
        """SafetyGate + actuador. TODO write pasa por el gate (spec §11)."""
        assert self._actuator is not None  # garantizado por __init__
        propuesta = decision.applied_phase.signal_groups
        resultado = self._gate.check_output(
            propuesta, context=f"seq={decision.seq}")

        t0 = time.perf_counter()
        self._actuator.apply(resultado.groups)
        actuation_ms = (time.perf_counter() - t0) * 1000.0

        if not resultado.safe:
            decision = decision.model_copy(update={
                "safe_mode": True,
                "safe_mode_reason": "safety_gate:todo_rojo_forzado",
                "reasons": list(decision.reasons) + resultado.violations,
                "applied_phase": decision.applied_phase.model_copy(
                    update={"signal_groups": resultado.groups}),
            })
        return decision.model_copy(update={"actuation_ms": actuation_ms})

    def tick(self) -> AppliedPhase:
        """Avanza la FSM sin nueva recomendación (espejo HIL ``per_step``).

        En modos con autoridad, la salida pasa por el mismo SafetyGate que
        una decisión normal. ADVISORY solo mantiene la referencia de fase.
        """
        phase = self._tsc.fsm.tick()
        if self._mode is Mode.ADVISORY:
            return phase

        assert self._actuator is not None
        resultado = self._gate.check_output(
            phase.signal_groups, context="hil_tick")
        self._actuator.apply(resultado.groups)
        if not resultado.safe:
            self._tsc.enter_safe_mode("safety_gate:hil_tick")
            return phase.model_copy(update={"signal_groups": resultado.groups})
        return phase

    def shutdown(self) -> None:
        """Apagado ordenado del actuador (todo-rojo)."""
        if self._actuator is not None:
            self._actuator.shutdown()
