"""Punto único de acceso de NSB a los límites de seguridad canónicos.

NSB NUNCA redefine límites: los importa de ``nucleo.seguridad_semaforica``,
que es la fuente única de verdad defendida en la tesis (Cap. 6/7). Este
módulo es el ÚNICO lugar de NSB autorizado a depender de nombres de ese
archivo, de modo que un cambio en el núcleo se absorbe aquí.

Además expone los techos operativos de ``clamp_tiempos`` (ámbar ≤ 6 s,
todo-rojo ≤ 5 s), que en el núcleo están embebidos en el método: la
validación de configuración de NSB debe respetarlos para no provocar
CLAMP permanente.
"""
from __future__ import annotations

import nsb._bootstrap  # noqa: F401  (garantiza importabilidad de `nucleo`)

from nucleo.seguridad_semaforica import (  # noqa: F401  (re-export deliberado)
    CONFIG_SEGURA,
    LIMITES,
    LimitesSeguridad,
    ValidadorSeguridadSemaforica,
    validador_seguridad,
    _es_numero_finito,
)

# Techos que clamp_tiempos aplica internamente (hardcoded en el núcleo).
# Si el núcleo los cambiara, actualizar SOLO aquí.
T_AMBAR_MAX = 6.0
T_TODO_ROJO_MAX = 5.0


def es_numero_finito(valor) -> bool:
    """Re-export público del helper privado del núcleo.

    Único punto de NSB que depende del nombre con guion bajo.
    """
    return _es_numero_finito(valor)
