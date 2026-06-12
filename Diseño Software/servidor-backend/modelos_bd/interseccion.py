"""
Modelo de Intersección para la base de datos
"""

from sqlalchemy import Column, String, Float, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class InterseccionDB(Base):
    """
    Tabla de intersecciones del sistema
    Representa cada semáforo en la red de Lima
    """
    __tablename__ = "intersecciones"

    id = Column(String(20), primary_key=True, index=True)  # ej: "LC-001"
    nombre = Column(String(200), nullable=False)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    num_carriles = Column(Integer, nullable=False, default=4)
    zona = Column(String(100), nullable=False)  # ej: "Centro Histórico"

    # Metadata adicional
    metadata_json = Column(JSON, nullable=True)  # Datos extra flexibles

    # Timestamps
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    metricas = relationship("MetricaTrafico", back_populates="interseccion")
    olas_verdes_origen = relationship(
        "OlaVerde",
        foreign_keys="OlaVerde.interseccion_origen_id",
        back_populates="interseccion_origen"
    )
    olas_verdes_destino = relationship(
        "OlaVerde",
        foreign_keys="OlaVerde.interseccion_destino_id",
        back_populates="interseccion_destino"
    )

    def __repr__(self):
        return f"<InterseccionDB(id={self.id}, nombre={self.nombre})>"


class ConexionInterseccionDB(Base):
    """
    Tabla de conexiones entre intersecciones (grafo de red vial)
    """
    __tablename__ = "conexiones_intersecciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    interseccion_origen_id = Column(String(20), ForeignKey('intersecciones.id'), nullable=False)
    interseccion_destino_id = Column(String(20), ForeignKey('intersecciones.id'), nullable=False)
    distancia_metros = Column(Float, nullable=False)
    tiempo_promedio_segundos = Column(Float, nullable=True)
    bidireccional = Column(Integer, default=1)  # 1=True, 0=False

    # Timestamps
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ConexionDB({self.interseccion_origen_id} → {self.interseccion_destino_id}, {self.distancia_metros}m)>"
