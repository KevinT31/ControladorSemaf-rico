"""Plan declarativo de fallos: qué inyectar y en qué seq (spec §32)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# Fallos soportados por los inyectores
FALLOS = (
    "nan_queue",        # queue_m = NaN (bypass de validación → guard)
    "inf_speed",        # speed_kmh = inf
    "duplicate",        # re-emite el seq anterior
    "out_of_order",     # emite un seq viejo
    "drop",             # no emite el estado (pérdida)
    "stale",            # estado con edad excesiva
    "sensado_invalido", # quality.valid = False
    "verde_200",        # recomendación con verde de 200 s (sabotaje pipeline)
    "conflicto_verde",  # salida con verdes conflictivos (sabotaje actuación)
    "predictor_roto",   # predictor que lanza excepción
)


@dataclass
class FaultPlan:
    """Mapa seq → lista de fallos a inyectar en ese punto de control."""
    fallos: Dict[int, List[str]] = field(default_factory=dict)

    def __post_init__(self):
        for seq, lista in self.fallos.items():
            for f in lista:
                if f not in FALLOS:
                    raise ValueError(f"fallo desconocido en seq {seq}: {f!r}")

    def en(self, seq: int) -> List[str]:
        return self.fallos.get(seq, [])
