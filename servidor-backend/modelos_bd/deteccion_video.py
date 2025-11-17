"""
Modelo de Detecciones de Video (YOLO)
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class DeteccionVideo(Base):
    """
    Detecciones individuales de vehículos desde video

    Usado para:
    - Tracking de vehículos
    - Análisis de tráfico
    - Machine Learning
    """
    __tablename__ = "detecciones_video"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    interseccion_id = Column(String(20), ForeignKey('intersecciones.id'), nullable=False, index=True)

    # Video fuente
    video_path = Column(String(500), nullable=False)
    frame_numero = Column(Integer, nullable=False)

    # Detección YOLO
    track_id = Column(Integer, nullable=True)  # ID de tracking
    clase = Column(String(50), nullable=False)  # 'car', 'truck', 'bus', 'motorcycle', etc
    confianza = Column(Float, nullable=False)  # 0.0 - 1.0
    bbox_x = Column(Float, nullable=False)
    bbox_y = Column(Float, nullable=False)
    bbox_ancho = Column(Float, nullable=False)
    bbox_alto = Column(Float, nullable=False)

    # Métricas del vehículo
    velocidad_kmh = Column(Float, nullable=True)
    direccion = Column(String(10), nullable=True)  # 'N', 'S', 'E', 'O'

    # Flags especiales
    es_emergencia = Column(Integer, default=0)  # 1=True, 0=False

    # Metadata adicional
    metadata_json = Column(JSON, nullable=True)

    # Relación
    interseccion = relationship("InterseccionDB")

    # Índice compuesto
    __table_args__ = (
        Index('idx_deteccion_video_track', 'video_path', 'track_id'),
        Index('idx_deteccion_interseccion_timestamp', 'interseccion_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<DeteccionVideo({self.clase}, track={self.track_id}, v={self.velocidad_kmh}km/h)>"
