"""
Envoltura de seguridad funcional para el lazo experimental.

Reutiliza nucleo.seguridad_semaforica (fuente única de límites: verde 10-120 s,
amarillo >= 3 s, todo-rojo >= 2 s, modo seguro 30/30/3/2). NINGUNA acción llega
a SUMO sin pasar por aquí; toda corrección o rechazo queda registrada como
evento de seguridad trazable.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from .entorno import RAIZ_SOFTWARE  # noqa: F401  (asegura sys.path)
from .base import AccionControl, EstadoInterseccion

from nucleo.seguridad_semaforica import ValidadorSeguridadSemaforica, LIMITES


class EnvolturaSeguridad:
    """Filtra acciones de control con la capa de seguridad funcional."""

    def __init__(self):
        self.validador = ValidadorSeguridadSemaforica()
        self.eventos: List[Dict] = []

    def filtrar(self, accion: AccionControl,
                estado: Optional[EstadoInterseccion] = None,
                t_sim: float = 0.0) -> Tuple[AccionControl, Dict]:
        """Devuelve (acción segura, resultado de seguridad trazable)."""
        estado_plano = estado.como_dict_plano() if estado is not None else None
        salida_difusa = {'t_verde_ns': accion.verde_ns, 't_verde_eo': accion.verde_eo}
        resultado = self.validador.aplicar_con_seguridad(salida_difusa, estado_plano)

        tiempos = resultado['tiempos']
        segura = AccionControl(
            verde_ns=float(tiempos['t_verde_ns']),
            verde_eo=float(tiempos['t_verde_eo']),
            origen=accion.origen,
            aplicar=accion.aplicar,
            detalle=dict(accion.detalle),
        )
        segura.detalle['seguridad'] = {
            'modo_seguro': resultado['modo_seguro'],
            'motivo_modo_seguro': resultado['motivo_modo_seguro'],
            'correcciones': resultado['correcciones'],
        }

        if resultado['modo_seguro'] or resultado['correcciones']:
            self.eventos.append({
                't_sim': t_sim,
                'origen': accion.origen,
                'solicitado_ns': accion.verde_ns,
                'solicitado_eo': accion.verde_eo,
                'aplicado_ns': segura.verde_ns,
                'aplicado_eo': segura.verde_eo,
                'modo_seguro': resultado['modo_seguro'],
                'motivo': resultado['motivo_modo_seguro'] or '; '.join(
                    c['motivo'] for c in resultado['correcciones']),
            })
        return segura, resultado

    @staticmethod
    def limites() -> Dict[str, float]:
        return {
            'verde_min': LIMITES.T_VERDE_MIN, 'verde_max': LIMITES.T_VERDE_MAX,
            'ambar_min': LIMITES.T_AMBAR_MIN, 'todo_rojo_min': LIMITES.T_TODO_ROJO_MIN,
            'ciclo_min': LIMITES.T_CICLO_MIN, 'ciclo_max': LIMITES.T_CICLO_MAX,
        }

    @staticmethod
    def es_finito(x) -> bool:
        try:
            return math.isfinite(float(x))
        except (TypeError, ValueError):
            return False
