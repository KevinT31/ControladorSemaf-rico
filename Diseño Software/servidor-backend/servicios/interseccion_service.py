"""
Servicio para gestión de Intersecciones
"""

from typing import List, Optional, Dict
from datetime import datetime
import logging

from .estado_global import estado_sistema

logger = logging.getLogger(__name__)


class InterseccionService:
    """Servicio para operaciones con intersecciones"""

    @staticmethod
    def obtener_todas() -> List[Dict]:
        """Retorna todas las intersecciones del sistema"""
        return list(estado_sistema.intersecciones.values())

    @staticmethod
    def obtener_por_id(interseccion_id: str) -> Optional[Dict]:
        """Obtiene una intersección por su ID"""
        return estado_sistema.intersecciones.get(interseccion_id)

    @staticmethod
    def filtrar_por_zona(zona: str) -> List[Dict]:
        """Filtra intersecciones por zona geográfica"""
        return [
            inter for inter in estado_sistema.intersecciones.values()
            if inter.get('zona', '').lower() == zona.lower()
        ]

    @staticmethod
    def calcular_metricas(interseccion_id: str) -> Dict:
        """
        Calcula métricas actuales de una intersección

        Returns:
            Dict con métricas (ICV, flujo, velocidad, etc)

        Raises:
            ValueError: Si el simulador no está activo o la intersección no existe
        """
        simulador = estado_sistema.simulador

        if not simulador:
            raise ValueError("Simulador no activo")

        # Obtener estado del simulador
        estado = simulador.obtener_estado(interseccion_id)
        if not estado:
            raise ValueError(f"Intersección {interseccion_id} no encontrada")

        # Calcular ICV
        calculador = estado_sistema.calculador_icv
        if not calculador:
            raise ValueError("Calculador ICV no inicializado")

        resultado_icv = calculador.calcular(
            longitud_cola=estado.longitud_cola,
            velocidad_promedio=estado.velocidad_promedio,
            flujo_vehicular=estado.flujo_vehicular
        )

        return {
            'interseccion_id': interseccion_id,
            'timestamp': estado.timestamp.isoformat(),
            'num_vehiculos': estado.num_vehiculos,
            'flujo_vehicular': estado.flujo_vehicular,
            'velocidad_promedio': estado.velocidad_promedio,
            'longitud_cola': estado.longitud_cola,
            'icv': resultado_icv['icv'],
            'clasificacion_icv': resultado_icv['clasificacion'],
            'color_icv': resultado_icv['color'],
            'fuente': estado_sistema.modo
        }

    @staticmethod
    def existe(interseccion_id: str) -> bool:
        """Verifica si una intersección existe"""
        return interseccion_id in estado_sistema.intersecciones

    @staticmethod
    def obtener_vecinos(interseccion_id: str) -> List[str]:
        """Obtiene los IDs de las intersecciones vecinas"""
        inter = InterseccionService.obtener_por_id(interseccion_id)
        if not inter:
            return []
        return inter.get('vecinos', [])

    @staticmethod
    def obtener_distancia_entre(origen_id: str, destino_id: str) -> Optional[float]:
        """Obtiene la distancia entre dos intersecciones si son vecinas"""
        inter_origen = InterseccionService.obtener_por_id(origen_id)
        if not inter_origen:
            return None

        distancias = inter_origen.get('distancia_vecinos', {})
        return distancias.get(destino_id)

    @staticmethod
    def total() -> int:
        """Retorna el número total de intersecciones"""
        return len(estado_sistema.intersecciones)
