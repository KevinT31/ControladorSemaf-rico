"""
Algoritmo de Olas Verdes Dinámicas con Enrutamiento Tipo Serpiente

Implementa un sistema de olas verdes que NO requiere que las intersecciones
estén en línea recta. 

Usa algoritmo A* con heurística euclidiana para encontrar rutas óptimas.
"""

import heapq
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class Interseccion:
    """Representa una intersección en la red"""
    id: str
    nombre: str
    latitud: float
    longitud: float
    vecinos: List[str]  # IDs de intersecciones conectadas
    distancia_vecinos: Dict[str, float]  # Distancia en metros


@dataclass
class VehiculoEmergencia:
    """Vehículo de emergencia detectado"""
    id: str
    tipo: str  # 'ambulancia', 'bomberos', 'policia'
    interseccion_actual: str
    destino: str
    velocidad_estimada: float  # km/h
    timestamp: datetime


class GrafoIntersecciones:
    """
    Grafo de intersecciones para enrutamiento
    """

    def __init__(self):
        self.intersecciones: Dict[str, Interseccion] = {}

    def agregar_interseccion(self, interseccion: Interseccion):
        """Agrega una intersección al grafo"""
        self.intersecciones[interseccion.id] = interseccion

    def agregar_conexion(
        self,
        id_origen: str,
        id_destino: str,
        distancia: float,
        bidireccional: bool = True
    ):
        """
        Agrega una conexión entre dos intersecciones

        Args:
            id_origen: ID de intersección origen
            id_destino: ID de intersección destino
            distancia: Distancia en metros
            bidireccional: Si True, agrega conexión en ambos sentidos
        """
        if id_origen not in self.intersecciones:
            raise ValueError(f"Intersección {id_origen} no existe")
        if id_destino not in self.intersecciones:
            raise ValueError(f"Intersección {id_destino} no existe")

        # Agregar vecino
        if id_destino not in self.intersecciones[id_origen].vecinos:
            self.intersecciones[id_origen].vecinos.append(id_destino)
            self.intersecciones[id_origen].distancia_vecinos[id_destino] = distancia

        if bidireccional:
            if id_origen not in self.intersecciones[id_destino].vecinos:
                self.intersecciones[id_destino].vecinos.append(id_origen)
                self.intersecciones[id_destino].distancia_vecinos[id_origen] = distancia

    def calcular_distancia_euclidiana(self, id1: str, id2: str) -> float:
        """Calcula distancia euclidiana entre dos intersecciones (heurística)"""
        i1 = self.intersecciones[id1]
        i2 = self.intersecciones[id2]

        # Aproximación: 1 grado ≈ 111 km
        lat_dist = (i2.latitud - i1.latitud) * 111000
        lon_dist = (i2.longitud - i1.longitud) * 111000 * np.cos(np.radians(i1.latitud))

        return np.sqrt(lat_dist**2 + lon_dist**2)


class CoordinadorOlasVerdes:
    """
    Coordina las olas verdes dinámicas tipo serpiente
    """

    def __init__(self, grafo: GrafoIntersecciones):
        self.grafo = grafo
        self.olas_activas: Dict[str, Dict] = {}  # vehicle_id -> info de ola

    def calcular_ruta_optima(
        self,
        origen: str,
        destino: str
    ) -> Optional[List[str]]:
        """
        Calcula la ruta óptima usando A*

        Args:
            origen: ID de intersección origen
            destino: ID de intersección destino

        Returns:
            Lista de IDs de intersecciones en la ruta, o None si no hay ruta
        """

        # Cola de prioridad: (f_score, id_interseccion)
        frontera = [(0, origen)]

        # Diccionarios para A*
        vino_de = {origen: None}
        g_score = {origen: 0}  # Costo desde origen

        while frontera:
            _, actual = heapq.heappop(frontera)

            if actual == destino:
                # Reconstruir ruta
                ruta = []
                nodo = destino
                while nodo is not None:
                    ruta.append(nodo)
                    nodo = vino_de[nodo]
                return ruta[::-1]  # Invertir para tener origen -> destino

            # Explorar vecinos
            interseccion = self.grafo.intersecciones[actual]
            for vecino in interseccion.vecinos:
                # Costo tentativo
                costo_tentativo = g_score[actual] + interseccion.distancia_vecinos[vecino]

                if vecino not in g_score or costo_tentativo < g_score[vecino]:
                    vino_de[vecino] = actual
                    g_score[vecino] = costo_tentativo

                    # f_score = g_score + heurística
                    h = self.grafo.calcular_distancia_euclidiana(vecino, destino)
                    f_score = costo_tentativo + h

                    heapq.heappush(frontera, (f_score, vecino))

        logger.warning(f"No se encontró ruta entre {origen} y {destino}")
        return None

    def activar_ola_verde(
        self,
        vehiculo: VehiculoEmergencia
    ) -> Dict:
        """
        Activa una ola verde para un vehículo de emergencia

        Args:
            vehiculo: Información del vehículo de emergencia

        Returns:
            Dict con información de la ola verde activada
        """

        # 1. Calcular ruta óptima
        ruta = self.calcular_ruta_optima(
            vehiculo.interseccion_actual,
            vehiculo.destino
        )

        if ruta is None:
            logger.error(f"No se pudo calcular ruta para vehículo {vehiculo.id}")
            return {'exito': False, 'mensaje': 'No hay ruta disponible'}

        # 2. Calcular ETAs a cada intersección
        etas = self._calcular_etas(ruta, vehiculo.velocidad_estimada)

        # 3. Generar comandos de sincronización
        comandos = []
        for i, (interseccion_id, eta) in enumerate(zip(ruta, etas)):
            comando = {
                'interseccion_id': interseccion_id,
                'accion': 'activar_verde',
                'direccion': self._obtener_direccion_entrada(ruta, i),
                'tiempo_anticipacion': 15,  # segundos antes del arribo
                'eta': eta,
                'duracion_minima': 30,  # segundos de verde garantizado
                'orden_secuencia': i
            }
            comandos.append(comando)

        # 4. Registrar ola activa
        ola_info = {
            'vehiculo_id': vehiculo.id,
            'tipo_vehiculo': vehiculo.tipo,
            'ruta': ruta,
            'etas': etas,
            'comandos': comandos,
            'timestamp_activacion': datetime.now(),
            'estado': 'activa'
        }

        self.olas_activas[vehiculo.id] = ola_info

        logger.info(
            f"Ola verde activada para {vehiculo.tipo} {vehiculo.id}. "
            f"Ruta: {' → '.join(ruta)}"
        )

        return {
            'exito': True,
            'vehiculo_id': vehiculo.id,
            'ruta': ruta,
            'num_intersecciones': len(ruta),
            'distancia_total': sum([self.grafo.intersecciones[ruta[i]].distancia_vecinos[ruta[i+1]]
                                   for i in range(len(ruta)-1)]),
            'tiempo_estimado': etas[-1],
            'comandos': comandos
        }

    def _calcular_etas(
        self,
        ruta: List[str],
        velocidad_kmh: float
    ) -> List[float]:
        """
        Calcula tiempos estimados de arribo (ETA) a cada intersección

        Args:
            ruta: Lista de IDs de intersecciones
            velocidad_kmh: Velocidad del vehículo en km/h

        Returns:
            Lista de ETAs en segundos desde el inicio
        """
        etas = [0.0]  # Origen en t=0
        tiempo_acumulado = 0.0

        for i in range(len(ruta) - 1):
            actual = ruta[i]
            siguiente = ruta[i + 1]

            # Obtener distancia
            distancia_m = self.grafo.intersecciones[actual].distancia_vecinos[siguiente]

            # Calcular tiempo (distancia / velocidad)
            velocidad_ms = velocidad_kmh / 3.6
            tiempo_s = distancia_m / velocidad_ms

            tiempo_acumulado += tiempo_s
            etas.append(tiempo_acumulado)

        return etas

    def _obtener_direccion_entrada(
        self,
        ruta: List[str],
        indice: int
    ) -> Optional[str]:
        """
        Determina la dirección de entrada del vehículo a una intersección

        Args:
            ruta: Lista de IDs de intersecciones
            indice: Índice de la intersección actual

        Returns:
            Dirección de entrada ('norte', 'sur', 'este', 'oeste', o None)
        """
        if indice == 0:
            return None  # Primera intersección, no hay entrada

        anterior = self.grafo.intersecciones[ruta[indice - 1]]
        actual = self.grafo.intersecciones[ruta[indice]]

        # Calcular ángulo de entrada
        dlat = actual.latitud - anterior.latitud
        dlon = actual.longitud - anterior.longitud

        angulo = np.degrees(np.arctan2(dlon, dlat))

        # Convertir ángulo a dirección cardinal
        if -45 <= angulo < 45:
            return 'norte'
        elif 45 <= angulo < 135:
            return 'este'
        elif -135 <= angulo < -45:
            return 'oeste'
        else:
            return 'sur'

    def calcular_offset_optimo(
        self,
        interseccion_origen: str,
        interseccion_destino: str,
        velocidad_progresion_kmh: float = 50.0,
        ciclo_segundos: float = 90.0
    ) -> float:
        """
        Calcula el offset óptimo entre dos intersecciones consecutivas (Cap 6.3.5)

        Fórmula exacta: φ_i,i+1 = (d_i / v_prog) mod T_ciclo

        Donde:
        - φ_i,i+1 es el offset entre intersección i e i+1 (segundos)
        - d_i es la distancia entre las intersecciones (metros)
        - v_prog es la velocidad de progresión (m/s)
        - T_ciclo es el tiempo de ciclo del semáforo (segundos)

        Args:
            interseccion_origen: ID de la intersección origen
            interseccion_destino: ID de la intersección destino
            velocidad_progresion_kmh: Velocidad de progresión en km/h (típicamente 40-60 km/h)
            ciclo_segundos: Tiempo de ciclo del semáforo en segundos (típicamente 60-120s)

        Returns:
            Offset óptimo en segundos

        Ejemplo:
            Si la distancia es 500m, velocidad 50 km/h (13.89 m/s), ciclo 90s:
            φ = (500 / 13.89) mod 90 = 36.0 mod 90 = 36.0 segundos
        """
        if interseccion_origen not in self.grafo.intersecciones:
            raise ValueError(f"Intersección origen {interseccion_origen} no existe en el grafo")

        if interseccion_destino not in self.grafo.intersecciones:
            raise ValueError(f"Intersección destino {interseccion_destino} no existe en el grafo")

        # Obtener distancia entre intersecciones
        origen = self.grafo.intersecciones[interseccion_origen]
        if interseccion_destino not in origen.distancia_vecinos:
            raise ValueError(
                f"No hay conexión directa entre {interseccion_origen} y {interseccion_destino}"
            )

        distancia_metros = origen.distancia_vecinos[interseccion_destino]

        # Convertir velocidad de km/h a m/s
        velocidad_ms = velocidad_progresion_kmh / 3.6

        # Calcular tiempo de viaje
        tiempo_viaje = distancia_metros / velocidad_ms

        # Calcular offset usando módulo del ciclo (Cap 6.3.5)
        offset = tiempo_viaje % ciclo_segundos

        logger.debug(
            f"Offset calculado (Cap 6.3.5): "
            f"{interseccion_origen} → {interseccion_destino} = {offset:.2f}s "
            f"(d={distancia_metros}m, v={velocidad_progresion_kmh}km/h, T={ciclo_segundos}s)"
        )

        return offset

    def calcular_offsets_ruta(
        self,
        ruta: List[str],
        velocidad_progresion_kmh: float = 50.0,
        ciclo_segundos: float = 90.0
    ) -> List[Dict]:
        """
        Calcula offsets óptimos para una ruta completa (Cap 6.3.5)

        Args:
            ruta: Lista de IDs de intersecciones en secuencia
            velocidad_progresion_kmh: Velocidad de progresión en km/h
            ciclo_segundos: Tiempo de ciclo del semáforo en segundos

        Returns:
            Lista de diccionarios con información de offset para cada par consecutivo
        """
        if len(ruta) < 2:
            return []

        offsets = []

        for i in range(len(ruta) - 1):
            origen = ruta[i]
            destino = ruta[i + 1]

            offset = self.calcular_offset_optimo(
                origen,
                destino,
                velocidad_progresion_kmh,
                ciclo_segundos
            )

            distancia = self.grafo.intersecciones[origen].distancia_vecinos[destino]

            offsets.append({
                'desde': origen,
                'hasta': destino,
                'offset_segundos': round(offset, 2),
                'distancia_metros': distancia,
                'velocidad_progresion_kmh': velocidad_progresion_kmh,
                'ciclo_segundos': ciclo_segundos,
                'formula': 'Capitulo_6.3.5'
            })

        logger.info(
            f"Offsets calculados para ruta de {len(ruta)} intersecciones "
            f"({len(offsets)} pares consecutivos)"
        )

        return offsets

    def visualizar_ruta(self, ruta: List[str]) -> Dict:
        """
        Genera datos para visualizar la ruta en el mapa

        Returns:
            Dict con coordenadas para dibujar la ruta tipo serpiente
        """
        coordenadas = []
        for inter_id in ruta:
            inter = self.grafo.intersecciones[inter_id]
            coordenadas.append({
                'lat': inter.latitud,
                'lng': inter.longitud,
                'nombre': inter.nombre
            })

        return {
            'tipo': 'LineString',
            'coordenadas': coordenadas,
            'estilo': {
                'color': '#00FF00',
                'ancho': 6,
                'opacidad': 0.8,
                'animacion': 'dash'  # Línea animada tipo serpiente
            }
        }


# Ejemplo de uso
if __name__ == "__main__":
    # Crear grafo de intersecciones de Lima
    grafo = GrafoIntersecciones()

    # Agregar intersecciones (ejemplo simplificado)
    intersecciones = [
        Interseccion('INT-001', 'Av. Arequipa - Av. Angamos',
                    -12.1063, -77.0315, [], {}),
        Interseccion('INT-002', 'Av. Arequipa - Av. República de Panamá',
                    -12.1010, -77.0315, [], {}),
        Interseccion('INT-003', 'Av. República de Panamá - Av. Aviación',
                    -12.1010, -77.0250, [], {}),
        Interseccion('INT-004', 'Av. Aviación - Av. Javier Prado',
                    -12.0897, -77.0250, [], {}),
    ]

    for inter in intersecciones:
        grafo.agregar_interseccion(inter)

    # Agregar conexiones (red tipo serpiente)
    grafo.agregar_conexion('INT-001', 'INT-002', 600)  # 600m
    grafo.agregar_conexion('INT-002', 'INT-003', 700)  # Giro este
    grafo.agregar_conexion('INT-003', 'INT-004', 1200) # Giro norte

    # Crear coordinador
    coordinador = CoordinadorOlasVerdes(grafo)

    # Simular vehículo de emergencia
    ambulancia = VehiculoEmergencia(
        id='AMB-001',
        tipo='ambulancia',
        interseccion_actual='INT-001',
        destino='INT-004',
        velocidad_estimada=50.0,  # km/h
        timestamp=datetime.now()
    )

    # Activar ola verde
    resultado = coordinador.activar_ola_verde(ambulancia)

    if resultado['exito']:
        print("✓ Ola verde activada exitosamente")
        print(f"  Ruta: {' → '.join(resultado['ruta'])}")
        print(f"  Distancia total: {resultado['distancia_total']:.0f}m")
        print(f"  Tiempo estimado: {resultado['tiempo_estimado']:.0f}s")
        print(f"\n  Comandos de sincronización:")
        for cmd in resultado['comandos']:
            print(f"    {cmd['orden_secuencia']+1}. {cmd['interseccion_id']} "
                  f"({cmd['direccion'] or 'origen'}) - ETA: {cmd['eta']:.0f}s")
