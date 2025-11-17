"""
Modelos Pydantic para Intersecciones
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime


class InterseccionBase(BaseModel):
    """Modelo base de Intersección"""
    id: str = Field(..., description="ID único de la intersección", min_length=3, max_length=20)
    nombre: str = Field(..., description="Nombre descriptivo", min_length=5, max_length=200)
    latitud: float = Field(..., description="Latitud GPS", ge=-90, le=90)
    longitud: float = Field(..., description="Longitud GPS", ge=-180, le=180)
    num_carriles: int = Field(..., description="Número de carriles", ge=1, le=20)
    zona: str = Field(..., description="Zona geográfica")

    @field_validator('zona')
    @classmethod
    def validar_zona(cls, v: str) -> str:
        zonas_validas = ['norte', 'sur', 'este', 'oeste', 'centro']
        if v.lower() not in zonas_validas:
            raise ValueError(f'Zona debe ser una de: {zonas_validas}')
        return v.lower()


class InterseccionCreate(InterseccionBase):
    """Modelo para crear nueva intersección"""
    pass


class InterseccionResponse(InterseccionBase):
    """Modelo de respuesta con datos completos"""
    vecinos: List[str] = Field(default_factory=list, description="IDs de intersecciones vecinas")
    distancia_vecinos: Dict[str, float] = Field(default_factory=dict, description="Distancias a vecinos")
    activo: bool = Field(default=True, description="Estado de la intersección")
    fecha_instalacion: Optional[datetime] = None

    class Config:
        from_attributes = True


class MetricasInterseccion(BaseModel):
    """Métricas en tiempo real de una intersección"""
    interseccion_id: str
    timestamp: str
    num_vehiculos: int = Field(..., ge=0)
    flujo_vehicular: float = Field(..., ge=0, description="Vehículos/minuto")
    velocidad_promedio: float = Field(..., ge=0, le=150, description="km/h")
    longitud_cola: float = Field(..., ge=0, description="Metros")
    icv: float = Field(..., ge=0, le=1, description="Índice de Congestión Vehicular")
    clasificacion_icv: str = Field(..., description="Fluido, Moderado, o Congestionado")
    color_icv: str = Field(..., description="Color para visualización")
    fuente: str = Field(default="simulador", description="Origen de datos")

    @field_validator('clasificacion_icv')
    @classmethod
    def validar_clasificacion(cls, v: str) -> str:
        validos = ['fluido', 'moderado', 'congestionado']
        if v.lower() not in validos:
            raise ValueError(f'Clasificación debe ser una de: {validos}')
        return v.lower()


class EstadisticasInterseccion(BaseModel):
    """Estadísticas agregadas de una intersección"""
    interseccion_id: str
    periodo_inicio: datetime
    periodo_fin: datetime
    icv_promedio: float
    icv_maximo: float
    icv_minimo: float
    velocidad_promedio: float
    flujo_promedio: float
    total_vehiculos: int
    horas_congestion: float
    porcentaje_congestion: float
