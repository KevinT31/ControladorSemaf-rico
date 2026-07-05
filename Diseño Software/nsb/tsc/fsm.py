"""Máquina de estados de fases semafóricas (spec §22, §25; decisiones D-05/06).

Ciclo normal:
  NS_VERDE → NS_AMBAR → TODO_ROJO_1 → EO_VERDE → EO_AMBAR → TODO_ROJO_2 → NS_VERDE

Garantías (defensa en profundidad — aunque el plan llegue ya validado, la
FSM vuelve a acotar con los LIMITES canónicos):

- un verde jamás dura menos de T_VERDE_MIN ni más de T_VERDE_MAX;
- todo verde que termina pasa SIEMPRE por ámbar (≥ T_AMBAR_MIN) y
  todo-rojo (≥ T_TODO_ROJO_MIN) antes del verde cruzado;
- un plan nuevo NUNCA acorta la fase en curso: se promueve a vigente al
  entrar al siguiente verde;
- la preempción EV respeta la misma secuencia segura: recorte del verde
  incompatible solo hasta su mínimo, luego ámbar → todo-rojo → verde
  objetivo (spec §22).

La FSM no conoce actuadores ni red: consume un Clock y produce AppliedPhase.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from nsb.domain.contracts import AppliedPhase, PlanSemaforico
from nsb.domain.enums import Direction, PhaseId, SignalColor, SignalGroup
from nsb.safety.limits import LIMITES
from nsb.tsc.clock import Clock

logger = logging.getLogger(__name__)

# Salidas físicas de cada fase (los 12 LEDs)
SALIDAS: Dict[PhaseId, Dict[SignalGroup, SignalColor]] = {
    PhaseId.NS_VERDE: {
        SignalGroup.NORTE: SignalColor.VERDE, SignalGroup.SUR: SignalColor.VERDE,
        SignalGroup.ESTE: SignalColor.ROJO, SignalGroup.OESTE: SignalColor.ROJO,
    },
    PhaseId.NS_AMBAR: {
        SignalGroup.NORTE: SignalColor.AMBAR, SignalGroup.SUR: SignalColor.AMBAR,
        SignalGroup.ESTE: SignalColor.ROJO, SignalGroup.OESTE: SignalColor.ROJO,
    },
    PhaseId.TODO_ROJO_1: {g: SignalColor.ROJO for g in SignalGroup},
    PhaseId.EO_VERDE: {
        SignalGroup.NORTE: SignalColor.ROJO, SignalGroup.SUR: SignalColor.ROJO,
        SignalGroup.ESTE: SignalColor.VERDE, SignalGroup.OESTE: SignalColor.VERDE,
    },
    PhaseId.EO_AMBAR: {
        SignalGroup.NORTE: SignalColor.ROJO, SignalGroup.SUR: SignalColor.ROJO,
        SignalGroup.ESTE: SignalColor.AMBAR, SignalGroup.OESTE: SignalColor.AMBAR,
    },
    PhaseId.TODO_ROJO_2: {g: SignalColor.ROJO for g in SignalGroup},
}

SIGUIENTE: Dict[PhaseId, PhaseId] = {
    PhaseId.NS_VERDE: PhaseId.NS_AMBAR,
    PhaseId.NS_AMBAR: PhaseId.TODO_ROJO_1,
    PhaseId.TODO_ROJO_1: PhaseId.EO_VERDE,
    PhaseId.EO_VERDE: PhaseId.EO_AMBAR,
    PhaseId.EO_AMBAR: PhaseId.TODO_ROJO_2,
    PhaseId.TODO_ROJO_2: PhaseId.NS_VERDE,
}

VERDES: Dict[Direction, PhaseId] = {
    Direction.NS: PhaseId.NS_VERDE,
    Direction.EO: PhaseId.EO_VERDE,
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(v, hi))


class PhaseFSM:
    """FSM de fases con reloj inyectable, plan pendiente y preempción EV."""

    def __init__(self, clock: Clock, plan_inicial: PlanSemaforico,
                 fase_inicial: PhaseId = PhaseId.NS_VERDE,
                 on_transition: Optional[Callable[[PhaseId, PhaseId], None]] = None):
        self._clock = clock
        self._plan = plan_inicial
        self._plan_pendiente: Optional[PlanSemaforico] = None
        self._fase = fase_inicial
        self._entered_at = clock.now()
        self._preempt: Optional[Direction] = None
        self._on_transition = on_transition
        self._transiciones: int = 0

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    @property
    def fase(self) -> PhaseId:
        return self._fase

    @property
    def plan_vigente(self) -> PlanSemaforico:
        return self._plan

    @property
    def plan_pendiente(self) -> Optional[PlanSemaforico]:
        return self._plan_pendiente

    @property
    def preempt_activo(self) -> Optional[Direction]:
        return self._preempt

    @property
    def transiciones(self) -> int:
        return self._transiciones

    def signal_groups(self) -> Dict[SignalGroup, SignalColor]:
        return dict(SALIDAS[self._fase])

    def applied_phase(self) -> AppliedPhase:
        return AppliedPhase(
            phase_id=self._fase,
            since_s=self._entered_at,
            signal_groups=self.signal_groups(),
            plan_en_vigor=self._plan,
        )

    # ------------------------------------------------------------------ #
    # Duración efectiva de la fase actual (acotada por LIMITES SIEMPRE)
    # ------------------------------------------------------------------ #
    def _duracion(self, fase: PhaseId) -> float:
        p = self._plan
        if fase is PhaseId.NS_VERDE:
            base = p.t_verde_ns
            if self._preempt is Direction.NS:
                base = LIMITES.T_VERDE_MAX      # extensión por EV
            elif self._preempt is Direction.EO:
                base = LIMITES.T_VERDE_MIN      # recorte seguro por EV cruzado
            return _clamp(base, LIMITES.T_VERDE_MIN, LIMITES.T_VERDE_MAX)
        if fase is PhaseId.EO_VERDE:
            base = p.t_verde_eo
            if self._preempt is Direction.EO:
                base = LIMITES.T_VERDE_MAX
            elif self._preempt is Direction.NS:
                base = LIMITES.T_VERDE_MIN
            return _clamp(base, LIMITES.T_VERDE_MIN, LIMITES.T_VERDE_MAX)
        if fase in (PhaseId.NS_AMBAR, PhaseId.EO_AMBAR):
            return max(p.t_ambar, LIMITES.T_AMBAR_MIN)
        return max(p.t_todo_rojo, LIMITES.T_TODO_ROJO_MIN)

    # ------------------------------------------------------------------ #
    # Órdenes
    # ------------------------------------------------------------------ #
    def request_plan(self, plan: PlanSemaforico) -> None:
        """Programa un plan. Se promueve a vigente al entrar al próximo
        verde — jamás acorta la fase en curso."""
        self._plan_pendiente = plan

    def request_preempt(self, direction: Direction) -> None:
        """Solicita prioridad EV hacia `direction` con transición segura."""
        if self._preempt is not direction:
            logger.warning("FSM: preempcion EV solicitada hacia %s (fase=%s)",
                           direction.value, self._fase.value)
        self._preempt = direction

    def clear_preempt(self) -> None:
        self._preempt = None

    # ------------------------------------------------------------------ #
    # Avance temporal
    # ------------------------------------------------------------------ #
    def tick(self) -> AppliedPhase:
        """Avanza la FSM hasta el instante del reloj. Puede encadenar varias
        transiciones si el reloj saltó (p. ej. SimClock avanza 25 s)."""
        ahora = self._clock.now()
        # Cota de seguridad de iteraciones: un salto de reloj gigantesco no
        # debe colgar el proceso (peor caso realista: horas de sim / 2 s).
        for _ in range(100_000):
            dur = self._duracion(self._fase)
            if ahora - self._entered_at < dur:
                break
            self._transicionar(momento=self._entered_at + dur)
        else:
            raise RuntimeError("FSM: exceso de transiciones en un tick "
                               "(¿reloj corrupto?)")
        return self.applied_phase()

    def _transicionar(self, momento: float) -> None:
        anterior = self._fase
        siguiente = SIGUIENTE[anterior]

        # Preempción EV: al salir de un todo-rojo se va al verde de la
        # dirección solicitada (posible salto de EO_VERDE o NS_VERDE).
        if self._preempt is not None and anterior in (
                PhaseId.TODO_ROJO_1, PhaseId.TODO_ROJO_2):
            siguiente = VERDES[self._preempt]

        # Promoción del plan pendiente al ENTRAR a un verde
        if siguiente in (PhaseId.NS_VERDE, PhaseId.EO_VERDE):
            if self._plan_pendiente is not None:
                self._plan = self._plan_pendiente
                self._plan_pendiente = None
            # La preempción se consume al alcanzar el verde objetivo
            if self._preempt is not None and siguiente is VERDES[self._preempt]:
                self._preempt = None

        self._fase = siguiente
        self._entered_at = momento
        self._transiciones += 1
        logger.debug("FSM: %s -> %s @ %.1fs", anterior.value, siguiente.value,
                     momento)
        if self._on_transition is not None:
            self._on_transition(anterior, siguiente)


def secuencia_es_segura(transiciones: List[PhaseId]) -> bool:
    """Auditor de secuencias (para tests): entre dos verdes cruzados debe
    existir al menos un ámbar y un todo-rojo intermedios."""
    ultimo_verde: Optional[PhaseId] = None
    vio_ambar = False
    vio_rojo = False
    for fase in transiciones:
        if fase in (PhaseId.NS_VERDE, PhaseId.EO_VERDE):
            if ultimo_verde is not None and fase is not ultimo_verde:
                if not (vio_ambar and vio_rojo):
                    return False
            ultimo_verde = fase
            vio_ambar = False
            vio_rojo = False
        elif fase in (PhaseId.NS_AMBAR, PhaseId.EO_AMBAR):
            vio_ambar = True
        elif fase in (PhaseId.TODO_ROJO_1, PhaseId.TODO_ROJO_2):
            vio_rojo = True
    return True
