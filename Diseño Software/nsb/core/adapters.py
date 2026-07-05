"""Adaptadores del núcleo científico canónico (spec §19).

REGLA: cero copia de lógica científica. Estos adaptadores solo traducen entre
los contratos de NSB (`nsb.domain.contracts`) y las firmas del núcleo
(`nucleo/`). Cualquier cambio de fórmula pertenece al núcleo, no aquí.

Colisión de nombres conocida: existen DOS clases `ParametrosInterseccion`
(en `indice_congestion` y en `estado_local`) con campos distintos. Aquí se
importa SIEMPRE con alias explícito para evitar el error.
"""
from __future__ import annotations

from typing import Dict, Tuple

import nsb._bootstrap  # noqa: F401

from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6
from nucleo.indice_congestion import (
    CalculadorICV,
    ParametrosInterseccion as ParametrosICV,  # alias: ver docstring
)

from nsb.domain.contracts import ApproachState, PlanSemaforico

# Velocidad de referencia del PI de eficiencia. MISMO valor (50 km/h) que
# `integracion-sumo/comparacion_sumo._demanda_fase`, que es el cálculo que
# alimentó al difuso en los resultados multibaseline de la tesis (ver D-D).
VEL_REF_KMH = 50.0


class AdaptadorICV:
    """Calcula (ICV, PI) por dirección a partir de un ApproachState.

    - ICV: `CalculadorICV.calcular` canónico (fórmula heredada, [0,1]).
    - PI: eficiencia acotada [0,1] = 0.5·fracción_en_movimiento +
      0.5·min(1, v/50) — idéntico al usado en los resultados de tesis (D-D).
    """

    def __init__(self, params: ParametrosICV | None = None):
        self._calc = CalculadorICV(params or ParametrosICV())

    def indicadores(self, a: ApproachState) -> Tuple[float, float]:
        """Devuelve (icv, pi) para una dirección."""
        resultado = self._calc.calcular(
            longitud_cola=a.queue_m,
            velocidad_promedio=a.speed_kmh,
            flujo_vehicular=a.flow_veh_min,
            num_vehiculos=a.num_vehicles,
        )
        icv = float(resultado['icv'])

        moving = max(0, a.num_vehicles - a.stopped_vehicles)
        frac_mov = (moving / a.num_vehicles) if a.num_vehicles else 1.0
        vel_norm = min(1.0, a.speed_kmh / VEL_REF_KMH)
        pi = 0.5 * frac_mov + 0.5 * vel_norm
        return icv, pi


class AdaptadorDifuso:
    """Envuelve `ControladorDifusoCapitulo6` (Mamdani, 12 reglas, ΔT%).

    Los tiempos base/ámbar/todo-rojo/ciclo vienen de la configuración del
    nodo (validada contra LIMITES al cargar); los límites internos del
    controlador (T_verde_min/max) son los de la tesis y no se tocan.
    """

    def __init__(self, t_base_ns: float = 30.0, t_base_eo: float = 30.0,
                 t_ambar: float = 3.0, t_todo_rojo: float = 2.0,
                 t_ciclo: float = 90.0):
        self._difuso = ControladorDifusoCapitulo6(
            T_base_NS=t_base_ns,
            T_base_EO=t_base_eo,
            T_ambar=t_ambar,
            T_todo_rojo=t_todo_rojo,
            T_ciclo=t_ciclo,
        )

    @property
    def controlador(self) -> ControladorDifusoCapitulo6:
        """Acceso de solo lectura al controlador canónico (golden master)."""
        return self._difuso

    def decidir_plan(self, icv_ns: float, pi_ns: float, ev_ns: float,
                     icv_eo: float, pi_eo: float, ev_eo: float
                     ) -> Tuple[PlanSemaforico, Dict]:
        """Ejecuta el control completo canónico y lo traduce a PlanSemaforico.

        Devuelve (plan, detalle) donde `detalle` es el dict crudo de
        `calcular_control_completo` (trazabilidad: deltas, reglas, inferencia).
        """
        control = self._difuso.calcular_control_completo(
            icv_ns=icv_ns, pi_ns=pi_ns, ev_ns=ev_ns,
            icv_eo=icv_eo, pi_eo=pi_eo, ev_eo=ev_eo,
        )
        plan = PlanSemaforico(
            t_verde_ns=control['NS']['T_verde'],
            t_verde_eo=control['EO']['T_verde'],
            t_ambar=self._difuso.T_ambar,
            t_todo_rojo=self._difuso.T_todo_rojo,
        )
        return plan, control

    @staticmethod
    def reglas_como_texto(control: Dict) -> list[str]:
        """Aplana las reglas disparadas de ambas direcciones a strings
        trazables (p. ej. "NS:R1: Emergencia + Congestión alta (0.83)")."""
        salida: list[str] = []
        for direccion in ('NS', 'EO'):
            inferencia = control.get(direccion, {}).get('inferencia', {})
            for regla in inferencia.get('reglas_disparadas', []):
                salida.append(
                    f"{direccion}:{regla['descripcion']} "
                    f"({regla['grado']:.3f})")
        return salida
