"""
Servicio para Integración con SUMO
"""

from typing import Dict, List
import logging
import json
from pathlib import Path
from datetime import datetime

from .estado_global import estado_sistema

logger = logging.getLogger(__name__)


class SumoService:
    """Servicio para operaciones con SUMO"""

    @staticmethod
    def obtener_calles_geojson() -> Dict:
        """Obtiene el GeoJSON de las calles SUMO"""
        ruta_geojson = Path(__file__).parent.parent.parent / 'integracion-sumo' / 'escenarios' / 'lima-centro' / 'calles.geojson'

        if not ruta_geojson.exists():
            raise FileNotFoundError("Archivo calles.geojson no encontrado")

        with open(ruta_geojson, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def obtener_estado_trafico() -> Dict:
        """Obtiene el estado actual del tráfico en SUMO"""
        if estado_sistema.modo != 'sumo':
            return {'calles': [], 'mensaje': 'Modo SUMO no activo'}

        conector = estado_sistema.conector_sumo
        if not conector or not getattr(conector, 'conectado', False):
            return {'calles': [], 'mensaje': 'SUMO no conectado'}

        try:
            estados = conector.obtener_estado_calles(limite=500)
            return {
                'calles': estados,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo tráfico SUMO: {e}")
            return {'calles': [], 'error': str(e)}

    @staticmethod
    def conectar(ruta_config: str, usar_gui: bool = False):
        """Conecta al simulador SUMO"""
        import sys
        integracion_path = Path(__file__).parent.parent.parent / 'integracion-sumo'
        sys.path.insert(0, str(integracion_path))

        from conector_sumo import ConectorSUMO

        estado_sistema.conector_sumo = ConectorSUMO(
            ruta_config_sumo=ruta_config,
            usar_gui=usar_gui
        )
        estado_sistema.conector_sumo.conectar()
        logger.info("SUMO conectado correctamente")

    @staticmethod
    def desconectar():
        """Desconecta del simulador SUMO"""
        if estado_sistema.conector_sumo:
            estado_sistema.conector_sumo.desconectar()
            estado_sistema.conector_sumo = None
            logger.info("SUMO desconectado")

    @staticmethod
    def exportar_historico(formato: str = "csv") -> str:
        """
        Exporta datos históricos de SUMO a CSV o Parquet
        """
        conector = estado_sistema.conector_sumo

        if not conector or not getattr(conector, 'conectado', False):
            logger.warning("SUMO no conectado, no se puede exportar")
            return ""

        ruta_base = Path(__file__).parent.parent.parent / 'datos' / 'resultados-sumo'
        ruta_base.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f"simulacion_{timestamp}.{formato}"
        ruta_completa = ruta_base / nombre_archivo

        try:
            # Obtener datos del conector
            estados_calles = conector.obtener_estado_calles(limite=1000)

            if formato == "csv":
                import csv
                with open(ruta_completa, 'w', newline='') as f:
                    if estados_calles:
                        writer = csv.DictWriter(f, fieldnames=estados_calles[0].keys())
                        writer.writeheader()
                        writer.writerows(estados_calles)
            elif formato == "json":
                import json
                with open(ruta_completa, 'w') as f:
                    json.dump(estados_calles, f, indent=2)

            logger.info(f"Exportación SUMO guardada en: {ruta_completa}")
            return str(ruta_completa)

        except Exception as e:
            logger.error(f"Error exportando datos SUMO: {e}")
            return ""

    @staticmethod
    def obtener_metricas() -> Dict:
        """Obtiene métricas agregadas de SUMO"""
        conector = estado_sistema.conector_sumo

        if not conector or not getattr(conector, 'conectado', False):
            return {
                'timestamp': datetime.now().isoformat(),
                'total_vehiculos': 0,
                'velocidad_promedio_red': 0.0,
                'tiempo_viaje_promedio': 0.0,
                'conectado': False
            }

        try:
            # Obtener métricas reales desde TraCI
            import traci
            vehiculos = traci.vehicle.getIDList()
            total_vehiculos = len(vehiculos)

            velocidades = [traci.vehicle.getSpeed(v) * 3.6 for v in vehiculos]  # m/s -> km/h
            velocidad_promedio = sum(velocidades) / len(velocidades) if velocidades else 0.0

            return {
                'timestamp': datetime.now().isoformat(),
                'total_vehiculos': total_vehiculos,
                'velocidad_promedio_red': velocidad_promedio,
                'tiempo_viaje_promedio': 0.0,  # Requiere tracking más complejo
                'conectado': True
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas SUMO: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'total_vehiculos': 0,
                'velocidad_promedio_red': 0.0,
                'tiempo_viaje_promedio': 0.0,
                'conectado': False,
                'error': str(e)
            }

    @staticmethod
    def obtener_estado() -> Dict:
        """Obtiene el estado de la conexión SUMO"""
        if estado_sistema.conector_sumo:
            return {
                'conectado': getattr(estado_sistema.conector_sumo, 'conectado', False),
                'modo_gui': False
            }
        return {'conectado': False}

    @staticmethod
    def inicializar_modo_sumo():
        """Inicializa el modo SUMO automáticamente"""
        try:
            ruta_config = Path(__file__).parent.parent.parent / 'integracion-sumo' / 'escenarios' / 'lima-centro' / 'osm.sumocfg'

            if ruta_config.exists():
                SumoService.conectar(str(ruta_config), usar_gui=False)
                logger.info("Modo SUMO inicializado correctamente")
            else:
                logger.warning("Archivo de configuración SUMO no encontrado")
        except ImportError:
            logger.warning("SUMO/TraCI no disponible")
        except Exception as e:
            logger.error(f"Error inicializando SUMO: {e}")
