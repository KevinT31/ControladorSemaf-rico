"""
Simulador de Tráfico de Lima

Genera tráfico sintético basado en patrones reales de Lima, Perú:
- Hora pico mañana: 7-9 AM
- Hora pico tarde: 6-8 PM
- Tráfico nocturno: bajo flujo
- Eventos de emergencia

Utiliza patrones determinísticos y ciclos de semáforo reales
para simular el comportamiento de cámaras de tráfico en intersecciones.
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class Interseccion:
    """Intersección simulada"""
    id: str
    nombre: str
    latitud: float
    longitud: float
    num_carriles: int = 4
    ciclo_semaforo: int = 120  # segundos (ciclo completo)
    tiempo_verde: int = 50  # segundos de luz verde
    tiempo_amarillo: int = 5  # segundos de luz amarilla
    offset_inicial: int = 0  # desfase para coordinación de olas verdes


@dataclass
class EstadoSemaforo:
    """Estado del semáforo"""
    fase: str  # 'verde', 'amarillo', 'rojo'
    tiempo_restante: float  # segundos hasta cambio de fase
    ciclo_actual: int  # número de ciclo


@dataclass
class EstadoTrafico:
    """Estado de tráfico en un instante"""
    timestamp: datetime
    interseccion_id: str
    num_vehiculos: int
    flujo_vehicular: float  # veh/min
    velocidad_promedio: float  # km/h
    longitud_cola: float  # metros
    icv: float = 0.0  # Índice de Congestión (0-1)
    semaforo: Optional[EstadoSemaforo] = None


class SimuladorLima:
    """
    Simulador de tráfico para intersecciones de Lima.
    Utiliza patrones determinísticos basados en ciclos de semáforo
    y características reales del tráfico limeño.
    """

    def __init__(self, intersecciones: List[Interseccion], escenario: str = "hora_pico_manana"):
        """
        Args:
            intersecciones: Lista de intersecciones a simular
            escenario: 'hora_pico_manana', 'hora_pico_tarde', 'trafico_nocturno'
        """
        self.intersecciones = {i.id: i for i in intersecciones}
        self.escenario = escenario

        # Parámetros de simulación según escenario
        self.configurar_escenario()

        # Estado actual
        self.tiempo_simulacion = datetime.now()
        self.tiempo_inicio = datetime.now()
        self.tiempo_acumulado = 0.0  # segundos desde inicio
        self.estados: Dict[str, EstadoTrafico] = {}

        # Estado de semáforos
        self.estados_semaforo: Dict[str, EstadoSemaforo] = {}
        self._inicializar_semaforos()

        # Acumuladores de tráfico (simulan cola de vehículos)
        self.vehiculos_acumulados: Dict[str, float] = {i.id: 0.0 for i in intersecciones}

        logger.info(f"Simulador inicializado con {len(intersecciones)} intersecciones")
        logger.info(f"Escenario: {escenario}")

    def _inicializar_semaforos(self):
        """Inicializa el estado de los semáforos con sus offsets"""
        for inter_id, inter in self.intersecciones.items():
            # Calcular fase inicial basada en offset
            tiempo_en_ciclo = inter.offset_inicial % inter.ciclo_semaforo

            if tiempo_en_ciclo < inter.tiempo_verde:
                fase = 'verde'
                tiempo_restante = inter.tiempo_verde - tiempo_en_ciclo
            elif tiempo_en_ciclo < inter.tiempo_verde + inter.tiempo_amarillo:
                fase = 'amarillo'
                tiempo_restante = inter.tiempo_verde + inter.tiempo_amarillo - tiempo_en_ciclo
            else:
                fase = 'rojo'
                tiempo_restante = inter.ciclo_semaforo - tiempo_en_ciclo

            self.estados_semaforo[inter_id] = EstadoSemaforo(
                fase=fase,
                tiempo_restante=tiempo_restante,
                ciclo_actual=0
            )

    def configurar_escenario(self):
        """
        Configura parámetros según el escenario.
        Parámetros basados en estudios de tráfico de Lima.
        """
        escenarios = {
            'hora_pico_manana': {
                'tasa_llegada': 22.0,  # veh/min por carril (llegada durante verde)
                'tasa_salida': 18.0,  # veh/min por carril (descarga durante verde)
                'velocidad_verde': 25.0,  # km/h cuando hay luz verde
                'velocidad_rojo': 8.0,  # km/h cuando hay cola
                'velocidad_libre': 45.0,  # km/h sin congestión
                'longitud_vehiculo': 5.0,  # metros promedio por vehículo
                'gap_seguridad': 2.0,  # metros entre vehículos
                'amplitud_variacion': 0.15,  # variación periódica del flujo
                'periodo_variacion': 300.0,  # segundos (5 min) para onda de tráfico
            },
            'hora_pico_tarde': {
                'tasa_llegada': 26.0,
                'tasa_salida': 16.0,
                'velocidad_verde': 20.0,
                'velocidad_rojo': 5.0,
                'velocidad_libre': 40.0,
                'longitud_vehiculo': 5.0,
                'gap_seguridad': 2.0,
                'amplitud_variacion': 0.20,
                'periodo_variacion': 240.0,
            },
            'trafico_nocturno': {
                'tasa_llegada': 4.0,
                'tasa_salida': 8.0,
                'velocidad_verde': 50.0,
                'velocidad_rojo': 35.0,
                'velocidad_libre': 60.0,
                'longitud_vehiculo': 5.0,
                'gap_seguridad': 3.0,
                'amplitud_variacion': 0.10,
                'periodo_variacion': 600.0,
            },
            'evento_emergencia': {
                'tasa_llegada': 30.0,
                'tasa_salida': 12.0,
                'velocidad_verde': 15.0,
                'velocidad_rojo': 3.0,
                'velocidad_libre': 25.0,
                'longitud_vehiculo': 5.0,
                'gap_seguridad': 1.5,
                'amplitud_variacion': 0.25,
                'periodo_variacion': 180.0,
            }
        }

        if self.escenario in escenarios:
            self.params = escenarios[self.escenario]
        else:
            logger.warning(f"Escenario '{self.escenario}' no reconocido, usando hora_pico_manana")
            self.params = escenarios['hora_pico_manana']

    def _actualizar_semaforo(self, inter_id: str, duracion_s: float):
        """Actualiza el estado del semáforo"""
        estado = self.estados_semaforo[inter_id]
        inter = self.intersecciones[inter_id]

        estado.tiempo_restante -= duracion_s

        if estado.tiempo_restante <= 0:
            # Cambiar de fase
            if estado.fase == 'verde':
                estado.fase = 'amarillo'
                estado.tiempo_restante = inter.tiempo_amarillo
            elif estado.fase == 'amarillo':
                estado.fase = 'rojo'
                tiempo_rojo = inter.ciclo_semaforo - inter.tiempo_verde - inter.tiempo_amarillo
                estado.tiempo_restante = tiempo_rojo
            else:  # rojo
                estado.fase = 'verde'
                estado.tiempo_restante = inter.tiempo_verde
                estado.ciclo_actual += 1

    def _calcular_variacion_temporal(self, tiempo_acumulado: float) -> float:
        """
        Calcula variación sinusoidal del tráfico basada en el tiempo.
        Simula las ondas naturales de tráfico (platoons).
        """
        periodo = self.params['periodo_variacion']
        amplitud = self.params['amplitud_variacion']
        # Onda sinusoidal determinística
        variacion = amplitud * math.sin(2 * math.pi * tiempo_acumulado / periodo)
        return variacion

    def simular_paso(self, duracion_s: float = 1.0) -> Dict[str, EstadoTrafico]:
        """
        Simula un paso de tiempo usando modelo determinístico.

        Modelo basado en:
        - Ciclos de semáforo reales
        - Tasas de llegada/salida según fase
        - Acumulación de vehículos durante rojo
        - Descarga durante verde
        - Variación sinusoidal para simular platoons naturales

        Args:
            duracion_s: Duración del paso en segundos

        Returns:
            Dict con estados de todas las intersecciones
        """
        self.tiempo_simulacion += timedelta(seconds=duracion_s)
        self.tiempo_acumulado += duracion_s

        # Calcular variación temporal (común a todas las intersecciones)
        variacion_temporal = self._calcular_variacion_temporal(self.tiempo_acumulado)

        for inter_id, inter in self.intersecciones.items():
            # Actualizar semáforo
            self._actualizar_semaforo(inter_id, duracion_s)
            estado_sem = self.estados_semaforo[inter_id]

            # Calcular llegadas (siempre hay vehículos llegando)
            tasa_llegada = self.params['tasa_llegada']
            # Aplicar variación temporal determinística
            tasa_llegada_actual = tasa_llegada * (1 + variacion_temporal)
            vehiculos_llegando = (tasa_llegada_actual * inter.num_carriles * duracion_s) / 60.0

            # Calcular salidas según fase del semáforo
            if estado_sem.fase == 'verde':
                tasa_salida = self.params['tasa_salida']
                vehiculos_saliendo = (tasa_salida * inter.num_carriles * duracion_s) / 60.0
                velocidad = self.params['velocidad_verde']
            elif estado_sem.fase == 'amarillo':
                # En amarillo, algunos vehículos aún pasan
                tasa_salida = self.params['tasa_salida'] * 0.5
                vehiculos_saliendo = (tasa_salida * inter.num_carriles * duracion_s) / 60.0
                velocidad = self.params['velocidad_rojo']
            else:  # rojo
                vehiculos_saliendo = 0.0
                velocidad = self.params['velocidad_rojo']

            # Actualizar acumulación
            self.vehiculos_acumulados[inter_id] += vehiculos_llegando - vehiculos_saliendo
            self.vehiculos_acumulados[inter_id] = max(0.0, self.vehiculos_acumulados[inter_id])

            # Si no hay vehículos acumulados, velocidad libre
            if self.vehiculos_acumulados[inter_id] < 1.0:
                velocidad = self.params['velocidad_libre']

            # Calcular métricas finales
            num_vehiculos = int(round(self.vehiculos_acumulados[inter_id]))

            # Flujo: vehículos que pasan por minuto
            flujo_vehicular = (vehiculos_saliendo * 60.0) / duracion_s if duracion_s > 0 else 0.0

            # Longitud de cola basada en vehículos acumulados
            longitud_vehiculo = self.params['longitud_vehiculo']
            gap_seguridad = self.params['gap_seguridad']
            longitud_cola = self.vehiculos_acumulados[inter_id] * (longitud_vehiculo + gap_seguridad)

            # Limitar longitud de cola a valores realistas (máx 200m por carril)
            longitud_cola = min(longitud_cola, 200.0 * inter.num_carriles)

            # Crear estado
            # Calcular ICV del núcleo si está disponible
            icv_val = 0.0
            try:
                # Import tardío para no romper si falta núcleo
                from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion
                _calc = CalculadorICV(ParametrosInterseccion())
                res_icv = _calc.calcular(
                    longitud_cola=float(longitud_cola),
                    velocidad_promedio=float(velocidad),
                    flujo_vehicular=float(flujo_vehicular)
                )
                icv_val = float(res_icv.get('icv', 0.0))
            except Exception:
                # Fallback simple si no está disponible
                # Combina flujo normalizado, cola normalizada y penalización de baja velocidad
                cap_flujo = max(1.0, inter.num_carriles * 30.0)
                flujo_norm = max(0.0, min(1.0, flujo_vehicular / cap_flujo))
                cola_norm = max(0.0, min(1.0, longitud_cola / (200.0 * inter.num_carriles)))
                vel_libre = self.params['velocidad_libre']
                vel_norm = max(0.0, min(1.0, velocidad / vel_libre))
                icv_val = 0.40 * flujo_norm + 0.30 * cola_norm + 0.15 * (1.0 - vel_norm)

            # Clamp estricto solicitado para modo simulador: [0.50, 0.60]
            icv_val = max(0.50, min(0.60, icv_val))

            estado = EstadoTrafico(
                timestamp=self.tiempo_simulacion,
                interseccion_id=inter_id,
                num_vehiculos=num_vehiculos,
                flujo_vehicular=flujo_vehicular,
                velocidad_promedio=velocidad,
                longitud_cola=longitud_cola,
                icv=icv_val,
                semaforo=EstadoSemaforo(
                    fase=estado_sem.fase,
                    tiempo_restante=estado_sem.tiempo_restante,
                    ciclo_actual=estado_sem.ciclo_actual
                )
            )

            self.estados[inter_id] = estado

        return self.estados

    def obtener_estado(self, interseccion_id: str) -> Optional[EstadoTrafico]:
        """Obtiene el estado actual de una intersección"""
        return self.estados.get(interseccion_id)

    def cambiar_escenario(self, nuevo_escenario: str):
        """Cambia el escenario de simulación"""
        self.escenario = nuevo_escenario
        self.configurar_escenario()
        logger.info(f"Escenario cambiado a: {nuevo_escenario}")


# Ejemplo de uso
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(level=logging.INFO)

    # Crear intersecciones de Lima con ciclos coordinados (ola verde)
    intersecciones_lima = [
        Interseccion(
            id='INT-001',
            nombre='Av. Arequipa - Av. Angamos',
            latitud=-12.1063,
            longitud=-77.0315,
            num_carriles=6,
            ciclo_semaforo=120,
            tiempo_verde=55,
            tiempo_amarillo=5,
            offset_inicial=0  # Primera intersección
        ),
        Interseccion(
            id='INT-002',
            nombre='Av. Javier Prado - Av. República de Panamá',
            latitud=-12.1010,
            longitud=-77.0315,
            num_carriles=8,
            ciclo_semaforo=120,
            tiempo_verde=60,
            tiempo_amarillo=5,
            offset_inicial=30  # Desfase de 30s para ola verde
        ),
        Interseccion(
            id='INT-003',
            nombre='Av. La Marina - Av. Faucett',
            latitud=-12.0545,
            longitud=-77.0848,
            num_carriles=6,
            ciclo_semaforo=120,
            tiempo_verde=50,
            tiempo_amarillo=5,
            offset_inicial=60  # Desfase de 60s
        ),
    ]

    # Crear simulador
    simulador = SimuladorLima(intersecciones_lima, escenario='hora_pico_manana')

    print("=" * 60)
    print("SIMULACIÓN REALISTA DE TRÁFICO EN LIMA")
    print("Modelo determinístico con ciclos de semáforo")
    print("=" * 60)
    print(f"\nEscenario: {simulador.escenario}")
    print(f"Intersecciones: {len(intersecciones_lima)}")
    print(f"\nParámetros del escenario:")
    print(f"  Tasa de llegada: {simulador.params['tasa_llegada']:.1f} veh/min/carril")
    print(f"  Tasa de salida: {simulador.params['tasa_salida']:.1f} veh/min/carril")
    print(f"  Velocidad en verde: {simulador.params['velocidad_verde']:.1f} km/h")
    print(f"  Velocidad con cola: {simulador.params['velocidad_rojo']:.1f} km/h")
    print("\n" + "=" * 60 + "\n")

    # Simular 180 segundos (3 minutos) - más de un ciclo completo
    for paso in range(180):
        estados = simulador.simular_paso(duracion_s=1.0)

        # Mostrar cada 30 segundos
        if paso % 30 == 0:
            print(f"⏱ Tiempo: {paso}s")
            for inter_id, estado in estados.items():
                inter = simulador.intersecciones[inter_id]
                sem = estado.semaforo
                print(f"\n  📍 {inter.nombre}:")
                print(f"     Semáforo: {sem.fase.upper()} (resta {sem.tiempo_restante:.0f}s)")
                print(f"     Vehículos en cola: {estado.num_vehiculos}")
                print(f"     Flujo actual: {estado.flujo_vehicular:.1f} veh/min")
                print(f"     Velocidad: {estado.velocidad_promedio:.1f} km/h")
                print(f"     Longitud de cola: {estado.longitud_cola:.1f} m")
            print("\n" + "-" * 60)

    print("\n✓ Simulación completada exitosamente")
    print("  (Modelo completamente determinístico sin valores aleatorios)")
