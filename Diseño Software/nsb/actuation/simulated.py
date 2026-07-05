"""Actuador simulado (obligatorio, spec §23): estado en memoria + log
estructurado + render opcional de consola. Es el backend por defecto en
Windows y el que usan los tests de integración.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from nsb.domain.enums import SignalColor, SignalGroup
from nsb.safety.gate import TODO_ROJO

logger = logging.getLogger(__name__)

_ICONO = {SignalColor.ROJO: "🔴", SignalColor.AMBAR: "🟡",
          SignalColor.VERDE: "🟢"}


class SimulatedActuator:
    """Backend simulado: guarda el estado y opcionalmente lo dibuja."""

    def __init__(self, render: bool = False, history_limit: int = 10_000):
        self._estado: Dict[SignalGroup, SignalColor] = dict(TODO_ROJO)
        self._render = render
        self._historia: List[Dict[SignalGroup, SignalColor]] = []
        self._history_limit = history_limit
        self._applies = 0

    @property
    def applies(self) -> int:
        return self._applies

    @property
    def historia(self) -> List[Dict[SignalGroup, SignalColor]]:
        """Historial de combinaciones aplicadas (verificación de invariantes
        en tests: nunca debe contener verdes conflictivos)."""
        return list(self._historia)

    def apply(self, groups: Dict[SignalGroup, SignalColor]) -> None:
        self._estado = dict(groups)
        self._applies += 1
        if len(self._historia) < self._history_limit:
            self._historia.append(dict(groups))
        logger.debug("SimulatedActuator: %s",
                     {g.value: c.value for g, c in groups.items()})
        if self._render:
            self._dibujar()

    def state(self) -> Dict[SignalGroup, SignalColor]:
        return dict(self._estado)

    def shutdown(self) -> None:
        self.apply(dict(TODO_ROJO))
        logger.info("SimulatedActuator: apagado ordenado (todo-rojo)")

    def _dibujar(self) -> None:
        e = self._estado
        try:
            print(f"        N {_ICONO[e[SignalGroup.NORTE]]}\n"
                  f"  O {_ICONO[e[SignalGroup.OESTE]]}      E {_ICONO[e[SignalGroup.ESTE]]}\n"
                  f"        S {_ICONO[e[SignalGroup.SUR]]}")
        except UnicodeEncodeError:
            # Consolas Windows cp1252: degradar a ASCII sin romper el nodo
            print("  N={} O={} E={} S={}".format(
                e[SignalGroup.NORTE].value, e[SignalGroup.OESTE].value,
                e[SignalGroup.ESTE].value, e[SignalGroup.SUR].value))
