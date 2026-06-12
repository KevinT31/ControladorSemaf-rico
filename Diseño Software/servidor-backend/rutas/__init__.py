"""
Rutas API del sistema
"""

from .intersecciones import router as intersecciones_router
from .emergencias import router as emergencias_router
from .simulacion import router as simulacion_router
from .video import router as video_router
from .sumo import router as sumo_router
from .websocket import router as websocket_router

__all__ = [
    'intersecciones_router',
    'emergencias_router',
    'simulacion_router',
    'video_router',
    'sumo_router',
    'websocket_router'
]
