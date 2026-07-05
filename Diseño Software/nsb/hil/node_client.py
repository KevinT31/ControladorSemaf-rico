"""Cliente HIL del nodo edge: conecta al gateway, procesa states, responde
decisiones. Reconexión con backoff exponencial; ante pérdida del enlace el
TSC local entra en modo seguro (spec §26-B) y se reintenta.
"""
from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass
from typing import Optional

from nsb.config import HilClientConfig
from nsb.domain.contracts import TrafficState
from nsb.domain.enums import WireType
from nsb.domain.wire import WireDecodeError, WireEnvelope, edad_segundos
from nsb.hil.protocol import ChannelClosed, LineChannel
from nsb.node import NsbNode
from nsb.telemetry.events import WARNING, evento

logger = logging.getLogger(__name__)


@dataclass
class ClientSummary:
    estados: int = 0
    reconexiones: int = 0
    errores_protocolo: int = 0
    terminado_por_bye: bool = False


class HilNodeClient:
    """Lado nodo del lazo HIL (bloqueante, monohilo — D-03)."""

    def __init__(self, node: NsbNode, cfg: HilClientConfig, node_id: str):
        self._node = node
        self._cfg = cfg
        self._node_id = node_id
        self._summary = ClientSummary()

    # ------------------------------------------------------------------ #
    def _conectar(self) -> Optional[LineChannel]:
        """Intenta conectar + handshake con backoff. None si se agota."""
        backoff = 1.0
        intentos = 0
        while True:
            try:
                sock = socket.create_connection(
                    (self._cfg.host, self._cfg.port),
                    timeout=self._cfg.connect_timeout_s)
                channel = LineChannel(sock)
                channel.send(WireEnvelope(
                    type=WireType.HELLO,
                    payload={"node_id": self._node_id,
                             "modes_supported": ["advisory", "tsc_emulated",
                                                 "automated_direct_lab"]}))
                ack = channel.recv(timeout_s=10.0)
                if ack.type is not WireType.HELLO_ACK:
                    raise ChannelClosed(f"se esperaba hello_ack: {ack.type}")
                logger.info("conectado al gateway (experiment=%s, seed=%s)",
                            ack.experiment_id, ack.payload.get("seed"))
                return channel
            except (OSError, ChannelClosed, WireDecodeError) as e:
                intentos += 1
                if intentos > 30:
                    logger.error("reconexión agotada tras %d intentos", intentos)
                    return None
                logger.warning("conexión falló (%s); reintento en %.0fs",
                               e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, self._cfg.reconnect_max_s)

    # ------------------------------------------------------------------ #
    def run(self) -> ClientSummary:
        channel = self._conectar()
        while channel is not None:
            try:
                self._servir(channel)
                break                       # bye limpio
            except ChannelClosed:
                # Pérdida HIL (spec §26-B): plan seguro local + reintento
                self._node.authority.tsc.enter_safe_mode("perdida_enlace_hil")
                self._node._emit(evento(
                    "hil_disconnect", self._node_id, WARNING))
                self._summary.reconexiones += 1
                channel = self._conectar()
        return self._summary

    def _servir(self, channel: LineChannel) -> None:
        while True:
            try:
                env = channel.recv(timeout_s=self._cfg.read_timeout_s)
            except socket.timeout:
                # El gateway marca el ritmo; un silencio largo se sondea
                channel.send(WireEnvelope(type=WireType.HEARTBEAT))
                continue
            except WireDecodeError as e:
                self._summary.errores_protocolo += 1
                logger.error("mensaje malformado del gateway: %s", e)
                continue

            if env.type is WireType.BYE:
                logger.info("gateway cerró la sesión: %s", env.payload)
                self._summary.terminado_por_bye = True
                return
            if env.type in (WireType.HEARTBEAT_ACK, WireType.TICK,
                            WireType.ERROR):
                if env.type is WireType.ERROR:
                    self._summary.errores_protocolo += 1
                    logger.warning("error del gateway: %s", env.payload)
                continue
            if env.type is WireType.HEARTBEAT:
                channel.send(WireEnvelope(type=WireType.HEARTBEAT_ACK))
                continue
            if env.type is not WireType.STATE:
                logger.warning("tipo inesperado %s; descartado", env.type)
                continue

            try:
                state = TrafficState.model_validate(env.payload)
            except Exception as e:
                # NaN/inf/esquema roto mueren AQUÍ, en la frontera (D-G)
                self._summary.errores_protocolo += 1
                logger.error("TrafficState inválido (seq=%s): %s", env.seq, e)
                continue

            _rec, decision = self._node.process_one(
                state, edad_s=edad_segundos(env))
            self._summary.estados += 1
            channel.send(WireEnvelope(
                type=WireType.DECISION,
                experiment_id=state.experiment_id,
                seq=state.seq,
                payload=decision.model_dump(mode="json")))
