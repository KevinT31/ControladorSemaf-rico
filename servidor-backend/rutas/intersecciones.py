"""
Rutas API para gestión de Intersecciones
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime, timedelta

from modelos.interseccion import (
    InterseccionResponse,
    MetricasInterseccion,
    EstadisticasInterseccion
)
from modelos.respuestas import ListaResponse

router = APIRouter(
    prefix="/api/intersecciones",
    tags=["Intersecciones"]
)


@router.get("/", response_model=List[InterseccionResponse])
async def listar_intersecciones():
    """
    Lista todas las intersecciones del sistema

    Returns:
        Lista de intersecciones con sus datos completos
    """
    from servicios.interseccion_service import InterseccionService
    return InterseccionService.obtener_todas()


@router.get("/{interseccion_id}", response_model=InterseccionResponse)
async def obtener_interseccion(interseccion_id: str):
    """
    Obtiene una intersección específica por su ID

    Args:
        interseccion_id: ID único de la intersección

    Returns:
        Datos completos de la intersección
    """
    from servicios.interseccion_service import InterseccionService

    inter = InterseccionService.obtener_por_id(interseccion_id)
    if not inter:
        raise HTTPException(
            status_code=404,
            detail=f"Intersección {interseccion_id} no encontrada"
        )
    return inter


@router.get("/{interseccion_id}/metricas", response_model=MetricasInterseccion)
async def obtener_metricas(interseccion_id: str):
    """
    Obtiene métricas en tiempo real de una intersección

    Args:
        interseccion_id: ID único de la intersección

    Returns:
        Métricas actuales (ICV, flujo, velocidad, cola)
    """
    from servicios.interseccion_service import InterseccionService

    try:
        return InterseccionService.calcular_metricas(interseccion_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{interseccion_id}/estadisticas", response_model=EstadisticasInterseccion)
async def obtener_estadisticas(
    interseccion_id: str,
    horas: int = Query(default=24, ge=1, le=720, description="Horas hacia atrás")
):
    """
    Obtiene estadísticas agregadas de una intersección

    Args:
        interseccion_id: ID único de la intersección
        horas: Número de horas hacia atrás para el análisis (1-720)

    Returns:
        Estadísticas agregadas del período
    """
    from servicios.estadisticas_service import EstadisticasService

    periodo_fin = datetime.now()
    periodo_inicio = periodo_fin - timedelta(hours=horas)

    try:
        return EstadisticasService.calcular_estadisticas(
            interseccion_id,
            periodo_inicio,
            periodo_fin
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/zona/{zona}", response_model=List[InterseccionResponse])
async def listar_por_zona(zona: str):
    """
    Lista intersecciones filtradas por zona geográfica

    Args:
        zona: Zona geográfica (norte, sur, este, oeste, centro)

    Returns:
        Lista de intersecciones en la zona especificada
    """
    from servicios.interseccion_service import InterseccionService

    zonas_validas = ['norte', 'sur', 'este', 'oeste', 'centro']
    if zona.lower() not in zonas_validas:
        raise HTTPException(
            status_code=400,
            detail=f"Zona inválida. Debe ser una de: {zonas_validas}"
        )

    return InterseccionService.filtrar_por_zona(zona.lower())
