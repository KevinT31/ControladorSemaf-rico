"""Contrato de las fuentes de estado (spec §12)."""
from __future__ import annotations

from typing import Iterator, Protocol

from nsb.domain.contracts import TrafficState


class TrafficStateSource(Protocol):
    """Fuente de TrafficState: iterable finito o infinito de estados.

    El nodo consume la fuente secuencialmente; el fin de la iteración
    significa fin del experimento (no error).
    """

    def __iter__(self) -> Iterator[TrafficState]: ...

    def close(self) -> None:
        """Libera recursos (archivos, sockets, cámaras)."""
        ...
