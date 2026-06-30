"""
Validación y rechazo de comandos peligrosos
============================================

La ciberseguridad no es solo "tener contraseña": es proteger la OPERACIÓN. Antes
de aplicar cualquier parámetro recibido de la nube/operador, este validador
comprueba que sea seguro. Un verde de 200 s, un amarillo de 0 s, un modo
desconocido o un valor no numérico se RECHAZAN (no se aplican) y se auditan.

Los límites de tiempo provienen de la capa de seguridad funcional
(nucleo/seguridad_semaforica.py), que es la única fuente de verdad.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Asegurar acceso al paquete 'nucleo' (raíz del proyecto)
_RAIZ = Path(__file__).parent.parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from nucleo.seguridad_semaforica import validador_seguridad  # noqa: E402

MODOS_VALIDOS = ("simulador", "video", "sumo")
_RE_ESCENARIO = re.compile(r"^[a-z0-9_]{1,32}$")


def validar_parametros_control(params: Dict) -> Tuple[bool, List[str]]:
    """
    Valida un diccionario de parámetros de control. Devuelve (ok, errores).
    Combina la validación de tiempos (capa de seguridad funcional) con la de
    parámetros operativos (escenario, intervalo).
    """
    if not isinstance(params, dict) or len(params) == 0:
        return False, ["payload vacío o no es un objeto"]

    # 1) Tiempos semafóricos (verde/amarillo/todo-rojo/ciclo)
    _, errores = validador_seguridad.validar_parametros_control(params)
    errores = list(errores)

    # 2) Escenario (formato seguro)
    if "escenario" in params:
        esc = str(params["escenario"])
        if not _RE_ESCENARIO.match(esc):
            errores.append(f"escenario '{esc}' con formato no permitido")

    # 3) Intervalo de simulación
    if "intervalo" in params:
        try:
            iv = float(params["intervalo"])
            if iv <= 0 or iv > 10:
                errores.append(f"intervalo={iv:g}s fuera de rango (0, 10]")
        except (TypeError, ValueError):
            errores.append("intervalo no numérico")

    return (len(errores) == 0, errores)


def validar_modo(modo: str) -> Tuple[bool, List[str]]:
    """Valida un cambio de modo de operación."""
    if modo not in MODOS_VALIDOS:
        return False, [f"modo '{modo}' inválido; permitidos: {', '.join(MODOS_VALIDOS)}"]
    return True, []


def validar_emergencia(payload: Dict) -> Tuple[bool, List[str]]:
    """Valida el payload de activación de ola verde (defensa básica de entrada)."""
    errores: List[str] = []
    if not isinstance(payload, dict):
        return False, ["payload de emergencia inválido"]

    velocidad = payload.get("velocidad_kmh", payload.get("velocidad"))
    if velocidad is not None:
        try:
            v = float(velocidad)
            if v <= 0 or v > 140:
                errores.append(f"velocidad={v:g} km/h fuera de rango (0, 140]")
        except (TypeError, ValueError):
            errores.append("velocidad no numérica")

    tipo = payload.get("tipo")
    if tipo is not None and str(tipo) not in ("ambulancia", "bomberos", "policia", "emergencia"):
        errores.append(f"tipo de emergencia '{tipo}' no reconocido")

    return (len(errores) == 0, errores)
