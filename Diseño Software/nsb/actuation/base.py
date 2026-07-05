"""Contrato de los backends de actuación (spec §23).

Todo `apply()` del sistema pasa ANTES por el SafetyGate — esa composición
vive en `nsb.node`/autoridad, no aquí; los backends son tontos a propósito:
reciben una combinación ya dictaminada y la materializan.
"""
from __future__ import annotations

from typing import Dict, Protocol

from nsb.domain.enums import SignalColor, SignalGroup


class ActuatorBackend(Protocol):
    """Backend de actuación de los 4 grupos × 3 colores (12 salidas)."""

    def apply(self, groups: Dict[SignalGroup, SignalColor]) -> None:
        """Materializa la combinación (LEDs físicos, memoria, etc.)."""
        ...

    def state(self) -> Dict[SignalGroup, SignalColor]:
        """Última combinación aplicada (para verificación/telemetría)."""
        ...

    def shutdown(self) -> None:
        """Apagado ordenado: lleva la maqueta a TODO-ROJO y libera recursos."""
        ...
