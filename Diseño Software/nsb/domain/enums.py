"""Enumeraciones del dominio NSB.

Los valores de cadena son los que viajan por la red y se persisten en JSONL,
por lo que NO deben cambiarse sin subir `schema_version` en los contratos.
"""
from __future__ import annotations

from enum import Enum


class Mode(str, Enum):
    """Modo de autoridad del nodo (spec §10)."""
    ADVISORY = "advisory"
    TSC_EMULATED = "tsc_emulated"
    AUTOMATED_DIRECT_LAB = "automated_direct_lab"


class Verdict(str, Enum):
    """Veredicto del TSC Emulator sobre una recomendación (spec §25)."""
    ACCEPT = "accept"
    CLAMP = "clamp"
    DEFER = "defer"
    REJECT = "reject"


class PhaseId(str, Enum):
    """Estados de la máquina de fases del ciclo NS/EO de la tesis.

    Secuencia: NS_VERDE → NS_AMBAR → TODO_ROJO_1 → EO_VERDE → EO_AMBAR
    → TODO_ROJO_2 → NS_VERDE.
    """
    NS_VERDE = "ns_verde"
    NS_AMBAR = "ns_ambar"
    TODO_ROJO_1 = "todo_rojo_1"
    EO_VERDE = "eo_verde"
    EO_AMBAR = "eo_ambar"
    TODO_ROJO_2 = "todo_rojo_2"


class SourceKind(str, Enum):
    """Origen del TrafficState (spec §12)."""
    SUMO_HIL = "sumo_hil"
    VIDEO = "video"
    REPLAY = "replay"
    MANUAL = "manual"


class SignalColor(str, Enum):
    """Color de un grupo de señal (un semáforo de la maqueta)."""
    ROJO = "R"
    AMBAR = "A"
    VERDE = "V"


class Direction(str, Enum):
    """Dirección de control de la intersección (modelo NS/EO de la tesis)."""
    NS = "NS"
    EO = "EO"


class SignalGroup(str, Enum):
    """Grupos de señal físicos: 4 accesos × 3 colores = 12 LEDs.

    N y S comparten estado (dirección NS); E y O comparten estado (EO).
    """
    NORTE = "N"
    SUR = "S"
    ESTE = "E"
    OESTE = "O"


class WireType(str, Enum):
    """Tipos de mensaje del protocolo HIL (spec §14)."""
    HELLO = "hello"
    HELLO_ACK = "hello_ack"
    STATE = "state"
    DECISION = "decision"
    TICK = "tick"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    ERROR = "error"
    BYE = "bye"


class TimeoutPolicy(str, Enum):
    """Política del gateway ante timeout del nodo (decisión D-C).

    - FALLBACK: mantiene el plan vigente (o CONFIG_SEGURA tras N timeouts
      consecutivos) y continúa — para demos.
    - FAIL_FAST: aborta la corrida con código ≠ 0 — para campañas de métricas,
      donde un timeout contamina el determinismo.
    """
    FALLBACK = "fallback"
    FAIL_FAST = "fail_fast"
