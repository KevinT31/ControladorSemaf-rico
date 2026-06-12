"""
Servicio para Estadísticas Agregadas
"""

from typing import Dict
from datetime import datetime, timedelta
import logging
import sys
from pathlib import Path

# Agregar modelos_bd al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modelos_bd import SessionLocal, MetricaTrafico
from sqlalchemy import func

logger = logging.getLogger(__name__)


class EstadisticasService:
    """Servicio para cálculo de estadísticas agregadas"""

    @staticmethod
    def guardar_metrica(
        interseccion_id: str,
        timestamp: datetime,
        num_vehiculos: int,
        icv: float,
        flujo_vehicular: float,
        velocidad_promedio: float,
        longitud_cola: float,
        fuente: str = "simulador",
        **kwargs
    ) -> bool:
        """
        Guarda una métrica en la base de datos

        Args:
            interseccion_id: ID de la intersección
            timestamp: Momento de la medición
            num_vehiculos: Número de vehículos detectados
            icv: Índice de Congestión Vehicular
            flujo_vehicular: Vehículos por minuto
            velocidad_promedio: Velocidad promedio en km/h
            longitud_cola: Longitud de la cola en metros
            fuente: Fuente de datos ('simulador', 'video', 'sumo')
            **kwargs: Campos opcionales (densidad, stopped_count, PI, etc.)

        Returns:
            True si se guardó correctamente
        """
        db = SessionLocal()
        try:
            metrica = MetricaTrafico(
                timestamp=timestamp,
                interseccion_id=interseccion_id,
                num_vehiculos=num_vehiculos,
                icv=icv,
                flujo_vehicular=flujo_vehicular,
                velocidad_promedio=velocidad_promedio,
                longitud_cola=longitud_cola,
                fuente=fuente,
                **kwargs  # Incluye campos opcionales
            )
            db.add(metrica)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error guardando métrica: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def calcular_estadisticas(
        interseccion_id: str,
        periodo_inicio: datetime,
        periodo_fin: datetime
    ) -> Dict:
        """
        Calcula estadísticas agregadas de una intersección en un período

        Args:
            interseccion_id: ID de la intersección
            periodo_inicio: Inicio del período
            periodo_fin: Fin del período

        Returns:
            Estadísticas agregadas REALES desde la base de datos
        """
        db = SessionLocal()
        try:
            # Consultar métricas del período
            metricas = db.query(MetricaTrafico).filter(
                MetricaTrafico.interseccion_id == interseccion_id,
                MetricaTrafico.timestamp >= periodo_inicio,
                MetricaTrafico.timestamp <= periodo_fin
            ).all()

            if not metricas:
                # Si no hay datos, retornar valores por defecto
                return {
                    'interseccion_id': interseccion_id,
                    'periodo_inicio': periodo_inicio,
                    'periodo_fin': periodo_fin,
                    'icv_promedio': 0.0,
                    'icv_maximo': 0.0,
                    'icv_minimo': 0.0,
                    'velocidad_promedio': 0.0,
                    'flujo_promedio': 0.0,
                    'total_vehiculos': 0,
                    'horas_congestion': 0.0,
                    'porcentaje_congestion': 0.0,
                    'num_registros': 0
                }

            # Calcular estadísticas
            icv_valores = [m.icv for m in metricas]
            velocidad_valores = [m.velocidad_promedio for m in metricas]
            flujo_valores = [m.flujo_vehicular for m in metricas]

            # Contar horas de congestión (ICV > 0.7)
            horas_congestion = sum(1 for m in metricas if m.icv > 0.7) / 60  # Asumiendo 1 métrica/minuto

            return {
                'interseccion_id': interseccion_id,
                'periodo_inicio': periodo_inicio,
                'periodo_fin': periodo_fin,
                'icv_promedio': sum(icv_valores) / len(icv_valores),
                'icv_maximo': max(icv_valores),
                'icv_minimo': min(icv_valores),
                'velocidad_promedio': sum(velocidad_valores) / len(velocidad_valores),
                'flujo_promedio': sum(flujo_valores) / len(flujo_valores),
                'total_vehiculos': sum(m.num_vehiculos for m in metricas),
                'horas_congestion': horas_congestion,
                'porcentaje_congestion': (horas_congestion / ((periodo_fin - periodo_inicio).total_seconds() / 3600)) * 100 if periodo_fin > periodo_inicio else 0,
                'num_registros': len(metricas)
            }

        except Exception as e:
            logger.error(f"Error calculando estadísticas: {e}")
            raise
        finally:
            db.close()

    @staticmethod
    def obtener_metricas_periodo(
        interseccion_id: str,
        horas: int = 24
    ) -> list:
        """
        Obtiene métricas de las últimas N horas

        Args:
            interseccion_id: ID de la intersección
            horas: Número de horas hacia atrás

        Returns:
            Lista de métricas
        """
        db = SessionLocal()
        try:
            limite_tiempo = datetime.utcnow() - timedelta(hours=horas)

            metricas = db.query(MetricaTrafico).filter(
                MetricaTrafico.interseccion_id == interseccion_id,
                MetricaTrafico.timestamp >= limite_tiempo
            ).order_by(MetricaTrafico.timestamp.desc()).all()

            return [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'icv': m.icv,
                    'flujo': m.flujo_vehicular,
                    'velocidad': m.velocidad_promedio,
                    'num_vehiculos': m.num_vehiculos,
                    'longitud_cola': m.longitud_cola
                }
                for m in metricas
            ]
        finally:
            db.close()
