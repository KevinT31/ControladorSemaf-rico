"""Bootstrap de imports para pytest.

Hace importables `nucleo` y `nsb` sin necesidad de instalar el proyecto como
paquete (la ruta del workspace contiene espacio y ñ, lo que hace frágil un
install editable en Windows). El mismo layout relativo se conserva al copiar
`nucleo/ + nsb/` a la Raspberry Pi, por lo que los imports no cambian entre
plataformas.
"""
import sys
from pathlib import Path

_RAIZ = str(Path(__file__).resolve().parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
