"""Triple compuerta de AUTOMATED_DIRECT_LAB (spec §10.3, decisión D-H).

El modo autónomo experimental SOLO puede activarse si coinciden LAS TRES
condiciones locales en el arranque del proceso:

1. ``allow_direct_lab: true`` en la configuración LOCAL del nodo;
2. flag CLI explícito ``--mode automated-direct-lab``;
3. variable de entorno ``NSB_CONFIRM_DIRECT_LAB`` con el ``node_id`` exacto
   del nodo que se autoriza (evita habilitar por accidente un nodo ajeno
   reutilizando un shell con la variable exportada).

NO existe (ni debe existir) ninguna ruta que active este modo por MQTT,
HTTP, archivo remoto o cambio en caliente: la verificación ocurre una sola
vez al construir el proceso y el modo solo puede DEGRADARSE después.
"""
from __future__ import annotations

import logging
import os

from nsb.domain.enums import Mode

logger = logging.getLogger(__name__)

ENV_CONFIRM = "NSB_CONFIRM_DIRECT_LAB"


class DirectLabDenied(PermissionError):
    """Activación de AUTOMATED_DIRECT_LAB denegada (compuertas incompletas)."""


def resolve_mode(config_mode: Mode, allow_direct_lab: bool,
                 cli_mode: Mode | None, node_id: str) -> Mode:
    """Resuelve el modo efectivo del proceso aplicando la triple compuerta.

    - `config_mode`: modo del YAML local.
    - `cli_mode`: modo pedido por CLI (None = usar el del YAML).
    - Para cualquier modo distinto de AUTOMATED_DIRECT_LAB no hay compuertas.
    - Para AUTOMATED_DIRECT_LAB se exigen las tres; si falta alguna se lanza
      DirectLabDenied (fallar ruidosamente, no degradar en silencio).
    """
    efectivo = cli_mode if cli_mode is not None else config_mode

    if efectivo is not Mode.AUTOMATED_DIRECT_LAB:
        return efectivo

    faltantes = []
    if not allow_direct_lab:
        faltantes.append("config local allow_direct_lab: true")
    if cli_mode is not Mode.AUTOMATED_DIRECT_LAB:
        faltantes.append("flag CLI --mode automated-direct-lab")
    confirm = os.environ.get(ENV_CONFIRM, "")
    if confirm != node_id:
        faltantes.append(
            f"variable de entorno {ENV_CONFIRM}={node_id!r} "
            f"(actual: {confirm!r})")

    if faltantes:
        raise DirectLabDenied(
            "AUTOMATED_DIRECT_LAB denegado; compuertas incompletas: "
            + "; ".join(faltantes))

    # Evento de alta importancia (spec §40): la activación debe quedar
    # inequívocamente registrada.
    logger.critical(
        "AUTOMATED_DIRECT_LAB ACTIVADO para node_id=%s — modo autónomo "
        "experimental de LABORATORIO con autoridad física local. "
        "Triple compuerta verificada (config + CLI + entorno).", node_id)
    return Mode.AUTOMATED_DIRECT_LAB
