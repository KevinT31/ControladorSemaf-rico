"""
Modelo de Ola Verde (Vehículos de Emergencia)
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class OlaVerde(Base):
    """
    Registro de olas verdes activadas para vehículos de emergencia
    """
    __tablename__ = "olas_verdes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehiculo_id = Column(String(50), unique=True, nullable=False, index=True)  # ej: "EMG-143022"
    tipo_vehiculo = Column(String(50), nullable=False)  # 'ambulancia', 'bomberos', 'policia'

    # Ubicaciones
    interseccion_origen_id = Column(String(20), ForeignKey('intersecciones.id'), nullable=False)
    interseccion_destino_id = Column(String(20), ForeignKey('intersecciones.id'), nullable=False)

    # Ruta calculada
    ruta_json = Column(JSON, nullable=False)  # Lista de IDs de intersecciones
    distancia_total_metros = Column(Float, nullable=False)
    tiempo_estimado_segundos = Column(Float, nullable=False)
    semaforos_sincronizados = Column(Integer, nullable=False)

    # Estado
    activo = Column(Boolean, default=True, nullable=False)
    completado = Column(Boolean, default=False, nullable=False)

    # Timestamps
    timestamp_activacion = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    timestamp_finalizacion = Column(DateTime, nullable=True)

    # Tiempo real vs estimado
    tiempo_total_segundos = Column(Float, nullable=True)  # Tiempo real cuando se completa

    # Relaciones
    interseccion_origen = relationship(
        "InterseccionDB",
        foreign_keys=[interseccion_origen_id],
        back_populates="olas_verdes_origen"
    )
    interseccion_destino = relationship(
        "InterseccionDB",
        foreign_keys=[interseccion_destino_id],
        back_populates="olas_verdes_destino"
    )

    def __repr__(self):
        estado = "ACTIVA" if self.activo else "COMPLETADA"
        return f"<OlaVerde({self.vehiculo_id}, {self.tipo_vehiculo}, {estado})>"
