"""
Modelos Pydantic para Respuestas Generales de la API
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class MensajeResponse(BaseModel):
    """Respuesta simple con mensaje"""
    mensaje: str
    timestamp: datetime = Field(default_factory=datetime.now)
    datos: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Respuesta de error estandarizada"""
    error: str
    detalle: Optional[str] = None
    codigo: str = Field(..., description="Código de error (ej: INTERSECCION_NO_ENCONTRADA)")
    timestamp: datetime = Field(default_factory=datetime.now)
    path: Optional[str] = None


class EstadoSistemaResponse(BaseModel):
    """Estado general del sistema"""
    modo: str = Field(..., description="Modo actual: simulador, video, o sumo")
    num_intersecciones: int = Field(..., ge=0)
    intersecciones: List[Dict[str, Any]]
    simulador_activo: bool = False
    video_activo: bool = False
    sumo_activo: bool = False
    websocket_conexiones: int = Field(default=0, ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)


class PaginacionResponse(BaseModel):
    """Metadatos de paginación"""
    pagina_actual: int = Field(..., ge=1)
    total_paginas: int = Field(..., ge=0)
    total_items: int = Field(..., ge=0)
    items_por_pagina: int = Field(..., ge=1, le=1000)
    tiene_siguiente: bool
    tiene_anterior: bool


class ListaResponse(BaseModel):
    """Respuesta genérica para listas con paginación"""
    datos: List[Any]
    paginacion: Optional[PaginacionResponse] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthCheckResponse(BaseModel):
    """Respuesta de health check"""
    status: str = Field(default="ok")
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.now)
    servicios: Dict[str, str] = Field(default_factory=dict)
    # servicios = {
    #     "base_datos": "ok",
    #     "simulador": "ok",
    #     "video": "ok",
    #     "sumo": "no_disponible"
    # }
