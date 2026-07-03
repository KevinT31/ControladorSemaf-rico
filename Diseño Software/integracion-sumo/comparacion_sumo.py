"""
Comparación REAL Tiempo-Fijo vs Adaptativo sobre SUMO.

Ejecuta dos simulaciones del MISMO escenario SUMO (misma semilla/demanda):
  1. BASE (tiempo fijo): los semáforos se fuerzan a programa estático con
     duraciones fijas (sin actuación).
  2. ADAPTATIVO: cada `intervalo_control` segundos se mide el estado real de
     cada intersección, se calcula el ICV (núcleo) y la lógica difusa decide
     el tiempo de verde, que se aplica vía TraCI/libsumo.

NO usa np.random: todas las métricas provienen de la simulación real de SUMO.
Devuelve dos listas de MetricasRed listas para SistemaComparacion.
"""

import sys
import logging
from collections import deque
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

# Núcleo
_RAIZ = Path(__file__).parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from nucleo.metricas_red import MetricasRed
from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion
from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6
from nucleo.seguridad_semaforica import LIMITES as _LIMITES_SEG

logger = logging.getLogger(__name__)

# Conexión SUMO (libsumo si está disponible)
_INTEG = Path(__file__).parent
if str(_INTEG) not in sys.path:
    sys.path.insert(0, str(_INTEG))
from conector_sumo import traci, USANDO_LIBSUMO  # noqa: E402

import sumolib  # noqa: E402

VEL_LIBRE_MS = 13.89  # ~50 km/h


def _iniciar(ruta_cfg: str, seed: Optional[int] = None):
    """Arranca SUMO headless con la configuración dada.

    `seed` fija la semilla de SUMO (reproducibilidad); sin ella SUMO usa la
    del .sumocfg o la por defecto y la corrida NO es semilla-controlada.
    """
    sumo_bin = sumolib.checkBinary('sumo')
    cmd = [sumo_bin, '-c', str(ruta_cfg), '--start', '--quit-on-end',
           '--no-warnings', 'true']
    if seed is not None:
        cmd += ['--seed', str(int(seed))]
    traci.start(cmd)


def _forzar_tiempo_fijo(t_verde: float = 30.0):
    """Reescribe cada semáforo como programa ESTÁTICO con verdes fijos.

    Mantiene la estructura de fases existente pero fija las duraciones de las
    fases de verde a `t_verde` y desactiva la actuación (type='static').
    """
    convertidos = 0
    for tls_id in traci.trafficlight.getIDList():
        try:
            logics = traci.trafficlight.getAllProgramLogics(tls_id)
            if not logics:
                continue
            logic = logics[0]
            for fase in logic.phases:
                estado = fase.state
                # Fase con algún verde -> duración fija; ámbar/rojo se respetan
                if 'g' in estado.lower():
                    fase.duration = t_verde
                    fase.minDur = t_verde
                    fase.maxDur = t_verde
            # type 0 = estático (sin actuación)
            try:
                logic.type = 0
            except Exception:
                pass
            traci.trafficlight.setProgramLogic(tls_id, logic)
            convertidos += 1
        except Exception:
            continue
    return convertidos


def _metricas_instante(ts: datetime, num_int: int) -> Tuple[MetricasRed, int, int]:
    """Construye una MetricasRed con datos REALES del paso actual de SUMO.

    Devuelve además (halting, arrived) del paso para acumular métricas de
    desempeño globales (demora total y throughput).
    """
    # Métricas REALES a nivel vehículo (O(vehículos), no O(edges); escala con
    # el tráfico y es viable en redes grandes como lima-amplio: 15k edges).
    veh_ids = traci.vehicle.getIDList()
    n_veh = len(veh_ids)
    suma_vel_ms = 0.0
    halting = 0
    for v in veh_ids:
        sp = traci.vehicle.getSpeed(v)  # m/s
        suma_vel_ms += sp
        if sp < 0.1:  # vehículo detenido
            halting += 1
    if n_veh:
        vavg_ms = suma_vel_ms / n_veh
        vavg = vavg_ms * 3.6  # km/h
        ql_red = halting / n_veh
        # ICV_red: PROXY de red de 2 términos (fracción detenida + caída de
        # velocidad). NO es el ICV de 4 componentes del núcleo (ese opera por
        # intersección dentro del lazo de control); al reportarlo debe
        # etiquetarse como "ICV de red (proxy)" para no confundirlos.
        icv_red = 0.5 * ql_red + 0.5 * (1.0 - min(1.0, vavg_ms / VEL_LIBRE_MS))
    else:
        vavg = 0.0
        ql_red = 0.0
        icv_red = 0.0

    # Flujo: vehículos que llegaron a destino en el paso -> veh/min (paso=1s)
    arrived = int(traci.simulation.getArrivedNumber())
    q_red = float(arrived) * 60.0

    libres = moderadas = congestionadas = 0

    metrica = MetricasRed(
        timestamp=ts,
        ICV_red=icv_red,
        Vavg_red=vavg,
        q_red=q_red,
        QL_red=ql_red,
        num_intersecciones=num_int,
        intersecciones_libres=libres,
        intersecciones_moderadas=moderadas,
        intersecciones_congestionadas=congestionadas,
    )
    return metrica, halting, arrived


class ContadorCruces:
    """FLUJO REAL por carril: vehículos que SALEN del carril (cruzan la línea
    de parada / avanzan al siguiente tramo) contados por diferencia de
    conjuntos de IDs, agregados en una ventana móvil.

    Corrige el cálculo anterior, que usaba vehículos PRESENTES por paso: con
    Δt≈1 s, 1 solo vehículo presente ya daba 60 veh/min y saturaba el cap de
    30 veh/min del ICV, dejando el término de flujo constante. Aquí el flujo
    es un conteo de CRUCES por ventana temporal (misma técnica que el
    acumulador de Webster en comparacion_multibaseline).

    `actualizar()` debe llamarse UNA vez por paso de simulación.
    """

    def __init__(self, lanes: List[str], ventana_s: int = 60):
        lanes = list(dict.fromkeys(lanes))
        self.ventana = max(1, int(ventana_s))
        self.vistos = {ln: set() for ln in lanes}
        self.hist = {ln: deque(maxlen=self.ventana) for ln in lanes}
        self.fallos_sensor = 0   # lecturas TraCI fallidas (trazabilidad)

    def actualizar(self):
        for ln, antes in self.vistos.items():
            try:
                ahora = set(traci.lane.getLastStepVehicleIDs(ln))
            except Exception:
                self.fallos_sensor += 1
                ahora = set()
            self.hist[ln].append(len(antes - ahora))
            self.vistos[ln] = ahora

    def flujo_veh_min(self, lanes: List[str]) -> float:
        """veh/min que cruzaron los carriles dados en la ventana móvil."""
        total = 0
        seg = 0
        for ln in lanes:
            h = self.hist.get(ln)
            if h:
                total += sum(h)
                seg = max(seg, len(h))
        return (total / seg) * 60.0 if seg else 0.0


# ----------------------------------------------------------------------
# Transición segura entre fases (compartido por difuso_ia y max-pressure)
# ----------------------------------------------------------------------
def _estado_ambar(estado_actual: str, estado_objetivo: str) -> str:
    """Estado de ámbar SINTÉTICO cuando el programa del TLS no trae fase 'y':
    toda señal que pierde el verde pasa a 'y'; el resto conserva su color.
    Garantiza que nunca haya un cambio directo verde->verde sin despeje.
    """
    out = []
    for a, b in zip(estado_actual, estado_objetivo):
        out.append('y' if (a in 'Gg' and b not in 'Gg') else a)
    return ''.join(out)


def _fase_todo_rojo_tras(logic, idx_ambar: int) -> Optional[int]:
    """Índice de la fase de despeje (todo-rojo) inmediatamente posterior al
    ámbar, si el programa la define (sin 'g' ni 'y'). El controlador debe
    servirla en vez de saltar directo al verde objetivo."""
    n = len(logic.phases)
    j = (idx_ambar + 1) % n
    st = logic.phases[j].state.lower()
    if 'g' not in st and 'y' not in st:
        return j
    return None


def _eventos_paso() -> dict:
    """Eventos de VALIDEZ del paso actual (auditoría del experimento):
    - teleports: vehículos que SUMO teletransporta (gridlock 'rescatado';
      --time-to-teleport). Si difieren mucho entre estrategias, sesgan
      demora/throughput y deben reportarse.
    - backlog: vehículos pendientes de inserción (la red no los admite);
      no aparecen en getIDList y por eso NO cuentan en la demora por halting.
    - departed: vehículos insertados este paso (denominador honesto de la
      demora por vehículo).
    """
    try:
        tele = int(traci.simulation.getStartingTeleportNumber())
    except Exception:
        tele = 0
    try:
        backlog = len(traci.simulation.getPendingVehicles())
    except Exception:
        backlog = 0
    try:
        dep = int(traci.simulation.getDepartedNumber())
    except Exception:
        dep = 0
    return {'teleports': tele, 'backlog': backlog, 'departed': dep}


def _mapear_semaforos() -> dict:
    """Mapea cada semáforo a sus fases de verde, los carriles entrantes que
    cada fase sirve, y el presupuesto total de verde del ciclo.

    Debe llamarse DESPUÉS de _forzar_tiempo_fijo (logica estática conocida).
    """
    info = {}
    for tls in traci.trafficlight.getIDList():
        try:
            logics = traci.trafficlight.getAllProgramLogics(tls)
            if not logics:
                continue
            logic = logics[0]
            links = traci.trafficlight.getControlledLinks(tls)  # por índice de señal
            fases_verdes = []
            for idx, ph in enumerate(logic.phases):
                st = ph.state
                if 'y' in st.lower():
                    continue  # fase de transición (ámbar), no se ajusta
                sig_verdes = [i for i, c in enumerate(st) if c in ('G', 'g')]
                if not sig_verdes:
                    continue
                lanes = []
                for i in sig_verdes:
                    if i < len(links) and links[i]:
                        for conn in links[i]:
                            if conn and conn[0]:
                                lanes.append(conn[0])  # carril entrante
                lanes = list(dict.fromkeys(lanes))
                if lanes:
                    fases_verdes.append({'idx': idx, 'lanes': lanes,
                                         'base': float(ph.duration)})
            if fases_verdes:
                info[tls] = {
                    'logic': logic,
                    'fases_verdes': fases_verdes,
                    'presupuesto': sum(g['base'] for g in fases_verdes),
                }
        except Exception:
            continue
    return info


def _demanda_fase(lanes, calc_icv,
                  medidor: Optional[ContadorCruces] = None) -> Tuple[float, float]:
    """ICV y PI (eficiencia) reales de una fase desde sus carriles entrantes.

    DEFINICIÓN ÚNICA DE FLUJO: vehículos que CRUZAN (salen del carril) por
    ventana temporal, medidos por `medidor` (ContadorCruces). El cálculo
    anterior usaba vehículos PRESENTES/Δt y saturaba el cap de 30 veh/min con
    un solo vehículo, dejando el término de flujo del ICV constante (bug).
    Sin medidor, el flujo se reporta 0 (término neutro) en vez de inventar
    un valor saturado.

    PI sigue la idea del Cap. 6 (PI = Vavg_movimiento / detenidos): es ALTO en
    flujo libre (eficiente) y BAJO bajo congestión (ineficiente). Se acota a
    [0,1] combinando la fracción de vehículos en movimiento y la velocidad
    normalizada, para alimentar los conjuntos difusos de PI.
    """
    cola_m = 0.0
    vels = []
    n_total = 0
    detenidos = 0
    for ln in lanes:
        try:
            n = traci.lane.getLastStepVehicleNumber(ln)
            n_total += n
            h = traci.lane.getLastStepHaltingNumber(ln)
            detenidos += h
            cola_m += h * 7.5
            vp = traci.lane.getLastStepMeanSpeed(ln) * 3.6
            if vp > 0:
                vels.append(vp)
        except Exception:
            continue
    vel_mov = sum(vels) / len(vels) if vels else 0.0
    flujo = medidor.flujo_veh_min(lanes) if medidor is not None else 0.0
    icv = calc_icv.calcular(
        longitud_cola=cola_m,
        velocidad_promedio=vel_mov,
        flujo_vehicular=min(flujo, 30.0),
    )['icv']
    # PI = eficiencia: alto si la mayoría se mueve y rápido; bajo si hay colas
    moving = max(0, n_total - detenidos)
    frac_mov = (moving / n_total) if n_total else 1.0
    vel_norm = min(1.0, vel_mov / 50.0)
    pi = 0.5 * frac_mov + 0.5 * vel_norm
    return icv, pi


def _redistribuir_verde(info: dict, calc_icv: CalculadorICV,
                        difuso: ControladorDifusoCapitulo6,
                        ema: dict = None, alpha: float = 0.4,
                        gamma: float = 2.0,
                        medidor: Optional[ContadorCruces] = None):
    """Control adaptativo POR DIRECCIÓN: reparte el MISMO presupuesto de verde
    del ciclo entre las fases proporcionalmente a su demanda difusa. El ciclo
    total NO cambia (comparación justa); las fases congestionadas reciben más
    verde a costa de las fluidas, sin hambrear (se respeta T_verde_min).

    Palancas:
    - ema/alpha (PALANCA 1, suavizado): media móvil exponencial del verde
      deseado por fase entre decisiones, para evitar oscilaciones por ruido
      del sensado instantáneo. `smoothed = alpha*nuevo + (1-alpha)*previo`.
    - gamma (PALANCA 3, agresividad): exponente sobre los pesos antes de
      repartir el presupuesto; gamma>1 concentra más verde en la fase más
      congestionada (control más decidido).
    """
    for tls, data in info.items():
        try:
            gps = data['fases_verdes']
            presupuesto = data['presupuesto']
            # Verde deseado por fase según ICV+PI reales -> difusa Mamdani
            deseados = []
            for g in gps:
                icv, pi = _demanda_fase(g['lanes'], calc_icv, medidor=medidor)
                delta = difuso.calcular_ajuste_verde(icv=icv, pi=pi, ev=0.0)['delta_t_porcentaje']
                d = difuso.calcular_tiempo_verde_ajustado(
                    T_base=g['base'], delta_t_porcentaje=delta)
                deseados.append(max(difuso.T_verde_min, d))

            # PALANCA 1: suavizado EMA del deseado por fase
            if ema is not None:
                prev = ema.get(tls)
                if prev is not None and len(prev) == len(deseados):
                    deseados = [alpha * d + (1 - alpha) * p
                                for d, p in zip(deseados, prev)]
                ema[tls] = deseados

            # PALANCA 3: agresividad (exponente gamma sobre los pesos)
            pesos = [d ** gamma for d in deseados]
            suma = sum(pesos)
            if suma <= 0:
                continue
            # Repartir el presupuesto en proporción al peso
            nuevos = [presupuesto * w / suma for w in pesos]
            # Garantizar mínimo y reescalar para conservar el presupuesto
            nuevos = [max(difuso.T_verde_min, x) for x in nuevos]
            s2 = sum(nuevos)
            if s2 > 0:
                nuevos = [presupuesto * x / s2 for x in nuevos]

            # ── Guardia de SEGURIDAD FUNCIONAL (autoridad central) ──
            # El módulo adaptativo NUNCA puede salir de los límites duros, pase
            # lo que pase con el reparto. Solo se registra si hubo que corregir.
            nuevos_seg = []
            for x in nuevos:
                xs = max(_LIMITES_SEG.T_VERDE_MIN, min(float(x), _LIMITES_SEG.T_VERDE_MAX))
                if abs(xs - x) > 1e-6:
                    logger.warning(f"[SEGURIDAD] verde {x:.1f}s acotado a {xs:.1f}s (límite duro)")
                nuevos_seg.append(xs)
            nuevos = nuevos_seg

            logic = data['logic']
            # Conservar la fase en curso para no reiniciar el ciclo
            try:
                logic.currentPhaseIndex = traci.trafficlight.getPhase(tls)
            except Exception:
                pass
            for g, nv in zip(gps, nuevos):
                ph = logic.phases[g['idx']]
                ph.duration = float(nv)
                ph.minDur = float(nv)
                ph.maxDur = float(nv)
            traci.trafficlight.setProgramLogic(tls, logic)
        except Exception as e:
            # El control de este TLS falló: se conserva el programa previo
            # (estado seguro conocido) y el fallo queda TRAZADO, no oculto.
            logger.warning(f"[difuso] fallo de control en TLS {tls}: "
                           f"{type(e).__name__}: {e}")
            continue


def _resumen_desempeno(demora_veh_s: int, arrivals: int, pasos: int) -> dict:
    """Métricas de desempeño global para evaluar control semafórico:
    - throughput: vehículos que completaron su viaje.
    - demora_media: segundos de detención por vehículo procesado (menor = mejor).
    """
    return {
        'throughput': arrivals,
        'demora_total_veh_s': demora_veh_s,
        'demora_media_s': (demora_veh_s / arrivals) if arrivals else 0.0,
    }


def ejecutar_comparacion_real(
    ruta_cfg: str,
    pasos: int = 700,
    intervalo_control: int = 25,
    max_tls_adaptativo: int = None,
    gamma: float = 5.0,
    alpha: float = 0.35,
    seed: Optional[int] = None,
) -> Tuple[List[MetricasRed], List[MetricasRed], dict]:
    """Ejecuta las dos simulaciones reales (misma semilla si se indica).

    Devuelve (metricas_fijo, metricas_adapt, resumen) donde `resumen` tiene
    métricas de desempeño global por estrategia: throughput y demora media.
    """
    params = ParametrosInterseccion()

    # ---- Corrida 1: TIEMPO FIJO ----
    _iniciar(ruta_cfg, seed=seed)
    n_int = len(traci.trafficlight.getIDList())
    _forzar_tiempo_fijo(t_verde=30.0)
    metricas_fijo: List[MetricasRed] = []
    demora_f = 0
    arr_f = 0
    base = datetime.now()
    for i in range(pasos):
        traci.simulationStep()
        met, halting, arrived = _metricas_instante(base + timedelta(seconds=i), n_int)
        metricas_fijo.append(met)
        demora_f += halting        # veh detenidos * 1s = veh·s de demora
        arr_f += arrived
    traci.close()

    # ---- Corrida 2: ADAPTATIVO (ICV + difusa Mamdani Cap.6, por dirección) ----
    calc_icv = CalculadorICV(params)
    difuso = ControladorDifusoCapitulo6()
    _iniciar(ruta_cfg, seed=seed)
    # Partimos del MISMO programa estático que el fijo y mapeamos sus fases,
    # así el presupuesto de verde por ciclo es idéntico al del caso base.
    _forzar_tiempo_fijo(t_verde=30.0)
    info = _mapear_semaforos()
    medidor = ContadorCruces([l for d in info.values()
                              for g in d['fases_verdes'] for l in g['lanes']])
    ema = {}  # PALANCA 1: estado de suavizado por semáforo
    metricas_adapt: List[MetricasRed] = []
    demora_a = 0
    arr_a = 0
    base2 = datetime.now()
    for i in range(pasos):
        traci.simulationStep()
        medidor.actualizar()
        if i % intervalo_control == 0:
            _redistribuir_verde(info, calc_icv, difuso,
                                ema=ema, alpha=alpha, gamma=gamma,
                                medidor=medidor)
        met, halting, arrived = _metricas_instante(base2 + timedelta(seconds=i), n_int)
        metricas_adapt.append(met)
        demora_a += halting
        arr_a += arrived
    traci.close()

    resumen = {
        'fijo': _resumen_desempeno(demora_f, arr_f, pasos),
        'adaptativo': _resumen_desempeno(demora_a, arr_a, pasos),
    }
    return metricas_fijo, metricas_adapt, resumen


if __name__ == '__main__':
    cfg = _INTEG / 'escenarios' / 'lima-centro' / 'comparacion.sumocfg'
    if not cfg.exists():
        cfg = _INTEG / 'escenarios' / 'lima-centro' / 'osm.sumocfg'
    mf, ma, res = ejecutar_comparacion_real(str(cfg), pasos=600, intervalo_control=15)
    import statistics as st
    print('motor libsumo:', USANDO_LIBSUMO)
    print('FIJO   ICV', round(st.mean(m.ICV_red for m in mf), 4),
          'Vavg', round(st.mean(m.Vavg_red for m in mf), 2),
          'throughput', res['fijo']['throughput'],
          'demora_media', round(res['fijo']['demora_media_s'], 2))
    print('ADAPT  ICV', round(st.mean(m.ICV_red for m in ma), 4),
          'Vavg', round(st.mean(m.Vavg_red for m in ma), 2),
          'throughput', res['adaptativo']['throughput'],
          'demora_media', round(res['adaptativo']['demora_media_s'], 2))
