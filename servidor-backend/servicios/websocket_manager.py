"""
Gestor de Conexiones WebSocket
"""

from fastapi import WebSocket
from typing import Dict, List, Set, Any
import logging
import uuid

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Gestor centralizado de conexiones WebSocket"""

    _conexiones: Dict[str, WebSocket] = {}
    _suscripciones: Dict[str, Set[str]] = {}  # conexion_id -> set de interseccion_ids

    @classmethod
    def agregar_conexion(cls, websocket: WebSocket) -> str:
        """
        Agrega una nueva conexión WebSocket

        Args:
            websocket: Objeto WebSocket de FastAPI

        Returns:
            ID único de la conexión
        """
        conexion_id = str(uuid.uuid4())
        cls._conexiones[conexion_id] = websocket
        cls._suscripciones[conexion_id] = set()
        logger.info(f"Conexión WebSocket agregada: {conexion_id}")
        return conexion_id

    @classmethod
    def remover_conexion(cls, conexion_id: str):
        """Remueve una conexión WebSocket"""
        if conexion_id in cls._conexiones:
            del cls._conexiones[conexion_id]
            if conexion_id in cls._suscripciones:
                del cls._suscripciones[conexion_id]
            logger.info(f"Conexión WebSocket removida: {conexion_id}")

    @classmethod
    def suscribir_interseccion(cls, conexion_id: str, interseccion_id: str):
        """Suscribe una conexión a actualizaciones de una intersección"""
        if conexion_id in cls._suscripciones:
            cls._suscripciones[conexion_id].add(interseccion_id)
            logger.debug(f"Conexión {conexion_id} suscrita a {interseccion_id}")

    @classmethod
    def desuscribir_interseccion(cls, conexion_id: str, interseccion_id: str):
        """Desuscribe una conexión de una intersección"""
        if conexion_id in cls._suscripciones:
            cls._suscripciones[conexion_id].discard(interseccion_id)
            logger.debug(f"Conexión {conexion_id} desuscrita de {interseccion_id}")

    @classmethod
    async def broadcast(cls, mensaje: Dict[str, Any]):
        """
        Envía un mensaje a todas las conexiones activas

        Args:
            mensaje: Diccionario con el mensaje a enviar
        """
        conexiones_cerradas = []

        for conexion_id, websocket in cls._conexiones.items():
            try:
                await websocket.send_json(mensaje)
            except Exception as e:
                logger.warning(f"Error enviando mensaje a {conexion_id}: {e}")
                conexiones_cerradas.append(conexion_id)

        # Limpiar conexiones cerradas
        for conexion_id in conexiones_cerradas:
            cls.remover_conexion(conexion_id)

    @classmethod
    async def enviar_a_suscriptores(cls, interseccion_id: str, mensaje: Dict[str, Any]):
        """
        Envía un mensaje solo a conexiones suscritas a una intersección específica

        Args:
            interseccion_id: ID de la intersección
            mensaje: Diccionario con el mensaje
        """
        conexiones_cerradas = []

        for conexion_id, websocket in cls._conexiones.items():
            # Verificar si está suscrito a esta intersección
            if interseccion_id in cls._suscripciones.get(conexion_id, set()):
                try:
                    await websocket.send_json(mensaje)
                except Exception as e:
                    logger.warning(f"Error enviando a {conexion_id}: {e}")
                    conexiones_cerradas.append(conexion_id)

        # Limpiar
        for conexion_id in conexiones_cerradas:
            cls.remover_conexion(conexion_id)

    @classmethod
    def total_conexiones(cls) -> int:
        """Retorna el número total de conexiones activas"""
        return len(cls._conexiones)

    @classmethod
    def obtener_suscripciones(cls, conexion_id: str) -> Set[str]:
        """Obtiene las suscripciones de una conexión"""
        return cls._suscripciones.get(conexion_id, set())

    @classmethod
    def limpiar_todas(cls):
        """Limpia todas las conexiones (útil para shutdown)"""
        cls._conexiones.clear()
        cls._suscripciones.clear()
        logger.info("Todas las conexiones WebSocket limpiadas")
