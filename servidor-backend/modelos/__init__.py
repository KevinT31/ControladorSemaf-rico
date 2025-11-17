"""
Modelos Pydantic para validación de datos del sistema
"""

from .interseccion import (
    InterseccionBase,
    InterseccionCreate,
    InterseccionResponse,
    MetricasInterseccion
)

from .emergencia import (
    VehiculoEmergenciaRequest,
    VehiculoEmergenciaResponse,
    OlaVerdeResponse
)

from .trafico import (
    EstadoTrafico,
    DeteccionVehiculo,
    ResultadoVideo
)

from .respuestas import (
    EstadoSistemaResponse,
    MensajeResponse,
    ErrorResponse
)

__all__ = [
    # Intersecciones
    'InterseccionBase',
    'InterseccionCreate',
    'InterseccionResponse',
    'MetricasInterseccion',

    # Emergencias
    'VehiculoEmergenciaRequest',
    'VehiculoEmergenciaResponse',
    'OlaVerdeResponse',

    # Tráfico
    'EstadoTrafico',
    'DeteccionVehiculo',
    'ResultadoVideo',

    # Respuestas
    'EstadoSistemaResponse',
    'MensajeResponse',
    'ErrorResponse'
]
