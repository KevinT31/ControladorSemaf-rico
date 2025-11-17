"""
Rutas API para Vehículos de Emergencia y Olas Verdes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List

from modelos.emergencia import (
    VehiculoEmergenciaRequest,
    OlaVerdeResponse,
    OlaVerdeHistorial
)
from modelos.respuestas import MensajeResponse

router = APIRouter(
    prefix="/api/emergencia",
    tags=["Emergencias"]
)


@router.post("/activar", response_model=OlaVerdeResponse)
async def activar_ola_verde(request: VehiculoEmergenciaRequest):
    """
    Activa una ola verde para un vehículo de emergencia

    Args:
        request: Datos del vehículo y ruta de emergencia

    Returns:
        Información completa de la ola verde activada
    """
    from servicios.emergencia_service import EmergenciaService

    try:
        resultado = await EmergenciaService.activar_ola_verde(request)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error activando ola verde: {str(e)}")


@router.post("/desactivar/{vehiculo_id}", response_model=MensajeResponse)
async def desactivar_ola_verde(vehiculo_id: str):
    """
    Desactiva manualmente una ola verde activa

    Args:
        vehiculo_id: ID del vehículo de emergencia

    Returns:
        Mensaje de confirmación
    """
    from servicios.emergencia_service import EmergenciaService

    try:
        EmergenciaService.desactivar_ola_verde(vehiculo_id)
        return MensajeResponse(
            mensaje=f"Ola verde desactivada para vehículo {vehiculo_id}"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/activas", response_model=List[OlaVerdeResponse])
async def listar_olas_verdes_activas():
    """
    Lista todas las olas verdes actualmente activas

    Returns:
        Lista de olas verdes activas
    """
    from servicios.emergencia_service import EmergenciaService
    return EmergenciaService.obtener_activas()


@router.get("/historial", response_model=List[OlaVerdeHistorial])
async def obtener_historial(
    limite: int = Query(default=50, ge=1, le=500, description="Número máximo de registros")
):
    """
    Obtiene el historial de olas verdes activadas

    Args:
        limite: Número máximo de registros a retornar (1-500)

    Returns:
        Lista histórica de olas verdes
    """
    from servicios.emergencia_service import EmergenciaService
    return EmergenciaService.obtener_historial(limite)


@router.get("/estadisticas", response_model=dict)
async def obtener_estadisticas_emergencias():
    """
    Obtiene estadísticas generales sobre olas verdes

    Returns:
        Estadísticas agregadas (total activadas, tiempo promedio, etc.)
    """
    from servicios.emergencia_service import EmergenciaService
    return EmergenciaService.calcular_estadisticas()
