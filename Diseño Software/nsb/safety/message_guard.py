"""Guard de mensajes entrantes (spec §11): antigüedad, secuencia y sanidad.

Complementa (no repite) la validación de Pydantic: los contratos ya rechazan
NaN/inf y esquemas malformados en la frontera; aquí se validan las
propiedades TEMPORALES y de ORDEN que un esquema no puede expresar:

- mensaje vencido (stale) según edad de reloj de pared — solo descarte,
  jamás decisión de control;
- seq duplicado (replay accidental o malicioso);
- seq fuera de orden (llega un seq menor al último aceptado);
- versión de esquema desconocida;
- sensado marcado inválido por la fuente (quality.valid = False).

El guard NO corrige: dictamina. El llamador decide el fallback.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from nsb.domain.contracts import TrafficState
from nsb.safety.limits import es_numero_finito

# Esquemas aceptados por esta versión del nodo
ESQUEMAS_ESTADO_ACEPTADOS = ("nsb.state/1",)


@dataclass
class GuardVerdict:
    """Resultado del guard: ok + razones de rechazo trazables."""
    ok: bool
    reasons: List[str] = field(default_factory=list)


class MessageGuard:
    """Valida propiedades temporales/de orden de los TrafficState entrantes.

    Mantiene estado mínimo (último seq aceptado por experimento) — se
    reinicia al cambiar de experiment_id, que es el comportamiento correcto
    para replays y corridas nuevas.
    """

    def __init__(self, max_age_s: Optional[float] = 30.0):
        self._max_age_s = max_age_s
        self._experiment_id: Optional[str] = None
        self._ultimo_seq: Optional[int] = None

    @property
    def ultimo_seq(self) -> Optional[int]:
        return self._ultimo_seq

    def check_state(self, state: TrafficState,
                    edad_s: Optional[float] = None) -> GuardVerdict:
        """Dictamina un TrafficState. Si es aceptado, avanza el seq interno.

        `edad_s`: edad del mensaje según relojes de pared (la calcula el
        transporte con `wire.edad_segundos`); None = no evaluable, no se
        rechaza por edad.
        """
        reasons: List[str] = []

        if state.schema_version not in ESQUEMAS_ESTADO_ACEPTADOS:
            reasons.append(f"bad_schema:{state.schema_version}")

        if (self._max_age_s is not None and edad_s is not None
                and edad_s > self._max_age_s):
            reasons.append(f"stale:edad={edad_s:.1f}s>max={self._max_age_s:.1f}s")

        if self._experiment_id == state.experiment_id and self._ultimo_seq is not None:
            if state.seq == self._ultimo_seq:
                reasons.append(f"duplicate_seq:{state.seq}")
            elif state.seq < self._ultimo_seq:
                reasons.append(
                    f"out_of_order:seq={state.seq}<ultimo={self._ultimo_seq}")

        if not state.quality.valid:
            reasons.append("sensado_invalido")

        # Defensa en profundidad: Pydantic ya rechaza NaN/inf al validar,
        # pero un estado construido SIN validación (model_construct, bug
        # interno, fault injection) no pasó por esa frontera. Se re-verifica
        # la finitud de todo lo numérico que alimenta la decisión.
        for dir_, ap in state.approaches.items():
            for campo in ("queue_m", "speed_kmh", "flow_veh_min"):
                if not es_numero_finito(getattr(ap, campo)):
                    reasons.append(
                        f"no_finito:{dir_.value}.{campo}={getattr(ap, campo)!r}")
        for campo in ("ev_ns", "ev_eo"):
            if not es_numero_finito(getattr(state, campo)):
                reasons.append(f"no_finito:{campo}={getattr(state, campo)!r}")

        if reasons:
            return GuardVerdict(ok=False, reasons=reasons)

        # Aceptado: avanzar ventana de secuencia (por experimento)
        self._experiment_id = state.experiment_id
        self._ultimo_seq = state.seq
        return GuardVerdict(ok=True)

    def reset(self) -> None:
        """Olvida la ventana de secuencia (nueva sesión/experimento)."""
        self._experiment_id = None
        self._ultimo_seq = None
