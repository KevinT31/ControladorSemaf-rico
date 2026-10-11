"""Limitador en memoria para intentos fallidos de autenticación."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterable


@dataclass
class _EstadoIntentos:
    fallos: Deque[float] = field(default_factory=deque)
    bloqueado_hasta: float = 0.0


class LimitadorLogin:
    """Aplica una ventana de fallos y un bloqueo temporal por clave."""

    def __init__(self, max_intentos: int, ventana_segundos: int,
                 bloqueo_segundos: int, max_claves: int = 10_000):
        if min(max_intentos, ventana_segundos, bloqueo_segundos, max_claves) < 1:
            raise ValueError("los parámetros del limitador deben ser positivos")
        self.max_intentos = int(max_intentos)
        self.ventana_segundos = int(ventana_segundos)
        self.bloqueo_segundos = int(bloqueo_segundos)
        self.max_claves = int(max_claves)
        self._estados: Dict[str, _EstadoIntentos] = {}
        self._lock = threading.RLock()

    def _recortar(self, estado: _EstadoIntentos, ahora: float) -> None:
        limite = ahora - self.ventana_segundos
        while estado.fallos and estado.fallos[0] <= limite:
            estado.fallos.popleft()
        if estado.bloqueado_hasta <= ahora:
            estado.bloqueado_hasta = 0.0

    def _depurar(self, ahora: float) -> None:
        for clave, estado in list(self._estados.items()):
            self._recortar(estado, ahora)
            if not estado.fallos and not estado.bloqueado_hasta:
                self._estados.pop(clave, None)

    def _obtener(self, clave: str, ahora: float) -> _EstadoIntentos:
        estado = self._estados.get(clave)
        if estado is not None:
            return estado
        if len(self._estados) >= self.max_claves:
            self._depurar(ahora)
        if len(self._estados) >= self.max_claves:
            # El diccionario conserva orden de inserción; retirar la entrada
            # más antigua evita crecimiento sin límite ante usuarios aleatorios.
            self._estados.pop(next(iter(self._estados)))
        estado = _EstadoIntentos()
        self._estados[clave] = estado
        return estado

    def reintento_en(self, claves: Iterable[str], ahora: float | None = None) -> int:
        """Devuelve segundos restantes de bloqueo (cero si se permite intentar)."""
        instante = time.monotonic() if ahora is None else float(ahora)
        restante = 0.0
        with self._lock:
            for clave in set(claves):
                estado = self._estados.get(clave)
                if estado is None:
                    continue
                self._recortar(estado, instante)
                restante = max(restante, estado.bloqueado_hasta - instante)
        return max(0, math.ceil(restante))

    def registrar_fallo(self, claves: Iterable[str], ahora: float | None = None) -> int:
        """Registra un fallo y devuelve el bloqueo resultante en segundos."""
        instante = time.monotonic() if ahora is None else float(ahora)
        restante = 0.0
        with self._lock:
            for clave in set(claves):
                estado = self._obtener(clave, instante)
                self._recortar(estado, instante)
                estado.fallos.append(instante)
                if len(estado.fallos) >= self.max_intentos:
                    estado.bloqueado_hasta = max(
                        estado.bloqueado_hasta, instante + self.bloqueo_segundos)
                restante = max(restante, estado.bloqueado_hasta - instante)
        return max(0, math.ceil(restante))

    def limpiar(self, claves: Iterable[str]) -> None:
        """Elimina el historial asociado a las claves indicadas."""
        with self._lock:
            for clave in set(claves):
                self._estados.pop(clave, None)

