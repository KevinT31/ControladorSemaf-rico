"""Fuente sintética de tests y demos (spec §12: ManualTestStateSource).

Genera secuencias PARAMETRIZADAS y DETERMINISTAS de TrafficState para
escenarios de laboratorio. No pretende realismo de tráfico: pretende
reproducibilidad y control de condiciones (congestión creciente, EV, etc.).
"""
from __future__ import annotations

import math
from typing import Iterator, Optional

from nsb.domain.contracts import ApproachState, EvEvent, TrafficState
from nsb.domain.enums import Direction, SourceKind

ESCENARIOS = ("uniforme", "congestion_ns", "congestion_eo", "emergencia_ns",
              "emergencia_eo", "vacio")


class ManualTestStateSource:
    """Secuencia determinista de estados según un escenario nombrado."""

    def __init__(self, escenario: str = "uniforme", pasos: int = 40,
                 experiment_id: str = "manual-demo",
                 intersection_id: str = "interseccion-01",
                 control_interval_s: float = 25.0):
        if escenario not in ESCENARIOS:
            raise ValueError(
                f"escenario desconocido: {escenario!r}; opciones: {ESCENARIOS}")
        self._escenario = escenario
        self._pasos = pasos
        self._experiment_id = f"{experiment_id}-{escenario}"
        self._intersection_id = intersection_id
        self._interval = control_interval_s

    def __iter__(self) -> Iterator[TrafficState]:
        for k in range(self._pasos):
            yield self._estado(k)

    def close(self) -> None:
        pass

    # ------------------------------------------------------------------ #
    def _estado(self, k: int) -> TrafficState:
        # Onda determinista suave (sin RNG): base de demanda variable
        fase = 0.5 + 0.5 * math.sin(k / 6.0)

        if self._escenario == "vacio":
            ns = ApproachState()
            eo = ApproachState()
        elif self._escenario == "congestion_ns":
            ns = self._acceso_congestionado(fase)
            eo = self._acceso_fluido(fase)
        elif self._escenario == "congestion_eo":
            ns = self._acceso_fluido(fase)
            eo = self._acceso_congestionado(fase)
        else:  # uniforme / emergencia_*
            ns = self._acceso_medio(fase)
            eo = self._acceso_medio(1.0 - fase)

        ev_ns = ev_eo = 0.0
        ev_event: Optional[EvEvent] = None
        if self._escenario == "emergencia_ns" and 10 <= k < 14:
            ev_ns = 1.0
            ev_event = EvEvent(approach=Direction.NS, confidence=0.93,
                               eta_s=18.0, track_id="ev-demo-ns")
        elif self._escenario == "emergencia_eo" and 10 <= k < 14:
            ev_eo = 1.0
            ev_event = EvEvent(approach=Direction.EO, confidence=0.93,
                               eta_s=18.0, track_id="ev-demo-eo")

        return TrafficState(
            experiment_id=self._experiment_id,
            intersection_id=self._intersection_id,
            source=SourceKind.MANUAL,
            seq=k,
            sim_time_s=k * self._interval,
            control_interval_s=self._interval,
            approaches={Direction.NS: ns, Direction.EO: eo},
            ev_ns=ev_ns, ev_eo=ev_eo, ev_event=ev_event,
        )

    @staticmethod
    def _acceso_congestionado(fase: float) -> ApproachState:
        return ApproachState(
            queue_m=60.0 + 40.0 * fase,
            speed_kmh=4.0 + 4.0 * (1 - fase),
            flow_veh_min=18.0 + 8.0 * fase,
            num_vehicles=int(20 + 10 * fase),
            stopped_vehicles=int(14 + 8 * fase),
        )

    @staticmethod
    def _acceso_fluido(fase: float) -> ApproachState:
        return ApproachState(
            queue_m=4.0 * fase,
            speed_kmh=38.0 + 10.0 * (1 - fase),
            flow_veh_min=6.0 + 2.0 * fase,
            num_vehicles=int(3 + 2 * fase),
            stopped_vehicles=0,
        )

    @staticmethod
    def _acceso_medio(fase: float) -> ApproachState:
        return ApproachState(
            queue_m=15.0 + 20.0 * fase,
            speed_kmh=18.0 + 12.0 * (1 - fase),
            flow_veh_min=10.0 + 6.0 * fase,
            num_vehicles=int(8 + 6 * fase),
            stopped_vehicles=int(3 + 4 * fase),
        )
