"""
Rutas API para control del Simulador de Tráfico
"""

from fastapi import APIRouter, HTTPException
from typing import Dict

from modelos.respuestas import MensajeResponse, EstadoSistemaResponse

router = APIRouter(
    prefix="/api/simulacion",
    tags=["Simulación"]
)


@router.get("/estado", response_model=EstadoSistemaResponse)
async def obtener_estado_sistema():
    """
    Obtiene el estado general del sistema

    Returns:
        Estado completo del sistema con modo activo
    """
    from servicios.simulacion_service import SimulacionService
    return SimulacionService.obtener_estado()


@router.post("/modo/cambiar", response_model=MensajeResponse)
async def cambiar_modo(modo: str):
    """
    Cambia el modo de operación del sistema

    Args:
        modo: Nuevo modo (simulador, video, sumo)

    Returns:
        Mensaje de confirmación
    """
    from servicios.simulacion_service import SimulacionService

    modos_validos = ['simulador', 'video', 'sumo']
    if modo not in modos_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Modo inválido. Debe ser uno de: {modos_validos}"
        )

    try:
        await SimulacionService.cambiar_modo(modo)
        return MensajeResponse(
            mensaje=f"Modo cambiado a {modo} correctamente",
            datos={'modo': modo}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pausar", response_model=MensajeResponse)
async def pausar_simulacion():
    """
    Pausa la simulación activa

    Returns:
        Mensaje de confirmación
    """
    from servicios.simulacion_service import SimulacionService

    SimulacionService.pausar()
    return MensajeResponse(mensaje="Simulación pausada")


@router.post("/reanudar", response_model=MensajeResponse)
async def reanudar_simulacion():
    """
    Reanuda una simulación pausada

    Returns:
        Mensaje de confirmación
    """
    from servicios.simulacion_service import SimulacionService

    SimulacionService.reanudar()
    return MensajeResponse(mensaje="Simulación reanudada")


@router.post("/reiniciar", response_model=MensajeResponse)
async def reiniciar_simulacion(escenario: str = "hora_pico_manana"):
    """
    Reinicia la simulación con un nuevo escenario

    Args:
        escenario: Nombre del escenario (hora_pico_manana, tarde, noche, etc)

    Returns:
        Mensaje de confirmación
    """
    from servicios.simulacion_service import SimulacionService

    try:
        SimulacionService.reiniciar(escenario)
        return MensajeResponse(
            mensaje=f"Simulación reiniciada con escenario {escenario}",
            datos={'escenario': escenario}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/parametros", response_model=Dict)
async def obtener_parametros():
    """
    Obtiene los parámetros actuales de la simulación

    Returns:
        Parámetros de configuración
    """
    from servicios.simulacion_service import SimulacionService
    return SimulacionService.obtener_parametros()


@router.put("/parametros", response_model=MensajeResponse)
async def actualizar_parametros(parametros: Dict):
    """
    Actualiza parámetros de la simulación

    Args:
        parametros: Diccionario con nuevos parámetros

    Returns:
        Mensaje de confirmación
    """
    from servicios.simulacion_service import SimulacionService

    try:
        SimulacionService.actualizar_parametros(parametros)
        return MensajeResponse(
            mensaje="Parámetros actualizados correctamente",
            datos=parametros
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
