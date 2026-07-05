"""Fixtures compartidas de la suite NSB."""
import pytest

from nsb.domain.contracts import ApproachState, PlanSemaforico, TrafficState
from nsb.domain.enums import Direction, SourceKind
from nsb.tsc.clock import ManualClock


@pytest.fixture
def clock():
    return ManualClock()


@pytest.fixture
def plan_base():
    return PlanSemaforico(t_verde_ns=30, t_verde_eo=30, t_ambar=3,
                          t_todo_rojo=2)


def make_state(seq=0, *, experiment_id="exp-test", ev_ns=0.0, ev_eo=0.0,
               ev_event=None, sim_time_s=None, ns=None, eo=None,
               quality=None, source=SourceKind.MANUAL,
               control_interval_s=25.0):
    """Fábrica de TrafficState con valores razonables por defecto."""
    kwargs = dict(
        experiment_id=experiment_id,
        intersection_id="int-test",
        source=source,
        seq=seq,
        sim_time_s=sim_time_s if sim_time_s is not None else seq * 25.0,
        control_interval_s=control_interval_s,
        approaches={
            Direction.NS: ns or ApproachState(
                queue_m=20, speed_kmh=15, flow_veh_min=8,
                num_vehicles=10, stopped_vehicles=4),
            Direction.EO: eo or ApproachState(
                queue_m=10, speed_kmh=25, flow_veh_min=6,
                num_vehicles=6, stopped_vehicles=2),
        },
        ev_ns=ev_ns, ev_eo=ev_eo, ev_event=ev_event,
    )
    if quality is not None:
        kwargs["quality"] = quality
    return TrafficState(**kwargs)


@pytest.fixture
def state_factory():
    return make_state
