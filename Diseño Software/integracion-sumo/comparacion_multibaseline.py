# -*- coding: utf-8 -*-
"""
Comparación multi-línea-base de control semafórico sobre SUMO (datos REALES).

Compara, sobre el MISMO escenario, demanda y semilla, varios controladores:
  - fijo            : tiempo fijo (verde estático), línea base.
  - actuated        : control actuado nativo de SUMO (gap-out por detector).
  - webster         : Webster adaptativo (ciclo óptimo recalculado por ventana).
  - webster_mod     : Webster modificado (ciclo práctico de Akçelik, 1981).
  - maxpressure     : política Max-Pressure (acíclica, Varaiya, 2013).
  - difuso          : NUESTRO núcleo (ICV + control difuso Mamdani, Cap. 6).

Las métricas provienen de la simulación REAL (no se usan números aleatorios
sintéticos): tiempo de viaje y espera por vehículo, velocidad media, cola,
throughput, flujo e ICV de red. Todas las estrategias comparten exactamente el
mismo `_metricas_instante`, por lo que la comparación es 1 a 1.

ATRIBUCIÓN (líneas base): las funciones Webster y Max-Pressure son una
reimplementación propia en TraCI plano de algoritmos clásicos publicados
—Webster (1958), Akçelik (1981) y la política Max-Pressure de Varaiya (2013)—,
siguiendo como referencia de marco abierto a:
  W. Genders y S. Razavi, "An Open-Source Framework for Adaptive Traffic Signal
  Control", arXiv:1909.00395 (2019); código: github.com/docwza/sumolights (GPLv3).
NO se reutiliza el código fuente de dicho repositorio (clean-room).
"""

import sys
import json
import csv
import logging
import random
import statistics as st
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

_INTEG = Path(__file__).parent
_RAIZ = _INTEG.parent
for _p in (str(_RAIZ), str(_INTEG)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sumolib  # noqa: E402
from conector_sumo import traci, USANDO_LIBSUMO  # noqa: E402
from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion  # noqa: E402
from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6  # noqa: E402
from nucleo.seguridad_semaforica import LIMITES as _LIM  # noqa: E402

# Reutilizamos la infraestructura ya validada del comparador base.
import comparacion_sumo as C  # noqa: E402

logger = logging.getLogger(__name__)
VEL_LIBRE_MS = 13.89  # ~50 km/h

T_MIN = float(_LIM.T_VERDE_MIN)   # 10 s
T_MAX = float(_LIM.T_VERDE_MAX)   # 120 s
TIME_TO_TELEPORT = 300            # s: SUMO teletransporta vehículos atascados
                                  # más de esto (rescata gridlock). Se REPORTA
                                  # el número de teleports por corrida porque
                                  # sesga demora/throughput si difiere entre
                                  # estrategias.


def _git_hash() -> str:
    """Hash corto del commit actual (trazabilidad del experimento)."""
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=str(_RAIZ),
            stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ''


def _pct(vals: List[float], p: float) -> float:
    """Percentil p (0-1) por orden simple (suficiente para reporte)."""
    if not vals:
        return 0.0
    s = sorted(vals)
    return float(s[min(len(s) - 1, int(p * len(s)))])


# ----------------------------------------------------------------------
# Arranque con semilla fija (comparación reproducible y justa)
# ----------------------------------------------------------------------
def _iniciar(ruta_cfg: str, seed: int, actuated: bool = False):
    sumo_bin = sumolib.checkBinary('sumo')
    cmd = [sumo_bin, '-c', str(ruta_cfg), '--start', '--quit-on-end',
           '--no-warnings', 'true', '--seed', str(seed),
           '--time-to-teleport', str(TIME_TO_TELEPORT)]
    traci.start(cmd)


def _aplicar_limites(valores: List[float]) -> List[float]:
    """Guardia de seguridad funcional: acota todo verde a [T_MIN, T_MAX]."""
    return [max(T_MIN, min(float(v), T_MAX)) for v in valores]


# ----------------------------------------------------------------------
# LÍNEA BASE: SUMO actuated (control actuado nativo)
# ----------------------------------------------------------------------
def _activar_actuated():
    """Convierte cada semáforo a programa ACTUADO de SUMO con rangos de verde.

    SUMO autogenera detectores de carril para el control actuado cuando el
    programa es 'actuated' y las fases verdes tienen minDur/maxDur distintos.
    """
    convertidos = 0
    for tls in traci.trafficlight.getIDList():
        try:
            logic = traci.trafficlight.getAllProgramLogics(tls)[0]
            for ph in logic.phases:
                if 'g' in ph.state.lower() and 'y' not in ph.state.lower():
                    ph.minDur = T_MIN
                    ph.maxDur = min(60.0, T_MAX)
                    ph.duration = ph.maxDur
            try:
                logic.type = 1  # 1 = actuated en TraCI (0 = static)
            except Exception:
                pass
            traci.trafficlight.setProgramLogic(tls, logic)
            convertidos += 1
        except Exception:
            continue
    return convertidos


# ----------------------------------------------------------------------
# LÍNEA BASE: Webster (1958) y Webster modificado (Akçelik, 1981)
# Reimplementación clean-room en TraCI plano.
# ----------------------------------------------------------------------
def _init_webster(info: dict) -> dict:
    return {tls: {'vistos': {l: set() for g in d['fases_verdes'] for l in g['lanes']},
                  'count': {l: 0 for g in d['fases_verdes'] for l in g['lanes']}}
            for tls, d in info.items()}


def _acumular_webster(info: dict, estado: dict):
    """Cada paso: cuenta vehículos servidos (que cruzaron) por carril de verde."""
    for tls, d in info.items():
        st_tls = estado[tls]
        for g in d['fases_verdes']:
            for lane in g['lanes']:
                try:
                    ahora = set(traci.lane.getLastStepVehicleIDs(lane))
                except Exception as e:
                    logger.debug(f'[webster] carril ilegible {lane}: {e}')
                    ahora = set()
                antes = st_tls['vistos'].get(lane, set())
                st_tls['count'][lane] = st_tls['count'].get(lane, 0) + len(antes - ahora)
                st_tls['vistos'][lane] = ahora


def _aplicar_webster(info: dict, estado: dict, update_freq: int,
                     modificado: bool = False, sat_flow: float = 0.44,
                     red_t: float = 3.0, yellow_t: float = 2.0):
    """Recalcula los verdes con el ciclo óptimo de Webster (o Akçelik).

    Webster (1958):   C0 = (1.5*L + 5) / (1 - Y)
    Akçelik (1981):   C0 = (1.4*L + 6) / (1 - Y)   [ciclo práctico modificado]
    Reparto del verde efectivo proporcional a la razón de flujo crítica yi/Y.
    """
    for tls, d in info.items():
        try:
            gps = d['fases_verdes']
            y_crit = []
            for g in gps:
                flujos = [(estado[tls]['count'].get(l, 0) / update_freq) / sat_flow
                          for l in g['lanes']]
                y_crit.append(max(flujos) if flujos else 0.0)
            Y = sum(y_crit)
            Y = min(Y, 0.85)
            Y = 0.01 if Y <= 0 else Y
            L = len(gps) * (red_t + yellow_t)
            if modificado:
                C = (1.4 * L + 6.0) / (1.0 - Y)
            else:
                C = (1.5 * L + 5.0) / (1.0 - Y)
            G = max(1.0, C - L)
            nuevos = []
            for y in y_crit:
                g_t = (y / Y) * G if Y > 0 else T_MIN
                nuevos.append(g_t)
            nuevos = _aplicar_limites(nuevos)
            logic = d['logic']
            try:
                logic.currentPhaseIndex = traci.trafficlight.getPhase(tls)
            except Exception:
                pass
            for g, nv in zip(gps, nuevos):
                ph = logic.phases[g['idx']]
                ph.duration = ph.minDur = ph.maxDur = float(nv)
            traci.trafficlight.setProgramLogic(tls, logic)
            # reiniciar ventana
            estado[tls]['count'] = {l: 0 for g in gps for l in g['lanes']}
        except Exception as e:
            logger.warning(f'[webster] fallo de control en TLS {tls}: '
                           f'{type(e).__name__}: {e}')
            continue


# ----------------------------------------------------------------------
# LÍNEA BASE: Max-Pressure (Varaiya, 2013) — acíclico
# Reimplementación clean-room en TraCI plano con ámbar explícito.
# ----------------------------------------------------------------------
def _init_maxpressure(info: dict) -> dict:
    """Precomputa carriles salientes por fase y prepara la máquina de estados."""
    estado = {}
    for tls, d in info.items():
        gps = d['fases_verdes']
        for g in gps:
            out = set()
            for lane in g['lanes']:
                try:
                    for link in traci.lane.getLinks(lane):
                        if link and link[0]:
                            out.add(link[0])
                except Exception:
                    continue
            g['out_lanes'] = list(out)
        # índice de ámbar siguiente a cada verde (primera fase con 'y' después)
        logic = d['logic']
        n = len(logic.phases)
        amber_de = {}
        for g in gps:
            j = (g['idx'] + 1) % n
            vueltas = 0
            while 'y' not in logic.phases[j].state.lower() and vueltas < n:
                j = (j + 1) % n
                vueltas += 1
            amber_de[g['idx']] = j if 'y' in logic.phases[j].state.lower() else None
        estado[tls] = {'t': 0, 'fase_idx': gps[0]['idx'], 'amber_de': amber_de,
                       'trans': []}
    return estado


def _aplicar_trans_mp(tls: str, tipo: str, val, dur: float, stt: dict):
    """Aplica un paso de transición de max-pressure (fase/estado/verde)."""
    if tipo == 'fase':
        traci.trafficlight.setPhase(tls, int(val))
        traci.trafficlight.setPhaseDuration(tls, float(dur))
    elif tipo == 'estado':
        traci.trafficlight.setRedYellowGreenState(tls, str(val))
    else:  # 'verde'
        traci.trafficlight.setPhase(tls, int(val))
        traci.trafficlight.setPhaseDuration(tls, float(dur))
        stt['fase_idx'] = int(val)
    stt['t'] = dur


def _paso_maxpressure(info: dict, estado: dict, green_t: float = 12.0,
                      yellow_t: float = 3.0):
    """Cada paso: por semáforo, mantiene fase; al expirar elige la de mayor presión.

    Transición SEGURA idéntica a la del controlador propuesto: siempre ámbar
    entre verdes distintos (sintetizado si el programa no trae fase 'y') y
    respeto del todo-rojo que el programa defina. Así la comparación no
    favorece a nadie en el manejo de transiciones.
    """
    for tls, d in info.items():
        try:
            stt = estado[tls]
            stt['t'] -= 1
            if stt['t'] > 0:
                continue
            # ¿pasos de transición pendientes (ámbar/todo-rojo/verde)?
            if stt['trans']:
                tipo, val, dur = stt['trans'].pop(0)
                _aplicar_trans_mp(tls, tipo, val, dur, stt)
                continue
            gps = d['fases_verdes']
            presiones = []
            for g in gps:
                inc = sum(traci.lane.getLastStepVehicleNumber(l) for l in g['lanes'])
                out = sum(traci.lane.getLastStepVehicleNumber(l) for l in g.get('out_lanes', []))
                presiones.append(inc - out)
            mejor = max(presiones)
            if mejor <= 0 and sum(abs(p) for p in presiones) == 0:
                k = random.randrange(len(gps))
            else:
                cand = [i for i, p in enumerate(presiones) if p == mejor]
                k = random.choice(cand)
            objetivo = gps[k]['idx']
            if objetivo != stt['fase_idx']:
                logic = d['logic']
                trans = []
                amber = stt['amber_de'].get(stt['fase_idx'])
                if amber is not None:
                    trans.append(('fase', amber, yellow_t))
                    allred = C._fase_todo_rojo_tras(logic, amber)
                    if allred is not None:
                        dur_ar = max(float(logic.phases[allred].duration),
                                     _LIM.T_TODO_ROJO_MIN)
                        trans.append(('fase', allred, dur_ar))
                else:
                    # programa sin fase 'y': ámbar SINTÉTICO, nunca cambio
                    # directo verde->verde (antes era un hueco de seguridad)
                    est_act = logic.phases[stt['fase_idx']].state
                    est_obj = logic.phases[objetivo].state
                    trans.append(('estado', C._estado_ambar(est_act, est_obj),
                                  yellow_t))
                trans.append(('verde', objetivo, green_t))
                tipo, val, dur = trans.pop(0)
                _aplicar_trans_mp(tls, tipo, val, dur, stt)
                stt['trans'] = trans
                continue
            traci.trafficlight.setPhase(tls, objetivo)
            traci.trafficlight.setPhaseDuration(tls, green_t)
            stt['t'] = green_t
            stt['fase_idx'] = objetivo
        except Exception as e:
            logger.warning(f'[maxpressure] fallo de control en TLS {tls}: '
                           f'{type(e).__name__}: {e}')
            continue


# ----------------------------------------------------------------------
# Runner genérico de una estrategia
# ----------------------------------------------------------------------
def ejecutar_estrategia(ruta_cfg: str, seed: int, pasos: int, estrategia: str,
                        intervalo: int = 25, webster_freq: int = 150,
                        params_ia: dict = None) -> dict:
    """Corre una estrategia sobre (cfg, seed) y devuelve métricas agregadas reales."""
    random.seed(seed)
    params = ParametrosInterseccion()
    es_actuated = (estrategia == 'actuated')
    _iniciar(ruta_cfg, seed, actuated=es_actuated)
    try:
        sumo_version = traci.getVersion()[1]
    except Exception:
        sumo_version = ''

    n_int = len(traci.trafficlight.getIDList())

    if es_actuated:
        _activar_actuated()
        info = None
    else:
        C._forzar_tiempo_fijo(t_verde=30.0)  # punto de partida común
        info = C._mapear_semaforos()

    # preparación por estrategia
    estado = None
    calc_icv = difuso = None
    ctrl_ia = None
    medidor = None
    ema = {}
    if estrategia in ('difuso', 'difuso_ia'):
        # flujo REAL (cruces por ventana) para el término de flujo del ICV;
        # sustituye el conteo de presentes que saturaba el cap (bug corregido)
        medidor = C.ContadorCruces([l for dd in info.values()
                                    for g in dd['fases_verdes']
                                    for l in g['lanes']])
    if estrategia in ('webster', 'webster_mod'):
        estado = _init_webster(info)
    elif estrategia == 'maxpressure':
        estado = _init_maxpressure(info)
    elif estrategia == 'difuso':
        calc_icv = CalculadorICV(params)
        difuso = ControladorDifusoCapitulo6()
    elif estrategia == 'difuso_ia':
        import difuso_ia as DIA
        p_ia = dict(params_ia or {})
        p_ia.setdefault('serie_prefix', f's{seed}')
        p_ia.setdefault('medidor_flujo', medidor)
        ctrl_ia = DIA.ControladorDifusoIA(info, p_ia)

    metricas: List = []
    demora_total = 0
    arrivals = 0
    travel = []
    depart_t: Dict[str, int] = {}
    teleports = 0
    backlog_sum = 0
    backlog_max = 0
    departed = 0
    base = datetime.now()

    for i in range(pasos):
        traci.simulationStep()
        if medidor is not None:
            medidor.actualizar()

        # tiempos de viaje por vehículo (MOE principal, como Genders 2019)
        try:
            for v in traci.simulation.getDepartedIDList():
                depart_t[v] = i
            for v in traci.simulation.getArrivedIDList():
                if v in depart_t:
                    travel.append(i - depart_t.pop(v))
        except Exception:
            pass

        # lógica de control por estrategia
        if estrategia in ('webster', 'webster_mod'):
            _acumular_webster(info, estado)
            if i > 0 and i % webster_freq == 0:
                _aplicar_webster(info, estado, webster_freq,
                                 modificado=(estrategia == 'webster_mod'))
        elif estrategia == 'maxpressure':
            _paso_maxpressure(info, estado)
        elif estrategia == 'difuso':
            if i % intervalo == 0:
                C._redistribuir_verde(info, calc_icv, difuso, ema=ema,
                                      alpha=0.35, gamma=5.0, medidor=medidor)
        elif estrategia == 'difuso_ia':
            ctrl_ia.paso(i)
        # 'fijo' y 'actuated' no requieren intervención por paso

        met, halting, arrived = C._metricas_instante(base + timedelta(seconds=i), n_int)
        metricas.append(met)
        demora_total += halting
        arrivals += arrived

        # auditoría de validez: teleports y backlog de inserción
        ev = C._eventos_paso()
        teleports += ev['teleports']
        backlog_sum += ev['backlog']
        backlog_max = max(backlog_max, ev['backlog'])
        departed += ev['departed']

    if ctrl_ia is not None:
        ctrl_ia.cerrar()
    traci.close()

    def _ag(attr):
        vals = [getattr(m, attr) for m in metricas]
        return st.mean(vals) if vals else 0.0

    res = {
        # ICV_red es el PROXY de red de 2 términos de _metricas_instante
        # (fracción detenida + caída de velocidad), NO el ICV de 4 componentes
        # del núcleo (ese vive dentro del lazo de control por intersección).
        'ICV_red': _ag('ICV_red'),
        'Vavg_red': _ag('Vavg_red'),
        'QL_red': _ag('QL_red'),
        'q_red': _ag('q_red'),
        'throughput': arrivals,
        # demora_media_s: veh·s detenidos / ARRIBOS (métrica histórica; ojo:
        # castiga doble a la estrategia con menos throughput). Se mantiene por
        # continuidad con resultados previos.
        'demora_media_s': (demora_total / arrivals) if arrivals else 0.0,
        # demora_media_veh_s: veh·s detenidos / vehículos INSERTADOS
        # (denominador honesto e igual entre estrategias pareadas).
        'demora_media_veh_s': (demora_total / departed) if departed else 0.0,
        'demora_total_veh_s': demora_total,
        'tviaje_media_s': st.mean(travel) if travel else 0.0,
        'tviaje_mediana_s': st.median(travel) if travel else 0.0,
        'tviaje_p90_s': _pct(travel, 0.90),
        'tviaje_p95_s': _pct(travel, 0.95),
        'tviaje_sd_s': st.pstdev(travel) if len(travel) > 1 else 0.0,
        'n_arribos': arrivals,
        'vehiculos_insertados': departed,
        # teleports: gridlock "rescatado" por SUMO (--time-to-teleport);
        # si difiere entre estrategias, el throughput/demora está sesgado.
        'teleports': teleports,
        'backlog_medio': backlog_sum / pasos if pasos else 0.0,
        'backlog_max': backlog_max,
        'sumo_version': sumo_version,
    }
    if medidor is not None:
        res['fallos_sensor_flujo'] = medidor.fallos_sensor
    if ctrl_ia is not None:
        res['ia'] = ctrl_ia.resumen_ia()
    return res


# ----------------------------------------------------------------------
# Campaña completa: todas las estrategias x N semillas
# ----------------------------------------------------------------------
ESTRATEGIAS = ['fijo', 'actuated', 'webster', 'webster_mod', 'maxpressure',
               'difuso', 'difuso_ia']


def _params_difuso_ia_efectivos(params_ia: dict = None) -> dict:
    """Parámetros difuso_ia REALMENTE usados (serializables), para el JSON."""
    import difuso_ia as DIA
    p = dict(DIA.PARAMS_DEFECTO)
    p.update(params_ia or {})
    return {k: v for k, v in p.items()
            if k not in ('recolector', 'medidor_flujo', 'log_ia')}


def ejecutar_campana(ruta_cfg: str, semillas: List[int], pasos: int = 700,
                     intervalo: int = 25, estrategias: List[str] = None,
                     params_ia: dict = None) -> dict:
    estrategias = estrategias or ESTRATEGIAS
    salida = {'generado': datetime.now().isoformat(),
              'cfg': Path(ruta_cfg).name, 'pasos': pasos,
              'intervalo_control': intervalo, 'semillas': semillas,
              'motor': 'libsumo' if USANDO_LIBSUMO else 'traci',
              'limites_verde': [T_MIN, T_MAX],
              # metadatos de reproducibilidad
              'git_hash': _git_hash(),
              'time_to_teleport': TIME_TO_TELEPORT,
              'params_estrategia': {
                  'fijo': {'t_verde': 30.0},
                  'actuated': {'minDur': T_MIN, 'maxDur': 60.0},
                  'webster': {'freq_s': 150, 'sat_flow': 0.44, 'Y_max': 0.85},
                  'webster_mod': {'freq_s': 150, 'sat_flow': 0.44,
                                  'Y_max': 0.85, 'akcelik': True},
                  'maxpressure': {'green_t': 12.0, 'yellow_t': 3.0},
                  'difuso': {'intervalo': intervalo, 'alpha': 0.35,
                             'gamma': 5.0, 't_verde_base': 30.0},
                  'difuso_ia': _params_difuso_ia_efectivos(params_ia),
              },
              'por_estrategia': {}}
    for est in estrategias:
        reps = []
        for s in semillas:
            try:
                r = ejecutar_estrategia(ruta_cfg, s, pasos, est, intervalo,
                                        params_ia=params_ia)
                r['seed'] = s
                reps.append(r)
                if not salida.get('sumo_version'):
                    salida['sumo_version'] = r.get('sumo_version', '')
                print(f"[{est:12s} seed {s:>3}] ICV={r['ICV_red']:.4f} "
                      f"Vavg={r['Vavg_red']:.2f} demora={r['demora_media_s']:.1f} "
                      f"tviaje={r['tviaje_media_s']:.1f} thr={r['throughput']} "
                      f"tele={r['teleports']}",
                      flush=True)
            except Exception as e:
                # la corrida fallida queda registrada EXPLÍCITAMENTE: una
                # estrategia con n_semillas menor es visible en el agregado
                print(f"[{est} seed {s}] ERROR: {type(e).__name__}: {e}",
                      flush=True)
                salida.setdefault('corridas_fallidas', []).append(
                    {'estrategia': est, 'seed': s,
                     'error': f'{type(e).__name__}: {e}'})
                try:
                    traci.close()
                except Exception:
                    pass
        salida['por_estrategia'][est] = reps
    return salida


def _agregar(reps: List[dict]) -> dict:
    if not reps:
        return {}
    keys = ['ICV_red', 'Vavg_red', 'QL_red', 'q_red', 'throughput',
            'demora_media_s', 'demora_media_veh_s', 'tviaje_media_s',
            'tviaje_mediana_s', 'tviaje_p90_s', 'tviaje_p95_s',
            'teleports', 'backlog_medio']
    out = {}
    for k in keys:
        vals = [r[k] for r in reps if k in r]
        out[k + '_mean'] = st.mean(vals) if vals else 0.0
        out[k + '_sd'] = st.pstdev(vals) if len(vals) > 1 else 0.0
    return out


def guardar(salida: dict, dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    # JSON crudo
    (dest_dir / 'comparacion_multibaseline.json').write_text(
        json.dumps(salida, indent=2, ensure_ascii=False), encoding='utf-8')
    # CSV agregado (media ± sd por estrategia) — consumible por el informe
    filas = []
    for est, reps in salida['por_estrategia'].items():
        ag = _agregar(reps)
        ag['estrategia'] = est
        ag['n_semillas'] = len(reps)
        filas.append(ag)
    if filas:
        cols = ['estrategia', 'n_semillas'] + [c for c in filas[0] if c not in ('estrategia', 'n_semillas')]
        with open(dest_dir / 'comparacion_multibaseline_agregado.csv', 'w',
                  newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for fila in filas:
                w.writerow(fila)
    print('Guardado en', dest_dir, flush=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, default=10)
    ap.add_argument('--pasos', type=int, default=700)
    ap.add_argument('--intervalo', type=int, default=25)
    ap.add_argument('--cfg', type=str, default='')
    args = ap.parse_args()

    cfg = Path(args.cfg) if args.cfg else (_INTEG / 'escenarios' / 'lima-centro' / 'comparacion.sumocfg')
    if not cfg.exists():
        cfg = _INTEG / 'escenarios' / 'lima-centro' / 'osm.sumocfg'
    semillas = list(range(1, args.seeds + 1))
    salida = ejecutar_campana(str(cfg), semillas, pasos=args.pasos, intervalo=args.intervalo)
    guardar(salida, _INTEG / 'resultados')
