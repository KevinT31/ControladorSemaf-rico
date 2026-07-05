"""Eventos de telemetría correlacionables (spec §30, §40).

Cada evento lleva las claves de correlación (experiment_id, node_id, seq,
recommendation_id) cuando aplican — nunca "todos los campos en cada evento".
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

# Severidades (subset de syslog, suficiente para el laboratorio)
DEBUG = "debug"
INFO = "info"
WARNING = "warning"
ERROR = "error"
CRITICAL = "critical"


class TelemetryEvent(BaseModel):
    """Evento estructurado, serializable a JSONL/MQTT."""
    model_config = ConfigDict(extra="forbid")

    ts_iso: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(
            timespec="milliseconds"))
    event: str                       # p. ej. "mode_change", "reject", "fallback"
    severity: str = INFO
    node_id: str
    experiment_id: Optional[str] = None
    seq: Optional[int] = None
    recommendation_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


def evento(event: str, node_id: str, severity: str = INFO,
           experiment_id: Optional[str] = None, seq: Optional[int] = None,
           recommendation_id: Optional[str] = None,
           **data: Any) -> TelemetryEvent:
    """Constructor compacto de eventos."""
    return TelemetryEvent(
        event=event, severity=severity, node_id=node_id,
        experiment_id=experiment_id, seq=seq,
        recommendation_id=recommendation_id, data=dict(data))
