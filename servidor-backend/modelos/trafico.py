"""
Modelos Pydantic para Datos de Tráfico y Video
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class EstadoTrafico(BaseModel):
    """Estado del tráfico en una calle o intersección"""
    edge_id: str = Field(..., description="ID de la calle/edge")
    timestamp: datetime
    num_vehiculos: int = Field(..., ge=0)
    velocidad_promedio: float = Field(..., ge=0)
    ocupacion: float = Field(..., ge=0, le=1, description="Ocupación de 0 a 1")
    tiempo_espera: float = Field(default=0.0, ge=0, description="Tiempo de espera en segundos")
    longitud_cola: Optional[float] = Field(default=0.0, ge=0)


class DeteccionVehiculo(BaseModel):
    """Detección individual de vehículo por YOLO"""
    clase: str = Field(..., description="Clase detectada (car, truck, bus, etc)")
    confianza: float = Field(..., ge=0, le=1, description="Confianza de la detección")
    bbox: List[float] = Field(..., description="Bounding box [x, y, width, height]", min_length=4, max_length=4)
    id_tracking: Optional[int] = Field(default=None, description="ID para seguimiento")


class ResultadoVideo(BaseModel):
    """Resultado del procesamiento de un frame de video"""
    interseccion_id: str
    frame_numero: int
    timestamp: datetime
    detecciones: List[DeteccionVehiculo]
    num_vehiculos: int = Field(..., ge=0)
    flujo_estimado: float = Field(..., ge=0, description="Vehículos/minuto")
    velocidad_promedio: float = Field(..., ge=0)
    longitud_cola: float = Field(..., ge=0)
    icv: float = Field(..., ge=0, le=1)
    clasificacion: str
    frame_base64: Optional[str] = Field(default=None, description="Frame procesado en base64")


class AnalisisVideoCSV(BaseModel):
    """Modelo para datos de CSV de análisis de video"""
    frame: int
    tiempo_s: float
    num_vehiculos: int
    flujo_veh_min: float
    velocidad_km_h: float
    longitud_cola_m: float
    emergencia: bool
    icv: float


class MetricasSUMO(BaseModel):
    """Métricas exportadas desde SUMO"""
    timestamp: datetime
    step: int
    edges: List[EstadoTrafico]
    total_vehiculos: int
    velocidad_promedio_red: float
    tiempo_viaje_promedio: float
