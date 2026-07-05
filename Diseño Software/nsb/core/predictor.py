"""Predictor opcional (spec §21).

HALLAZGO DE AUDITORÍA (D-01): la CNN-LSTM descrita en la especificación NO
existe en el repositorio (ni código ni modelo entrenado). Por honestidad
científica aquí solo se define el contrato `PredictorBackend` y el
`DisabledPredictor` por defecto. Cuando exista un modelo real, se implementa
otro backend sin tocar el pipeline; los mocks viven exclusivamente en tests.

Garantía de la spec: el predictor NUNCA bloquea la seguridad — ante cualquier
problema (deshabilitado, no disponible, error, timeout) el pipeline sigue con
el núcleo difuso y lo registra en `PredictorInfo.fallback_reason`.
"""
from __future__ import annotations

from typing import Optional, Protocol

from nsb.domain.contracts import PredictorInfo, TrafficState


class PredictorBackend(Protocol):
    """Contrato de un predictor de tráfico opcional."""

    @property
    def enabled(self) -> bool: ...

    @property
    def available(self) -> bool: ...

    def predict(self, state: TrafficState) -> Optional[dict]:
        """Predicción opcional. None => sin predicción (fallback a difuso)."""
        ...

    def info(self) -> PredictorInfo:
        """Estado del predictor para telemetría."""
        ...


class DisabledPredictor:
    """Predictor por defecto: no existe modelo en el repo (D-01)."""

    enabled = False
    available = False

    def predict(self, state: TrafficState) -> Optional[dict]:
        return None

    def info(self) -> PredictorInfo:
        return PredictorInfo(
            enabled=False, available=False, used=False,
            fallback_reason="predictor_deshabilitado (CNN-LSTM no existe en el repo)",
            inference_ms=None,
        )
