"""
Rutas API para Vehículos de Emergencia y Olas Verdes
"""

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from typing import List

from modelos.emergencia import (
    VehiculoEmergenciaRequest,
    OlaVerdeResponse,
    OlaVerdeHistorial
)
from modelos.respuestas import MensajeResponse
from seguridad.dependencias import requiere_rol
from seguridad.auditoria import registrar_evento

router = APIRouter(
    prefix="/api/emergencia",
    tags=["Emergencias"]
)


@router.get("/ruta-optima")
async def ruta_optima_emergencia(
    origen_lat: float = Query(...), origen_lon: float = Query(...),
    destino_lat: float = Query(...), destino_lon: float = Query(...)
):
    """Ruta de emergencia CONSCIENTE DE LA CONGESTIÓN sobre la red SUMO.

    Devuelve la geometría (siguiendo calles) por el camino más despejado dado el
    tráfico actual, y los semáforos (controladores) que quedan en la ruta para
    abrirles la ola verde.
    """
    from servicios.ruta_emergencia import calcular_ruta_emergencia

    try:
        resultado = calcular_ruta_emergencia(
            (origen_lon, origen_lat), (destino_lon, destino_lat)
        )
        if not resultado:
            raise HTTPException(status_code=503, detail="SUMO no conectado o sin ruta")
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando ruta: {str(e)}")


@router.post("/activar", response_model=OlaVerdeResponse)
async def activar_ola_verde(request: VehiculoEmergenciaRequest, http: Request,
                            usuario: dict = Depends(requiere_rol('tecnico', 'admin'))):
    """
    Activa una ola verde para un vehículo de emergencia
    (requiere rol tecnico/admin; auditado)

    Args:
        request: Datos del vehículo y ruta de emergencia

    Returns:
        Información completa de la ola verde activada
    """
    from servicios.emergencia_service import EmergenciaService

    ip = http.client.host if http.client else ""
    try:
        detalle = request.model_dump() if hasattr(request, "model_dump") else dict(request)
    except Exception:
        detalle = {}

    try:
        resultado = await EmergenciaService.activar_ola_verde(request)
        registrar_evento(usuario.get('username'), usuario.get('rol'), 'ACTIVAR_OLA_VERDE',
                         '/api/emergencia/activar', 'ACEPTADO', 'ola verde activada',
                         detalle=detalle, ip=ip)
        return resultado
    except ValueError as e:
        msg = str(e)
        # Si el coordinador no está inicializado, esto es un error de servidor
        if 'Coordinador' in msg or 'coordinador' in msg:
            raise HTTPException(status_code=500, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error activando ola verde: {str(e)}")


@router.post("/estimar")
async def estimar_destinos(request: dict):
    """
    Estima tiempo/distancia para varios destinos sin activar la ola verde.

    Request JSON esperado: { "origen": "INT-001", "destinos": ["INT-007","INT-010"] }
    """
    try:
        origen = request.get('origen')
        destinos = request.get('destinos', [])
        from servicios.emergencia_service import EmergenciaService
        resultados = EmergenciaService.estimar_destinos(origen, destinos)
        return resultados
    except ValueError as e:
        msg = str(e)
        if 'Coordinador' in msg or 'coordinador' in msg:
            raise HTTPException(status_code=500, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error estimando destinos: {str(e)}")


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
