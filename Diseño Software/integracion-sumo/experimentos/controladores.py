"""
Controladores experimentales.

  - ControladorTiempoFijo     : programa estático 30/30 (línea base).
  - ControladorDifusoSUMO     : ICV+PI reales -> Mamdani Cap.6 -> verdes NS/EO.
  - ControladorDifusoPredictivo: igual que el difuso, pero el ICV que entra al
      Mamdani se mezcla con el ICV FUTURO predicho por la CNN-LSTM:
          ICV_control = (1-beta)*ICV_actual + beta*ICV_predicho
      con fallback ROBUSTO al difuso base ante cualquier anomalía. La IA nunca
      fija el verde directamente; solo anticipa la congestión.

Todos devuelven AccionControl; la envoltura de seguridad se aplica en el runner
(ninguna acción llega a SUMO sin pasar por nucleo.seguridad_semaforica).
"""
from __future__ import annotations

import logging
import math
from collections import deque
from typing import Dict, List, Optional

from .entorno import RAIZ_SOFTWARE  # noqa: F401  (asegura sys.path)
from .base import AccionControl, ControladorTrafico, EstadoInterseccion

from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 1) Tiempo fijo (línea base)
# --------------------------------------------------------------------------- #
class ControladorTiempoFijo(ControladorTrafico):
    tipo = 'fixed'

    def __init__(self, verde_ns: float = 30.0, verde_eo: float = 30.0):
        super().__init__()
        self.verde_ns = verde_ns
        self.verde_eo = verde_eo

    def decide(self, estado: EstadoInterseccion) -> AccionControl:
        # aplicar=False: el programa estático de la red ya es 30/30; no se toca.
        return AccionControl(self.verde_ns, self.verde_eo,
                             origen=self.tipo, aplicar=False)


# --------------------------------------------------------------------------- #
# 2) Difuso Mamdani (Capítulo 6) por dirección
# --------------------------------------------------------------------------- #
class ControladorDifusoSUMO(ControladorTrafico):
    tipo = 'fuzzy'

    def __init__(self, t_base: float = 30.0, t_ciclo: float = 70.0,
                 t_ambar: float = 3.0, t_todo_rojo: float = 2.0,
                 alpha_suavizado: float = 0.35):
        """
        alpha_suavizado: EMA sobre los verdes decididos entre intervalos
        (palanca validada en la comparación multibaseline; evita oscilaciones
        por ruido de sensado). alpha=1.0 desactiva el suavizado.
        """
        super().__init__()
        self.difuso = ControladorDifusoCapitulo6(
            T_base_NS=t_base, T_base_EO=t_base,
            T_ambar=t_ambar, T_todo_rojo=t_todo_rojo, T_ciclo=t_ciclo)
        self.alpha = alpha_suavizado
        self._ema: Optional[List[float]] = None

    def reset(self, contexto: Optional[Dict] = None):
        super().reset(contexto)
        self._ema = None

    # ICV que entra al Mamdani; el predictivo lo redefine para mezclar futuro
    def _icv_para_control(self, estado: EstadoInterseccion) -> Dict:
        return {'icv_ns': estado.ns.icv, 'icv_eo': estado.eo.icv,
                'fallback': False, 'motivo_fallback': None,
                'icv_pred_ns': None, 'icv_pred_eo': None, 'beta': 0.0}

    def decide(self, estado: EstadoInterseccion) -> AccionControl:
        entrada = self._icv_para_control(estado)

        resultado = self.difuso.calcular_control_completo(
            icv_ns=entrada['icv_ns'], pi_ns=estado.ns.pi, ev_ns=0.0,
            icv_eo=entrada['icv_eo'], pi_eo=estado.eo.pi, ev_eo=0.0)
        verde_ns = resultado['NS']['T_verde']
        verde_eo = resultado['EO']['T_verde']

        # Suavizado EMA entre decisiones (estabilidad del lazo)
        if self._ema is not None and 0.0 < self.alpha < 1.0:
            verde_ns = self.alpha * verde_ns + (1 - self.alpha) * self._ema[0]
            verde_eo = self.alpha * verde_eo + (1 - self.alpha) * self._ema[1]
        self._ema = [verde_ns, verde_eo]

        def _reglas(inferencia: Dict) -> List[str]:
            return [f"{r['descripcion']} (α={r['grado']:.2f})"
                    for r in inferencia['reglas_disparadas']]

        detalle = {
            'icv_actual_ns': estado.ns.icv, 'icv_actual_eo': estado.eo.icv,
            'icv_control_ns': entrada['icv_ns'], 'icv_control_eo': entrada['icv_eo'],
            'icv_pred_ns': entrada['icv_pred_ns'], 'icv_pred_eo': entrada['icv_pred_eo'],
            'beta': entrada['beta'],
            'fallback': entrada['fallback'],
            'motivo_fallback': entrada['motivo_fallback'],
            'pi_ns': estado.ns.pi, 'pi_eo': estado.eo.pi,
            'delta_pct_ns': resultado['NS']['delta_t_porcentaje'],
            'delta_pct_eo': resultado['EO']['delta_t_porcentaje'],
            'reglas_ns': _reglas(resultado['NS']['inferencia']),
            'reglas_eo': _reglas(resultado['EO']['inferencia']),
        }
        return AccionControl(verde_ns, verde_eo, origen=self.tipo, detalle=detalle)


# --------------------------------------------------------------------------- #
# 3) Difuso PREDICTIVO asistido por CNN-LSTM (la IA no reemplaza al difuso)
# --------------------------------------------------------------------------- #
class ControladorDifusoPredictivo(ControladorDifusoSUMO):
    tipo = 'fuzzy_predictive_ai'

    #: diferencia máxima tolerada entre ICV predicho y actual antes de descartar
    UMBRAL_DISCREPANCIA = 0.35

    def __init__(self, beta: float = 0.40, ventana: int = 8,
                 ruta_artefactos: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.beta = beta
        self.ventana = ventana
        self._buffer: deque = deque(maxlen=ventana)
        self._predictor = None
        self._error_carga: Optional[str] = None
        self._ruta_artefactos = ruta_artefactos
        self._cargar_predictor()

    def _cargar_predictor(self):
        try:
            from ia.inferencia import PredictorICV  # import perezoso (torch)
            self._predictor = PredictorICV.cargar(self._ruta_artefactos)
            logger.info('[fuzzy_predictive_ai] modelo CNN-LSTM cargado')
        except Exception as e:  # sin modelo/scalers/torch -> siempre fallback
            self._predictor = None
            self._error_carga = f'{type(e).__name__}: {e}'
            logger.warning(f'[fuzzy_predictive_ai] modelo NO disponible '
                           f'({self._error_carga}); se usará difuso base')

    @property
    def modelo_disponible(self) -> bool:
        return self._predictor is not None

    def reset(self, contexto: Optional[Dict] = None):
        super().reset(contexto)
        self._buffer.clear()

    def observe(self, estado: EstadoInterseccion):
        # El vector de características DEBE coincidir con ia.secuencias.CARACTERISTICAS
        self._buffer.append(self._vector_caracteristicas(estado))

    @staticmethod
    def _vector_caracteristicas(estado: EstadoInterseccion) -> List[float]:
        ns, eo = estado.ns, estado.eo
        return [ns.icv, eo.icv, ns.pi, eo.pi,
                ns.cola_veh, eo.cola_veh, ns.espera_s, eo.espera_s,
                ns.vel_kmh, eo.vel_kmh, ns.flujo_veh_min, eo.flujo_veh_min,
                ns.ocupacion, eo.ocupacion,
                estado.verde_actual_ns, estado.verde_actual_eo]

    def _icv_para_control(self, estado: EstadoInterseccion) -> Dict:
        """Combina ICV actual con el predicho, con cadena de fallbacks."""
        base = {'icv_ns': estado.ns.icv, 'icv_eo': estado.eo.icv,
                'icv_pred_ns': None, 'icv_pred_eo': None,
                'beta': 0.0, 'fallback': True, 'motivo_fallback': None}

        if self._predictor is None:
            base['motivo_fallback'] = f'modelo_no_disponible ({self._error_carga})'
            return base
        if len(self._buffer) < self.ventana:
            base['motivo_fallback'] = (
                f'buffer_insuficiente ({len(self._buffer)}/{self.ventana})')
            return base
        try:
            pred = self._predictor.predecir(list(self._buffer))
        except Exception as e:
            base['motivo_fallback'] = f'error_inferencia ({type(e).__name__}: {e})'
            return base

        icv_pred_ns, icv_pred_eo = float(pred[0]), float(pred[1])
        if not (math.isfinite(icv_pred_ns) and math.isfinite(icv_pred_eo)):
            base['motivo_fallback'] = 'prediccion_nan'
            return base
        if not (0.0 <= icv_pred_ns <= 1.0 and 0.0 <= icv_pred_eo <= 1.0):
            base['motivo_fallback'] = (
                f'prediccion_fuera_de_rango (ns={icv_pred_ns:.3f}, eo={icv_pred_eo:.3f})')
            return base
        if (abs(icv_pred_ns - estado.ns.icv) > self.UMBRAL_DISCREPANCIA or
                abs(icv_pred_eo - estado.eo.icv) > self.UMBRAL_DISCREPANCIA):
            base['motivo_fallback'] = (
                f'discrepancia_excesiva (>{self.UMBRAL_DISCREPANCIA})')
            base['icv_pred_ns'], base['icv_pred_eo'] = icv_pred_ns, icv_pred_eo
            return base

        b = self.beta
        return {
            'icv_ns': (1 - b) * estado.ns.icv + b * icv_pred_ns,
            'icv_eo': (1 - b) * estado.eo.icv + b * icv_pred_eo,
            'icv_pred_ns': icv_pred_ns, 'icv_pred_eo': icv_pred_eo,
            'beta': b, 'fallback': False, 'motivo_fallback': None,
        }


# --------------------------------------------------------------------------- #
# Registro / fábrica
# --------------------------------------------------------------------------- #
CONTROLADORES_DISPONIBLES = {
    'fixed': ControladorTiempoFijo,
    'fuzzy': ControladorDifusoSUMO,
    'fuzzy_predictive_ai': ControladorDifusoPredictivo,
}


def crear_controlador(tipo: str, **kwargs) -> ControladorTrafico:
    if tipo not in CONTROLADORES_DISPONIBLES:
        raise ValueError(f"Controlador desconocido: {tipo!r}. "
                         f"Disponibles: {sorted(CONTROLADORES_DISPONIBLES)}")
    return CONTROLADORES_DISPONIBLES[tipo](**kwargs)
