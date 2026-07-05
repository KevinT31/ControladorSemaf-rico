"""Inserción idempotente del directorio padre de `nsb/` en sys.path.

Permite ejecutar `python -m nsb ...` o los entry points desde cualquier
directorio de trabajo, tanto en Windows (desarrollo) como en la Raspberry Pi
(despliegue por copia), sin instalar el proyecto como paquete.

`nucleo/` vive junto a `nsb/` en ambos entornos, así que basta con exponer
el padre común.
"""
import sys
from pathlib import Path


def ensure_path() -> None:
    """Garantiza que `nucleo` y `nsb` sean importables. Idempotente."""
    raiz = str(Path(__file__).resolve().parent.parent)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)


ensure_path()
