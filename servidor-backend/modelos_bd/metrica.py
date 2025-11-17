"""
Modelo de Métricas de Tráfico (Serie Temporal)
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class MetricaTrafico(Base):
    """
    Serie temporal de métricas de tráfico

    Optimizada para TimescaleDB (hypertable en timestamp)
    Compatible con SQLite para desarrollo
    """
    __tablename__ = "metricas_trafico"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    interseccion_id = Column(String(20), ForeignKey('intersecciones.id'), nullable=False, index=True)

    # Métricas principales
    num_vehiculos = Column(Integer, nullable=False, default=0)
    icv = Column(Float, nullable=False)  # Índice de Congestión Vehicular (0-1)
    flujo_vehicular = Column(Float, nullable=False)  # veh/min
    velocidad_promedio = Column(Float, nullable=False)  # km/h
    longitud_cola = Column(Float, nullable=False)  # metros
    densidad = Column(Float, nullable=True)  # veh/m

    # Métricas adicionales del Capítulo 6
    stopped_count = Column(Integer, nullable=True)  # Vehículos detenidos
    parametro_intensidad = Column(Float, nullable=True)  # PI

    # Control aplicado
    tiempo_verde_ns = Column(Float, nullable=True)  # segundos
    tiempo_verde_eo = Column(Float, nullable=True)  # segundos
    tipo_control = Column(String(50), nullable=True)  # 'fijo', 'adaptativo', 'emergencia'

    # Fuente de datos
    fuente = Column(String(50), nullable=False)  # 'simulador', 'video', 'sumo'

    # Relaciones
    interseccion = relationship("InterseccionDB", back_populates="metricas")

    # Índice compuesto para consultas rápidas
    __table_args__ = (
        Index('idx_metrica_interseccion_timestamp', 'interseccion_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<MetricaTrafico({self.interseccion_id}, {self.timestamp}, ICV={self.icv:.2f})>"
