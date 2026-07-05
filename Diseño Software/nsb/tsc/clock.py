"""Relojes inyectables (decisión D-B).

La FSM y el TSC jamás llaman a `time.time()` directamente: reciben un
`Clock`. Así el mismo código corre con tiempo de simulación (HIL), tiempo
de pared (demos con LEDs) o tiempo controlado (tests deterministas).
"""
from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    """Fuente de tiempo monotónica en segundos (el dominio depende de la
    implementación: sim_time de SUMO, reloj de pared o manual)."""

    def now(self) -> float: ...


class WallClock:
    """Reloj de pared monotónico (demos con LEDs en tiempo real)."""

    def now(self) -> float:
        return time.monotonic()


class SimClock:
    """Reloj de simulación: avanza SOLO cuando el gateway informa sim_time.

    Rechaza retrocesos (un sim_time menor al actual se ignora y se registra
    por el llamador si le importa) — SUMO nunca retrocede dentro de un
    experimento.
    """

    def __init__(self, start_s: float = 0.0):
        self._t = float(start_s)

    def set_time(self, sim_time_s: float) -> bool:
        """Actualiza el tiempo. Devuelve False si se ignoró por retroceso."""
        t = float(sim_time_s)
        if t < self._t:
            return False
        self._t = t
        return True

    def now(self) -> float:
        return self._t


class ManualClock:
    """Reloj de tests: control absoluto del tiempo."""

    def __init__(self, start_s: float = 0.0):
        self._t = float(start_s)

    def advance(self, dt_s: float) -> None:
        if dt_s < 0:
            raise ValueError("ManualClock no retrocede")
        self._t += float(dt_s)

    def set(self, t_s: float) -> None:
        if t_s < self._t:
            raise ValueError("ManualClock no retrocede")
        self._t = float(t_s)

    def now(self) -> float:
        return self._t
