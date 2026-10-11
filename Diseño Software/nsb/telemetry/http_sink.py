"""Sink HTTP hacia el backend FastAPI EXISTENTE (D-F).

Mapea la telemetría NSB al contrato que el backend ya consume:
``POST /api/estado-local/ingresar`` espera el paquete de
``nucleo/estado_local.py:obtener_paquete_telemetria()`` (state_matrix con
SC/Vavg/q/k/ICV/PI/EV por dirección N/S/E/O). No se toca el backend ni se
crea un segundo modelo de datos.

La telemetría JAMÁS bloquea el control: fallos de red se registran y se
descartan (el JSONL local sigue siendo la fuente de verdad). stdlib
urllib — sin dependencias nuevas.
"""
from __future__ import annotations

import json
import logging
import math
import queue
import threading
import time
import urllib.error
import urllib.request
from typing import Optional
from urllib.parse import urlsplit

from nsb.domain.contracts import RecommendationEnvelope, TrafficState
from nsb.domain.enums import Direction

logger = logging.getLogger(__name__)

MAX_QUEUED = 256
CLOSE_FLUSH_S = 2.0


def paquete_estado_local(state: TrafficState,
                         rec: Optional[RecommendationEnvelope]) -> dict:
    """Traduce TrafficState(+Recommendation) NSB → paquete estado_local.

    El modelo NSB es por dirección compuesta (NS/EO); el backend espera las
    4 direcciones N/S/E/O: cada dirección compuesta se reporta en sus dos
    accesos (mismo criterio que la maqueta de 12 LEDs: N y S comparten
    estado)."""
    ns = state.approaches[Direction.NS]
    eo = state.approaches[Direction.EO]

    icv_ns = rec.computed.icv_ns if rec else 0.0
    icv_eo = rec.computed.icv_eo if rec else 0.0
    pi_ns = rec.computed.pi_ns if rec else 0.0
    pi_eo = rec.computed.pi_eo if rec else 0.0

    # El backend EstadoGlobalRed espera métricas como filas y el orden
    # [N, S, E, O], no un mapping de dirección -> métricas.
    dens_ns = ns.num_vehicles / 100.0  # densidad aprox. veh/m (100 m ref.)
    dens_eo = eo.num_vehicles / 100.0
    state_matrix = {
        "SC": [ns.stopped_vehicles, ns.stopped_vehicles,
               eo.stopped_vehicles, eo.stopped_vehicles],
        "Vavg": [ns.speed_kmh, ns.speed_kmh, eo.speed_kmh, eo.speed_kmh],
        "q": [ns.flow_veh_min, ns.flow_veh_min,
              eo.flow_veh_min, eo.flow_veh_min],
        "k": [dens_ns, dens_ns, dens_eo, dens_eo],
        "ICV": [icv_ns, icv_ns, icv_eo, icv_eo],
        "PI": [pi_ns, pi_ns, pi_eo, pi_eo],
        "EV": [state.ev_ns, state.ev_ns, state.ev_eo, state.ev_eo],
    }

    return {
        "intersection_id": state.intersection_id,
        "timestamp": state.wall_time_iso,
        "state_matrix": state_matrix,
        "emergency_vehicles": ([] if state.ev_event is None else [{
            "id": state.ev_event.track_id,
            "approach": state.ev_event.approach.value,
            "confidence": state.ev_event.confidence,
            "eta_s": state.ev_event.eta_s,
        }]),
        "fuente": f"nsb:{state.source.value}",
    }


class HttpSink:
    """POST best-effort al backend mediante una cola no bloqueante."""

    def __init__(self, url: str, timeout_s: float = 2.0,
                 token: Optional[str] = None,
                 max_queued: int = MAX_QUEUED):
        partes = urlsplit(url)
        if partes.scheme not in ("http", "https") or not partes.netloc:
            raise ValueError("url debe ser una URL http(s) válida")
        if not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("timeout_s debe ser finito y > 0")
        if (isinstance(max_queued, bool) or not isinstance(max_queued, int)
                or max_queued < 1):
            raise ValueError("max_queued debe ser un entero >= 1")
        self._url = url
        self._timeout = timeout_s
        self._token = token
        self._fallos_consecutivos = 0
        self._deshabilitado = False
        self._omitidos_circuito = 0
        self._dropped = 0
        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=max_queued)
        self._stop = threading.Event()
        self._closed = False
        self._worker = threading.Thread(
            target=self._run, name="nsb-http-telemetry", daemon=True)
        self._worker.start()

    @property
    def dropped(self) -> int:
        return self._dropped

    def emit_state(self, state: TrafficState,
                   rec: Optional[RecommendationEnvelope]) -> bool:
        """Encola sin esperar a la red; True significa aceptado por la cola."""
        if self._closed:
            self._dropped += 1
            return False
        cuerpo = json.dumps(paquete_estado_local(state, rec)).encode("utf-8")
        try:
            self._queue.put_nowait(cuerpo)
            return True
        except queue.Full:
            self._dropped += 1
            logger.warning("HttpSink: cola llena; telemetría descartada")
            return False

    def _post(self, cuerpo: bytes) -> None:
        # Circuit breaker: tras cinco fallos se descartan 49 paquetes y el
        # número 50 prueba de nuevo. La red nunca frena el hilo de control.
        if self._deshabilitado:
            self._omitidos_circuito += 1
            self._dropped += 1
            if self._omitidos_circuito < 50:
                return
            self._deshabilitado = False
            self._omitidos_circuito = 0

        req = urllib.request.Request(
            self._url, data=cuerpo, method="POST",
            headers={"Content-Type": "application/json"})
        if self._token:
            req.add_header("Authorization", f"Bearer {self._token}")
        try:
            # ``self._url`` se restringe a http(s) en ``__init__``.
            with urllib.request.urlopen(  # nosec B310
                    req, timeout=self._timeout) as resp:
                ok = 200 <= resp.status < 300
            if not ok:
                raise urllib.error.URLError(f"HTTP status {resp.status}")
            self._fallos_consecutivos = 0
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            self._fallos_consecutivos += 1
            self._dropped += 1
            if self._fallos_consecutivos == 1:
                logger.warning("HttpSink: backend inaccesible (%s); "
                               "la telemetría local continúa", e)
            if self._fallos_consecutivos >= 5:
                self._deshabilitado = True

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                cuerpo = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self._post(cuerpo)
            except Exception:
                self._dropped += 1
                logger.exception("HttpSink: error inesperado; paquete descartado")
            finally:
                self._queue.task_done()

    def close(self) -> None:
        """Detiene el worker; la espera queda acotada por el timeout HTTP."""
        if self._closed:
            return
        self._closed = True
        # En una corrida corta el shutdown puede llegar inmediatamente tras
        # el último estado. Dar una ventana acotada evita perder toda la cola.
        deadline = time.monotonic() + CLOSE_FLUSH_S
        while self._queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.01)
        self._stop.set()
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
            else:
                self._dropped += 1
                self._queue.task_done()
        self._worker.join(timeout=self._timeout + 0.2)
