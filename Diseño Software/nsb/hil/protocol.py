"""Canal de línea JSON sobre sockets síncronos (D-03) + handshake HIL.

Secuencia (spec §14):

    nodo → hello      {node_id, modes_supported, resume?}
    gw   → hello_ack  {experiment_id, control_interval_s, seed,
                       scenario_digest, next_seq}
    gw   → state      {TrafficState}          (por punto de control)
    nodo → decision   {DecisionEnvelope}
    ...
    gw   → bye        {resumen}

Errores de protocolo se reportan con type=error y cierran la sesión.
"""
from __future__ import annotations

import socket
from typing import Optional

from nsb.domain.wire import (
    MAX_LINE_BYTES,
    WireDecodeError,
    WireEnvelope,
    decode,
    encode,
)


class ChannelClosed(ConnectionError):
    """El otro extremo cerró la conexión."""


class LineChannel:
    """Framing de líneas JSON sobre un socket TCP (bloqueante con timeout)."""

    def __init__(self, sock: socket.socket):
        self._sock = sock
        self._buffer = b""
        # Latencia primero: los mensajes son pequeños y uno-por-uno
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def send(self, env: WireEnvelope) -> None:
        try:
            self._sock.sendall(encode(env))
        except OSError as e:
            raise ChannelClosed(f"envío falló: {e}") from e

    def recv(self, timeout_s: Optional[float]) -> WireEnvelope:
        """Lee una línea completa. Lanza:
        - socket.timeout si no llega línea completa en el plazo;
        - ChannelClosed si el peer cerró;
        - WireDecodeError si la línea es basura (el llamador decide).
        """
        self._sock.settimeout(timeout_s)
        while b"\n" not in self._buffer:
            if len(self._buffer) > MAX_LINE_BYTES:
                raise WireDecodeError("línea sin terminar excede el máximo")
            try:
                chunk = self._sock.recv(65536)
            except socket.timeout:
                raise
            except OSError as e:
                raise ChannelClosed(f"recepción falló: {e}") from e
            if not chunk:
                raise ChannelClosed("conexión cerrada por el peer")
            self._buffer += chunk
        linea, self._buffer = self._buffer.split(b"\n", 1)
        return decode(linea)

    def close(self) -> None:
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._sock.close()
