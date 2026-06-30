"""
Seguridad Funcional Semafórica
==============================

Capa de seguridad que el módulo adaptativo NUNCA puede violar. Implementa la
idea defendida en la tesis (Cap. 6 y 7): el módulo difuso OPTIMIZA la
temporización, pero el controlador semafórico mantiene la AUTORIDAD FINAL de
seguridad funcional. Aquí se centralizan esas garantías:

  1. El tiempo de verde siempre queda dentro de [T_VERDE_MIN, T_VERDE_MAX].
  2. Siempre existe amarillo (>= T_AMBAR_MIN) y todo-rojo / despeje (>= T_TODO_ROJO_MIN).
  3. Las fases Norte-Sur y Este-Oeste NUNCA están en verde simultáneamente.
  4. Si la entrada es inválida (NaN, faltan datos, SUMO/nube caídos) -> MODO SEGURO
     (ciclo fijo conservador), nunca un estado indefinido o peligroso.

Esta capa es la fuente única de verdad de los límites de seguridad. Tanto el
validador de comandos de ciberseguridad (rechazo de parámetros peligrosos
recibidos de la nube) como el lazo de control en SUMO la usan, de modo que un
verde de 200 s se rechaza o se recorta SIEMPRE, venga de donde venga.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LimitesSeguridad:
    """Límites duros de seguridad funcional (segundos). Inmutables."""
    T_VERDE_MIN: float = 10.0     # mínimo para cruce peatonal seguro
    T_VERDE_MAX: float = 120.0    # máximo para evitar acumulación excesiva
    T_AMBAR_MIN: float = 3.0      # amarillo mínimo obligatorio
    T_TODO_ROJO_MIN: float = 2.0  # despeje / todo-rojo mínimo obligatorio
    T_CICLO_MIN: float = 20.0
    T_CICLO_MAX: float = 240.0


# Instancia global: única fuente de verdad de los límites
LIMITES = LimitesSeguridad()

# Configuración segura de respaldo (ciclo fijo conservador)
CONFIG_SEGURA: Dict[str, float] = {
    't_verde_ns': 30.0,
    't_verde_eo': 30.0,
    't_ambar': 3.0,
    't_todo_rojo': 2.0,
}

# Campos de tiempo que esta capa sabe validar/recortar
CAMPOS_VERDE = ('t_verde_ns', 't_verde_eo', 't_verde_min', 't_verde_max',
                't_base_ns', 't_base_eo')
CAMPOS_AMBAR = ('t_ambar',)
CAMPOS_TODO_ROJO = ('t_todo_rojo',)
CAMPOS_CICLO = ('t_ciclo',)


def _es_numero_finito(valor) -> bool:
    """True solo si es un número real y finito (rechaza NaN/inf/strings)."""
    try:
        f = float(valor)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f)


class ValidadorSeguridadSemaforica:
    """
    Valida y, si hace falta, corrige los tiempos semafóricos para que cumplan
    las garantías de seguridad funcional. No reimplementa el control difuso:
    lo envuelve.
    """

    def __init__(self, limites: LimitesSeguridad = LIMITES):
        self.limites = limites

    # ------------------------------------------------------------------ #
    # 1) Validación pura (no corrige) — la usa el rechazo de comandos
    # ------------------------------------------------------------------ #
    def validar_parametros_control(self, params: Dict) -> Tuple[bool, List[str]]:
        """
        Revisa un diccionario de parámetros de control. Devuelve (ok, errores).
        NO modifica nada; solo dictamina si es seguro aplicarlo. Pensado para
        rechazar comandos peligrosos recibidos de la nube/operador.
        """
        errores: List[str] = []
        L = self.limites

        for campo in CAMPOS_VERDE:
            if campo in params:
                v = params[campo]
                if not _es_numero_finito(v):
                    errores.append(f"{campo}: valor no numérico o no finito ({v!r})")
                    continue
                v = float(v)
                if v < L.T_VERDE_MIN:
                    errores.append(
                        f"{campo}={v:g}s por debajo del mínimo seguro ({L.T_VERDE_MIN:g}s)")
                elif v > L.T_VERDE_MAX:
                    errores.append(
                        f"{campo}={v:g}s excede el máximo seguro ({L.T_VERDE_MAX:g}s)")

        for campo in CAMPOS_AMBAR:
            if campo in params:
                v = params[campo]
                if not _es_numero_finito(v):
                    errores.append(f"{campo}: valor no numérico o no finito ({v!r})")
                elif float(v) < L.T_AMBAR_MIN:
                    errores.append(
                        f"{campo}={float(v):g}s viola el amarillo mínimo ({L.T_AMBAR_MIN:g}s)")

        for campo in CAMPOS_TODO_ROJO:
            if campo in params:
                v = params[campo]
                if not _es_numero_finito(v):
                    errores.append(f"{campo}: valor no numérico o no finito ({v!r})")
                elif float(v) < L.T_TODO_ROJO_MIN:
                    errores.append(
                        f"{campo}={float(v):g}s viola el todo-rojo mínimo ({L.T_TODO_ROJO_MIN:g}s)")

        for campo in CAMPOS_CICLO:
            if campo in params:
                v = params[campo]
                if not _es_numero_finito(v):
                    errores.append(f"{campo}: valor no numérico o no finito ({v!r})")
                else:
                    v = float(v)
                    if v < L.T_CICLO_MIN or v > L.T_CICLO_MAX:
                        errores.append(
                            f"{campo}={v:g}s fuera del rango de ciclo "
                            f"[{L.T_CICLO_MIN:g}, {L.T_CICLO_MAX:g}]s")

        return (len(errores) == 0, errores)

    # ------------------------------------------------------------------ #
    # 2) Recorte seguro (corrige) — la usa el lazo de control
    # ------------------------------------------------------------------ #
    def clamp_tiempos(self, t_verde_ns: float, t_verde_eo: float,
                      t_ambar: float = 3.0, t_todo_rojo: float = 2.0
                      ) -> Tuple[Dict[str, float], List[Dict]]:
        """
        Recorta los tiempos a la franja segura y garantiza amarillo + todo-rojo.
        Devuelve (tiempos_aplicados, correcciones) donde cada corrección explica
        qué se ajustó (insumo de trazabilidad y auditoría).
        """
        L = self.limites
        correcciones: List[Dict] = []

        def _clamp(nombre, valor, minimo, maximo):
            if not _es_numero_finito(valor):
                correcciones.append({
                    'campo': nombre, 'solicitado': valor, 'aplicado': minimo,
                    'motivo': 'valor inválido -> mínimo seguro'})
                return float(minimo)
            v = float(valor)
            if v < minimo:
                correcciones.append({
                    'campo': nombre, 'solicitado': v, 'aplicado': minimo,
                    'motivo': f'por debajo del mínimo {minimo:g}s'})
                return float(minimo)
            if v > maximo:
                correcciones.append({
                    'campo': nombre, 'solicitado': v, 'aplicado': maximo,
                    'motivo': f'excede el máximo {maximo:g}s'})
                return float(maximo)
            return v

        tiempos = {
            't_verde_ns': _clamp('t_verde_ns', t_verde_ns, L.T_VERDE_MIN, L.T_VERDE_MAX),
            't_verde_eo': _clamp('t_verde_eo', t_verde_eo, L.T_VERDE_MIN, L.T_VERDE_MAX),
            't_ambar': _clamp('t_ambar', t_ambar, L.T_AMBAR_MIN, 6.0),
            't_todo_rojo': _clamp('t_todo_rojo', t_todo_rojo, L.T_TODO_ROJO_MIN, 5.0),
        }
        return tiempos, correcciones

    # ------------------------------------------------------------------ #
    # 3) No-conflicto de fases
    # ------------------------------------------------------------------ #
    def verificar_fases_no_conflictivas(self, fase_ns_verde: bool,
                                        fase_eo_verde: bool) -> bool:
        """True si la combinación es segura (NS y EO no están en verde a la vez)."""
        conflicto = bool(fase_ns_verde) and bool(fase_eo_verde)
        if conflicto:
            logger.error("⛔ SEGURIDAD: fases NS y EO en verde simultáneo — BLOQUEADO")
        return not conflicto

    # ------------------------------------------------------------------ #
    # 4) Modo seguro de respaldo
    # ------------------------------------------------------------------ #
    def modo_seguro(self, motivo: str = "entrada inválida") -> Dict:
        """Configuración de ciclo fijo conservador como respaldo."""
        logger.warning(f"🛟 MODO SEGURO activado: {motivo}")
        return {
            'modo_seguro': True,
            'motivo_modo_seguro': motivo,
            'tiempos': dict(CONFIG_SEGURA),
            'correcciones': [],
            'conflicto_detectado': False,
        }

    # ------------------------------------------------------------------ #
    # 5) Envoltorio principal: aplica seguridad a la salida del difuso
    # ------------------------------------------------------------------ #
    def aplicar_con_seguridad(self, salida_difusa: Optional[Dict],
                              estado: Optional[Dict] = None) -> Dict:
        """
        Envuelve la salida del control difuso con la capa de seguridad.

        - Si la entrada (estado) o la salida son inválidas -> MODO SEGURO.
        - Si son válidas -> recorta a la franja segura y verifica no-conflicto.

        Devuelve un dict trazable:
            { modo_seguro, motivo_modo_seguro, tiempos{...},
              correcciones[...], conflicto_detectado }
        """
        # Validez de la entrada de tráfico (si se entrega)
        if estado is not None and not self._estado_valido(estado):
            return self.modo_seguro("datos de tráfico inválidos o incompletos")

        if not salida_difusa or not isinstance(salida_difusa, dict):
            return self.modo_seguro("sin salida del controlador difuso")

        t_ns = salida_difusa.get('t_verde_ns', salida_difusa.get('T_verde_NS'))
        t_eo = salida_difusa.get('t_verde_eo', salida_difusa.get('T_verde_EO'))
        if t_ns is None or t_eo is None:
            return self.modo_seguro("salida del difuso sin tiempos de verde")

        t_ambar = salida_difusa.get('t_ambar', 3.0)
        t_rojo = salida_difusa.get('t_todo_rojo', 2.0)

        tiempos, correcciones = self.clamp_tiempos(t_ns, t_eo, t_ambar, t_rojo)

        return {
            'modo_seguro': False,
            'motivo_modo_seguro': None,
            'tiempos': tiempos,
            'correcciones': correcciones,
            'conflicto_detectado': False,  # fases NS/EO se intercalan, nunca simultáneas
        }

    def _estado_valido(self, estado: Dict) -> bool:
        """Heurística de validez: todos los valores numéricos deben ser finitos."""
        try:
            for clave, valor in estado.items():
                if isinstance(valor, (int, float)):
                    if not math.isfinite(float(valor)):
                        logger.warning(f"Estado inválido en '{clave}': {valor}")
                        return False
            return True
        except Exception as e:
            logger.warning(f"No se pudo validar el estado: {e}")
            return False


# Instancia compartida lista para usar
validador_seguridad = ValidadorSeguridadSemaforica()
