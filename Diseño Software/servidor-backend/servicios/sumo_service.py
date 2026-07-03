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


def _get_traci():
    """Devuelve el módulo de conexión SUMO activo (libsumo o traci), el mismo
    que usa ConectorSUMO. Necesario porque el conector puede usar libsumo
    (in-process) y un 'import traci' suelto no vería la simulación en curso."""
    import sys
    integracion_path = Path(__file__).parent.parent.parent / 'integracion-sumo'
    if str(integracion_path) not in sys.path:
        sys.path.insert(0, str(integracion_path))
    from conector_sumo import traci as _t
    return _t


def _escenarios_dir() -> Path:
    return Path(__file__).parent.parent.parent / 'integracion-sumo' / 'escenarios'


# Preferencia de escenario para el DASHBOARD. Cada entrada empareja el .sumocfg
# con SU calles.geojson (deben venir de la MISMA red para que casen los IDs).
# Orden: hora punta densa (lima-amplio) > alta demanda centro > centro normal.
_PREFERENCIA_ESCENARIOS = [
    ('lima-metropolitano', 'horapico.sumocfg'),
    ('lima-amplio', 'horapico.sumocfg'),
    ('lima-centro', 'comparacion.sumocfg'),
    ('lima-centro', 'osm.sumocfg'),
    ('lima-amplio', 'lima_amplio.sumocfg'),
]


def _config_y_geojson_preferidos():
    """Devuelve (ruta_sumocfg, ruta_calles_geojson) del primer escenario
    disponible según _PREFERENCIA_ESCENARIOS, o (None, None)."""
    base = _escenarios_dir()
    for carpeta, cfg in _PREFERENCIA_ESCENARIOS:
        ruta_cfg = base / carpeta / cfg
        ruta_geo = base / carpeta / 'calles.geojson'
        if ruta_cfg.exists() and ruta_geo.exists():
            return ruta_cfg, ruta_geo
    return None, None


class ControlAdaptativoSUMO:
    """Adaptador que ejecuta el controlador CANÓNICO del proyecto
    (ControladorDifusoIA de integracion-sumo/difuso_ia.py) sobre la MISMA
    conexión SUMO del backend (comparten conector_sumo, sea libsumo o traci).

    Se activa solo si settings.CONTROL_ADAPTATIVO != 'off'. Ante cualquier
    fallo al construirlo se loguea el error y el backend sigue SIN control
    (comportamiento actual); nunca se tumba el servidor.
    """

    def __init__(self):
        self.ctrl = None          # instancia de ControladorDifusoIA
        self.medidor = None       # ContadorCruces (flujo real por ventana)
        self.paso_actual = 0      # índice de paso pasado a ctrl.paso(i)
        self.fallo = False        # construcción fallida: no reintentar por paso
        self.modo_cfg = 'off'     # valor de CONTROL_ADAPTATIVO aplicado

    def asegurar(self):
        """Construye el controlador si la configuración lo pide y SUMO está
        conectado. Idempotente y barata cuando ya está construido o falló."""
        if self.ctrl is not None or self.fallo:
            return
        try:
            from config import settings
            modo_cfg = str(getattr(settings, 'CONTROL_ADAPTATIVO', 'off'))
        except Exception as e_cfg:
            logger.warning(f"No se pudo leer CONTROL_ADAPTATIVO: {e_cfg}")
            return
        if modo_cfg not in ('difuso_ia', 'difuso_ia_off'):
            return
        conector = getattr(estado_sistema, 'conector_sumo', None)
        if not conector or not getattr(conector, 'conectado', False):
            return
        try:
            import sys
            integracion_path = Path(__file__).parent.parent.parent / 'integracion-sumo'
            if str(integracion_path) not in sys.path:
                sys.path.insert(0, str(integracion_path))
            # difuso_ia y comparacion_sumo importan conector_sumo.traci, el
            # mismo módulo de conexión que usa el conector del backend.
            import comparacion_sumo as C
            import difuso_ia as D

            # Programa estático conocido antes de mapear fases (requisito de
            # _mapear_semaforos) y punto de partida honesto para el control.
            C._forzar_tiempo_fijo(t_verde=30.0)
            info = C._mapear_semaforos()
            medidor = C.ContadorCruces(
                [l for d in info.values() for g in d['fases_verdes'] for l in g['lanes']])
            modo_ia = 'guardia' if modo_cfg == 'difuso_ia' else 'off'
            self.ctrl = D.ControladorDifusoIA(
                info, {'modo_ia': modo_ia, 'medidor_flujo': medidor})
            self.medidor = medidor
            self.modo_cfg = modo_cfg
            self.paso_actual = 0
            logger.info(f"✓ Controlador difuso-IA canónico activo "
                        f"(CONTROL_ADAPTATIVO={modo_cfg}, modo_ia={modo_ia}, "
                        f"{len(info)} semáforos)")
        except Exception as e:
            self.fallo = True
            logger.error(f"No se pudo construir el controlador difuso-IA; "
                         f"se continúa SIN control adaptativo: {e}")

    def paso(self):
        """Llamar UNA vez tras cada simular_paso(). No hace nada sin controlador."""
        if self.ctrl is None:
            return
        try:
            if self.medidor is not None:
                self.medidor.actualizar()
            self.ctrl.paso(self.paso_actual)
            self.paso_actual += 1
        except Exception as e:
            logger.error(f"Error en paso del controlador difuso-IA: {e}")

    def reset(self):
        """Descarta el controlador (al desconectar/reconectar SUMO)."""
        self.ctrl = None
        self.medidor = None
        self.paso_actual = 0
        self.fallo = False
        self.modo_cfg = 'off'

    def estado_api(self) -> Dict:
        """Campos para /api/sumo/estado: controlador_activo y resumen_ia."""
        if self.ctrl is None:
            return {'controlador_activo': 'ninguno'}
        out = {'controlador_activo': self.modo_cfg}
        try:
            out['resumen_ia'] = self.ctrl.resumen_ia()
        except Exception as e:
            out['resumen_ia'] = {'error': str(e)}
        return out


# Singleton compartido por main.py (bucle auto-step) y este servicio (polls)
control_adaptativo = ControlAdaptativoSUMO()


class SumoService:
    """Servicio para operaciones con SUMO"""

    @staticmethod
    def obtener_calles_geojson() -> Dict:
        """Obtiene el GeoJSON de calles del escenario preferido (el mismo cuya
        red corre en SUMO), para que la geometría case con la congestión."""
        _, ruta_geojson = _config_y_geojson_preferidos()
        if not ruta_geojson or not ruta_geojson.exists():
            raise FileNotFoundError("Archivo calles.geojson no encontrado")

        with open(ruta_geojson, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Pasos de simulación a avanzar por cada poll del dashboard. El frontend
    # consulta /api/sumo/trafico cada ~2s, así la simulación corre ~6x tiempo real.
    PASOS_POR_POLL = 8

    @staticmethod
    def obtener_estado_trafico() -> Dict:
        """Obtiene el estado actual del tráfico en SUMO, AVANZANDO la simulación.

        Cada llamada (poll del dashboard) hace avanzar SUMO unos pasos para que
        el tráfico evolucione y los colores reflejen congestión real cambiante.
        """
        if estado_sistema.modo != 'sumo':
            # Sin datos medidos: payload placeholder, no proviene de SUMO
            return {'calles': [], 'mensaje': 'Modo SUMO no activo',
                    'origen_datos': 'estimado'}

        conector = estado_sistema.conector_sumo
        if not conector or not getattr(conector, 'conectado', False):
            return {'calles': [], 'mensaje': 'SUMO no conectado',
                    'origen_datos': 'estimado'}

        try:
            # Controlador adaptativo canónico (opcional, CONTROL_ADAPTATIVO)
            control_adaptativo.asegurar()
            # Avanzar la simulación (libsumo es in-process; este endpoint es
            # async -> corre en el hilo del event loop, sin condición de carrera).
            for _ in range(SumoService.PASOS_POR_POLL):
                if not conector.simular_paso():
                    break
                control_adaptativo.paso()

            estados = conector.obtener_estado_calles(limite=2000)
            activas = [e for e in estados if e.get('vehiculos', 0) > 0]
            icv_prom = (sum(e.get('congestion', 0) for e in activas) / len(activas)) if activas else 0.0

            # Calibración automática hacia el tráfico real de HERE (ajusta la
            # demanda de SUMO para acercar la congestión simulada a la real).
            try:
                from .calibracion_service import calibrar
                calibrar(_get_traci())
            except Exception as e_cal:
                logger.debug(f"Calibración omitida: {e_cal}")

            return {
                'calles': estados,
                'fuente': 'sumo_real',
                'origen_datos': 'sumo',  # medición real de la simulación SUMO
                'calles_con_trafico': len(activas),
                'icv_red_promedio': round(icv_prom, 3),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo tráfico SUMO: {e}")
            return {'calles': [], 'error': str(e), 'origen_datos': 'estimado'}

    @staticmethod
    def conectar(ruta_config: str, usar_gui: bool = False):
        """Conecta al simulador SUMO"""
        import sys
        integracion_path = Path(__file__).parent.parent.parent / 'integracion-sumo'
        sys.path.insert(0, str(integracion_path))

        from conector_sumo import ConectorSUMO

        # Conexión nueva: descartar cualquier controlador de la anterior
        control_adaptativo.reset()
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
            control_adaptativo.reset()
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
            # Obtener métricas reales desde la simulación activa (libsumo/traci)
            traci = _get_traci()
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

                        ruta_cfg, _ = _config_y_geojson_preferidos()

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
                    traci = _get_traci()
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
                        traci = _get_traci()
                        ids_semaforos = traci.trafficlight.getIDList()
                        for idx, sid in enumerate(ids_semaforos):
                            try:
                                m = con.obtener_metricas_interseccion(sid)
                                res = calculador_icv.calcular(
                                    longitud_cola=m.get('longitud_cola', 0.0),
                                    velocidad_promedio=m.get('velocidad_promedio', 0.0),
                                    flujo_vehicular=m.get('flujo_vehicular', 0.0)
                                )
                                # ICV REAL calculado por el núcleo (sin clamp ni jitter)
                                icv_val = float(res.get('icv', 0.0))

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

                respuesta = {
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
                    'fuente': 'sumo_real',
                    'origen_datos': 'sumo'  # medición real de la simulación SUMO
                }
                # Estado del controlador adaptativo canónico (si está activo)
                respuesta.update(control_adaptativo.estado_api())
                return respuesta

            # No conectado: razón
            razon = 'desconocida'
            if getattr(estado_sistema, 'modo', None) != 'sumo':
                razon = 'modo_no_sumo'
            elif not conector:
                razon = 'conector_nulo'
            elif not getattr(conector, 'conectado', False):
                try:
                    _get_traci()  # noqa: F841
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
                'intersecciones': intersecciones_verdes,
                # Placeholder (todo en 0/verde), no es medición de SUMO
                'origen_datos': 'estimado',
                'controlador_activo': 'ninguno'
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado SUMO: {e}")
            return {'conectado': False, 'error': str(e),
                    'origen_datos': 'estimado', 'controlador_activo': 'ninguno'}

    @staticmethod
    def inicializar_modo_sumo():
        """Inicializa el modo SUMO automáticamente"""
        try:
            ruta_config, _ = _config_y_geojson_preferidos()

            if ruta_config and ruta_config.exists():
                SumoService.conectar(str(ruta_config), usar_gui=False)
                logger.info(f"Modo SUMO inicializado: {ruta_config.parent.name}/{ruta_config.name}")
            else:
                logger.warning("Archivo de configuración SUMO no encontrado")
        except ImportError:
            logger.warning("SUMO/TraCI no disponible")
        except Exception as e:
            logger.error(f"Error inicializando SUMO: {e}")
