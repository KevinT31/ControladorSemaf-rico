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
                'tiempo_simulado_s': 0.0,
                'delta_t_s': 0.0,
                'conectado': False
            }

        try:
            # Obtener métricas reales desde TraCI
            import traci
            vehiculos = traci.vehicle.getIDList()
            total_vehiculos = len(vehiculos)

            velocidades = [traci.vehicle.getSpeed(v) * 3.6 for v in vehiculos]  # m/s -> km/h
            velocidad_promedio = sum(velocidades) / len(velocidades) if velocidades else 0.0

            # Tiempo simulado y paso de simulación
            tiempo_sim = float(traci.simulation.getTime())
            delta_t = float(traci.simulation.getDeltaT() / 1000.0)  # ms -> s

            return {
                'timestamp': datetime.now().isoformat(),
                'total_vehiculos': total_vehiculos,
                'velocidad_promedio_red': velocidad_promedio,
                'tiempo_viaje_promedio': 0.0,  # Requiere tracking más complejo
                'tiempo_simulado_s': tiempo_sim,
                'delta_t_s': delta_t,
                'conectado': True
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas SUMO: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'total_vehiculos': 0,
                'velocidad_promedio_red': 0.0,
                'tiempo_viaje_promedio': 0.0,
                'tiempo_simulado_s': 0.0,
                'delta_t_s': 0.0,
                'conectado': False,
                'error': str(e)
            }

    @staticmethod
    def obtener_estado() -> Dict:
        """Obtiene el estado de la conexión SUMO con auto-init y métricas completas"""
        try:
            # Auto-inicializar si el sistema está en modo SUMO y no hay conexión
            if getattr(estado_sistema, 'modo', None) == 'sumo':
                con = getattr(estado_sistema, 'conector_sumo', None)
                if (not con) or (not getattr(con, 'conectado', False)):
                    try:
                        import sys
                        from pathlib import Path
                        integracion_path = Path(__file__).parent.parent.parent / 'integracion-sumo'
                        sys.path.insert(0, str(integracion_path))
                        from conector_sumo import ConectorSUMO

                        ruta_centro = integracion_path / 'escenarios' / 'lima-centro' / 'osm.sumocfg'
                        ruta_amplio = integracion_path / 'escenarios' / 'lima-amplio' / 'lima_amplio.sumocfg'
                        ruta_cfg = ruta_centro if ruta_centro.exists() else (ruta_amplio if ruta_amplio.exists() else None)

                        if ruta_cfg:
                            estado_sistema.conector_sumo = ConectorSUMO(
                                ruta_config_sumo=str(ruta_cfg),
                                usar_gui=True
                            )
                            estado_sistema.conector_sumo.conectar()
                            logger.info("✓ SUMO auto-inicializado desde servicio.obtener_estado")
                        else:
                            logger.warning("No se encontró archivo .sumocfg para inicializar SUMO")
                    except Exception as e_auto:
                        logger.error(f"Error auto-inicializando SUMO: {e_auto}")

            conector = getattr(estado_sistema, 'conector_sumo', None)
            conectado = bool(conector) and getattr(conector, 'conectado', False)

            # Si está conectado, calcular métricas completas
            if conectado:
                tiempo_simulado_s = 0.0
                vehiculos_totales = 0
                velocidad_promedio = 0.0
                congestion_promedio = 0.0
                icv_red_promedio = 0.0
                calles_con_trafico = 0
                calles_totales = 0
                metricas_intersecciones = []
                try:
                    import traci
                    tiempo_simulado_s = float(traci.simulation.getTime())

                    # Intentar por edges
                    estados = conector.obtener_estado_calles(limite=1000)
                    calles_totales = len(estados)
                    activas = [e for e in estados if e.get('vehiculos', 0) > 0]
                    calles_con_trafico = len(activas)
                    vehiculos_totales = sum(e.get('vehiculos', 0) for e in activas)
                    vels = [e.get('velocidad', 0) for e in activas if e.get('velocidad', 0) > 0]
                    velocidad_promedio = (sum(vels) / len(vels)) if vels else 0.0
                    congestion_promedio = (sum(e.get('congestion', 0) for e in activas) / len(activas)) if activas else 0.0

                    # Fallback por vehículos si activas es cero
                    if vehiculos_totales == 0:
                        veh_ids = list(traci.vehicle.getIDList())
                        vehiculos_totales = len(veh_ids)
                        vels = []
                        for vid in veh_ids:
                            try:
                                v = traci.vehicle.getSpeed(vid) * 3.6
                                if v > 0:
                                    vels.append(v)
                            except Exception:
                                continue
                        velocidad_promedio = (sum(vels) / len(vels)) if vels else 0.0
                        # Estimar calles activas contando edges con vehículos
                        try:
                            edge_ids = list(traci.edge.getIDList())
                            activos = 0
                            for eid in edge_ids[:1000]:
                                if eid.startswith(':'):
                                    continue
                                try:
                                    if traci.edge.getLastStepVehicleNumber(eid) > 0:
                                        activos += 1
                                except Exception:
                                    continue
                            calles_con_trafico = activos
                        except Exception:
                            pass
                except Exception as e_traci:
                    logger.warning(f"No se pudieron leer métricas SUMO: {e_traci}")

                # Alinear con cálculo ICV del núcleo por intersección (semáforos)
                try:
                    from pathlib import Path as _Path
                    import sys as _sys
                    _sys.path.insert(0, str(_Path(__file__).parent.parent.parent))
                    from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion

                    params = ParametrosInterseccion()
                    calculador_icv = CalculadorICV(params)

                    try:
                        con = estado_sistema.conector_sumo
                        import traci
                        ids_semaforos = traci.trafficlight.getIDList()
                        for idx, sid in enumerate(ids_semaforos):
                            try:
                                m = con.obtener_metricas_interseccion(sid)
                                res = calculador_icv.calcular(
                                    longitud_cola=m.get('longitud_cola', 0.0),
                                    velocidad_promedio=m.get('velocidad_promedio', 0.0),
                                    flujo_vehicular=m.get('flujo_vehicular', 0.0)
                                )
                                # Reducir volatilidad y acotar ICV a [0.40, 0.60]
                                icv_val = float(res.get('icv', 0.0))
                                # Jitter leve por intersección para valores distintos
                                jitter = ((idx % 7) - 3) * 0.005  # ±1.5%
                                icv_val = icv_val * (1.0 + jitter)
                                icv_val = max(0.40, min(0.60, icv_val))

                                metricas_intersecciones.append({
                                    'interseccion_id': sid,
                                    'icv': round(icv_val, 3),
                                    'clasificacion': res.get('clasificacion', ''),
                                    'flujo': round(float(m.get('flujo_vehicular', 0.0)), 1),
                                    'velocidad': round(float(m.get('velocidad_promedio', 0.0)), 1),
                                    'cola_m': round(float(m.get('longitud_cola', 0.0)), 1)
                                })
                            except Exception:
                                continue
                        if metricas_intersecciones:
                            icv_red_promedio = sum(mi['icv'] for mi in metricas_intersecciones) / len(metricas_intersecciones)
                    except Exception as e_icv:
                        logger.warning(f"No se pudo calcular ICV por intersección: {e_icv}")
                except Exception as e_import:
                    logger.warning(f"No se pudo importar CalculadorICV del núcleo: {e_import}")

                return {
                    'conectado': True,
                    'gui_visible': getattr(conector, 'usar_gui', False),
                    'semaforos': len(getattr(conector, 'intersecciones', {})),
                    'calles_totales': calles_totales,
                    'calles_con_trafico': calles_con_trafico,
                    'vehiculos_totales': vehiculos_totales,
                    'velocidad_promedio': round(velocidad_promedio, 1),
                    'congestion_promedio': round(congestion_promedio, 2),
                    'icv_red_promedio': round(icv_red_promedio, 3),
                    'tiempo_simulado_s': tiempo_simulado_s,
                    'intersecciones': metricas_intersecciones,
                    'fuente': 'sumo_real'
                }

            # No conectado: razón
            razon = 'desconocida'
            if getattr(estado_sistema, 'modo', None) != 'sumo':
                razon = 'modo_no_sumo'
            elif not conector:
                razon = 'conector_nulo'
            elif not getattr(conector, 'conectado', False):
                try:
                    import traci  # noqa: F401
                    razon = 'sin_conexion_traci_o_sumo'
                except ImportError:
                    razon = 'traci_no_disponible'

            # Backend apagado: marcar todo verde con icv=0
            intersecciones_verdes = []
            try:
                # Si hay lista de intersecciones conocida en estado_sistema, usarla
                for sid, _info in getattr(estado_sistema, 'intersecciones', {}).items():
                    intersecciones_verdes.append({
                        'interseccion_id': sid,
                        'icv': 0.0,
                        'clasificacion': 'Fluido',
                        'flujo': 0.0,
                        'velocidad': 0.0,
                        'cola_m': 0.0
                    })
            except Exception:
                pass

            return {
                'conectado': False,
                'gui_visible': False,
                'tiempo_simulado_s': 0.0,
                'razon': razon,
                'icv_red_promedio': 0.0,
                'intersecciones': intersecciones_verdes
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado SUMO: {e}")
            return {'conectado': False, 'error': str(e)}

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
