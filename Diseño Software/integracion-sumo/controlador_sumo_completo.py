# -*- coding: utf-8 -*-
"""
Controlador SUMO Completo con Sistema Adaptativo del Capítulo 6
Integración completa entre SUMO y el sistema de control adaptativo

Extrae automáticamente todas las métricas de SUMO y aplica:
- Estado Local con CamMask
- Control Difuso con 12 reglas jerárquicas
- Métricas de red agregadas
- Comparación adaptativo vs no adaptativo
"""

import sys
import math
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import logging

# Importar TraCI si está disponible
try:
    import traci
    TRACI_DISPONIBLE = True
except ImportError:
    TRACI_DISPONIBLE = False
    logging.warning("TraCI no disponible. Instalar SUMO y agregar tools al PYTHONPATH")

# Importar módulos del núcleo
sys.path.insert(0, str(Path(__file__).parent.parent))

from nucleo.estado_local import (
    EstadoLocalInterseccion,
    ParametrosInterseccion,
    VehiculoEmergencia
)
from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6
from nucleo.metricas_red import (
    MetricasInterseccion,
    MetricasRed,
    ConfiguracionInterseccion,
    AgregadorMetricasRed
)
from nucleo.sistema_comparacion import (
    SistemaComparacion,
    TipoControl,
    ParametrosControlFijo
)

logger = logging.getLogger(__name__)


@dataclass
class ConfiguracionSUMO:
    """Configuración para la integración con SUMO"""
    ruta_config: Path  # Ruta al archivo .sumocfg
    puerto: int = 8813
    usar_gui: bool = True
    paso_simulacion: float = 1.0  # segundos
    intervalo_control: int = 30  # Aplicar control cada N pasos
    modo_comparacion: bool = False  # True para comparar con tiempo fijo
    guardar_metricas: bool = True
    directorio_salida: Optional[Path] = None

    def __post_init__(self):
        self.ruta_config = Path(self.ruta_config)
        if self.directorio_salida is not None:
            self.directorio_salida = Path(self.directorio_salida)
        if not 1 <= int(self.puerto) <= 65535:
            raise ValueError("puerto debe estar entre 1 y 65535")
        if self.paso_simulacion <= 0:
            raise ValueError("paso_simulacion debe ser mayor que cero")
        if self.intervalo_control < 1:
            raise ValueError("intervalo_control debe ser al menos 1")


class ExtractorMetricasSUMO:
    """
    Extrae métricas de tráfico de SUMO y las convierte al formato
    del sistema de estado local
    """

    def __init__(self, id_interseccion: str, id_semaforo_sumo: str):
        """
        Args:
            id_interseccion: ID interno de la intersección
            id_semaforo_sumo: ID del semáforo en SUMO
        """
        self.id_interseccion = id_interseccion
        self.id_semaforo_sumo = id_semaforo_sumo

    def extraer_metricas_direccion(
        self,
        lanes_ns: List[str],
        lanes_eo: List[str]
    ) -> Tuple[Dict, Dict]:
        """
        Extrae métricas de SUMO para ambas direcciones

        Args:
            lanes_ns: IDs de los carriles Norte-Sur
            lanes_eo: IDs de los carriles Este-Oeste

        Returns:
            Tupla (metricas_ns, metricas_eo) con las métricas extraídas
        """
        metricas_ns = self._extraer_metricas_lanes(lanes_ns)
        metricas_eo = self._extraer_metricas_lanes(lanes_eo)

        return metricas_ns, metricas_eo

    def _extraer_metricas_lanes(self, lanes: List[str]) -> Dict:
        """
        Extrae métricas de un conjunto de carriles

        Returns:
            Dict con: num_vehiculos, velocidades, colas, flujo
        """
        if not TRACI_DISPONIBLE:
            return {}

        num_vehiculos_total = 0
        velocidades = []
        num_detenidos = 0
        longitud_carriles = []

        for lane in lanes:
            try:
                # Número de vehículos
                num_veh = traci.lane.getLastStepVehicleNumber(lane)
                num_vehiculos_total += num_veh

                # Velocidad promedio (m/s → km/h)
                vel_promedio = traci.lane.getLastStepMeanSpeed(lane)
                if vel_promedio > 0:
                    velocidades.append(vel_promedio * 3.6)

                # Vehículos detenidos (velocidad < 0.1 m/s)
                num_halt = traci.lane.getLastStepHaltingNumber(lane)
                num_detenidos += num_halt

                # Longitud del carril
                longitud = traci.lane.getLength(lane)
                longitud_carriles.append(longitud)

            except Exception as e:
                logger.debug(f"Error extrayendo métricas de lane {lane}: {e}")
                continue

        # Calcular promedios
        velocidad_promedio = sum(velocidades) / len(velocidades) if velocidades else 0.0
        longitud_total_lanes = sum(longitud_carriles) if longitud_carriles else 100.0

        # Calcular flujo (vehículos/minuto)
        # Estimación: vehículos actuales * (60s / paso_simulación)
        paso_sim = traci.simulation.getDeltaT()
        flujo_estimado = (num_vehiculos_total / paso_sim) * 60.0 if paso_sim > 0 else 0.0
        flujo_estimado = min(flujo_estimado, 30.0)  # Cap en flujo de saturación

        # Densidad (vehículos/metro)
        densidad = num_vehiculos_total / longitud_total_lanes if longitud_total_lanes > 0 else 0.0

        # Longitud de cola (estimación: vehículos detenidos * 7.5m)
        longitud_cola = num_detenidos * 7.5

        return {
            'num_vehiculos': num_vehiculos_total,
            'velocidad_promedio': velocidad_promedio,
            'num_detenidos': num_detenidos,
            'longitud_cola': longitud_cola,
            'flujo_vehicular': flujo_estimado,
            'densidad': densidad
        }

    def detectar_vehiculos_emergencia(self) -> List[VehiculoEmergencia]:
        """
        Detecta vehículos de emergencia en SUMO

        Returns:
            Lista de vehículos de emergencia detectados
        """
        if not TRACI_DISPONIBLE:
            return []

        vehiculos_emergencia = []

        try:
            # Obtener todos los vehículos en la simulación
            ids_vehiculos = traci.vehicle.getIDList()

            for veh_id in ids_vehiculos:
                # Verificar si es vehículo de emergencia
                # (en SUMO, típicamente tienen tipo "emergency" o similar)
                tipo_veh = traci.vehicle.getTypeID(veh_id)

                if 'emergency' in tipo_veh.lower() or 'ambulance' in tipo_veh.lower():
                    pos = traci.vehicle.getPosition(veh_id)
                    vel = traci.vehicle.getSpeed(veh_id)
                    angulo = float(traci.vehicle.getAngle(veh_id)) % 360.0
                    # En SUMO: 0°=N, 90°=E, 180°=S y 270°=O.
                    indice_direccion = int(((angulo + 45.0) % 360.0) // 90.0)
                    direccion = ("N", "E", "S", "O")[indice_direccion]
                    angulo_rad = math.radians(angulo)

                    # Crear objeto VehiculoEmergencia
                    veh_emergencia = VehiculoEmergencia(
                        # ``hash()`` cambia entre procesos; CRC32 mantiene el ID
                        # estable durante ejecuciones reproducibles.
                        id_tracking=zlib.crc32(veh_id.encode("utf-8")),
                        clase='ambulancia',  # Simplificado
                        pos_x=pos[0],
                        pos_y=pos[1],
                        vel_x=vel * math.sin(angulo_rad),
                        vel_y=vel * math.cos(angulo_rad),
                        direccion_inicial=direccion,
                        confidence=1.0
                    )
                    vehiculos_emergencia.append(veh_emergencia)

        except Exception as e:
            logger.debug(f"Error detectando vehículos de emergencia: {e}")

        return vehiculos_emergencia


class ControladorSUMOAdaptativo:
    """
    Controlador principal que integra SUMO con el sistema adaptativo
    del Capítulo 6
    """

    def __init__(self, config: ConfiguracionSUMO):
        """
        Args:
            config: Configuración de SUMO
        """
        if not TRACI_DISPONIBLE:
            raise RuntimeError(
                "TraCI no disponible. "
                "Instalar SUMO desde https://sumo.dlr.de/docs/Downloads.php"
            )

        self.config = config

        # Validar configuración
        if not config.ruta_config.exists():
            raise FileNotFoundError(f"Config SUMO no encontrada: {config.ruta_config}")

        self.conectado = False

        # Diccionario de semáforos e intersecciones
        self.semaforos_sumo: Dict[str, Dict] = {}
        self.estados_locales: Dict[str, EstadoLocalInterseccion] = {}
        self.controladores_difusos: Dict[str, ControladorDifusoCapitulo6] = {}
        self.extractores: Dict[str, ExtractorMetricasSUMO] = {}

        # Agregador de métricas de red
        self.agregador_metricas: Optional[AgregadorMetricasRed] = None

        # Sistema de comparación
        self.sistema_comparacion: Optional[SistemaComparacion] = None

        # Histórico de métricas
        self.metricas_adaptativo: List[MetricasRed] = []
        self.metricas_tiempo_fijo: List[MetricasRed] = []

        # Mapeo de lanes a direcciones (configurado después de conectar)
        self.mapeo_lanes: Dict[str, Dict[str, List[str]]] = {}

        logger.info("ControladorSUMOAdaptativo inicializado")

    def conectar(self):
        """Inicia SUMO y conecta vía TraCI"""
        comando_sumo = 'sumo-gui' if self.config.usar_gui else 'sumo'

        opciones = [
            comando_sumo,
            '-c', str(self.config.ruta_config),
            '--step-length', str(self.config.paso_simulacion),
            '--start',
            '--quit-on-end'
        ]

        try:
            traci.start(opciones, port=self.config.puerto)
            self.conectado = True
            logger.info(f"✓ Conectado a SUMO (GUI: {self.config.usar_gui})")

            # Inicializar componentes
            self._inicializar_semaforos()
            self._crear_agregador_metricas()

            if self.config.modo_comparacion:
                self._crear_sistema_comparacion()

        except Exception as e:
            logger.error(f"Error conectando a SUMO: {e}")
            raise

    def _inicializar_semaforos(self):
        """Inicializa semáforos y crea componentes del sistema"""
        ids_semaforos = traci.trafficlight.getIDList()

        logger.info(f"Semáforos detectados: {len(ids_semaforos)}")

        for id_sem in ids_semaforos:
            logger.info(f"  Inicializando semáforo: {id_sem}")

            # Obtener información del semáforo
            programa = traci.trafficlight.getProgram(id_sem)
            fase = traci.trafficlight.getPhase(id_sem)
            duracion_fase = traci.trafficlight.getPhaseDuration(id_sem)
            lanes_controlados = traci.trafficlight.getControlledLanes(id_sem)

            # Clasificar lanes por dirección (NS vs EO)
            # Simplificación: primeros 50% son NS, segundos 50% son EO
            n_lanes = len(lanes_controlados)
            lanes_ns = lanes_controlados[:n_lanes//2]
            lanes_eo = lanes_controlados[n_lanes//2:]

            self.mapeo_lanes[id_sem] = {
                'ns': lanes_ns,
                'eo': lanes_eo
            }

            # Guardar info del semáforo
            self.semaforos_sumo[id_sem] = {
                'id': id_sem,
                'programa': programa,
                'fase_actual': fase,
                'duracion_fase': duracion_fase,
                'lanes_controlados': lanes_controlados
            }

            # Crear estado local
            params = ParametrosInterseccion(SC_MAX=50.0, V_MAX=60.0)
            self.estados_locales[id_sem] = EstadoLocalInterseccion(id_sem, params)

            # Crear controlador difuso
            self.controladores_difusos[id_sem] = ControladorDifusoCapitulo6(
                T_base_NS=30.0,
                T_base_EO=30.0,
                T_ciclo=90.0
            )

            # Crear extractor de métricas
            self.extractores[id_sem] = ExtractorMetricasSUMO(
                id_interseccion=id_sem,
                id_semaforo_sumo=id_sem
            )

        logger.info(f"✓ {len(ids_semaforos)} semáforos inicializados")

    def _crear_agregador_metricas(self):
        """Crea el agregador de métricas de red"""
        configuraciones = []

        for id_sem in self.semaforos_sumo.keys():
            config = ConfiguracionInterseccion(
                id=id_sem,
                nombre=f"Intersección {id_sem}",
                peso=1.0
            )
            configuraciones.append(config)

        directorio_datos = (
            self.config.directorio_salida if self.config.guardar_metricas else None
        )
        if directorio_datos:
            directorio_datos = directorio_datos / "metricas_red"

        self.agregador_metricas = AgregadorMetricasRed(
            configuraciones=configuraciones,
            directorio_datos=directorio_datos
        )

        logger.info("✓ Agregador de métricas creado")

    def _crear_sistema_comparacion(self):
        """Crea el sistema de comparación"""
        configuraciones = []

        for id_sem in self.semaforos_sumo.keys():
            config = ConfiguracionInterseccion(
                id=id_sem,
                nombre=f"Intersección {id_sem}",
                peso=1.0
            )
            configuraciones.append(config)

        directorio_resultados = self.config.directorio_salida
        if directorio_resultados:
            directorio_resultados = directorio_resultados / "comparacion"

        self.sistema_comparacion = SistemaComparacion(
            configuraciones_intersecciones=configuraciones,
            directorio_resultados=directorio_resultados
        )

        logger.info("✓ Sistema de comparación creado")

    def ejecutar_simulacion(
        self,
        num_pasos: Optional[int] = None,
        modo_control: TipoControl = TipoControl.ADAPTATIVO
    ):
        """
        Ejecuta la simulación de SUMO con control

        Args:
            num_pasos: Número de pasos (None = hasta que termine)
            modo_control: Tipo de control a aplicar
        """
        if not self.conectado:
            raise RuntimeError("No conectado a SUMO")

        logger.info(f"🚀 Iniciando simulación (modo: {modo_control.value})")

        paso = 0
        continuar = True

        try:
            while continuar:
                # Ejecutar paso de simulación
                traci.simulationStep()
                paso += 1

                # Actualizar métricas
                self._actualizar_metricas_paso()

                # Aplicar control cada N pasos
                if paso % self.config.intervalo_control == 0:
                    if modo_control == TipoControl.ADAPTATIVO:
                        self._aplicar_control_adaptativo()
                    elif modo_control == TipoControl.TIEMPO_FIJO:
                        self._aplicar_control_tiempo_fijo()

                # Verificar si continuar
                if num_pasos and paso >= num_pasos:
                    continuar = False
                else:
                    continuar = traci.simulation.getMinExpectedNumber() > 0

                # Log de progreso
                if paso % 100 == 0:
                    metricas_actual = self.agregador_metricas.obtener_metricas_red_actual()
                    if metricas_actual:
                        logger.info(
                            f"Paso {paso}: ICV_red={metricas_actual.ICV_red:.3f}, "
                            f"Vavg_red={metricas_actual.Vavg_red:.1f} km/h"
                        )

        except traci.exceptions.FatalTraCIError:
            logger.info("Simulación terminada (cerrada externamente)")
        except KeyboardInterrupt:
            logger.info("Simulación detenida por usuario")
        finally:
            logger.info(f"✓ Simulación completada ({paso} pasos)")

        return paso

    def _actualizar_metricas_paso(self):
        """Actualiza métricas de todas las intersecciones en el paso actual"""
        timestamp = datetime.now()

        for id_sem in self.semaforos_sumo.keys():
            extractor = self.extractores[id_sem]
            estado_local = self.estados_locales[id_sem]

            # Obtener mapeo de lanes
            lanes_ns = self.mapeo_lanes[id_sem]['ns']
            lanes_eo = self.mapeo_lanes[id_sem]['eo']

            # Extraer métricas de SUMO
            metricas_ns, metricas_eo = extractor.extraer_metricas_direccion(
                lanes_ns, lanes_eo
            )

            # Detectar vehículos de emergencia
            vehiculos_emergencia = extractor.detectar_vehiculos_emergencia()

            # Actualizar estado local con vehículos de emergencia
            for veh_emerg in vehiculos_emergencia:
                estado_local.actualizar_vehiculo_emergencia(veh_emerg)

            # Actualizar estado local con métricas (simplificado)
            # En implementación real, pasaríamos detecciones de vehículos
            # Crear objeto de métricas de intersección
            metricas_inter = MetricasInterseccion(
                interseccion_id=id_sem,
                timestamp=timestamp,
                sc_ns=metricas_ns.get('num_detenidos', 0),
                sc_eo=metricas_eo.get('num_detenidos', 0),
                vavg_ns=metricas_ns.get('velocidad_promedio', 0),
                vavg_eo=metricas_eo.get('velocidad_promedio', 0),
                q_ns=metricas_ns.get('flujo_vehicular', 0),
                q_eo=metricas_eo.get('flujo_vehicular', 0),
                k_ns=metricas_ns.get('densidad', 0),
                k_eo=metricas_eo.get('densidad', 0),
                ev_ns=sum(1 for v in vehiculos_emergencia
                          if v.direccion_inicial in ('N', 'S')),
                ev_eo=sum(1 for v in vehiculos_emergencia
                          if v.direccion_inicial in ('E', 'O'))
            )

            # Calcular ICV y PI usando las fórmulas del estado local
            # (simplificado aquí, en realidad usaríamos estado_local.calcular_icv)
            def calcular_icv_simple(sc, vavg, q, k):
                w1, w2, w3, w4 = 0.4, 0.3, 0.2, 0.1
                sc_norm = min(sc / 50.0, 1.0)
                v_norm = 1.0 - min(vavg / 60.0, 1.0)
                k_norm = min(k / 0.15, 1.0)
                q_norm = 1.0 - min(q / 30.0, 1.0)
                return w1*sc_norm + w2*v_norm + w3*k_norm + w4*q_norm

            metricas_inter.icv_ns = calcular_icv_simple(
                metricas_inter.sc_ns,
                metricas_inter.vavg_ns,
                metricas_inter.q_ns,
                metricas_inter.k_ns
            )
            metricas_inter.icv_eo = calcular_icv_simple(
                metricas_inter.sc_eo,
                metricas_inter.vavg_eo,
                metricas_inter.q_eo,
                metricas_inter.k_eo
            )

            metricas_inter.pi_ns = metricas_inter.vavg_ns / (metricas_inter.sc_ns + 1.0)
            metricas_inter.pi_eo = metricas_inter.vavg_eo / (metricas_inter.sc_eo + 1.0)

            # Actualizar agregador de métricas
            if self.agregador_metricas:
                self.agregador_metricas.actualizar_metricas_interseccion(metricas_inter)

    def _aplicar_control_adaptativo(self):
        """Aplica control adaptativo a todos los semáforos"""
        for id_sem in self.semaforos_sumo.keys():
            controlador = self.controladores_difusos[id_sem]

            # Obtener métricas actuales
            metricas_actual = self.agregador_metricas.metricas_actuales.get(id_sem)
            if not metricas_actual:
                continue

            # Aplicar control difuso
            resultado = controlador.calcular_control_completo(
                icv_ns=metricas_actual.icv_ns,
                pi_ns=metricas_actual.pi_ns,
                ev_ns=metricas_actual.ev_ns,
                icv_eo=metricas_actual.icv_eo,
                pi_eo=metricas_actual.pi_eo,
                ev_eo=metricas_actual.ev_eo
            )

            # Aplicar tiempos de verde en SUMO
            # Nota: SUMO usa índices de fase, aquí simplificamos
            # Fase 0 = Verde NS, Fase 2 = Verde EO (típico)
            try:
                fase_actual = traci.trafficlight.getPhase(id_sem)

                # Alternar entre fases
                if fase_actual in [0, 1]:  # NS activo
                    traci.trafficlight.setPhaseDuration(
                        id_sem,
                        int(resultado['NS']['T_verde'])
                    )
                else:  # EO activo
                    traci.trafficlight.setPhaseDuration(
                        id_sem,
                        int(resultado['EO']['T_verde'])
                    )

            except Exception as e:
                logger.debug(f"Error aplicando control a {id_sem}: {e}")

    def _aplicar_control_tiempo_fijo(self):
        """Aplica control de tiempo fijo (sin adaptación)"""
        params_fijo = ParametrosControlFijo()

        for id_sem in self.semaforos_sumo.keys():
            try:
                fase_actual = traci.trafficlight.getPhase(id_sem)

                if fase_actual in [0, 1]:  # NS activo
                    duracion = params_fijo.T_verde_ns
                else:  # EO activo
                    duracion = params_fijo.T_verde_eo

                traci.trafficlight.setPhaseDuration(id_sem, int(duracion))

            except Exception as e:
                logger.debug(f"Error aplicando tiempo fijo a {id_sem}: {e}")

    def desconectar(self):
        """Cierra la conexión con SUMO"""
        if self.conectado:
            traci.close()
            self.conectado = False
            logger.info("✓ Desconectado de SUMO")

    def exportar_resultados(self, archivo_salida: Optional[Path] = None):
        """Exporta todos los resultados de la simulación"""
        if not archivo_salida:
            directorio = (
                self.config.directorio_salida
                or self.config.ruta_config.parent / "resultados_sumo"
            )
            archivo_salida = directorio / "resultados_simulacion.json"

        if self.agregador_metricas:
            self.agregador_metricas.exportar_historico(archivo_salida)
            logger.info(f"✓ Resultados exportados a {archivo_salida}")


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CONTROLADOR SUMO CON SISTEMA ADAPTATIVO DEL CAPÍTULO 6")
    print("="*70 + "\n")

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if not TRACI_DISPONIBLE:
        print("❌ TraCI no está disponible")
        print("\nPara usar esta integración:")
        print("1. Instalar SUMO desde: https://sumo.dlr.de/docs/Downloads.php")
        print("2. Agregar <SUMO_HOME>/tools al PYTHONPATH")
        print("3. Preparar tu escenario SUMO (.sumocfg, .net.xml, .rou.xml)")
        sys.exit(1)

    # Buscar configuración de SUMO
    ruta_config = Path(__file__).parent / 'escenarios' / 'lima-centro' / 'lima_centro.sumocfg'

    if not ruta_config.exists():
        print(f"❌ Configuración de SUMO no encontrada: {ruta_config}")
        print("\n📋 Para usar este controlador:")
        print("1. Crea tu escenario de SUMO en:")
        print(f"   {ruta_config.parent}/")
        print("\n2. Archivos necesarios:")
        print("   - lima_centro.sumocfg  (configuración)")
        print("   - lima_centro.net.xml  (red)")
        print("   - lima_centro.rou.xml  (rutas)")
        print("\n3. Ejecuta nuevamente este script")
        sys.exit(1)

    # Crear configuración
    config = ConfiguracionSUMO(
        ruta_config=ruta_config,
        usar_gui=True,
        intervalo_control=30,
        modo_comparacion=False,
        guardar_metricas=True,
        directorio_salida=Path("./resultados_sumo")
    )

    # Crear controlador
    controlador = ControladorSUMOAdaptativo(config)

    try:
        # Conectar a SUMO
        controlador.conectar()

        # Ejecutar simulación con control adaptativo
        print("\n🚀 Ejecutando simulación con control adaptativo...")
        print("   (Presiona Ctrl+C para detener)\n")

        num_pasos = controlador.ejecutar_simulacion(
            num_pasos=500,  # O None para simular hasta el final
            modo_control=TipoControl.ADAPTATIVO
        )

        # Exportar resultados
        print("\n📊 Exportando resultados...")
        controlador.exportar_resultados()

        print(f"\n✅ Simulación completada exitosamente ({num_pasos} pasos)")

    except KeyboardInterrupt:
        print("\n\n⏹️  Simulación detenida por el usuario")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Error en la simulación")

    finally:
        controlador.desconectar()

    print("\n" + "="*70)
    print("✓ Proceso completado")
    print("="*70 + "\n")
