"""VideoStateSource (spec §12, §15): TrafficState desde video de dron.

SOLO ADVISORY: la CLI rechaza cualquier otro modo con esta fuente. El video
jamás actúa sobre semáforos — se registran recomendaciones para comparación
offline (`drone_video_validation.md`).

Agregación por punto de control: los frames procesados dentro de cada
ventana de ``control_interval_s`` segundos DE VIDEO se agregan a un
TrafficState. ``sim_time_s`` = frontera de la ventana (tiempo de video):
determinista y reproducible — el reloj de pared no participa (D-B).

Calidad (spec §16): ``camera_moving`` y ``calibrated`` los declara el
operador (no se inventan detecciones de movimiento de cámara ni
calibraciones); una ventana sin frames procesados sale ``valid=False`` y el
MessageGuard del nodo la rechaza.
"""
from __future__ import annotations

from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from nsb.domain.contracts import ApproachState, EvEvent, TrafficState
from nsb.domain.enums import Direction, SourceKind
from nsb.vision.provider import FrameMetrics

EV_UMBRAL = 0.5   # confianza mínima para reportar evento EV (ADVISORY igual)


def agregar_ventana(frames: List[FrameMetrics]) -> ApproachState:
    """Agrega los frames de una ventana a un ApproachState (media simple).

    Media y no máximo: un falso positivo de un frame no debe dominar el
    punto de control. La velocidad promedia solo frames con vehículos en
    movimiento detectados (speed>0); si no hubo, queda 0 (parado o vacío —
    el ICV canónico distingue por SC y flujo).
    """
    if not frames:
        return ApproachState()
    n = len(frames)
    speeds = [f.speed_kmh for f in frames if f.speed_kmh > 0]
    return ApproachState(
        num_vehicles=round(sum(f.num_vehicles for f in frames) / n),
        stopped_vehicles=round(sum(f.stopped_vehicles for f in frames) / n),
        queue_m=sum(f.queue_m for f in frames) / n,
        speed_kmh=(sum(speeds) / len(speeds)) if speeds else 0.0,
        flow_veh_min=sum(f.flow_veh_min for f in frames) / n,
    )


class VideoStateSource:
    """Fuente de TrafficState desde un proveedor de pares (NS, EO).

    El proveedor es inyectable: en producción ``DualRoiVideoProvider``
    (YOLO real); en tests, cualquier iterable de pares FrameMetrics.
    """

    def __init__(self, provider: Iterable[Tuple[FrameMetrics, FrameMetrics]],
                 experiment_id: str,
                 intersection_id: str = "interseccion-01",
                 control_interval_s: float = 25.0,
                 camera_moving: bool = False,
                 calibrated: bool = False,
                 metadata: Optional[Dict[str, str]] = None):
        if control_interval_s <= 0:
            raise ValueError("control_interval_s debe ser > 0")
        self._provider = provider
        self._experiment_id = experiment_id
        self._intersection_id = intersection_id
        self._interval = control_interval_s
        self._camera_moving = camera_moving
        self._calibrated = calibrated
        self._metadata = dict(metadata or {})

    # ------------------------------------------------------------------ #
    def _estado(self, seq: int, fin_ventana: float,
                ns: List[FrameMetrics], eo: List[FrameMetrics]) -> TrafficState:
        ev_ns = max((f.ev_confidence for f in ns), default=0.0)
        ev_eo = max((f.ev_confidence for f in eo), default=0.0)
        ev_event = None
        if max(ev_ns, ev_eo) >= EV_UMBRAL:
            approach = Direction.NS if ev_ns >= ev_eo else Direction.EO
            ev_event = EvEvent(approach=approach,
                               confidence=max(ev_ns, ev_eo))
        frames_ventana = len(ns) + len(eo)
        return TrafficState(
            experiment_id=self._experiment_id,
            intersection_id=self._intersection_id,
            source=SourceKind.VIDEO,
            seq=seq,
            sim_time_s=round(fin_ventana, 3),
            control_interval_s=self._interval,
            approaches={Direction.NS: agregar_ventana(ns),
                        Direction.EO: agregar_ventana(eo)},
            ev_ns=ev_ns,
            ev_eo=ev_eo,
            ev_event=ev_event,
            quality={
                # ventana vacía => inválida: el guard la rechaza (no se
                # fabrica un estado a partir de cero frames)
                "valid": frames_ventana > 0,
                "camera_moving": self._camera_moving,
                "calibrated": self._calibrated,
            },
            metadata={**self._metadata,
                      "frames_ventana": str(frames_ventana)},
        )

    def __iter__(self) -> Iterator[TrafficState]:
        seq = 0
        fin = self._interval
        ns: List[FrameMetrics] = []
        eo: List[FrameMetrics] = []
        alguno = False
        for m_ns, m_eo in self._provider:
            alguno = True
            # cerrar todas las ventanas anteriores al frame actual
            while m_ns.t_s >= fin:
                yield self._estado(seq, fin, ns, eo)
                seq += 1
                fin += self._interval
                ns, eo = [], []
            ns.append(m_ns)
            eo.append(m_eo)
        if ns or eo:                       # ventana final parcial
            yield self._estado(seq, fin, ns, eo)
        elif not alguno:
            raise ValueError(
                "el proveedor de video no produjo ningún frame procesable")

    def close(self) -> None:
        close = getattr(self._provider, "close", None)
        if close is not None:
            close()
