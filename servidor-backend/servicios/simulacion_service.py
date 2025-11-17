"""
Servicio para control del Simulador de Tráfico
"""

from typing import Dict
import logging
from .estado_global import estado_sistema
from .websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class SimulacionService:
    """Servicio para operaciones del simulador"""

    @staticmethod
    def obtener_estado() -> Dict:
        """Retorna el estado actual del sistema"""
        resumen = estado_sistema.obtener_resumen()
        resumen['intersecciones'] = list(estado_sistema.intersecciones.values())
        return resumen

    @staticmethod
    async def cambiar_modo(nuevo_modo: str):
        """Cambia el modo de operación"""
        estado_sistema.cambiar_modo(nuevo_modo)

        # Inicializar modo SUMO si es necesario
        if nuevo_modo == 'sumo':
            from .sumo_service import SumoService
            SumoService.inicializar_modo_sumo()

        await WebSocketManager.broadcast({
            'tipo': 'modo_cambiado',
            'datos': {'modo': nuevo_modo}
        })

    @staticmethod
    def pausar():
        """Pausa la simulación"""
        estado_sistema.simulacion_pausada = True
        logger.info("Simulación pausada")

    @staticmethod
    def reanudar():
        """Reanuda la simulación"""
        estado_sistema.simulacion_pausada = False
        logger.info("Simulación reanudada")

    @staticmethod
    def reiniciar(escenario: str = "hora_pico_manana"):
        """Reinicia la simulación con un nuevo escenario"""
        if estado_sistema.simulador:
            # Reinicializar simulador con nuevo escenario
            from main import inicializar_sistema
            inicializar_sistema()
            logger.info(f"Simulación reiniciada con escenario: {escenario}")

    @staticmethod
    def obtener_parametros() -> Dict:
        """Obtiene parámetros de la simulación"""
        escenario = getattr(estado_sistema, 'escenario_actual', 'hora_pico_manana')
        return {
            'modo': estado_sistema.modo,
            'pausada': estado_sistema.simulacion_pausada,
            'escenario': escenario
        }

    @staticmethod
    def actualizar_parametros(parametros: Dict):
        """Actualiza parámetros de la simulación dinámicamente"""
        if 'escenario' in parametros:
            estado_sistema.escenario_actual = parametros['escenario']
            logger.info(f"Escenario cambiado a: {parametros['escenario']}")

        if 'intervalo' in parametros:
            estado_sistema.intervalo_simulacion = parametros['intervalo']
            logger.info(f"Intervalo de simulación cambiado a: {parametros['intervalo']}")

        logger.info(f"Parámetros actualizados correctamente: {parametros}")
