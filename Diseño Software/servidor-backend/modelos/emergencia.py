"""
Modelos Pydantic para Vehículos de Emergencia y Olas Verdes
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class TipoVehiculo(str, Enum):
    """Tipos de vehículos de emergencia"""
    AMBULANCIA = "ambulancia"
    BOMBEROS = "bomberos"
    POLICIA = "policia"


class PrioridadEmergencia(str, Enum):
    """Niveles de prioridad"""
    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"


class VehiculoEmergenciaRequest(BaseModel):
    """Request para activar ola verde"""
    tipo: TipoVehiculo = Field(..., description="Tipo de vehículo de emergencia")
    origen: str = Field(..., description="ID de intersección origen", min_length=3)
    destino: str = Field(..., description="ID de intersección destino", min_length=3)
    velocidad: float = Field(default=50.0, description="Velocidad estimada en km/h", ge=20, le=120)
    prioridad: Optional[PrioridadEmergencia] = Field(default=PrioridadEmergencia.ALTA)

    @field_validator('origen', 'destino')
    @classmethod
    def validar_no_vacio(cls, v: str) -> str:
        if not v or v.strip() == '':
            raise ValueError('Origen y destino no pueden estar vacíos')
        return v.strip()


class VehiculoEmergenciaResponse(BaseModel):
    """Respuesta con datos del vehículo de emergencia"""
    id: str
    tipo: TipoVehiculo
    interseccion_actual: str
    destino: str
    velocidad_estimada: float
    prioridad: str
    timestamp: datetime

    class Config:
        from_attributes = True


class OlaVerdeResponse(BaseModel):
    """Respuesta completa de activación de ola verde"""
    vehiculo: VehiculoEmergenciaResponse
    ruta: List[str] = Field(..., description="Lista ordenada de IDs de intersecciones")
    distancia_total: float = Field(..., description="Distancia total en metros")
    tiempo_estimado: float = Field(..., description="Tiempo estimado en segundos")
    semaforos_sincronizados: int = Field(..., description="Número de semáforos en verde")
    mensaje: str = Field(default="Ola verde activada correctamente")
    timestamp_activacion: datetime = Field(default_factory=datetime.now)


class OlaVerdeHistorial(BaseModel):
    """Registro histórico de ola verde"""
    id: int
    vehiculo_id: str
    tipo_vehiculo: str
    origen_id: str
    destino_id: str
    ruta: List[str]
    velocidad_estimada: float
    distancia_total: float
    tiempo_total: Optional[float]
    timestamp_activacion: datetime
    timestamp_desactivacion: Optional[datetime]
    completado: bool = False

    class Config:
        from_attributes = True
