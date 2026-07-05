"""Sink JSONL local (SIEMPRE activo — fuente de verdad de la telemetría).

Un archivo por corrida: ``{dir}/{node_id}_{experiment_id}_{ts}.events.jsonl``.
UTF-8 explícito (riesgo conocido de cp1252 en Windows). Rotación simple por
tamaño para no llenar la SD de la Pi en corridas largas.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Optional

from nsb.telemetry.events import TelemetryEvent

logger = logging.getLogger(__name__)

MAX_BYTES_DEFAULT = 50 * 1024 * 1024  # 50 MiB por archivo


def _slug(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", texto)[:80]


class JsonlSink:
    """Escritor de eventos JSONL con rotación por tamaño."""

    def __init__(self, directory: str | Path, node_id: str,
                 experiment_id: str = "sin-experimento",
                 max_bytes: int = MAX_BYTES_DEFAULT):
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._node = _slug(node_id)
        self._exp = _slug(experiment_id)
        self._max_bytes = max_bytes
        self._f: Optional[IO[str]] = None
        self._bytes = 0
        self._parte = 0
        self._abrir()

    @property
    def path(self) -> Optional[Path]:
        return self._path if self._f is not None else None

    def _abrir(self) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        sufijo = f".{self._parte}" if self._parte else ""
        self._path = self._dir / (
            f"{self._node}_{self._exp}_{ts}{sufijo}.events.jsonl")
        self._f = open(self._path, "w", encoding="utf-8", newline="\n")
        self._bytes = 0

    def emit(self, event: TelemetryEvent) -> None:
        if self._f is None:
            return  # sink cerrado: la telemetría jamás tumba el control
        try:
            linea = event.model_dump_json() + "\n"
            self._f.write(linea)
            self._bytes += len(linea.encode("utf-8"))
            if self._bytes >= self._max_bytes:
                self._f.close()
                self._parte += 1
                self._abrir()
        except OSError as e:
            logger.error("JsonlSink: fallo de escritura (%s); sink desactivado", e)
            try:
                self._f.close()
            finally:
                self._f = None

    def close(self) -> None:
        if self._f is not None:
            self._f.close()
            self._f = None
