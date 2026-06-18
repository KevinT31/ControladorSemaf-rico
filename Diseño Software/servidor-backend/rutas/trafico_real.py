"""Ruta API para el tráfico REAL del mundo (HERE), capa independiente de SUMO."""
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api", tags=["Tráfico real (HERE)"])


@router.get("/trafico-real")
async def trafico_real(
    oeste: Optional[float] = Query(None), sur: Optional[float] = Query(None),
    este: Optional[float] = Query(None), norte: Optional[float] = Query(None)
):
    """Devuelve segmentos de tráfico real (HERE) con color por jamFactor.

    Sin parámetros usa el bbox del escenario metropolitano por defecto.
    """
    from servicios.trafico_real_service import obtener_trafico_real, BBOX_DEFECTO

    bbox = None
    if None not in (oeste, sur, este, norte):
        bbox = (oeste, sur, este, norte)
    return obtener_trafico_real(bbox)


@router.get("/comparacion")
async def comparacion_sumo_vs_real():
    """Comparación SUMO (simulado) vs HERE (real) + estado de calibración.

    Devuelve la congestión simulada, la real (objetivo), la escala de demanda
    aplicada y el % de coincidencia. Lo consume el panel del mapa.
    """
    from servicios.calibracion_service import ultima_comparacion
    return ultima_comparacion()
