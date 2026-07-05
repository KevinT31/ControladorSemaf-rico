"""Métricas de sistema (spec §31): CPU, RAM, temperatura.

La temperatura solo existe en Linux (`/sys/class/thermal` o
psutil.sensors_temperatures); en Windows se reporta None — jamás se inventa
un valor (spec §50).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import psutil
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

_THERMAL = Path("/sys/class/thermal/thermal_zone0/temp")


class SystemSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpu_percent: float
    ram_mb: float
    ram_percent: float
    temperature_c: Optional[float] = None   # None si la plataforma no expone


def snapshot() -> SystemSnapshot:
    vm = psutil.virtual_memory()
    return SystemSnapshot(
        cpu_percent=psutil.cpu_percent(interval=None),
        ram_mb=(vm.total - vm.available) / (1024 * 1024),
        ram_percent=vm.percent,
        temperature_c=_leer_temperatura(),
    )


def _leer_temperatura() -> Optional[float]:
    # Ruta Raspberry Pi / Linux genérico
    try:
        if _THERMAL.exists():
            return int(_THERMAL.read_text().strip()) / 1000.0
    except (OSError, ValueError):
        pass
    try:
        temps = getattr(psutil, "sensors_temperatures", lambda: {})()
        for entradas in temps.values():
            if entradas:
                return float(entradas[0].current)
    except Exception:
        pass
    return None


def percentiles(valores: List[float]) -> dict:
    """p50/p95/p99 sin numpy (suficiente para el benchmark). p99 solo con
    muestras suficientes (spec §31)."""
    if not valores:
        return {"n": 0}
    v = sorted(valores)
    n = len(v)

    def p(q: float) -> float:
        idx = min(n - 1, max(0, round(q * (n - 1))))
        return v[int(idx)]

    out = {"n": n, "min": v[0], "max": v[-1],
           "mean": sum(v) / n, "p50": p(0.50), "p95": p(0.95)}
    if n >= 100:
        out["p99"] = p(0.99)
    return out
