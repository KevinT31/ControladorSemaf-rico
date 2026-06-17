"""
Conector con SUMO (Simulation of Urban MObility)

Permite controlar semáforos en SUMO usando nuestro algoritmo de control
adaptativo basado en ICV + Lógica Difusa.
"""

import sys
from pathlib import Path
import numpy as np
from typing import Dict, List, Tuple
import logging

# Conexión con SUMO.
# Preferimos libsumo (SUMO embebido en el proceso Python, SIN socket TCP):
# es más rápido y evita que el Firewall de Windows bloquee el socket de
# escucha de sumo.exe. Si libsumo no está, usamos traci (socket clásico).
# Ambos exponen la misma API, por lo que el resto del código no cambia.
USANDO_LIBSUMO = False
try:
    import libsumo as traci
    USANDO_LIBSUMO = True
    TRACI_DISPONIBLE = True
except ImportError:
    try:
        import traci
        TRACI_DISPONIBLE = True
    except ImportError:
        TRACI_DISPONIBLE = False
        logging.warning("Ni libsumo ni traci disponibles. Instalar 'eclipse-sumo' y 'libsumo'.")

# sumolib para localizar los binarios (sumo / sumo-gui) de forma robusta
try:
    import sumolib
    SUMOLIB_DISPONIBLE = True
except ImportError:
    SUMOLIB_DISPONIBLE = False

logger = logging.getLogger(__name__)


class ConectorSUMO:
    """
    Interfaz para controlar simulaciones SUMO
    """

    def __init__(
        self,
        ruta_config_sumo: str,
        puerto: int = 8813,
        usar_gui: bool = True
    ):
        """
        Args:
            ruta_config_sumo: Ruta al archivo .sumocfg
            puerto: Puerto TraCI
            usar_gui: True para sumo-gui, False para sumo (sin GUI)
        """
        if not TRACI_DISPONIBLE:
            raise RuntimeError(
                "TraCI no está disponible. "
                "Instalar SUMO desde https://sumo.dlr.de/docs/Downloads.php"
            )

        self.ruta_config = Path(ruta_config_sumo)
        if not self.ruta_config.exists():
            raise FileNotFoundError(f"Config SUMO no encontrada: {ruta_config_sumo}")

        self.puerto = puerto
        self.usar_gui = usar_gui
        self.conectado = False

        # Diccionario de intersecciones
        self.intersecciones: Dict[str, Dict] = {}

    def conectar(self):
        """Inicia SUMO y conecta (libsumo si está disponible, si no traci)"""
        # libsumo es headless: no soporta GUI. Si se pide GUI pero estamos en
        # libsumo, caemos a 'sumo' headless (el dashboard web es la visualización).
        usar_gui_efectivo = self.usar_gui and not USANDO_LIBSUMO
        nombre_binario = 'sumo-gui' if usar_gui_efectivo else 'sumo'

        # Localizar el binario de forma robusta (eclipse-sumo vía pip)
        if SUMOLIB_DISPONIBLE:
            comando_sumo = sumolib.checkBinary(nombre_binario)
        else:
            comando_sumo = nombre_binario

        opciones = [
            comando_sumo,
            '-c', str(self.ruta_config),
            '--start',
            '--quit-on-end'
        ]

        try:
            # libsumo.start() no acepta el argumento 'port'
            if USANDO_LIBSUMO:
                traci.start(opciones)
            else:
                traci.start(opciones, port=self.puerto)
            self.conectado = True
            motor = 'libsumo (sin socket)' if USANDO_LIBSUMO else 'traci (socket)'
            logger.info(f"[OK] Conectado a SUMO vía {motor} (GUI: {usar_gui_efectivo})")

            # Obtener información de semáforos
            self._inicializar_semaforos()

        except Exception as e:
            logger.error(f"Error conectando a SUMO: {e}")
            raise

    def _inicializar_semaforos(self):
        """Obtiene la lista de semáforos de SUMO"""
        ids_semaforos = traci.trafficlight.getIDList()

        for id_sem in ids_semaforos:
            self.intersecciones[id_sem] = {
                'id': id_sem,
                'programa_actual': traci.trafficlight.getProgram(id_sem),
                'fase_actual': traci.trafficlight.getPhase(id_sem),
                'duracion_fase': traci.trafficlight.getPhaseDuration(id_sem)
            }

        logger.info(f"Semáforos detectados: {len(self.intersecciones)}")
        for id_sem in ids_semaforos:
            logger.info(f"  - {id_sem}")

    def obtener_metricas_interseccion(self, id_semaforo: str) -> Dict:
        """
        Obtiene métricas de tráfico de una intersección

        Args:
            id_semaforo: ID del semáforo en SUMO

        Returns:
            Dict con métricas: flujo, velocidad, cola, densidad
        """
        if not self.conectado:
            raise RuntimeError("No conectado a SUMO")

        # Obtener lanes controlados por el semáforo
        lanes_controlados = traci.trafficlight.getControlledLanes(id_semaforo)

        # Calcular métricas
        num_vehiculos_total = 0
        velocidades = []
        longitud_cola_total = 0

        for lane in lanes_controlados:
            # Número de vehículos
            num_veh = traci.lane.getLastStepVehicleNumber(lane)
            num_vehiculos_total += num_veh

            # Velocidad promedio
            vel_promedio = traci.lane.getLastStepMeanSpeed(lane)  # m/s
            if vel_promedio > 0:
                velocidades.append(vel_promedio * 3.6)  # Convertir a km/h

            # Longitud de cola (número de vehículos detenidos)
            cola = traci.lane.getLastStepHaltingNumber(lane)
            longitud_cola_total += cola

        # Calcular promedios
        velocidad_promedio = np.mean(velocidades) if velocidades else 0.0

        # Estimar flujo (veh/min)
        # Simplificación: num_vehiculos en ventana de 1 paso de simulación
        paso_sim = traci.simulation.getDeltaT()  # segundos
        flujo = (num_vehiculos_total / paso_sim) * 60  # veh/min

        return {
            'id_interseccion': id_semaforo,
            'num_vehiculos': num_vehiculos_total,
            'flujo_vehicular': min(flujo, 30),  # Cap en flujo de saturación
            'velocidad_promedio': velocidad_promedio,
            'longitud_cola': longitud_cola_total * 7.5,  # Aprox 7.5m por vehículo
            'timestamp': traci.simulation.getTime()
        }

    def establecer_fase_semaforo(
        self,
        id_semaforo: str,
        fase: int,
        duracion: int
    ):
        """
        Establece la fase y duración de un semáforo

        Args:
            id_semaforo: ID del semáforo
            fase: Índice de fase (0, 1, 2, ...)
            duracion: Duración en segundos
        """
        if not self.conectado:
            raise RuntimeError("No conectado a SUMO")

        try:
            traci.trafficlight.setPhase(id_semaforo, fase)
            traci.trafficlight.setPhaseDuration(id_semaforo, duracion)
            logger.debug(f"Semáforo {id_semaforo}: fase {fase}, duración {duracion}s")
        except Exception as e:
            logger.error(f"Error estableciendo fase: {e}")

    def simular_paso(self) -> bool:
        """
        Ejecuta un paso de simulación

        Returns:
            True si la simulación continúa, False si terminó
        """
        if not self.conectado:
            raise RuntimeError("No conectado a SUMO")

        try:
            traci.simulationStep()
            return traci.simulation.getMinExpectedNumber() > 0
        except traci.exceptions.FatalTraCIError:
            return False
        except Exception as e:
            logger.error(f"Error en paso de simulación: {e}")
            return False

    def obtener_estado_calles(self, limite: int = 500) -> List[Dict]:
        """
        Obtiene el estado de tráfico de todas las calles (edges)

        Args:
            limite: Número máximo de calles a consultar

        Returns:
            Lista de dicts con estado de cada calle
        """
        if not self.conectado:
            raise RuntimeError("No conectado a SUMO")

        estados = []

        try:
            # Velocidad de referencia para normalizar (50 km/h urbano típico)
            vel_max = 13.89  # m/s

            # Calles ACTIVAS: derivar de los vehículos presentes (O(vehículos)).
            # En redes grandes (p.ej. lima-amplio, 15k edges) iterar todos los
            # edges es lento y, peor, un corte por los primeros N deja fuera los
            # corredores con tráfico. Con la lista de vehículos obtenemos justo
            # las calles donde HAY tráfico, sin importar el tamaño de la red.
            edges_activos = []
            vistos = set()
            try:
                for vid in traci.vehicle.getIDList():
                    try:
                        eid = traci.vehicle.getRoadID(vid)
                    except Exception:
                        continue
                    if not eid or eid.startswith(':') or eid in vistos:
                        continue
                    vistos.add(eid)
                    edges_activos.append(eid)
                    if len(edges_activos) >= limite:
                        break
            except Exception:
                pass

            # Fallback (sin vehículos o API no disponible): primeros edges
            if not edges_activos:
                edges_activos = [e for e in traci.edge.getIDList()[:limite]
                                 if not e.startswith(':')]

            for edge_id in edges_activos:
                try:
                    # Métricas REALES del edge (directo de SUMO, sin ajustes sintéticos)
                    num_vehiculos = traci.edge.getLastStepVehicleNumber(edge_id)
                    velocidad_promedio = traci.edge.getLastStepMeanSpeed(edge_id)  # m/s
                    ocupacion = traci.edge.getLastStepOccupancy(edge_id) * 100.0   # 0..1 -> %

                    # Congestión derivada de ocupación y velocidad reales.
                    # Edge vacío => congestión 0. Con vehículos: combina ocupación
                    # (cuánto del carril está usado) y caída de velocidad respecto a la libre.
                    if num_vehiculos == 0:
                        congestion = 0.0
                    else:
                        ratio_ocupacion = max(0.0, min(1.0, ocupacion / 100.0))
                        ratio_velocidad = max(0.0, min(1.0, velocidad_promedio / vel_max))
                        congestion = 0.5 * ratio_ocupacion + 0.5 * (1.0 - ratio_velocidad)
                        congestion = min(max(congestion, 0.0), 1.0)

                    estados.append({
                        'id': edge_id,
                        'vehiculos': num_vehiculos,
                        'velocidad': round(velocidad_promedio * 3.6, 1),  # km/h
                        'ocupacion': round(ocupacion, 1),
                        'congestion': round(congestion, 2)
                    })
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error obteniendo estado de calles: {e}")

        return estados

    def desconectar(self):
        """Cierra la conexión con SUMO"""
        if self.conectado:
            traci.close()
            self.conectado = False
            logger.info("[OK] Desconectado de SUMO")


class ControladorSemaforicoSUMO:
    """
    Implementa control adaptativo sobre semáforos de SUMO
    """

    def __init__(
        self,
        conector: ConectorSUMO,
        calculador_icv,  # Instancia de CalculadorICV
        controlador_difuso  # Instancia de ControladorDifuso
    ):
        self.conector = conector
        self.calculador_icv = calculador_icv
        self.controlador_difuso = controlador_difuso

        # Historial de decisiones
        self.historial = []

    def ejecutar_control_adaptativo(
        self,
        id_semaforo: str,
        tiempo_espera: float = 30.0
    ) -> Dict:
        """
        Ejecuta un ciclo de control adaptativo

        Args:
            id_semaforo: ID del semáforo a controlar
            tiempo_espera: Tiempo de espera actual (s)

        Returns:
            Dict con decisión tomada
        """
        # 1. Obtener métricas de SUMO
        metricas = self.conector.obtener_metricas_interseccion(id_semaforo)

        # 2. Calcular ICV
        resultado_icv = self.calculador_icv.calcular(
            longitud_cola=metricas['longitud_cola'],
            velocidad_promedio=metricas['velocidad_promedio'],
            flujo_vehicular=metricas['flujo_vehicular']
        )

        # 3. Aplicar lógica difusa
        resultado_difuso = self.controlador_difuso.calcular(
            icv=resultado_icv['icv'],
            tiempo_espera=tiempo_espera
        )
        tiempo_verde = resultado_difuso['tiempo_verde']

        # 4. Aplicar decisión en SUMO
        # Fase 0 = verde NS, Fase 2 = verde EW (típico)
        fase_actual = self.conector.intersecciones[id_semaforo]['fase_actual']
        siguiente_fase = (fase_actual + 1) % 4  # Ciclar fases

        self.conector.establecer_fase_semaforo(
            id_semaforo,
            siguiente_fase,
            int(tiempo_verde)
        )

        decision = {
            'timestamp': metricas['timestamp'],
            'interseccion': id_semaforo,
            'icv': resultado_icv['icv'],
            'clasificacion': resultado_icv['clasificacion'],
            'tiempo_verde_asignado': tiempo_verde,
            'fase': siguiente_fase,
            'metricas': metricas
        }

        self.historial.append(decision)

        logger.info(
            f"Control adaptativo {id_semaforo}: "
            f"ICV={resultado_icv['icv']:.2f} ({resultado_icv['clasificacion']}) "
            f"→ Verde={tiempo_verde:.0f}s"
        )

        return decision


# Ejemplo de uso
if __name__ == "__main__":
    if not TRACI_DISPONIBLE:
        print("❌ TraCI no está disponible")
        print("Instalar SUMO desde: https://sumo.dlr.de/docs/Downloads.php")
        print("Agregar <SUMO_HOME>/tools al PYTHONPATH")
        sys.exit(1)

    # Importar módulos necesarios
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion
    from nucleo.controlador_difuso import ControladorDifuso

    # Configurar
    params = ParametrosInterseccion()
    calculador_icv = CalculadorICV(params)
    controlador_difuso = ControladorDifuso()

    # Conectar a SUMO (ajustar ruta a tu simulación)
    ruta_config = Path(__file__).parent / 'escenarios' / 'lima-centro' / 'lima_centro.sumocfg'

    if not ruta_config.exists():
        print(f"❌ Configuración de SUMO no encontrada: {ruta_config}")
        print("\nCopia tu simulación de SUMO a:")
        print(f"  {ruta_config.parent}/")
        sys.exit(1)

    conector = ConectorSUMO(
        ruta_config_sumo=str(ruta_config),
        usar_gui=True
    )

    conector.conectar()

    # Crear controlador
    controlador = ControladorSemaforicoSUMO(
        conector,
        calculador_icv,
        controlador_difuso
    )

    # Simular 500 pasos (ejemplo)
    print("Iniciando simulación con control adaptativo...")

    paso = 0
    while conector.simular_paso() and paso < 500:
        # Aplicar control cada 30 pasos (30 segundos)
        if paso % 30 == 0:
            for id_sem in conector.intersecciones.keys():
                controlador.ejecutar_control_adaptativo(id_sem)

        paso += 1

    conector.desconectar()

    print(f"\n✓ Simulación completada ({paso} pasos)")
    print(f"Decisiones registradas: {len(controlador.historial)}")
