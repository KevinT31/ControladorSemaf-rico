"""
Rutas API para control del Simulador de Tráfico
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Dict

from modelos.respuestas import MensajeResponse, EstadoSistemaResponse
from seguridad.dependencias import requiere_rol
from seguridad.validador_comandos import validar_parametros_control, validar_modo
from seguridad.auditoria import registrar_evento

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
async def cambiar_modo(modo: str, request: Request,
                       usuario: dict = Depends(requiere_rol('tecnico', 'admin'))):
    """
    Cambia el modo de operación del sistema (requiere rol tecnico/admin; auditado)

    Args:
        modo: Nuevo modo (simulador, video, sumo)

    Returns:
        Mensaje de confirmación
    """
    from servicios.simulacion_service import SimulacionService

    ip = request.client.host if request.client else ""
    ok, errores = validar_modo(modo)
    if not ok:
        registrar_evento(usuario.get('username'), usuario.get('rol'), 'CAMBIAR_MODO',
                         '/api/simulacion/modo/cambiar', 'RECHAZADO', '; '.join(errores),
                         detalle={'modo': modo}, ip=ip)
        raise HTTPException(
            status_code=400,
            detail=f"Modo inválido. Debe ser uno de: simulador, video, sumo"
        )

    try:
        await SimulacionService.cambiar_modo(modo)
        registrar_evento(usuario.get('username'), usuario.get('rol'), 'CAMBIAR_MODO',
                         '/api/simulacion/modo/cambiar', 'ACEPTADO', f"modo -> {modo}",
                         detalle={'modo': modo}, ip=ip)
        return MensajeResponse(
            mensaje=f"Modo cambiado a {modo} correctamente",
            datos={'modo': modo}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pausar", response_model=MensajeResponse)
async def pausar_simulacion(_usuario: dict = Depends(requiere_rol('tecnico', 'admin'))):
    """
    Pausa la simulación activa (requiere rol tecnico/admin)

    Returns:
        Mensaje de confirmación
    """
    from servicios.simulacion_service import SimulacionService

    SimulacionService.pausar()
    return MensajeResponse(mensaje="Simulación pausada")


@router.post("/reanudar", response_model=MensajeResponse)
async def reanudar_simulacion(_usuario: dict = Depends(requiere_rol('tecnico', 'admin'))):
    """
    Reanuda una simulación pausada (requiere rol tecnico/admin)

    Returns:
        Mensaje de confirmación
    """
    from servicios.simulacion_service import SimulacionService

    SimulacionService.reanudar()
    return MensajeResponse(mensaje="Simulación reanudada")


@router.post("/reiniciar", response_model=MensajeResponse)
async def reiniciar_simulacion(escenario: str = "hora_pico_manana",
                               _usuario: dict = Depends(requiere_rol('tecnico', 'admin'))):
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
async def actualizar_parametros(parametros: Dict, request: Request,
                                usuario: dict = Depends(requiere_rol('tecnico', 'admin'))):
    """
    Actualiza parámetros de la simulación (requiere rol tecnico/admin).

    Valida y RECHAZA parámetros peligrosos (p.ej. tiempos de verde fuera de los
    límites de seguridad) antes de aplicarlos, y audita cada intento.
    """
    from servicios.simulacion_service import SimulacionService

    ip = request.client.host if request.client else ""
    ok, errores = validar_parametros_control(parametros)
    if not ok:
        registrar_evento(usuario.get('username'), usuario.get('rol'), 'ACTUALIZAR_PARAMETROS',
                         '/api/simulacion/parametros', 'RECHAZADO', '; '.join(errores),
                         detalle=parametros, ip=ip)
        raise HTTPException(
            status_code=422,
            detail={"mensaje": "Comando rechazado por seguridad funcional",
                    "errores": errores})

    try:
        SimulacionService.actualizar_parametros(parametros)
        registrar_evento(usuario.get('username'), usuario.get('rol'), 'ACTUALIZAR_PARAMETROS',
                         '/api/simulacion/parametros', 'ACEPTADO', 'parámetros aplicados',
                         detalle=parametros, ip=ip)
        return MensajeResponse(
            mensaje="Parámetros actualizados correctamente",
            datos=parametros
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
