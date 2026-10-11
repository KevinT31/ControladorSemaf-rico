"""Tests de propiedades por fuzz sembrado (spec §34; D-09: sin Hypothesis).

Miles de secuencias pseudoaleatorias (seed fija ⇒ reproducibles) de
solicitudes válidas, inválidas y hostiles contra FSM + TSC + SafetyGate.
Tras CADA evento se verifican las invariantes:

  I1. Nunca verdes conflictivos simultáneos (matriz de conflictos).
  I2. Entre dos verdes cruzados siempre hay ámbar y todo-rojo.
  I3. Un verde jamás dura más de T_VERDE_MAX ni un ámbar/todo-rojo menos
      que su mínimo.
  I4. Toda entrada no finita o fuera de orden se rechaza sin excepción
      no controlada.
"""
import random

import pytest

from nsb.actuation.simulated import SimulatedActuator
from nsb.authority.modes import Authority
from nsb.core.adapters import AdaptadorDifuso, AdaptadorICV
from nsb.core.pipeline import DecisionPipeline
from nsb.domain.contracts import ApproachState, PlanSemaforico, TrafficState
from nsb.domain.enums import Direction, Mode, PhaseId, SourceKind
from nsb.faults.injectors import _con_campo_corrupto
from nsb.safety.conflict_matrix import ConflictMatrix
from nsb.safety.limits import LIMITES
from nsb.safety.message_guard import MessageGuard
from nsb.tsc.clock import ManualClock
from nsb.tsc.emulator import TscEmulator
from nsb.tsc.fsm import PhaseFSM, secuencia_es_segura

SEEDS = [7, 42, 20260705]


def estado_aleatorio(rng: random.Random, seq: int) -> TrafficState:
    def acceso():
        n = rng.randint(0, 60)
        return ApproachState(
            queue_m=rng.uniform(0, 400),
            speed_kmh=rng.uniform(0, 90),
            flow_veh_min=rng.uniform(0, 45),
            num_vehicles=n,
            stopped_vehicles=rng.randint(0, n) if n else 0)

    return TrafficState(
        experiment_id="fuzz", intersection_id="int-fuzz",
        source=SourceKind.MANUAL, seq=seq, sim_time_s=seq * 25.0,
        control_interval_s=25.0,
        approaches={Direction.NS: acceso(), Direction.EO: acceso()},
        ev_ns=rng.choice([0.0, 0.0, 0.0, 1.0]),
        ev_eo=rng.choice([0.0, 0.0, 0.0, 1.0]),
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_fuzz_autoridad_completa(seed, tmp_path):
    """Secuencias mixtas (válidas + corruptas + duplicadas) contra la
    autoridad completa: las invariantes I1..I4 se sostienen siempre."""
    rng = random.Random(seed)
    clock = ManualClock()
    actuator = SimulatedActuator(history_limit=100_000)
    pipeline = DecisionPipeline(AdaptadorICV(), AdaptadorDifuso(),
                                Mode.TSC_EMULATED)
    fsm = PhaseFSM(clock=clock, plan_inicial=PlanSemaforico(
        t_verde_ns=30, t_verde_eo=30))
    transiciones = [fsm.fase]
    fsm._on_transition = lambda a, b: transiciones.append(b)
    tsc = TscEmulator(fsm=fsm, mode=Mode.TSC_EMULATED)
    authority = Authority(mode=Mode.TSC_EMULATED, pipeline=pipeline,
                          tsc=tsc, guard=MessageGuard(), actuator=actuator)
    matrix = ConflictMatrix()

    seq = 0
    for _ in range(600):
        accion = rng.random()
        clock.advance(rng.uniform(0.0, 40.0))

        if accion < 0.55:                       # estado válido nuevo
            st = estado_aleatorio(rng, seq)
            seq += 1
        elif accion < 0.70 and seq > 0:         # duplicado / viejo
            st = estado_aleatorio(rng, rng.randint(0, max(0, seq - 1)))
        elif accion < 0.85:                     # corrupto no finito
            st = estado_aleatorio(rng, seq)
            seq += 1
            campo = rng.choice(["queue_m", "speed_kmh", "flow_veh_min"])
            valor = rng.choice([float("nan"), float("inf"), float("-inf")])
            st = _con_campo_corrupto(
                st, rng.choice([Direction.NS, Direction.EO]), campo, valor)
        else:                                   # solo avance de tiempo
            fsm.tick()
            for g in (actuator.state(),):
                assert matrix.es_segura(g)
            continue

        rec, decision = authority.process_state(st)   # I4: jamás explota

        # I1 sobre TODO lo aplicado físicamente
        assert matrix.es_segura(actuator.state()), (
            f"seed={seed}: conflicto físico tras seq={st.seq}")

    # I1 sobre el historial completo
    assert all(matrix.es_segura(g) for g in actuator.historia)
    # I2 sobre la secuencia de fases completa
    assert secuencia_es_segura(transiciones), f"seed={seed}"
    # El gate jamás tuvo que intervenir (la FSM ya es segura por diseño)
    assert authority.gate.violaciones_totales == 0


@pytest.mark.parametrize("seed", SEEDS)
def test_fuzz_fsm_duraciones(seed):
    """I3: medición directa de duraciones de fase bajo planes hostiles."""
    rng = random.Random(seed)
    clock = ManualClock()
    fsm = PhaseFSM(clock=clock, plan_inicial=PlanSemaforico(
        t_verde_ns=30, t_verde_eo=30))

    entradas = {}   # fase -> momento de entrada
    duraciones = []  # (fase, duracion)

    def registrar(anterior, nueva):
        ahora = fsm._entered_at
        if anterior in entradas:
            duraciones.append((anterior, ahora - entradas[anterior]))
        entradas[nueva] = ahora

    entradas[fsm.fase] = 0.0
    fsm._on_transition = registrar

    for _ in range(400):
        if rng.random() < 0.3:
            # Plan hostil: los contratos permiten >0; la FSM debe acotar
            fsm.request_plan(PlanSemaforico(
                t_verde_ns=rng.uniform(0.1, 500),
                t_verde_eo=rng.uniform(0.1, 500),
                t_ambar=rng.uniform(0.1, 50),
                t_todo_rojo=rng.uniform(0.1, 50)))
        if rng.random() < 0.15:
            fsm.request_preempt(rng.choice([Direction.NS, Direction.EO]))
        clock.advance(rng.uniform(0.5, 20.0))
        fsm.tick()

    assert duraciones, "el fuzz debe producir transiciones"
    for fase, dur in duraciones:
        if fase in (PhaseId.NS_VERDE, PhaseId.EO_VERDE):
            assert dur <= LIMITES.T_VERDE_MAX + 1e-6, (fase, dur)
            assert dur >= LIMITES.T_VERDE_MIN - 1e-6, (fase, dur)
        elif fase in (PhaseId.NS_AMBAR, PhaseId.EO_AMBAR):
            assert dur >= LIMITES.T_AMBAR_MIN - 1e-6, (fase, dur)
        else:
            assert dur >= LIMITES.T_TODO_ROJO_MIN - 1e-6, (fase, dur)
