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
import urllib.error
import urllib.request
from typing import Optional

from nsb.domain.contracts import RecommendationEnvelope, TrafficState
from nsb.domain.enums import Direction

logger = logging.getLogger(__name__)


def paquete_estado_local(state: TrafficState,
                         rec: Optional[RecommendationEnvelope]) -> dict:
    """Traduce TrafficState(+Recommendation) NSB → paquete estado_local.

    El modelo NSB es por dirección compuesta (NS/EO); el backend espera las
    4 direcciones N/S/E/O: cada dirección compuesta se reporta en sus dos
    accesos (mismo criterio que la maqueta de 12 LEDs: N y S comparten
    estado)."""
    ns = state.approaches[Direction.NS]
    eo = state.approaches[Direction.EO]

    def fila(ap, icv, pi, ev):
        return {
            "SC": ap.stopped_vehicles,
            "Vavg": ap.speed_kmh,
            "q": ap.flow_veh_min,
            "k": (ap.num_vehicles / 100.0),   # densidad aprox veh/m (100 m ref)
            "ICV": icv, "PI": pi, "EV": ev,
        }

    icv_ns = rec.computed.icv_ns if rec else 0.0
    icv_eo = rec.computed.icv_eo if rec else 0.0
    pi_ns = rec.computed.pi_ns if rec else 0.0
    pi_eo = rec.computed.pi_eo if rec else 0.0

    return {
        "intersection_id": state.intersection_id,
        "timestamp": state.wall_time_iso,
        "state_matrix": {
            "N": fila(ns, icv_ns, pi_ns, state.ev_ns),
            "S": fila(ns, icv_ns, pi_ns, state.ev_ns),
            "E": fila(eo, icv_eo, pi_eo, state.ev_eo),
            "O": fila(eo, icv_eo, pi_eo, state.ev_eo),
        },
        "emergency_vehicles": int(state.ev_event is not None),
        "fuente": f"nsb:{state.source.value}",
    }


class HttpSink:
    """POST best-effort al endpoint existente del backend."""

    def __init__(self, url: str, timeout_s: float = 2.0,
                 token: Optional[str] = None):
        self._url = url
        self._timeout = timeout_s
        self._token = token
        self._fallos_consecutivos = 0
        self._deshabilitado = False

    def emit_state(self, state: TrafficState,
                   rec: Optional[RecommendationEnvelope]) -> bool:
        """True si se entregó. Tras 5 fallos consecutivos se auto-deshabilita
        (se reintenta re-habilitar cada 50 emisiones)."""
        if self._deshabilitado:
            self._fallos_consecutivos += 1
            if self._fallos_consecutivos % 50 == 0:
                self._deshabilitado = False   # reintento periódico
            return False
        cuerpo = json.dumps(paquete_estado_local(state, rec)).encode("utf-8")
        req = urllib.request.Request(
            self._url, data=cuerpo, method="POST",
            headers={"Content-Type": "application/json"})
        if self._token:
            req.add_header("Authorization", f"Bearer {self._token}")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                ok = 200 <= resp.status < 300
            self._fallos_consecutivos = 0
            return ok
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            self._fallos_consecutivos += 1
            if self._fallos_consecutivos == 1:
                logger.warning("HttpSink: backend inaccesible (%s); "
                               "la telemetría local continúa", e)
            if self._fallos_consecutivos >= 5:
                self._deshabilitado = True
            return False
