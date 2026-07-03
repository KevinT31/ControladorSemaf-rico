# -*- coding: utf-8 -*-
"""
Controlador DIFUSO+IA acíclico para redes SUMO (estrategia 'difuso_ia').

Motivación (benchmark multibaseline): el difuso cíclico solo REDISTRIBUYE el
verde dentro de un ciclo fijo, por lo que sirve fases vacías y pierde contra
actuated (gap-out) y max-pressure (acíclico). Este controlador da al difuso
las mismas capacidades estructurales, manteniendo la interpretabilidad y
añadiendo anticipación por CNN-LSTM:

  1) SELECCIÓN DE FASE (acíclica): al expirar el verde se sirve la fase de
     mayor demanda;  demanda = (1-β)·cola_actual + β·cola_predicha (CNN-LSTM).
     Con β=0 es un difuso acíclico puro (sin IA).
  2) DURACIÓN DEL VERDE: Mamdani Cap.6 (ICV+PI reales de la fase elegida)
     -> delta% -> T_verde, acotado por la guardia de seguridad. El término
     de flujo del ICV usa CRUCES reales por ventana (ContadorCruces), no
     vehículos presentes.
  3) GAP-OUT: si la fase servida se vació y no llegan vehículos, el verde
     termina temprano (nunca antes del mínimo de seguridad).
  4) ANTI-INANICIÓN: se re-evalúa DURANTE el verde (cada `starve_check_s`).
     Cota de espera de una fase con cola: t_starve + t_ambar + starve_check_s
     si el verde en curso ya superó su mínimo; en el peor caso (verde recién
     iniciado) t_starve + t_verde_min + t_ambar.
  5) TRANSICIÓN SEGURA: siempre ámbar (>= T_AMBAR_MIN) entre verdes
     distintos; si el programa del TLS no define fase 'y', se SINTETIZA un
     estado de ámbar (nunca cambio directo verde->verde). Si el programa
     define fase de despeje (todo-rojo) tras el ámbar, se respeta.

La IA NUNCA fija el verde: solo anticipa la cola por fase; ante cualquier
anomalía (modelo ausente, buffer incompleto, NaN) la mezcla cae a β=0 y el
motivo queda contado y trazado. Con `log_ia` se registra CADA inferencia
(entrada agregada, predicción, veto/abstención, régimen, latencia) para
poder auditar post-hoc si cada intervención ayudó o perjudicó.
"""
from __future__ import annotations

import logging
import math
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from conector_sumo import traci
from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion
from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6
from nucleo.seguridad_semaforica import LIMITES as _LIM

import comparacion_sumo as C

logger = logging.getLogger(__name__)

# ----------------------------- parámetros ----------------------------- #
PARAMS_DEFECTO = {
    'modo_ia': 'guardia',   # 'off'    : difuso acíclico puro (sin CNN-LSTM)
                            # 'guardia': skip solo si actual Y predicha bajas
                            #            + extensión por crecimiento previsto
                            # 'mezcla' : cola_ef=(1-β)·actual+β·pred (histórico)
                            # 'sombra' : predice y REGISTRA pero nunca actúa
                            #            (medición del aporte sin intervenir)
    'beta': 0.0,            # peso de la predicción (solo modo 'mezcla')
    't_base': 25.0,         # verde base del Mamdani (s)
    't_verde_min': float(_LIM.T_VERDE_MIN),   # 10 s
    't_verde_max': 45.0,    # tope operativo (< T_VERDE_MAX de seguridad)
    't_ambar': 3.0,         # >= T_AMBAR_MIN (se valida en __init__)
    't_todo_rojo': 0.0,     # despeje SINTÉTICO tras el ámbar (s); 0 = solo se
                            # sirve el todo-rojo que el programa defina
    't_starve': 45.0,       # espera máxima tolerada de una fase con demanda (s)
    'starve_check_s': 5,    # cadencia del chequeo de inanición DURANTE verde
    'gap_umbral_s': 2.0,    # segundos seguidos sin demanda para gap-out
    'gap_considera_mov': False,  # True: el gap-out además exige 0 vehículos en
                            # movimiento (no corta verde con pelotón cruzando)
    'w_mov': 0.4,           # peso de vehículos en movimiento en la demanda
    'umbral_skip': 1.0,     # demanda efectiva mínima para servir una fase
    'k_ext_cola': 1.0,      # s extra de verde por vehículo en cola (cap 12 s)
    'ia_veto': True,        # guardia: la cola predicha veta saltos de fase
    'ia_margen_veto': 0.0,  # margen de confianza (veh): la cola predicha debe
                            # superar umbral_skip en al menos este margen para
                            # vetar. El MAE de test es ~0.43 veh: margen>0
                            # suprime vetos atribuibles a ruido de predicción.
    'ia_ext': False,        # extensión por crecimiento previsto (ablación:
                            # no aporta en MEDIA y daña en ALTA; se conserva
                            # solo como palanca de investigación)
    'ia_gate_sat': 6.0,     # veh: la IA solo interviene si la saturación
                            # SOSTENIDA (EMA de la suma de colas del cruce)
                            # es <= este umbral. En saturación las políticas
                            # reactivas son casi óptimas y anticipar desvía
                            # verde; la IA "sabe cuándo no intervenir".
    'ia_gate_alpha': 0.15,  # suavizado del detector de régimen local (EMA)
    'ia_gate_dens': 4.0,    # veh en red POR CRUCE controlado (densidad de
                            # red, cf. diagrama fundamental macroscópico):
                            # sobre este nivel la red opera saturada y la
                            # anticipación desvía verde -> IA global off.
                            # Instantáneo (sin retardo) y no lo enmascara el
                            # propio control (las colas sí).
    'grid_s': 15,           # rejilla de muestreo para los buffers de la IA
    'ventana': 8,           # W de la CNN-LSTM de fases
    'ruta_artefactos': None,   # carpeta de artefactos IA (None = defecto)
    'recolector': None,     # ruta CSV: si se da, registra series por fase
    'log_ia': None,         # ruta CSV: traza por DECISIÓN e INFERENCIA
                            # (cola actual/predicha por fase, veto, gate,
                            # régimen, fallback, latencia) + muestras de
                            # rejilla para evaluar vetos post-hoc
    'medidor_flujo': None,  # comparacion_sumo.ContadorCruces compartido: flujo
                            # REAL (cruces/ventana) para el término del ICV
}

CARACTERISTICAS_FASE = ['cola_n', 'nveh_n', 'ocupacion', 'vel_n',
                        'verde_activa', 'espera_fase_n']
# Normalización canónica (fuente única: ia.secuencias_fase). El fallback local
# permite operar sin el paquete ia instalado (modo_ia='off').
try:
    from ia.secuencias_fase import NORMALIZACION_FASE
except Exception:                                    # pragma: no cover
    NORMALIZACION_FASE = {'cola_veh': 30.0, 'nveh': 40.0,
                          'vel_kmh': 50.0, 'espera_s': 120.0}
COLA_NORM = float(NORMALIZACION_FASE['cola_veh'])
NVEH_NORM = float(NORMALIZACION_FASE['nveh'])
VEL_NORM_KMH = float(NORMALIZACION_FASE['vel_kmh'])
ESPERA_NORM_S = float(NORMALIZACION_FASE['espera_s'])

_CAMPOS_LOG = ['evento', 't', 'tls', 'fase_idx', 'cola_veh', 'cola_pred_veh',
               'demanda_ef', 'seleccionada', 'vetada', 'gate', 'sat_ema',
               'dens_red', 'latencia_ms', 'dur_s', 'fallback', 'modo']


def _medir_fase(lanes: List[str], stats: Optional[dict] = None
                ) -> Tuple[float, float, float, float]:
    """(cola_veh, n_veh, ocupacion_media, vel_kmh) reales de una fase.

    Un carril ilegible NO se ignora en silencio: se cuenta en
    stats['fallos_sensor'] (subconteo trazable, no invisible).
    """
    cola = 0
    n = 0
    ocup = 0.0
    suma_v = 0.0
    for ln in lanes:
        try:
            k = traci.lane.getLastStepVehicleNumber(ln)
            n += k
            cola += traci.lane.getLastStepHaltingNumber(ln)
            ocup += traci.lane.getLastStepOccupancy(ln)
            suma_v += traci.lane.getLastStepMeanSpeed(ln) * k
        except Exception:
            if stats is not None:
                stats['fallos_sensor'] = stats.get('fallos_sensor', 0) + 1
            continue
    n_lanes = max(1, len(lanes))
    vel_kmh = (suma_v / n * 3.6) if n else 0.0
    return float(cola), float(n), ocup / n_lanes, vel_kmh


class ControladorDifusoIA:
    """Máquina de estados por semáforo: verde -> (gap-out|expira|inanición)
    -> ámbar (-> todo-rojo si el programa lo define) -> verde."""

    def __init__(self, info: dict, params: Optional[dict] = None):
        self.p = dict(PARAMS_DEFECTO)
        if params:
            self.p.update(params)
        # invariantes de seguridad sobre los parámetros (no negociables)
        self.p['t_ambar'] = max(float(self.p['t_ambar']), _LIM.T_AMBAR_MIN)
        if float(self.p['t_todo_rojo']) > 0.0:
            self.p['t_todo_rojo'] = max(float(self.p['t_todo_rojo']),
                                        _LIM.T_TODO_ROJO_MIN)
        self.info = {tls: d for tls, d in info.items()
                     if len(d['fases_verdes']) >= 2}
        # carriles de SALIDA por fase (término de presión, Varaiya 2013)
        for d in self.info.values():
            for g in d['fases_verdes']:
                out = set()
                for lane in g['lanes']:
                    try:
                        for link in traci.lane.getLinks(lane):
                            if link and link[0]:
                                out.add(link[0])
                    except Exception:
                        continue
                g['out_lanes'] = list(out)
        self.calc_icv = CalculadorICV(ParametrosInterseccion())
        self.difuso = ControladorDifusoCapitulo6()
        self.t_min = float(self.p['t_verde_min'])
        self.t_max = float(min(self.p['t_verde_max'], _LIM.T_VERDE_MAX))
        self.medidor: Optional[C.ContadorCruces] = self.p.get('medidor_flujo')

        # --- máquina de estados por TLS (esqueleto tipo max-pressure) ---
        self.estado: Dict[str, dict] = {}
        for tls, d in self.info.items():
            logic = d['logic']
            n = len(logic.phases)
            amber_de = {}
            for g in d['fases_verdes']:
                j = (g['idx'] + 1) % n
                vueltas = 0
                while 'y' not in logic.phases[j].state.lower() and vueltas < n:
                    j = (j + 1) % n
                    vueltas += 1
                amber_de[g['idx']] = j if 'y' in logic.phases[j].state.lower() else None
            self.estado[tls] = {
                't': 0.0,                     # tiempo restante del estado actual
                'fase_idx': d['fases_verdes'][0]['idx'],
                'trans': [],                  # pasos de transición pendientes
                'elapsed': 0.0,               # tiempo en el verde actual
                'gap': 0.0,                   # segundos seguidos sin demanda
                'ultimo_fin': {g['idx']: 0.0 for g in d['fases_verdes']},
            }

        # --- IA: buffers por (tls, fase) en rejilla fija ---
        self._buffers: Dict[Tuple[str, int], deque] = {}
        self._predictor = None
        self._error_ia: Optional[str] = None
        self._stats = {'fallos_sensor': 0}
        self.n_pred = 0
        self.n_fallback_ia = 0
        self.n_veto = 0          # saltos vetados por cola predicha
        self.n_veto_sombra = 0   # vetos que HABRÍA hecho (modo sombra)
        self.n_ext = 0           # extensiones anticipadas aplicadas
        self.s_ext = 0.0         # segundos de verde añadidos por la IA
        self.n_gate_cerrado = 0  # decisiones con IA abstenida por régimen
        self.n_error_paso = 0    # fallos del lazo de decisión (trazados)
        self.n_ambar_sintetico = 0   # transiciones sin fase 'y' en programa
        self.n_todo_rojo = 0     # fases de despeje servidas
        self.n_corte_inanicion = 0   # verdes cortados por anti-inanición
        self._fallback_motivos: Dict[str, int] = {}
        self._lat_ms: deque = deque(maxlen=20000)   # latencias de inferencia
        self._dens_red: float = 0.0   # veh en red / cruces controlados
        if str(self.p['modo_ia']) in ('guardia', 'sombra') \
                or float(self.p['beta']) > 0.0:
            self._cargar_predictor()

        # --- recolector de series (para entrenar la CNN-LSTM de fases) ---
        self._recolector = None
        if self.p['recolector']:
            ruta = Path(self.p['recolector'])
            ruta.parent.mkdir(parents=True, exist_ok=True)
            nuevo = not ruta.exists()
            self._recolector = open(ruta, 'a', encoding='utf-8')
            if nuevo:
                self._recolector.write(
                    'serie_id,t,' + ','.join(CARACTERISTICAS_FASE) + '\n')
        self._serie_prefix = str(self.p.get('serie_prefix', 'run'))

        # --- log de trazabilidad IA (una fila por fase evaluada/decisión) ---
        self._log = None
        if self.p['log_ia']:
            ruta = Path(self.p['log_ia'])
            ruta.parent.mkdir(parents=True, exist_ok=True)
            nuevo = not ruta.exists()
            self._log = open(ruta, 'a', encoding='utf-8')
            if nuevo:
                self._log.write(','.join(_CAMPOS_LOG) + '\n')

    # ------------------------------------------------------------------ #
    def _cargar_predictor(self):
        try:
            from ia.inferencia_fase import PredictorFase
            self._predictor = PredictorFase.cargar(self.p['ruta_artefactos'])
        except Exception as e:
            self._predictor = None
            self._error_ia = f'{type(e).__name__}: {e}'
            logger.warning(f'[difuso_ia] IA no disponible ({self._error_ia}); '
                           f'se opera con beta=0')
            return
        # Validar que la normalización usada al ENTRENAR coincide con la de
        # inferencia (constantes de este módulo). Un desalineamiento aquí
        # sería un error sistemático silencioso: se prefiere desactivar la IA.
        norm_cfg = self._predictor.config.get('normalizacion')
        if norm_cfg is None:
            logger.warning('[difuso_ia] artefactos sin registro de '
                           'normalización (modelo previo a esta validación); '
                           'se asume que coincide con %s', NORMALIZACION_FASE)
        else:
            desalineado = any(
                abs(float(norm_cfg.get(k, float('nan'))) - float(v)) > 1e-9
                for k, v in NORMALIZACION_FASE.items())
            if desalineado:
                self._predictor = None
                self._error_ia = (f'normalizacion_desalineada: entrenado con '
                                  f'{norm_cfg}, inferencia usa '
                                  f'{NORMALIZACION_FASE}')
                logger.error(f'[difuso_ia] {self._error_ia}; IA desactivada '
                             f'(re-entrenar con ia.entrenamiento_fase)')
                return
        logger.info('[difuso_ia] CNN-LSTM de fases cargada')

    @property
    def ia_activa(self) -> bool:
        if self._predictor is None or str(self.p['modo_ia']) == 'off':
            return False
        return (str(self.p['modo_ia']) in ('guardia', 'sombra')
                or float(self.p['beta']) > 0.0)

    # ------------------------------------------------------------------ #
    # Trazabilidad
    # ------------------------------------------------------------------ #
    def _log_fila(self, **kv):
        if self._log is None:
            return
        fila = [str(kv.get(c, '')) for c in _CAMPOS_LOG]
        self._log.write(','.join(fila) + '\n')

    # ------------------------------------------------------------------ #
    # Rejilla de muestreo: alimenta buffers de la IA y el recolector
    # ------------------------------------------------------------------ #
    def _muestrear_rejilla(self, t_sim: float):
        for tls, d in self.info.items():
            stt = self.estado[tls]
            for g in d['fases_verdes']:
                cola, nveh, ocup, vel = _medir_fase(g['lanes'], self._stats)
                espera = max(0.0, t_sim - stt['ultimo_fin'].get(g['idx'], 0.0))
                vec = [min(1.0, cola / COLA_NORM),
                       min(1.0, nveh / NVEH_NORM),
                       min(1.0, ocup),
                       min(1.0, vel / VEL_NORM_KMH),
                       1.0 if g['idx'] == stt['fase_idx'] and not stt['trans'] else 0.0,
                       min(1.0, espera / ESPERA_NORM_S)]
                clave = (tls, g['idx'])
                buf = self._buffers.get(clave)
                if buf is None:
                    buf = self._buffers[clave] = deque(maxlen=int(self.p['ventana']))
                buf.append(vec)
                if self._recolector is not None:
                    self._recolector.write(
                        f'{self._serie_prefix}|{tls}|{g["idx"]},{t_sim:.0f},'
                        + ','.join(f'{v:.4f}' for v in vec) + '\n')
                # muestra de rejilla en el log IA: la cola REAL en t permite
                # evaluar post-hoc si una predicción/veto anterior acertó
                self._log_fila(evento='muestra', t=f'{t_sim:.0f}', tls=tls,
                               fase_idx=g['idx'], cola_veh=f'{cola:.1f}',
                               modo=str(self.p['modo_ia']))

    def _predecir_colas(self, tls: str, d: dict) -> Optional[List[float]]:
        """Cola predicha (vehículos) por fase, o None si no hay IA lista.

        Todo fallback queda contado por MOTIVO en self._fallback_motivos y
        el último motivo en self._ultimo_fallback (para el log de decisión).
        """
        self._ultimo_fallback = ''
        if not self.ia_activa:
            return None

        def _fallback(motivo: str):
            self.n_fallback_ia += 1
            self._ultimo_fallback = motivo
            self._fallback_motivos[motivo] = \
                self._fallback_motivos.get(motivo, 0) + 1
            return None

        ventanas = []
        for g in d['fases_verdes']:
            buf = self._buffers.get((tls, g['idx']))
            if buf is None or len(buf) < int(self.p['ventana']):
                return _fallback('buffer_incompleto')
            ventanas.append(list(buf))
        t0 = time.perf_counter()
        try:
            pred_norm = self._predictor.predecir_lote(ventanas)
        except Exception as e:
            self._error_ia = f'{type(e).__name__}: {e}'
            return _fallback('excepcion_inferencia')
        self._lat_ms.append((time.perf_counter() - t0) * 1000.0)
        colas = []
        for pn in pred_norm:
            if not math.isfinite(pn):
                return _fallback('prediccion_no_finita')
            colas.append(max(0.0, min(1.0, pn)) * COLA_NORM)
        self.n_pred += 1
        return colas

    # ------------------------------------------------------------------ #
    # Decisión: elegir fase y duración (difuso + IA)
    # ------------------------------------------------------------------ #
    def _decidir(self, tls: str, d: dict, t_sim: float):
        """Rotación CÍCLICA (equidad garantizada, como actuated) con:
        - SALTO de fases sin demanda efectiva (actuated no puede saltar);
          con IA, la cola PREDICHA puede vetar el salto (no se salta una fase
          a la que está por llegar un pelotón).
        - DURACIÓN difusa Mamdani (ICV+PI reales de la fase a servir), con
          extensión anticipada si la IA prevé crecimiento de cola.
        """
        stt = self.estado[tls]
        gps = d['fases_verdes']
        beta = float(self.p['beta'])
        w_mov = float(self.p['w_mov'])
        modo_ia = str(self.p['modo_ia'])

        medidas = [_medir_fase(g['lanes'], self._stats) for g in gps]
        # detector de régimen: EMA de la suma de colas del cruce (saturación
        # SOSTENIDA, robusta a instantes drenados de una red saturada)
        suma_colas = sum(m[0] for m in medidas)
        a_g = float(self.p['ia_gate_alpha'])
        sat_ema = stt.get('sat_ema')
        sat_ema = suma_colas if sat_ema is None else (
            a_g * suma_colas + (1.0 - a_g) * sat_ema)
        stt['sat_ema'] = sat_ema
        gate_abierto = (sat_ema <= float(self.p['ia_gate_sat'])
                        and self._dens_red <= float(self.p['ia_gate_dens']))
        colas_pred = None
        if modo_ia == 'sombra':
            # sombra: SIEMPRE predice (medición del MAE en todos los
            # regímenes) pero jamás toca la decisión
            colas_pred = self._predecir_colas(tls, d)
        elif gate_abierto:
            colas_pred = self._predecir_colas(tls, d)
        elif self.ia_activa:
            self.n_gate_cerrado += 1
            self._ultimo_fallback = ''
        lat_ms = round(self._lat_ms[-1], 3) if (
            colas_pred is not None and self._lat_ms) else ''

        # Demanda efectiva por fase. En modo 'guardia' la predicción NO se
        # mezcla (una red MSE regresa a la media y sesga colas grandes/chicas);
        # solo VETA saltos: una fase con cola prevista alta cuenta como con
        # demanda aunque hoy esté vacía. El veto exige superar umbral_skip por
        # ia_margen_veto (confianza: no vetar por ruido de predicción).
        # En 'mezcla', β pondera solo la cola. En 'sombra', nada se altera.
        umbral_d = float(self.p['umbral_skip'])
        margen = float(self.p['ia_margen_veto'])
        demanda_ef = []
        vetadas = [0] * len(gps)
        for k, (cola, nveh, _, _) in enumerate(medidas):
            cola_ef = cola
            if colas_pred is not None:
                if modo_ia == 'mezcla' and beta > 0.0:
                    cola_ef = (1.0 - beta) * cola + beta * colas_pred[k]
                elif modo_ia == 'guardia' and self.p['ia_veto']:
                    if colas_pred[k] >= umbral_d + margen:
                        cola_ef = max(cola, colas_pred[k])
                elif modo_ia == 'sombra':
                    # veto hipotético: se cuenta y registra, no se aplica
                    mov_s = w_mov * max(0.0, nveh - cola)
                    if (cola + mov_s < umbral_d
                            <= max(cola, colas_pred[k]) + mov_s
                            and colas_pred[k] >= umbral_d + margen):
                        self.n_veto_sombra += 1
                        vetadas[k] = 1
            mov = w_mov * max(0.0, nveh - cola)
            if modo_ia != 'sombra' and cola + mov < umbral_d <= cola_ef + mov:
                self.n_veto += 1
                vetadas[k] = 1
            demanda_ef.append(cola_ef + mov)

        # ANTI-INANICIÓN: fase con demanda esperando demasiado -> prioridad
        k_starve = None
        peor_espera = 0.0
        for k, g in enumerate(gps):
            espera = t_sim - stt['ultimo_fin'].get(g['idx'], 0.0)
            if (medidas[k][0] >= 1.0 and espera >= float(self.p['t_starve'])
                    and espera > peor_espera and g['idx'] != stt['fase_idx']):
                k_starve, peor_espera = k, espera

        k_act = next((k for k, g in enumerate(gps)
                      if g['idx'] == stt['fase_idx']), 0)
        if k_starve is not None:
            k_sel = k_starve
        else:
            # ROTACIÓN: siguiente fase del ciclo, saltando las vacías
            umbral = float(self.p['umbral_skip'])
            n_f = len(gps)
            k_sel = None
            for salto in range(1, n_f + 1):
                k_cand = (k_act + salto) % n_f
                if k_cand == k_act:
                    continue
                if demanda_ef[k_cand] >= umbral:
                    k_sel = k_cand
                    break
            if k_sel is None:
                # nadie tiene demanda: si la actual tampoco, avanzar igual
                k_sel = k_act if demanda_ef[k_act] >= umbral else (k_act + 1) % n_f

        # DURACIÓN: Mamdani Cap.6 con ICV+PI reales de la fase elegida.
        # El flujo del ICV proviene del medidor de CRUCES (si se inyectó).
        icv, pi = C._demanda_fase(gps[k_sel]['lanes'], self.calc_icv,
                                  medidor=self.medidor)
        delta = self.difuso.calcular_ajuste_verde(icv=icv, pi=pi, ev=0.0)[
            'delta_t_porcentaje']
        dur = self.difuso.calcular_tiempo_verde_ajustado(
            T_base=float(self.p['t_base']), delta_t_porcentaje=delta)
        # extensión por cola presente (el Mamdani acota a ±25%; colas grandes
        # ameritan verdes más largos para amortizar el ámbar)
        k_ext = float(self.p['k_ext_cola'])
        if k_ext > 0.0:
            dur += min(12.0, k_ext * medidas[k_sel][0])
        # extensión anticipada: la IA prevé más cola de la que hay ahora
        if colas_pred is not None and self.p['ia_ext'] and modo_ia != 'sombra':
            crecimiento = colas_pred[k_sel] - medidas[k_sel][0]
            if crecimiento > 0:
                extra = min(8.0, 2.0 * crecimiento)
                dur += extra
                self.n_ext += 1
                self.s_ext += extra
        dur = max(self.t_min, min(float(dur), self.t_max))  # guardia dura

        # trazabilidad: una fila por fase evaluada en esta decisión
        if self._log is not None:
            for k, g in enumerate(gps):
                pred_k = f'{colas_pred[k]:.2f}' if colas_pred is not None else ''
                self._log_fila(
                    evento='decision', t=f'{t_sim:.0f}', tls=tls,
                    fase_idx=g['idx'], cola_veh=f'{medidas[k][0]:.1f}',
                    cola_pred_veh=pred_k, demanda_ef=f'{demanda_ef[k]:.2f}',
                    seleccionada=1 if k == k_sel else 0, vetada=vetadas[k],
                    gate=1 if gate_abierto else 0, sat_ema=f'{sat_ema:.2f}',
                    dens_red=f'{self._dens_red:.2f}', latencia_ms=lat_ms,
                    dur_s=f'{dur:.1f}' if k == k_sel else '',
                    fallback=getattr(self, '_ultimo_fallback', ''),
                    modo=modo_ia)

        objetivo = gps[k_sel]['idx']
        actual_idx = stt['fase_idx']
        if objetivo != actual_idx:
            stt['ultimo_fin'][actual_idx] = t_sim
            self._iniciar_transicion(tls, d, actual_idx, objetivo, dur)
            return
        # misma fase: renovar el verde sin transición
        traci.trafficlight.setPhase(tls, objetivo)
        traci.trafficlight.setPhaseDuration(tls, dur)
        stt['t'] = dur
        stt['fase_idx'] = objetivo
        stt['elapsed'] = 0.0
        stt['gap'] = 0.0
        stt['trans'] = []

    # ------------------------------------------------------------------ #
    # Transición segura: verde -> ámbar (-> todo-rojo) -> verde
    # ------------------------------------------------------------------ #
    def _iniciar_transicion(self, tls: str, d: dict, actual_idx: int,
                            objetivo: int, dur: float):
        """Encadena los pasos de transición y aplica el primero YA.

        Invariante: NUNCA hay cambio directo verde->verde. Si el programa no
        define fase de ámbar, se sintetiza un estado 'y' para las señales que
        pierden el verde. Si el programa define despeje (todo-rojo) tras el
        ámbar, se sirve (antes se saltaba con setPhase directo: bug).
        """
        stt = self.estado[tls]
        logic = d['logic']
        t_ambar = float(self.p['t_ambar'])
        t_ar = float(self.p['t_todo_rojo'])
        trans: List[Tuple[str, object, float]] = []

        amber = self._amber_de(tls, actual_idx)
        if amber is not None:
            trans.append(('fase', amber, t_ambar))
            allred = C._fase_todo_rojo_tras(logic, amber)
            if allred is not None:
                dur_ar = max(float(logic.phases[allred].duration),
                             _LIM.T_TODO_ROJO_MIN)
                trans.append(('fase', allred, dur_ar))
                self.n_todo_rojo += 1
            elif t_ar > 0.0:
                n_sig = len(logic.phases[actual_idx].state)
                trans.append(('estado', 'r' * n_sig, t_ar))
                self.n_todo_rojo += 1
        else:
            # programa sin fase 'y': ámbar SINTÉTICO (invariante de seguridad)
            est_act = logic.phases[actual_idx].state
            est_obj = logic.phases[objetivo].state
            trans.append(('estado', C._estado_ambar(est_act, est_obj), t_ambar))
            self.n_ambar_sintetico += 1
            if t_ar > 0.0:
                trans.append(('estado', 'r' * len(est_act), t_ar))
                self.n_todo_rojo += 1
        trans.append(('verde', objetivo, dur))

        tipo, val, paso_dur = trans.pop(0)
        self._aplicar_transicion(tls, tipo, val, paso_dur)
        stt['t'] = paso_dur
        stt['trans'] = trans

    def _aplicar_transicion(self, tls: str, tipo: str, val, dur: float):
        if tipo == 'fase':
            traci.trafficlight.setPhase(tls, int(val))
            traci.trafficlight.setPhaseDuration(tls, float(dur))
        elif tipo == 'estado':
            # estado explícito (ámbar/todo-rojo sintético); setPhase posterior
            # devuelve el control al programa del TLS
            traci.trafficlight.setRedYellowGreenState(tls, str(val))
        else:  # 'verde'
            stt = self.estado[tls]
            traci.trafficlight.setPhase(tls, int(val))
            traci.trafficlight.setPhaseDuration(tls, float(dur))
            stt['fase_idx'] = int(val)
            stt['elapsed'] = 0.0
            stt['gap'] = 0.0

    def _amber_de(self, tls: str, idx_verde: int) -> Optional[int]:
        d = self.info[tls]
        logic = d['logic']
        n = len(logic.phases)
        j = (idx_verde + 1) % n
        vueltas = 0
        while 'y' not in logic.phases[j].state.lower() and vueltas < n:
            j = (j + 1) % n
            vueltas += 1
        return j if 'y' in logic.phases[j].state.lower() else None

    # ------------------------------------------------------------------ #
    # Un paso de simulación
    # ------------------------------------------------------------------ #
    def paso(self, i: int):
        t_sim = float(i)
        if self.ia_activa and i % 5 == 0:
            # densidad de red (detector de régimen, una llamada cada 5 s)
            try:
                self._dens_red = (traci.vehicle.getIDCount()
                                  / max(1, len(self.info)))
            except Exception as e:
                self._stats['fallos_sensor'] = \
                    self._stats.get('fallos_sensor', 0) + 1
                logger.debug(f'[difuso_ia] densidad de red ilegible: {e}')
        if i % int(self.p['grid_s']) == 0 and (
                self._recolector is not None or self._log is not None
                or self.ia_activa):
            self._muestrear_rejilla(t_sim)

        for tls, d in self.info.items():
            try:
                stt = self.estado[tls]
                stt['t'] -= 1.0

                # durante el VERDE: gap-out y anti-inanición
                if not stt['trans'] and stt['t'] > 0:
                    stt['elapsed'] += 1.0
                    if stt['elapsed'] >= self.t_min:
                        # GAP-OUT (tras el mínimo de seguridad)
                        g_act = next((g for g in d['fases_verdes']
                                      if g['idx'] == stt['fase_idx']), None)
                        if g_act is not None:
                            cola, nveh, _, _ = _medir_fase(g_act['lanes'],
                                                           self._stats)
                            sin_demanda = cola <= 0.0 and (
                                not self.p['gap_considera_mov'] or nveh <= 0.0)
                            if sin_demanda:
                                stt['gap'] += 1.0
                            else:
                                stt['gap'] = 0.0
                            if stt['gap'] >= float(self.p['gap_umbral_s']):
                                stt['t'] = 0.0   # corta el verde: decide ya
                        # ANTI-INANICIÓN DURA: re-evaluada DURANTE el verde
                        # (no solo al expirar). Si otra fase con cola superó
                        # t_starve, se corta el verde ya; _decidir la servirá
                        # con prioridad. Cota real de espera:
                        #   t_starve + starve_check_s + t_ambar   (verde>min)
                        #   t_starve + t_verde_min + t_ambar      (peor caso)
                        if (stt['t'] > 0
                                and i % int(self.p['starve_check_s']) == 0):
                            for g in d['fases_verdes']:
                                if g['idx'] == stt['fase_idx']:
                                    continue
                                espera = t_sim - stt['ultimo_fin'].get(
                                    g['idx'], 0.0)
                                if espera < float(self.p['t_starve']):
                                    continue
                                cola_g, _, _, _ = _medir_fase(g['lanes'],
                                                              self._stats)
                                if cola_g >= 1.0:
                                    stt['t'] = 0.0
                                    self.n_corte_inanicion += 1
                                    break
                    if stt['t'] > 0:
                        continue

                if stt['t'] > 0:
                    continue

                # ¿pasos de transición pendientes (ámbar/todo-rojo/verde)?
                if stt['trans']:
                    tipo, val, dur = stt['trans'].pop(0)
                    self._aplicar_transicion(tls, tipo, val, dur)
                    stt['t'] = dur
                    continue

                self._decidir(tls, d, t_sim)
            except Exception as e:
                # el fallo de un cruce no tumba el resto, pero queda TRAZADO:
                # el TLS conserva su última fase aplicada (estado seguro)
                self.n_error_paso += 1
                if self.n_error_paso <= 5:
                    logger.warning(f'[difuso_ia] fallo de decisión en {tls} '
                                   f'(paso {i}): {type(e).__name__}: {e}')
                continue

    def cerrar(self):
        if self._recolector is not None:
            self._recolector.close()
            self._recolector = None
        if self._log is not None:
            self._log.close()
            self._log = None

    def resumen_ia(self) -> dict:
        lat = sorted(self._lat_ms)

        def _pct(p):
            if not lat:
                return None
            return round(lat[min(len(lat) - 1, int(p * len(lat)))], 3)

        return {'ia_activa': self.ia_activa, 'modo_ia': str(self.p['modo_ia']),
                'beta': float(self.p['beta']),
                'predicciones': self.n_pred, 'fallbacks_ia': self.n_fallback_ia,
                'fallbacks_por_motivo': dict(self._fallback_motivos),
                'vetos_skip': self.n_veto, 'vetos_sombra': self.n_veto_sombra,
                'margen_veto': float(self.p['ia_margen_veto']),
                'extensiones': self.n_ext,
                'seg_extension': round(self.s_ext, 1),
                'gate_cerrado': self.n_gate_cerrado,
                'dens_red_final': round(self._dens_red, 2),
                'latencia_ms_p50': _pct(0.50),
                'latencia_ms_p95': _pct(0.95),
                'errores_paso': self.n_error_paso,
                'fallos_sensor': self._stats.get('fallos_sensor', 0),
                'ambar_sintetico': self.n_ambar_sintetico,
                'todo_rojo_servidos': self.n_todo_rojo,
                'cortes_inanicion': self.n_corte_inanicion,
                'error_ia': self._error_ia}
