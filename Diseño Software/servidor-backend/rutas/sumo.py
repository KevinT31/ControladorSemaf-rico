"""
Rutas API para Integración con SUMO
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List

from modelos.trafico import MetricasSUMO
from modelos.respuestas import MensajeResponse

router = APIRouter(
    prefix="/api/sumo",
    tags=["Integración SUMO"]
)


@router.get("/calles", response_model=Dict)
async def obtener_calles_sumo():
    """
    Obtiene el GeoJSON con las calles de la red SUMO

    Returns:
        GeoJSON con la geometría de las calles
    """
    from servicios.sumo_service import SumoService

    try:
        geojson = SumoService.obtener_calles_geojson()
        return geojson
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Archivo de calles no encontrado. Ejecuta extraer_calles.py primero."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trafico", response_model=Dict)
async def obtener_trafico_actual():
    """
    Obtiene el estado actual del tráfico en las calles SUMO

    Returns:
        Estado de tráfico en todas las calles activas
    """
    from servicios.sumo_service import SumoService

    try:
        return SumoService.obtener_estado_trafico()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conectar", response_model=MensajeResponse)
async def conectar_sumo(
    ruta_config: str = Query(..., description="Ruta al archivo .sumocfg"),
    usar_gui: bool = Query(default=False, description="Usar interfaz gráfica")
):
    """
    Conecta al simulador SUMO

    Args:
        ruta_config: Ruta al archivo de configuración SUMO (.sumocfg)
        usar_gui: Si se debe usar la GUI de SUMO

    Returns:
        Mensaje de confirmación
    """
    from servicios.sumo_service import SumoService

    try:
        SumoService.conectar(ruta_config, usar_gui)
        return MensajeResponse(
            mensaje="Conectado a SUMO correctamente",
            datos={'ruta_config': ruta_config, 'gui': usar_gui}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/desconectar", response_model=MensajeResponse)
async def desconectar_sumo():
    """
    Desconecta del simulador SUMO

    Returns:
        Mensaje de confirmación
    """
    from servicios.sumo_service import SumoService

    try:
        SumoService.desconectar()
        return MensajeResponse(mensaje="Desconectado de SUMO")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exportar-historico", response_model=MensajeResponse)
async def exportar_datos_historicos(formato: str = Query(default="csv", regex="^(csv|parquet)$")):
    """
    Exporta datos de tráfico de SUMO a formato CSV o Parquet para ML

    Args:
        formato: Formato de exportación (csv o parquet)

    Returns:
        Mensaje con la ruta del archivo generado
    """
    from servicios.sumo_service import SumoService

    try:
        ruta_archivo = SumoService.exportar_historico(formato)
        return MensajeResponse(
            mensaje=f"Datos históricos exportados a {formato.upper()}",
            datos={'archivo': ruta_archivo, 'formato': formato}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metricas", response_model=MetricasSUMO)
async def obtener_metricas_sumo():
    """
    Obtiene métricas agregadas de la simulación SUMO actual

    Returns:
        Métricas generales de la red
    """
    from servicios.sumo_service import SumoService

    try:
        return SumoService.obtener_metricas()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/estado", response_model=Dict)
async def obtener_estado_sumo():
    """
    Obtiene el estado de la conexión con SUMO

    Returns:
        Estado de la conexión y simulación
    """
    from servicios.sumo_service import SumoService
    return SumoService.obtener_estado()
