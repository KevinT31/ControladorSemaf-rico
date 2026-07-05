"""Tests de la FSM de fases: ciclo, mínimos, plan pendiente, preempción EV."""
import pytest

from nsb.domain.contracts import PlanSemaforico
from nsb.domain.enums import Direction, PhaseId, SignalColor, SignalGroup
from nsb.safety.conflict_matrix import ConflictMatrix
from nsb.safety.limits import LIMITES
from nsb.tsc.clock import ManualClock
from nsb.tsc.fsm import PhaseFSM, secuencia_es_segura


def make_fsm(clock, plan=None, registrar=None):
    plan = plan or PlanSemaforico(t_verde_ns=30, t_verde_eo=30,
                                  t_ambar=3, t_todo_rojo=2)
    return PhaseFSM(clock=clock, plan_inicial=plan, on_transition=registrar)


class TestCicloNormal:
    def test_secuencia_completa(self):
        clock = ManualClock()
        visitadas = [PhaseId.NS_VERDE]
        fsm = make_fsm(clock,
                       registrar=lambda a, b: visitadas.append(b))
        # Un ciclo completo: 30+3+2+30+3+2 = 70 s
        for _ in range(70):
            clock.advance(1.0)
            fsm.tick()
        assert visitadas[:7] == [
            PhaseId.NS_VERDE, PhaseId.NS_AMBAR, PhaseId.TODO_ROJO_1,
            PhaseId.EO_VERDE, PhaseId.EO_AMBAR, PhaseId.TODO_ROJO_2,
            PhaseId.NS_VERDE]
        assert secuencia_es_segura(visitadas)

    def test_salto_de_reloj_encadena_transiciones(self):
        clock = ManualClock()
        fsm = make_fsm(clock)
        clock.advance(35.0)   # 30 de verde + 3 ámbar + 2 rojo => EO_VERDE
        fsm.tick()
        assert fsm.fase is PhaseId.EO_VERDE

    def test_nunca_verdes_conflictivos_en_ningun_estado(self):
        clock = ManualClock()
        fsm = make_fsm(clock)
        matrix = ConflictMatrix()
        for _ in range(500):
            clock.advance(1.0)
            ap = fsm.tick()
            assert matrix.es_segura(ap.signal_groups), (
                f"conflicto en fase {ap.phase_id}")

    def test_salidas_fisicas_coherentes(self):
        clock = ManualClock()
        fsm = make_fsm(clock)
        g = fsm.signal_groups()
        assert g[SignalGroup.NORTE] is SignalColor.VERDE
        assert g[SignalGroup.SUR] is SignalColor.VERDE
        assert g[SignalGroup.ESTE] is SignalColor.ROJO
        assert g[SignalGroup.OESTE] is SignalColor.ROJO


class TestLimitesDuros:
    def test_verde_respeta_maximo(self):
        clock = ManualClock()
        # Plan con verde de 500 s (los contratos lo permiten; la FSM acota)
        plan = PlanSemaforico(t_verde_ns=500, t_verde_eo=30)
        fsm = make_fsm(clock, plan=plan)
        clock.advance(LIMITES.T_VERDE_MAX + 0.5)
        fsm.tick()
        assert fsm.fase is PhaseId.NS_AMBAR   # cortó en T_VERDE_MAX

    def test_verde_respeta_minimo(self):
        clock = ManualClock()
        plan = PlanSemaforico(t_verde_ns=1, t_verde_eo=30)  # 1 s: ilegal
        fsm = make_fsm(clock, plan=plan)
        clock.advance(5.0)
        fsm.tick()
        assert fsm.fase is PhaseId.NS_VERDE   # aún en verde: mínimo 10 s

    def test_ambar_y_todo_rojo_minimos(self):
        clock = ManualClock()
        plan = PlanSemaforico(t_verde_ns=10, t_verde_eo=10,
                              t_ambar=0.5, t_todo_rojo=0.1)
        fsm = make_fsm(clock, plan=plan)
        clock.advance(10.0)
        fsm.tick()
        assert fsm.fase is PhaseId.NS_AMBAR
        clock.advance(1.0)   # 1 s < T_AMBAR_MIN (3 s)
        fsm.tick()
        assert fsm.fase is PhaseId.NS_AMBAR   # el ámbar no puede acortarse
        clock.advance(2.0)   # total 3 s de ámbar
        fsm.tick()
        assert fsm.fase is PhaseId.TODO_ROJO_1
        clock.advance(1.0)   # 1 s < T_TODO_ROJO_MIN (2 s)
        fsm.tick()
        assert fsm.fase is PhaseId.TODO_ROJO_1


class TestPlanPendiente:
    def test_no_acorta_fase_en_curso(self):
        clock = ManualClock()
        fsm = make_fsm(clock)
        clock.advance(5.0)
        fsm.tick()
        fsm.request_plan(PlanSemaforico(t_verde_ns=12, t_verde_eo=12))
        # El verde NS en curso sigue siendo de 30 s
        clock.advance(20.0)   # t=25 < 30
        fsm.tick()
        assert fsm.fase is PhaseId.NS_VERDE
        assert fsm.plan_vigente.t_verde_ns == 30

    def test_se_promueve_al_entrar_al_proximo_verde(self):
        clock = ManualClock()
        fsm = make_fsm(clock)
        fsm.request_plan(PlanSemaforico(t_verde_ns=12, t_verde_eo=12))
        clock.advance(35.0)   # NS_VERDE(30)+ámbar(3)+rojo(2) => entra EO_VERDE
        fsm.tick()
        assert fsm.fase is PhaseId.EO_VERDE
        assert fsm.plan_vigente.t_verde_eo == 12
        assert fsm.plan_pendiente is None


class TestPreempcionEV:
    def test_extiende_verde_propio(self):
        clock = ManualClock()
        fsm = make_fsm(clock)
        fsm.request_preempt(Direction.NS)
        clock.advance(60.0)   # > 30 s del plan, < 120 s máximo
        fsm.tick()
        assert fsm.fase is PhaseId.NS_VERDE   # extendido por EV

    def test_recorta_verde_cruzado_respetando_minimo(self):
        clock = ManualClock()
        visitadas = [PhaseId.NS_VERDE]
        fsm = make_fsm(clock, registrar=lambda a, b: visitadas.append(b))
        clock.advance(2.0)
        fsm.tick()
        fsm.request_preempt(Direction.EO)   # EV cruzado con NS en verde
        # El verde NS no puede cortarse antes de T_VERDE_MIN (10 s)
        clock.advance(6.0)   # t=8 < 10
        fsm.tick()
        assert fsm.fase is PhaseId.NS_VERDE
        clock.advance(2.0)   # t=10 => corta
        fsm.tick()
        assert fsm.fase is PhaseId.NS_AMBAR
        # Secuencia segura completa hasta el verde EO
        clock.advance(5.0)   # ámbar 3 + rojo 2
        fsm.tick()
        assert fsm.fase is PhaseId.EO_VERDE
        assert secuencia_es_segura(visitadas)
        assert fsm.preempt_activo is None   # consumida al llegar

    def test_desde_todo_rojo_va_al_verde_objetivo(self):
        clock = ManualClock()
        fsm = make_fsm(clock)
        clock.advance(33.5)   # dentro de TODO_ROJO_1 (30+3=33 .. 35)
        fsm.tick()
        assert fsm.fase is PhaseId.TODO_ROJO_1
        fsm.request_preempt(Direction.NS)   # EV hacia NS
        clock.advance(1.5)    # completa el todo-rojo
        fsm.tick()
        # Sin preempción tocaría EO_VERDE; con EV va a NS_VERDE
        assert fsm.fase is PhaseId.NS_VERDE

    def test_todo_rojo_nunca_se_acorta_por_preempcion(self):
        clock = ManualClock()
        fsm = make_fsm(clock)
        clock.advance(33.1)
        fsm.tick()
        assert fsm.fase is PhaseId.TODO_ROJO_1
        fsm.request_preempt(Direction.NS)
        clock.advance(1.0)   # 1.1 s de rojo < 2 s mínimo
        fsm.tick()
        assert fsm.fase is PhaseId.TODO_ROJO_1
