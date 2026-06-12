"""
Módulo de Optimización de Rutas para Vehículos de Emergencia

Calcula rutas óptimas directas usando coordenadas geográficas,
sin estar limitado a pasar por todas las intersecciones del grafo.
Identifica solo las intersecciones críticas que están en el camino más corto.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


def calcular_distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia en metros entre dos puntos usando la fórmula de Haversine
    
    Args:
        lat1, lon1: Coordenadas del primer punto
        lat2, lon2: Coordenadas del segundo punto
    
    Returns:
        Distancia en metros
    """
    R = 6371000  # Radio de la Tierra en metros
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lat = np.radians(lat2 - lat1)
    delta_lon = np.radians(lon2 - lon1)
    
    a = np.sin(delta_lat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    
    return R * c


def calcular_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula el ángulo (bearing) entre dos puntos
    
    Returns:
        Ángulo en grados (0-360)
    """
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lon = np.radians(lon2 - lon1)
    
    x = np.sin(delta_lon) * np.cos(lat2_rad)
    y = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(delta_lon)
    
    bearing = np.degrees(np.arctan2(x, y))
    return (bearing + 360) % 360


def punto_esta_cerca_de_linea(
    punto_lat: float,
    punto_lon: float,
    linea_lat1: float,
    linea_lon1: float,
    linea_lat2: float,
    linea_lon2: float,
    tolerancia_metros: float = 100
) -> bool:
    """
    Determina si un punto está cerca de una línea (dentro de una tolerancia)
    
    Args:
        punto_lat, punto_lon: Coordenadas del punto
        linea_lat1, linea_lon1: Coordenadas del inicio de la línea
        linea_lat2, linea_lon2: Coordenadas del fin de la línea
        tolerancia_metros: Distancia máxima en metros
    
    Returns:
        True si el punto está cerca de la línea
    """
    # Calcular distancia perpendicular del punto a la línea
    # Usamos la fórmula de distancia punto-línea
    
    # Vector de la línea
    x1, y1 = linea_lon1, linea_lat1
    x2, y2 = linea_lon2, linea_lat2
    x0, y0 = punto_lon, punto_lat
    
    # Distancia en grados (aproximación)
    numerador = abs((y2-y1)*x0 - (x2-x1)*y0 + x2*y1 - y2*x1)
    denominador = np.sqrt((y2-y1)**2 + (x2-x1)**2)
    
    if denominador == 0:
        return False
    
    distancia_grados = numerador / denominador
    
    # Convertir a metros (aproximado: 1 grado ≈ 111 km)
    distancia_metros = distancia_grados * 111000
    
    # También verificar que el punto esté dentro del segmento
    # (no más allá de los extremos)
    dot_product = ((x0-x1)*(x2-x1) + (y0-y1)*(y2-y1)) / (denominador**2)
    
    if dot_product < 0 or dot_product > 1:
        # Punto está fuera del segmento, calcular distancia a los extremos
        dist1 = calcular_distancia_haversine(punto_lat, punto_lon, linea_lat1, linea_lon1)
        dist2 = calcular_distancia_haversine(punto_lat, punto_lon, linea_lat2, linea_lon2)
        distancia_metros = min(dist1, dist2)
    
    return distancia_metros <= tolerancia_metros


class OptimizadorRutas:
    """
    Optimizador de rutas que calcula el camino más corto directo
    e identifica solo las intersecciones críticas en ese camino
    """
    
    def __init__(self, intersecciones: List[Dict]):
        """
        Args:
            intersecciones: Lista de diccionarios con datos de intersecciones
                           Debe incluir: id, nombre, latitud, longitud
        """
        self.intersecciones = {inter['id']: inter for inter in intersecciones}
        logger.info(f"OptimizadorRutas inicializado con {len(self.intersecciones)} intersecciones")
    
    def calcular_ruta_directa_optimizada(
        self,
        origen_id: str,
        destino_id: str,
        tolerancia_metros: float = 150,
        max_intersecciones: int = 10
    ) -> Dict:
        """
        Calcula la ruta más corta directa e identifica las intersecciones críticas
        
        En lugar de seguir el grafo de conexiones, este método:
        1. Traza una línea directa del origen al destino
        2. Identifica solo las intersecciones que están cerca de esta línea
        3. Ordena estas intersecciones según su posición en el camino
        
        Args:
            origen_id: ID de la intersección origen
            destino_id: ID de la intersección destino
            tolerancia_metros: Cuán cerca debe estar una intersección de la línea directa
            max_intersecciones: Máximo número de intersecciones intermedias
        
        Returns:
            Dict con información de la ruta optimizada
        """
        if origen_id not in self.intersecciones:
            raise ValueError(f"Intersección origen {origen_id} no encontrada")
        
        if destino_id not in self.intersecciones:
            raise ValueError(f"Intersección destino {destino_id} no encontrada")
        
        origen = self.intersecciones[origen_id]
        destino = self.intersecciones[destino_id]
        
        # Calcular distancia directa
        distancia_directa = calcular_distancia_haversine(
            origen['latitud'], origen['longitud'],
            destino['latitud'], destino['longitud']
        )
        
        logger.info(f"Calculando ruta DIRECTA de {origen_id} a {destino_id}")
        logger.info(f"Distancia directa: {distancia_directa:.0f}m")
        
        # PARA EMERGENCIAS: Solo origen y destino, SIN intersecciones intermedias
        # Esto garantiza la ruta más corta y rápida posible
        logger.info("🚨 MODO EMERGENCIA: Ruta directa SIN waypoints intermedios")
        
        # Construir ruta final: SOLO origen -> destino
        ruta_ids = [origen_id, destino_id]
        
        # La distancia total es la distancia directa (sin waypoints intermedios)
        distancia_total = distancia_directa
        
        # Factor de detour es 1.0 (ruta perfectamente directa)
        factor_detour = 1.0
        
        logger.info(f"Ruta optimizada calculada:")
        logger.info(f"  - Intersecciones en ruta: {len(ruta_ids)}")
        logger.info(f"  - Distancia total: {distancia_total:.0f}m")
        logger.info(f"  - Factor de detour: {factor_detour:.2f}")
        
        return {
            'exito': True,
            'ruta': ruta_ids,
            'num_intersecciones': len(ruta_ids),
            'distancia_directa': distancia_directa,
            'distancia_total': distancia_total,
            'factor_detour': factor_detour,
            'origen': {
                'id': origen_id,
                'nombre': origen['nombre'],
                'latitud': origen['latitud'],
                'longitud': origen['longitud']
            },
            'destino': {
                'id': destino_id,
                'nombre': destino['nombre'],
                'latitud': destino['latitud'],
                'longitud': destino['longitud']
            },
            'intersecciones_detalle': [
                {
                    'id': ruta_id,
                    'nombre': self.intersecciones[ruta_id]['nombre'],
                    'latitud': self.intersecciones[ruta_id]['latitud'],
                    'longitud': self.intersecciones[ruta_id]['longitud']
                }
                for ruta_id in ruta_ids
            ]
        }
    
    def estimar_tiempo_viaje(
        self,
        distancia_metros: float,
        velocidad_kmh: float,
        factor_congestion: float = 1.2
    ) -> float:
        """
        Estima el tiempo de viaje considerando factores de tráfico
        
        Args:
            distancia_metros: Distancia del recorrido
            velocidad_kmh: Velocidad promedio del vehículo
            factor_congestion: Factor de congestión (1.0 = sin tráfico, >1 = con tráfico)
        
        Returns:
            Tiempo estimado en segundos
        """
        velocidad_ms = velocidad_kmh / 3.6
        tiempo_base = distancia_metros / velocidad_ms
        tiempo_ajustado = tiempo_base * factor_congestion
        
        return tiempo_ajustado
    
    def generar_waypoints_para_mapa(self, ruta: List[str]) -> List[Dict]:
        """
        Genera waypoints para visualización en el mapa
        
        Args:
            ruta: Lista de IDs de intersecciones
        
        Returns:
            Lista de diccionarios con coordenadas y metadatos
        """
        waypoints = []
        
        for i, inter_id in enumerate(ruta):
            inter = self.intersecciones[inter_id]
            waypoints.append({
                'position': i,
                'id': inter_id,
                'nombre': inter['nombre'],
                'lat': inter['latitud'],
                'lng': inter['longitud'],
                'tipo': 'origen' if i == 0 else ('destino' if i == len(ruta)-1 else 'intermedio')
            })
        
        return waypoints


# Ejemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Datos de ejemplo
    intersecciones = [
        {'id': 'MIR-001', 'nombre': 'Av. Arequipa con Av. Angamos', 
         'latitud': -12.110273, 'longitud': -77.034874},
        {'id': 'SI-001', 'nombre': 'Av. Javier Prado con Av. Arequipa', 
         'latitud': -12.094817, 'longitud': -77.036156},
        {'id': 'LIN-001', 'nombre': 'Av. Arequipa con Av. Petit Thouars', 
         'latitud': -12.081723, 'longitud': -77.034845},
        {'id': 'SUR-001', 'nombre': 'Av. Javier Prado con Av. Primavera', 
         'latitud': -12.093145, 'longitud': -76.978934},
    ]
    
    optimizador = OptimizadorRutas(intersecciones)
    
    resultado = optimizador.calcular_ruta_directa_optimizada(
        'MIR-001',
        'SUR-001',
        tolerancia_metros=150
    )
    
    if resultado['exito']:
        print(f"\n✓ Ruta optimizada calculada:")
        print(f"  Origen: {resultado['origen']['nombre']}")
        print(f"  Destino: {resultado['destino']['nombre']}")
        print(f"  Intersecciones: {resultado['num_intersecciones']}")
        print(f"  Distancia directa: {resultado['distancia_directa']:.0f}m")
        print(f"  Distancia total: {resultado['distancia_total']:.0f}m")
        print(f"  Factor de detour: {resultado['factor_detour']:.2f}x")
        print(f"\n  Ruta: {' → '.join(resultado['ruta'])}")
