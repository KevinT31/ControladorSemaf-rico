"""Matriz de conflictos por grupos de señal (spec §11, decisión D-05).

Formaliza —sin inventar topologías ajenas a la tesis— la regla de seguridad
del Cap. 6: las direcciones NS y EO jamás pueden estar en verde a la vez.
Se expresa como matriz explícita sobre los 4 grupos físicos (N, S, E, O)
para que la invariante sea comprobable sobre el estado real de los 12 LEDs,
no solo sobre una abstracción.

La verificación binaria canónica (`verificar_fases_no_conflictivas`) se
reutiliza como doble control de la misma propiedad.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, List, Tuple

from nsb.domain.enums import SignalColor, SignalGroup
from nsb.safety.limits import validador_seguridad

# Pares de grupos DECLARADOS conflictivos: un verde simultáneo en cualquiera
# de estos pares es un estado prohibido. N-S son compatibles entre sí (misma
# dirección de la tesis), igual que E-O.
PARES_CONFLICTIVOS: FrozenSet[FrozenSet[SignalGroup]] = frozenset({
    frozenset({SignalGroup.NORTE, SignalGroup.ESTE}),
    frozenset({SignalGroup.NORTE, SignalGroup.OESTE}),
    frozenset({SignalGroup.SUR, SignalGroup.ESTE}),
    frozenset({SignalGroup.SUR, SignalGroup.OESTE}),
})


class ConflictMatrix:
    """Dictamina si una combinación de colores de los 4 grupos es segura."""

    def __init__(self,
                 pares: FrozenSet[FrozenSet[SignalGroup]] = PARES_CONFLICTIVOS):
        self._pares = pares

    def conflictos(self, grupos: Dict[SignalGroup, SignalColor]
                   ) -> List[Tuple[SignalGroup, SignalGroup]]:
        """Devuelve la lista de pares conflictivos EN VERDE simultáneo.

        Lista vacía = combinación segura. El ámbar no se considera verde:
        la ventana de despeje la garantiza la FSM (ámbar + todo-rojo), y la
        invariante crítica de la spec es sobre verdes.
        """
        verdes = {g for g, c in grupos.items() if c is SignalColor.VERDE}
        hallados: List[Tuple[SignalGroup, SignalGroup]] = []
        for par in self._pares:
            if par <= verdes:
                a, b = sorted(par, key=lambda g: g.value)
                hallados.append((a, b))
        return hallados

    def es_segura(self, grupos: Dict[SignalGroup, SignalColor]) -> bool:
        """True si NO existe ningún par conflictivo en verde.

        Doble control: además de la matriz propia, se consulta la regla
        binaria canónica de la tesis (NS verde y EO verde a la vez).
        """
        if self.conflictos(grupos):
            return False
        ns_verde = any(
            grupos.get(g) is SignalColor.VERDE
            for g in (SignalGroup.NORTE, SignalGroup.SUR))
        eo_verde = any(
            grupos.get(g) is SignalColor.VERDE
            for g in (SignalGroup.ESTE, SignalGroup.OESTE))
        return validador_seguridad.verificar_fases_no_conflictivas(
            ns_verde, eo_verde)
