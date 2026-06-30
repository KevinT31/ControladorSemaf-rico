"""
Rutas de Parámetros de Control (actualización segura desde la nube/operador)
============================================================================
    GET  /api/control/parametros  -> parámetros base vigentes + límites de seguridad
    PUT  /api/control/parametros  -> actualiza parámetros (tecnico/admin), VALIDADO

Este es el punto donde la tesis cobra sentido en ciberseguridad: la nube/operador
"actualiza parámetros del controlador local", pero el módulo local VALIDA y
RECHAZA los comandos peligrosos (p.ej. un verde de 200 s) antes de aplicarlos,
y AUDITA cada intento.
"""

import sys
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException, Request, Depends

from estado_control import config_control
from seguridad.dependencias import requiere_rol
from seguridad.validador_comandos import validar_parametros_control
from seguridad.auditoria import registrar_evento

# Acceso a límites de seguridad (fuente única de verdad)
_RAIZ = Path(__file__).parent.parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))
from nucleo.seguridad_semaforica import LIMITES  # noqa: E402

router = APIRouter(prefix="/api/control", tags=["Control"])


def _limites_dict() -> Dict:
    return {
        "t_verde_min": LIMITES.T_VERDE_MIN,
        "t_verde_max": LIMITES.T_VERDE_MAX,
        "t_ambar_min": LIMITES.T_AMBAR_MIN,
        "t_todo_rojo_min": LIMITES.T_TODO_ROJO_MIN,
        "t_ciclo_min": LIMITES.T_CICLO_MIN,
        "t_ciclo_max": LIMITES.T_CICLO_MAX,
    }


@router.get("/parametros")
async def obtener_parametros_control():
    """Parámetros base vigentes del controlador y límites de seguridad."""
    return {"parametros": dict(config_control), "limites": _limites_dict()}


@router.put("/parametros")
async def actualizar_parametros_control(
    parametros: Dict,
    request: Request,
    usuario: dict = Depends(requiere_rol("tecnico", "admin")),
):
    """
    Actualiza los parámetros base del controlador. Rechaza (422) cualquier valor
    que viole los límites de seguridad funcional y lo registra en auditoría.
    """
    ip = request.client.host if request.client else ""
    ok, errores = validar_parametros_control(parametros)

    if not ok:
        registrar_evento(usuario["username"], usuario["rol"], "ACTUALIZAR_PARAMETROS",
                         "/api/control/parametros", "RECHAZADO", "; ".join(errores),
                         detalle=parametros, ip=ip)
        raise HTTPException(
            status_code=422,
            detail={"mensaje": "Comando rechazado por seguridad funcional",
                    "errores": errores})

    # Aplicar solo claves conocidas y numéricas
    aplicados = {}
    for clave, valor in parametros.items():
        if clave in config_control:
            try:
                config_control[clave] = float(valor)
                aplicados[clave] = config_control[clave]
            except (TypeError, ValueError):
                pass
        elif clave in ("escenario", "intervalo"):
            aplicados[clave] = valor  # operativos, no de tiempo

    registrar_evento(usuario["username"], usuario["rol"], "ACTUALIZAR_PARAMETROS",
                     "/api/control/parametros", "ACEPTADO", "parámetros aplicados",
                     detalle=aplicados, ip=ip)
    return {
        "mensaje": "Parámetros aplicados correctamente",
        "aplicados": aplicados,
        "parametros": dict(config_control),
    }
