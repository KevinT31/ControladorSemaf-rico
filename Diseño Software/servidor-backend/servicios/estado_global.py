"""
Estado Global del Sistema

Gestiona el estado compartido entre todos los componentes del sistema
"""

from typing import Dict, List, Optional, Any
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class EstadoSistema:
    """Clase para gestionar el estado global del sistema"""

    def __init__(self):
        self.modo: str = 'simulador'  # 'simulador', 'video', 'sumo'
        self.simulador: Optional[Any] = None
        self.calculador_icv: Optional[Any] = None
        self.controlador_difuso: Optional[Any] = None
        self.coordinador_olas_verdes: Optional[Any] = None
        self.procesador_video: Optional[Any] = None
        self.conector_sumo: Optional[Any] = None

        # Datos
        self.intersecciones: Dict[str, Dict] = {}
        self.olas_verdes_activas: Dict[str, Any] = {}

        # WebSocket
        self.conexiones_ws: List[WebSocket] = []

        # Contadores
        self.video_frame_count: int = 0
        self.simulacion_pausada: bool = False

        logger.info("Estado del sistema inicializado")

    def obtener_resumen(self) -> Dict:
        """Retorna un resumen del estado actual"""
        return {
            'modo': self.modo,
            'num_intersecciones': len(self.intersecciones),
            'simulador_activo': self.simulador is not None,
            'video_activo': self.procesador_video is not None,
            'sumo_activo': self.conector_sumo is not None and getattr(self.conector_sumo, 'conectado', False),
            'olas_verdes_activas': len(self.olas_verdes_activas),
            'websocket_conexiones': len(self.conexiones_ws),
            'simulacion_pausada': self.simulacion_pausada
        }

    def limpiar_modo_anterior(self):
        """Limpia recursos del modo anterior antes de cambiar"""
        if self.modo == 'sumo' and self.conector_sumo:
            try:
                self.conector_sumo.desconectar()
                self.conector_sumo = None
                logger.info("Conector SUMO desconectado")
            except Exception as e:
                logger.warning(f"Error desconectando SUMO: {e}")

        if self.modo == 'video' and self.procesador_video:
            self.procesador_video = None
            logger.info("Procesador de video desactivado")

    def cambiar_modo(self, nuevo_modo: str):
        """Cambia el modo de operación del sistema"""
        if nuevo_modo not in ['simulador', 'video', 'sumo']:
            raise ValueError(f"Modo inválido: {nuevo_modo}")

        self.limpiar_modo_anterior()
        self.modo = nuevo_modo
        logger.info(f"Modo cambiado a: {nuevo_modo}")


# Instancia global
estado_sistema = EstadoSistema()
