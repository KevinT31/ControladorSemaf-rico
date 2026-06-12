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

        # Construir métricas por intersección con ICV clamped [0.40, 0.60]
        inter_out = []
        try:
            # Intentar usar núcleo para cálculo ICV si hay métricas
            from pathlib import Path as _Path
            import sys as _Sys
            _Sys.path.insert(0, str(_Path(__file__).parent.parent.parent))
            from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion
            calc = CalculadorICV(ParametrosInterseccion())
        except Exception:
            calc = None

        for idx, (iid, info) in enumerate(estado_sistema.intersecciones.items()):
            # Tomar métricas si existen; sino, usar valores mínimos
            flujo = float(info.get('flujo', 0.0))
            velocidad = float(info.get('velocidad', 0.0))
            cola_m = float(info.get('cola_m', 0.0))

            icv_val = 0.0
            clas = 'Fluido'
            if calc:
                try:
                    res = calc.calcular(longitud_cola=cola_m, velocidad_promedio=velocidad, flujo_vehicular=flujo)
                    icv_val = float(res.get('icv', 0.0))
                    clas = res.get('clasificacion', 'Fluido')
                except Exception:
                    icv_val = 0.0
                    clas = 'Fluido'

            # Jitter leve por intersección para diversidad
            jitter = ((idx % 7) - 3) * 0.005
            icv_val = icv_val * (1.0 + jitter)
            # Clamp estricto solicitado
            icv_val = max(0.50, min(0.60, icv_val)) if resumen.get('modo') == 'simulador' else icv_val

            inter_out.append({
                'interseccion_id': iid,
                'icv': round(icv_val, 3),
                'clasificacion': clas,
                'flujo': round(flujo, 1),
                'velocidad': round(velocidad, 1),
                'cola_m': round(cola_m, 1)
            })

        # Promedio de red de ICV en modo simulador
        icv_prom = 0.0
        if inter_out:
            icv_prom = sum(i['icv'] for i in inter_out) / len(inter_out)
            # Clamp también el promedio en modo simulador
            if resumen.get('modo') == 'simulador':
                icv_prom = max(0.50, min(0.60, icv_prom))

        resumen['intersecciones'] = inter_out
        resumen['icv_red_promedio'] = round(icv_prom, 3)
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
        try:
            # 1) Pausar cualquier bucle de simulación activo
            estado_sistema.simulacion_pausada = True

            # 2) Cancelar auto-step de SUMO si existe y desconectar
            try:
                if getattr(estado_sistema, 'sumo_auto_step', None):
                    try:
                        estado_sistema.sumo_auto_step.cancel()
                    finally:
                        estado_sistema.sumo_auto_step = None
                if getattr(estado_sistema, 'conector_sumo', None):
                    try:
                        estado_sistema.conector_sumo.desconectar()
                    finally:
                        estado_sistema.conector_sumo = None
                logger.info("SUMO detenido y desconectado durante reinicio")
            except Exception as e_sumo:
                logger.warning(f"No se pudo detener SUMO al reiniciar: {e_sumo}")

            # 3) Limpiar métricas y estado global básico
            try:
                estado_sistema.estado_global_red = None
                # No cerrar conexiones WS aquí; el manager las mantiene
            except Exception:
                pass

            # 4) Forzar modo simulador y recrear simulador con el escenario solicitado
            try:
                estado_sistema.modo = 'simulador'
                # Sincronizar modo con servicios.estado_global si existe
                from .estado_global import estado_sistema as estado_global
                try:
                    estado_global.modo = 'simulador'
                except Exception:
                    pass
            except Exception:
                pass

            # 5) Re-inicializar todo el sistema (intersecciones, calculadores, simulador, grafo, etc.)
            from main import inicializar_sistema
            inicializar_sistema()

            # 6) Persistir el escenario deseado y reanudar
            try:
                estado_sistema.escenario_actual = escenario
            except Exception:
                pass
            estado_sistema.simulacion_pausada = False

            # 7) Notificar a clientes
            try:
                import asyncio as _asyncio
                # Broadcast sin bloquear (si no hay loop, omitir)
                loop = _asyncio.get_event_loop()
                if loop and not loop.is_closed():
                    loop.create_task(WebSocketManager.broadcast({
                        'tipo': 'simulacion_reiniciada',
                        'datos': {'escenario': escenario, 'modo': 'simulador'}
                    }))
            except Exception as e_ws:
                logger.warning(f"No se pudo notificar reinicio por WebSocket: {e_ws}")

            logger.info(f"✓ Backend reiniciado. Escenario activo: {escenario}")
        except Exception as e:
            logger.error(f"Error al reiniciar la simulación: {e}")
            raise

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
