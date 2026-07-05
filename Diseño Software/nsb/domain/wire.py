"""Envelope de transporte del protocolo HIL + framing JSON-lines.

Un mensaje = una línea JSON UTF-8 terminada en ``\\n``. El envelope usa
``extra="ignore"`` (a diferencia de los contratos científicos) para permitir
compatibilidad hacia adelante: un campo nuevo de una versión futura no debe
tirar la conexión.

La antigüedad de un mensaje se evalúa en el receptor con ``sent_at_iso``
(solo para descarte de mensajes vencidos — nunca para decidir control).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from nsb.domain.enums import WireType

SCHEMA_HIL = "nsb.hil/1"

# Tamaño máximo de línea aceptado (defensa contra basura/DoS accidental)
MAX_LINE_BYTES = 1_048_576  # 1 MiB


class WireEnvelope(BaseModel):
    """Sobre de transporte de todos los mensajes HIL (spec §14)."""
    model_config = ConfigDict(extra="ignore")

    type: WireType
    schema_version: str = SCHEMA_HIL
    experiment_id: Optional[str] = None
    seq: Optional[Annotated[int, Field(ge=0)]] = None
    sent_at_iso: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)


def now_iso() -> str:
    """Timestamp UTC ISO-8601 con milisegundos (solo informativo)."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def encode(env: WireEnvelope) -> bytes:
    """Serializa un envelope a una línea JSON UTF-8 terminada en \\n."""
    if not env.sent_at_iso:
        env = env.model_copy(update={"sent_at_iso": now_iso()})
    return (env.model_dump_json() + "\n").encode("utf-8")


class WireDecodeError(ValueError):
    """Línea no decodificable como WireEnvelope válido."""


def decode(line: bytes) -> WireEnvelope:
    """Parsea una línea (sin o con \\n final) a WireEnvelope.

    Lanza WireDecodeError ante JSON malformado, tamaño excesivo o
    violación de esquema — el llamador decide si responde ``error``
    o descarta.
    """
    if len(line) > MAX_LINE_BYTES:
        raise WireDecodeError(
            f"línea de {len(line)} bytes excede el máximo {MAX_LINE_BYTES}")
    try:
        data = json.loads(line.decode("utf-8").strip())
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise WireDecodeError(f"JSON malformado: {e}") from e
    if not isinstance(data, dict):
        raise WireDecodeError(f"se esperaba objeto JSON, llegó {type(data).__name__}")
    try:
        return WireEnvelope.model_validate(data)
    except Exception as e:  # pydantic.ValidationError sin acoplar el import
        raise WireDecodeError(f"envelope inválido: {e}") from e


def edad_segundos(env: WireEnvelope, ahora_iso: Optional[str] = None) -> Optional[float]:
    """Edad del mensaje en segundos según relojes de pared (informativo).

    Devuelve None si ``sent_at_iso`` está ausente o es inválido; el
    MessageGuard trata None como "no evaluable" (no rechaza por edad).
    """
    if not env.sent_at_iso:
        return None
    try:
        enviado = datetime.fromisoformat(env.sent_at_iso)
        ahora = (datetime.fromisoformat(ahora_iso) if ahora_iso
                 else datetime.now(timezone.utc))
        if enviado.tzinfo is None or ahora.tzinfo is None:
            return None
        return (ahora - enviado).total_seconds()
    except ValueError:
        return None
