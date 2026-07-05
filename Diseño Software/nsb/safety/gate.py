"""SafetyGate: invariante final ante TODO write al actuador (spec §11, §34).

ÚLTIMA línea de defensa, en TODOS los modos (incluido AUTOMATED_DIRECT_LAB):
ninguna combinación de verdes declarada conflictiva por la matriz puede
llegar al hardware. Si se detecta, se fuerza TODO-ROJO y se reporta con
severidad crítica.

Diseño deliberado: esta clase NO es configurable ni inyectable por config —
se construye dentro del camino de actuación. No existe flag, modo debug ni
mensaje remoto que la desactive (spec §10.3).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from nsb.domain.enums import SignalColor, SignalGroup
from nsb.safety.conflict_matrix import ConflictMatrix

logger = logging.getLogger(__name__)

TODO_ROJO: Dict[SignalGroup, SignalColor] = {
    g: SignalColor.ROJO for g in SignalGroup
}


@dataclass
class GateResult:
    """Resultado del gate sobre una salida propuesta."""
    safe: bool
    groups: Dict[SignalGroup, SignalColor]      # lo que DEBE aplicarse
    violations: List[str] = field(default_factory=list)


class SafetyGate:
    """Verifica la invariante de no-conflicto sobre la salida física."""

    def __init__(self) -> None:
        # Matriz propia, no inyectada: nadie puede pasar una matriz vacía.
        self._matrix = ConflictMatrix()
        self._violaciones_totales = 0

    @property
    def violaciones_totales(self) -> int:
        return self._violaciones_totales

    def check_output(self, groups: Dict[SignalGroup, SignalColor],
                     context: Optional[str] = None) -> GateResult:
        """Dictamina una salida propuesta para los 4 grupos de señal.

        - Combinación segura → se devuelve tal cual (safe=True).
        - Conflicto o grupos incompletos → safe=False y `groups`=TODO-ROJO;
          el llamador DEBE aplicar el resultado del gate, no su propuesta.
        """
        violations: List[str] = []

        faltantes = set(SignalGroup) - set(groups)
        if faltantes:
            violations.append(
                "grupos_incompletos:" +
                ",".join(sorted(g.value for g in faltantes)))

        for a, b in self._matrix.conflictos(groups):
            violations.append(f"verdes_conflictivos:{a.value}+{b.value}")

        if violations:
            self._violaciones_totales += 1
            logger.critical(
                "SAFETY GATE: salida BLOQUEADA -> TODO-ROJO forzado "
                "(contexto=%s, violaciones=%s)", context or "n/a", violations)
            return GateResult(safe=False, groups=dict(TODO_ROJO),
                              violations=violations)

        return GateResult(safe=True, groups=dict(groups))
