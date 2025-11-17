"""
Servicio para gestión de Vehículos de Emergencia y Olas Verdes
"""

from typing import List, Dict
from datetime import datetime
import logging

from modelos.emergencia import VehiculoEmergenciaRequest, OlaVerdeResponse
from .estado_global import estado_sistema
from .websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class EmergenciaService:
    """Servicio para operaciones de emergencia y olas verdes"""

    @staticmethod
    async def activar_ola_verde(request: VehiculoEmergenciaRequest) -> OlaVerdeResponse:
        """
        Activa una ola verde para un vehículo de emergencia

        Args:
            request: Datos del vehículo y ruta

        Returns:
            OlaVerdeResponse con la ruta calculada

        Raises:
            ValueError: Si las intersecciones no existen o no hay ruta
        """
        coordinador = estado_sistema.coordinador_olas_verdes

        if not coordinador:
            raise ValueError("Coordinador de olas verdes no inicializado")

        # Verificar que origen y destino existan
        from .interseccion_service import InterseccionService

        if not InterseccionService.existe(request.origen):
            raise ValueError(f"Intersección origen {request.origen} no encontrada")

        if not InterseccionService.existe(request.destino):
            raise ValueError(f"Intersección destino {request.destino} no encontrada")

        # Crear vehículo de emergencia
        # Importar la clase del módulo olas_verdes_dinamicas
        import sys
        from pathlib import Path
        nucleo_path = Path(__file__).parent.parent.parent / 'nucleo'
        sys.path.insert(0, str(nucleo_path))

        from olas_verdes_dinamicas import VehiculoEmergencia

        vehiculo_id = f"EMG-{datetime.now().strftime('%H%M%S')}"
        vehiculo = VehiculoEmergencia(
            id=vehiculo_id,
            tipo=request.tipo.value,
            interseccion_actual=request.origen,
            destino=request.destino,
            velocidad_estimada=request.velocidad,
            timestamp=datetime.now()
        )

        # Activar ola verde
        resultado = coordinador.activar_ola_verde(vehiculo)

        # Guardar en estado global
        estado_sistema.olas_verdes_activas[vehiculo_id] = {
            'vehiculo': vehiculo,
            'resultado': resultado,
            'timestamp_activacion': datetime.now()
        }

        # Notificar por WebSocket
        await WebSocketManager.broadcast({
            'tipo': 'ola_verde_activada',
            'datos': resultado
        })

        logger.info(f"Ola verde activada: {vehiculo_id} de {request.origen} a {request.destino}")

        # Construir respuesta
        from modelos.emergencia import VehiculoEmergenciaResponse

        vehiculo_response = VehiculoEmergenciaResponse(
            id=vehiculo.id,
            tipo=request.tipo,
            interseccion_actual=vehiculo.interseccion_actual,
            destino=vehiculo.destino,
            velocidad_estimada=vehiculo.velocidad_estimada,
            prioridad=request.prioridad.value if request.prioridad else "alta",
            timestamp=vehiculo.timestamp
        )

        return OlaVerdeResponse(
            vehiculo=vehiculo_response,
            ruta=resultado.get('ruta', []),
            distancia_total=resultado.get('distancia_total', 0),
            tiempo_estimado=resultado.get('tiempo_estimado', 0),
            semaforos_sincronizados=len(resultado.get('ruta', [])),
            mensaje="Ola verde activada correctamente",
            timestamp_activacion=datetime.now()
        )

    @staticmethod
    def desactivar_ola_verde(vehiculo_id: str):
        """Desactiva una ola verde activa"""
        if vehiculo_id not in estado_sistema.olas_verdes_activas:
            raise ValueError(f"Ola verde {vehiculo_id} no encontrada o ya desactivada")

        del estado_sistema.olas_verdes_activas[vehiculo_id]
        logger.info(f"Ola verde desactivada: {vehiculo_id}")

    @staticmethod
    def obtener_activas() -> List[Dict]:
        """Retorna todas las olas verdes actualmente activas"""
        return [
            {
                'vehiculo_id': vehiculo_id,
                'tipo': data['vehiculo'].tipo,
                'origen': data['vehiculo'].interseccion_actual,
                'destino': data['vehiculo'].destino,
                'ruta': data['resultado'].get('ruta', []),
                'timestamp_activacion': data['timestamp_activacion'].isoformat()
            }
            for vehiculo_id, data in estado_sistema.olas_verdes_activas.items()
        ]

    @staticmethod
    def obtener_historial(limite: int = 50) -> List[Dict]:
        """
        Obtiene historial de olas verdes desde la base de datos
        """
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from modelos_bd import SessionLocal, OlaVerde

        db = SessionLocal()
        try:
            olas = db.query(OlaVerde).order_by(
                OlaVerde.timestamp_activacion.desc()
            ).limit(limite).all()

            return [
                {
                    'vehiculo_id': ola.vehiculo_id,
                    'tipo': ola.tipo_vehiculo,
                    'origen': ola.interseccion_origen_id,
                    'destino': ola.interseccion_destino_id,
                    'ruta': ola.ruta_json,
                    'distancia_total': ola.distancia_total_metros,
                    'tiempo_estimado': ola.tiempo_estimado_segundos,
                    'activo': ola.activo,
                    'completado': ola.completado,
                    'timestamp_activacion': ola.timestamp_activacion.isoformat(),
                    'timestamp_finalizacion': ola.timestamp_finalizacion.isoformat() if ola.timestamp_finalizacion else None
                }
                for ola in olas
            ]
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            # Fallback a las activas
            return EmergenciaService.obtener_activas()[:limite]
        finally:
            db.close()

    @staticmethod
    def calcular_estadisticas() -> Dict:
        """
        Calcula estadísticas generales sobre olas verdes desde la BD
        """
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from modelos_bd import SessionLocal, OlaVerde
        from sqlalchemy import func

        db = SessionLocal()
        try:
            # Estadísticas de la BD
            total_historico = db.query(func.count(OlaVerde.id)).scalar()
            total_activas_bd = db.query(func.count(OlaVerde.id)).filter(
                OlaVerde.activo == True
            ).scalar()
            total_completadas = db.query(func.count(OlaVerde.id)).filter(
                OlaVerde.completado == True
            ).scalar()

            # Por tipo
            tipos_query = db.query(
                OlaVerde.tipo_vehiculo,
                func.count(OlaVerde.id)
            ).group_by(OlaVerde.tipo_vehiculo).all()

            tipos_dict = {tipo: count for tipo, count in tipos_query}

            # Tiempo promedio (solo completadas)
            tiempo_promedio = db.query(
                func.avg(OlaVerde.tiempo_total_segundos)
            ).filter(OlaVerde.completado == True).scalar() or 0

            return {
                'total_historico': total_historico,
                'total_activas': total_activas_bd,
                'total_completadas': total_completadas,
                'tiempo_promedio_segundos': float(tiempo_promedio),
                'tipos': {
                    'ambulancia': tipos_dict.get('ambulancia', 0),
                    'bomberos': tipos_dict.get('bomberos', 0),
                    'policia': tipos_dict.get('policia', 0)
                }
            }
        except Exception as e:
            logger.error(f"Error calculando estadísticas: {e}")
            # Fallback a memoria
            activas = estado_sistema.olas_verdes_activas
            return {
                'total_activas': len(activas),
                'tipos': {
                    'ambulancia': sum(1 for d in activas.values() if d['vehiculo'].tipo == 'ambulancia'),
                    'bomberos': sum(1 for d in activas.values() if d['vehiculo'].tipo == 'bomberos'),
                    'policia': sum(1 for d in activas.values() if d['vehiculo'].tipo == 'policia')
                }
            }
        finally:
            db.close()
