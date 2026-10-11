"""Cliente HIL del nodo edge: conecta al gateway, procesa states, responde
decisiones. Reconexión con backoff exponencial; ante pérdida del enlace el
TSC local entra en modo seguro (spec §26-B) y se reintenta.
"""
from __future__ import annotations

import logging
import math
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
        self._experiment_id: Optional[str] = None

    # ------------------------------------------------------------------ #
    def _conectar(self) -> Optional[LineChannel]:
        """Intenta conectar + handshake con backoff. None si se agota."""
        backoff = 1.0
        intentos = 0
        while True:
            sock: Optional[socket.socket] = None
            channel: Optional[LineChannel] = None
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
                if not ack.experiment_id:
                    raise WireDecodeError("hello_ack sin experiment_id")
                self._experiment_id = ack.experiment_id
                logger.info("conectado al gateway (experiment=%s, seed=%s)",
                            ack.experiment_id, ack.payload.get("seed"))
                return channel
            except (OSError, ChannelClosed, WireDecodeError) as e:
                # Un handshake fallido también debe liberar el descriptor. En
                # reconexiones repetidas, omitir este cierre agota los sockets.
                if channel is not None:
                    channel.close()
                elif sock is not None:
                    sock.close()
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
            finally:
                # Cierra tanto tras BYE como tras caída o excepción inesperada.
                # La siguiente conexión, si aplica, se crea después del cierre.
                channel.close()
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
            if env.type is WireType.TICK:
                try:
                    sim_time = float(env.payload["sim_time_s"])
                    if (env.experiment_id != self._experiment_id
                            or not math.isfinite(sim_time) or sim_time < 0):
                        raise ValueError("experimento o sim_time inválido")
                    self._node.process_tick(sim_time)
                except (KeyError, TypeError, ValueError) as e:
                    self._summary.errores_protocolo += 1
                    logger.error("tick HIL inválido: %s", e)
                continue
            if env.type in (WireType.HEARTBEAT_ACK, WireType.ERROR):
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
            if (env.experiment_id != self._experiment_id
                    or env.experiment_id != state.experiment_id
                    or env.seq != state.seq):
                self._summary.errores_protocolo += 1
                logger.error(
                    "state HIL inconsistente: envelope=(exp=%r, seq=%r), "
                    "payload=(exp=%r, seq=%r)",
                    env.experiment_id, env.seq,
                    state.experiment_id, state.seq)
                continue

            _rec, decision = self._node.process_one(
                state, edad_s=edad_segundos(env))
            self._summary.estados += 1
            channel.send(WireEnvelope(
                type=WireType.DECISION,
                experiment_id=state.experiment_id,
                seq=state.seq,
                payload=decision.model_dump(mode="json")))
