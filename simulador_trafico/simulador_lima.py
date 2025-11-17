"""
Simulador de Tráfico de Lima

Genera tráfico sintético basado en patrones reales de Lima, Perú:
- Hora pico mañana: 7-9 AM
- Hora pico tarde: 6-8 PM
- Tráfico nocturno: bajo flujo
- Eventos de emergencia
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import random
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


@dataclass
class EstadoTrafico:
    """Estado de tráfico en un instante"""
    timestamp: datetime
    interseccion_id: str
    num_vehiculos: int
    flujo_vehicular: float  # veh/min
    velocidad_promedio: float  # km/h
    longitud_cola: float  # metros


class SimuladorLima:
    """
    Simulador de tráfico para intersecciones de Lima
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
        self.estados: Dict[str, EstadoTrafico] = {}

        logger.info(f"Simulador inicializado con {len(intersecciones)} intersecciones")
        logger.info(f"Escenario: {escenario}")

    def configurar_escenario(self):
        """Configura parámetros según el escenario"""
        escenarios = {
            'hora_pico_manana': {
                'flujo_base': 25.0,  # veh/min
                'velocidad_base': 15.0,  # km/h
                'variabilidad_flujo': 0.3,
                'variabilidad_velocidad': 0.2,
                'prob_congestion': 0.7
            },
            'hora_pico_tarde': {
                'flujo_base': 28.0,
                'velocidad_base': 12.0,
                'variabilidad_flujo': 0.35,
                'variabilidad_velocidad': 0.25,
                'prob_congestion': 0.8
            },
            'trafico_nocturno': {
                'flujo_base': 5.0,
                'velocidad_base': 50.0,
                'variabilidad_flujo': 0.4,
                'variabilidad_velocidad': 0.15,
                'prob_congestion': 0.1
            },
            'evento_emergencia': {
                'flujo_base': 30.0,
                'velocidad_base': 8.0,
                'variabilidad_flujo': 0.5,
                'variabilidad_velocidad': 0.3,
                'prob_congestion': 0.95
            }
        }

        if self.escenario in escenarios:
            self.params = escenarios[self.escenario]
        else:
            logger.warning(f"Escenario '{self.escenario}' no reconocido, usando hora_pico_manana")
            self.params = escenarios['hora_pico_manana']

    def simular_paso(self, duracion_s: float = 1.0) -> Dict[str, EstadoTrafico]:
        """
        Simula un paso de tiempo

        Args:
            duracion_s: Duración del paso en segundos

        Returns:
            Dict con estados de todas las intersecciones
        """
        self.tiempo_simulacion += timedelta(seconds=duracion_s)

        for inter_id, inter in self.intersecciones.items():
            # Generar tráfico con variabilidad
            flujo_base = self.params['flujo_base']
            velocidad_base = self.params['velocidad_base']

            # Agregar variabilidad aleatoria
            variacion_flujo = np.random.uniform(
                -self.params['variabilidad_flujo'],
                self.params['variabilidad_flujo']
            )
            variacion_velocidad = np.random.uniform(
                -self.params['variabilidad_velocidad'],
                self.params['variabilidad_velocidad']
            )

            flujo = max(0, flujo_base * (1 + variacion_flujo))
            velocidad = max(5, velocidad_base * (1 + variacion_velocidad))

            # Calcular número de vehículos
            num_vehiculos = int(flujo * inter.num_carriles / 2)

            # Calcular longitud de cola (mayor con menor velocidad)
            if velocidad < 20:
                longitud_cola = np.random.uniform(50, 120)
            elif velocidad < 40:
                longitud_cola = np.random.uniform(20, 50)
            else:
                longitud_cola = np.random.uniform(0, 20)

            # Crear estado
            estado = EstadoTrafico(
                timestamp=self.tiempo_simulacion,
                interseccion_id=inter_id,
                num_vehiculos=num_vehiculos,
                flujo_vehicular=flujo,
                velocidad_promedio=velocidad,
                longitud_cola=longitud_cola
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
    # Crear intersecciones de Lima
    intersecciones_lima = [
        Interseccion(
            id='INT-001',
            nombre='Av. Arequipa - Av. Angamos',
            latitud=-12.1063,
            longitud=-77.0315,
            num_carriles=6
        ),
        Interseccion(
            id='INT-002',
            nombre='Av. Javier Prado - Av. República de Panamá',
            latitud=-12.1010,
            longitud=-77.0315,
            num_carriles=8
        ),
        Interseccion(
            id='INT-003',
            nombre='Av. La Marina - Av. Faucett',
            latitud=-12.0545,
            longitud=-77.0848,
            num_carriles=6
        ),
    ]

    # Crear simulador
    simulador = SimuladorLima(intersecciones_lima, escenario='hora_pico_manana')

    print("=== SIMULACIÓN DE TRÁFICO EN LIMA ===\n")
    print(f"Escenario: {simulador.escenario}")
    print(f"Intersecciones: {len(intersecciones_lima)}\n")

    # Simular 10 pasos
    for paso in range(10):
        estados = simulador.simular_paso(duracion_s=1.0)

        if paso % 3 == 0:
            print(f"Tiempo {paso}s:")
            for inter_id, estado in estados.items():
                print(f"  {simulador.intersecciones[inter_id].nombre}:")
                print(f"    Vehículos: {estado.num_vehiculos}")
                print(f"    Flujo: {estado.flujo_vehicular:.1f} veh/min")
                print(f"    Velocidad: {estado.velocidad_promedio:.1f} km/h")
                print(f"    Cola: {estado.longitud_cola:.1f} m")
            print()

    print("\n✓ Simulación completada")
