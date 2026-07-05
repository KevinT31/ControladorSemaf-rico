"""Replay reproducible (spec §18): grabación y reproducción JSONL.

Formato: una línea JSON UTF-8 por registro, con un campo ``kind``:

    {"kind": "state",    "data": {<TrafficState>}}
    {"kind": "decision", "data": {<DecisionEnvelope>}}
    {"kind": "recommendation", "data": {<RecommendationEnvelope>}}

Se graban estados Y decisiones; el replay reproduce los estados y permite
comparar las decisiones nuevas contra las grabadas (regresión determinista).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import IO, Iterator, Optional

from nsb.domain.contracts import (
    DecisionEnvelope,
    RecommendationEnvelope,
    TrafficState,
)

KIND_STATE = "state"
KIND_DECISION = "decision"
KIND_RECOMMENDATION = "recommendation"


class ReplayWriter:
    """Grabador JSONL de estados/recomendaciones/decisiones."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._f: Optional[IO[str]] = open(self._path, "w", encoding="utf-8",
                                          newline="\n")
        self._registros = 0

    @property
    def registros(self) -> int:
        return self._registros

    def _write(self, kind: str, model) -> None:
        if self._f is None:
            raise RuntimeError("ReplayWriter ya cerrado")
        linea = json.dumps({"kind": kind,
                            "data": json.loads(model.model_dump_json())},
                           ensure_ascii=False)
        self._f.write(linea + "\n")
        self._registros += 1

    def write_state(self, state: TrafficState) -> None:
        self._write(KIND_STATE, state)

    def write_recommendation(self, rec: RecommendationEnvelope) -> None:
        self._write(KIND_RECOMMENDATION, rec)

    def write_decision(self, decision: DecisionEnvelope) -> None:
        self._write(KIND_DECISION, decision)

    def close(self) -> None:
        if self._f is not None:
            self._f.close()
            self._f = None


class ReplayStateSource:
    """Fuente que reproduce los TrafficState de un JSONL grabado."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"replay no encontrado: {self._path}")
        self._f: Optional[IO[str]] = None

    def __iter__(self) -> Iterator[TrafficState]:
        with open(self._path, encoding="utf-8") as f:
            self._f = f
            for num, linea in enumerate(f, start=1):
                linea = linea.strip()
                if not linea:
                    continue
                reg = json.loads(linea)
                if reg.get("kind") != KIND_STATE:
                    continue
                try:
                    yield TrafficState.model_validate(reg["data"])
                except Exception as e:
                    raise ValueError(
                        f"{self._path}:{num}: TrafficState inválido: {e}") from e
        self._f = None

    def close(self) -> None:
        # El manejador de contexto del iterador cierra el archivo; noop aquí.
        pass


def leer_decisiones(path: str | Path) -> Iterator[DecisionEnvelope]:
    """Itera las decisiones grabadas en un JSONL (comparación de regresión)."""
    with open(path, encoding="utf-8") as f:
        for num, linea in enumerate(f, start=1):
            linea = linea.strip()
            if not linea:
                continue
            reg = json.loads(linea)
            if reg.get("kind") != KIND_DECISION:
                continue
            yield DecisionEnvelope.model_validate(reg["data"])


def digest_decisiones(path: str | Path) -> str:
    """SHA-256 de los campos DECISORIOS de las decisiones de una corrida.

    Excluye deliberadamente las mediciones no deterministas
    (processing_ms, actuation_ms): dos corridas idénticas deben producir el
    mismo digest aunque el hardware tarde distinto.
    """
    h = hashlib.sha256()
    for d in leer_decisiones(path):
        nucleo_decision = d.model_dump(mode="json", exclude={
            "processing_ms", "actuation_ms"})
        h.update(json.dumps(nucleo_decision, sort_keys=True,
                            ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()
