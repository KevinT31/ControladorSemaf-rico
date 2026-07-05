"""Tests de ConflictMatrix, MessageGuard y SafetyGate."""
import pytest

from nsb.domain.contracts import QualityFlags
from nsb.domain.enums import SignalColor, SignalGroup
from nsb.safety.conflict_matrix import ConflictMatrix
from nsb.safety.gate import TODO_ROJO, SafetyGate
from nsb.safety.message_guard import MessageGuard

from tests.conftest import make_state

V, A, R = SignalColor.VERDE, SignalColor.AMBAR, SignalColor.ROJO
N, S, E, O = (SignalGroup.NORTE, SignalGroup.SUR, SignalGroup.ESTE,
              SignalGroup.OESTE)


def combo(n=R, s=R, e=R, o=R):
    return {N: n, S: s, E: e, O: o}


class TestConflictMatrix:
    def setup_method(self):
        self.m = ConflictMatrix()

    def test_todo_rojo_es_seguro(self):
        assert self.m.es_segura(combo())

    def test_ns_verde_es_seguro(self):
        assert self.m.es_segura(combo(n=V, s=V))

    def test_eo_verde_es_seguro(self):
        assert self.m.es_segura(combo(e=V, o=V))

    @pytest.mark.parametrize("g", [
        combo(n=V, e=V), combo(n=V, o=V), combo(s=V, e=V), combo(s=V, o=V),
        combo(n=V, s=V, e=V), combo(n=V, s=V, e=V, o=V),
    ])
    def test_verdes_cruzados_conflictivos(self, g):
        assert not self.m.es_segura(g)
        assert self.m.conflictos(g)

    def test_ambar_no_cuenta_como_verde(self):
        # NS en ámbar + EO en rojo: transición normal, segura
        assert self.m.es_segura(combo(n=A, s=A))


class TestSafetyGate:
    def test_salida_segura_pasa_intacta(self):
        gate = SafetyGate()
        g = combo(n=V, s=V)
        res = gate.check_output(g)
        assert res.safe and res.groups == g
        assert gate.violaciones_totales == 0

    def test_conflicto_fuerza_todo_rojo(self):
        gate = SafetyGate()
        res = gate.check_output(combo(n=V, e=V))
        assert not res.safe
        assert res.groups == TODO_ROJO
        assert any("verdes_conflictivos" in v for v in res.violations)
        assert gate.violaciones_totales == 1

    def test_grupos_incompletos_fuerza_todo_rojo(self):
        gate = SafetyGate()
        res = gate.check_output({N: V, S: V})   # faltan E y O
        assert not res.safe
        assert res.groups == TODO_ROJO
        assert any("grupos_incompletos" in v for v in res.violations)

    def test_gate_no_es_configurable(self):
        # La matriz es interna: no existe parámetro para inyectar una vacía.
        import inspect
        params = inspect.signature(SafetyGate.__init__).parameters
        assert list(params) == ["self"]


class TestMessageGuard:
    def test_acepta_secuencia_normal(self):
        g = MessageGuard()
        assert g.check_state(make_state(seq=0)).ok
        assert g.check_state(make_state(seq=1)).ok
        assert g.check_state(make_state(seq=5)).ok   # gaps permitidos (pérdida)

    def test_rechaza_duplicado(self):
        g = MessageGuard()
        assert g.check_state(make_state(seq=3)).ok
        v = g.check_state(make_state(seq=3))
        assert not v.ok and any("duplicate_seq" in r for r in v.reasons)

    def test_rechaza_fuera_de_orden(self):
        g = MessageGuard()
        assert g.check_state(make_state(seq=5)).ok
        v = g.check_state(make_state(seq=2))
        assert not v.ok and any("out_of_order" in r for r in v.reasons)

    def test_rechazo_no_avanza_ventana(self):
        g = MessageGuard()
        assert g.check_state(make_state(seq=1)).ok
        g.check_state(make_state(seq=1))       # duplicado: rechazado
        assert g.check_state(make_state(seq=2)).ok   # el 2 sigue siendo válido

    def test_rechaza_vencido(self):
        g = MessageGuard(max_age_s=10.0)
        v = g.check_state(make_state(seq=0), edad_s=11.0)
        assert not v.ok and any("stale" in r for r in v.reasons)

    def test_edad_none_no_rechaza(self):
        g = MessageGuard(max_age_s=10.0)
        assert g.check_state(make_state(seq=0), edad_s=None).ok

    def test_rechaza_esquema_desconocido(self):
        g = MessageGuard()
        st = make_state(seq=0).model_copy(update={"schema_version": "nsb.state/99"})
        v = g.check_state(st)
        assert not v.ok and any("bad_schema" in r for r in v.reasons)

    def test_rechaza_sensado_invalido(self):
        g = MessageGuard()
        st = make_state(seq=0, quality=QualityFlags(valid=False))
        v = g.check_state(st)
        assert not v.ok and "sensado_invalido" in v.reasons

    def test_nuevo_experimento_reinicia_ventana(self):
        g = MessageGuard()
        assert g.check_state(make_state(seq=7, experiment_id="exp-A")).ok
        # seq=0 de un experimento nuevo NO es out-of-order
        assert g.check_state(make_state(seq=0, experiment_id="exp-B")).ok
