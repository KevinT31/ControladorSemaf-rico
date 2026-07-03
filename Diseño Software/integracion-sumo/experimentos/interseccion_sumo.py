"""
Adaptador de infraestructura: sensa y actúa sobre UN semáforo de SUMO.

Clasifica automáticamente las señales del semáforo en ejes NS/EO a partir del
rumbo geométrico de sus carriles entrantes, identifica las fases de verde de
cada eje en el programa vigente y permite:
  - leer el estado agregado por eje (colas, velocidad, espera, ocupación...)
  - aplicar nuevos tiempos de verde SIN alterar amarillos ni todo-rojo.

Funciona con cualquier intersección de 2 ejes cuyo programa alterne verdes
(el canónico de cruce-simple, o semáforos reales de las redes de Lima cuyo
programa se haya normalizado antes con un programa estático).
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Tuple

from .entorno import traci
from .base import EstadoEje

logger = logging.getLogger(__name__)

M_POR_VEHICULO = 7.5          # longitud media ocupada por vehículo detenido
FLUJO_SATURACION_VEH_MIN = 30.0  # cap del núcleo ICV


def _rumbo_es_ns(shape: List[Tuple[float, float]]) -> bool:
    """True si el carril corre principalmente Norte-Sur (|dy| > |dx|)."""
    (x0, y0), (x1, y1) = shape[0], shape[-1]
    return abs(y1 - y0) > abs(x1 - x0)


class InterseccionSUMO:
    """Interfaz de UNA intersección semaforizada dentro de la simulación activa."""

    def __init__(self, tls_id: str):
        self.tls_id = tls_id
        self.lanes_ns: List[str] = []
        self.lanes_eo: List[str] = []
        self.largo_ns_km = 0.0
        self.largo_eo_km = 0.0
        self.idx_fase_ns: int = -1
        self.idx_fase_eo: int = -1
        self.logic = None
        self.preparada = False

    # ------------------------------------------------------------------ #
    # Preparación: clasificar señales/carriles/fases
    # ------------------------------------------------------------------ #
    def preparar(self) -> 'InterseccionSUMO':
        links = traci.trafficlight.getControlledLinks(self.tls_id)
        # carril entrante por índice de señal
        lane_por_senal: Dict[int, str] = {}
        for idx, conns in enumerate(links):
            if conns and conns[0] and conns[0][0]:
                lane_por_senal[idx] = conns[0][0]

        # eje por carril según rumbo geométrico
        eje_por_senal: Dict[int, str] = {}
        vistos: Dict[str, str] = {}
        for idx, lane in lane_por_senal.items():
            if lane not in vistos:
                try:
                    shape = traci.lane.getShape(lane)
                    vistos[lane] = 'ns' if _rumbo_es_ns(shape) else 'eo'
                except Exception:
                    vistos[lane] = 'ns'
            eje_por_senal[idx] = vistos[lane]

        self.lanes_ns = sorted({l for l, e in vistos.items() if e == 'ns'})
        self.lanes_eo = sorted({l for l, e in vistos.items() if e == 'eo'})
        self.largo_ns_km = sum(traci.lane.getLength(l) for l in self.lanes_ns) / 1000.0
        self.largo_eo_km = sum(traci.lane.getLength(l) for l in self.lanes_eo) / 1000.0

        # localizar la fase de verde de cada eje en el programa vigente
        logics = traci.trafficlight.getAllProgramLogics(self.tls_id)
        if not logics:
            raise RuntimeError(f'Semáforo {self.tls_id} sin programa')
        self.logic = logics[0]
        for idx, fase in enumerate(self.logic.phases):
            st = fase.state
            if 'y' in st.lower() or not any(c in 'Gg' for c in st):
                continue  # transición o fase sin verde
            # eje mayoritario de las señales en verde de esta fase
            votos = {'ns': 0, 'eo': 0}
            for i, c in enumerate(st):
                if c in 'Gg' and i in eje_por_senal:
                    votos[eje_por_senal[i]] += 1
            eje = 'ns' if votos['ns'] >= votos['eo'] else 'eo'
            if eje == 'ns' and self.idx_fase_ns < 0:
                self.idx_fase_ns = idx
            elif eje == 'eo' and self.idx_fase_eo < 0:
                self.idx_fase_eo = idx

        if self.idx_fase_ns < 0 or self.idx_fase_eo < 0:
            raise RuntimeError(
                f'Semáforo {self.tls_id}: no se pudieron identificar fases de '
                f'verde NS y EO (¿programa no canónico?)')

        self.preparada = True
        logger.info(
            f'[{self.tls_id}] ejes: NS={len(self.lanes_ns)} carriles, '
            f'EO={len(self.lanes_eo)} carriles; fase NS={self.idx_fase_ns}, '
            f'fase EO={self.idx_fase_eo}')
        return self

    # ------------------------------------------------------------------ #
    # Sensado instantáneo por eje (el runner promedia por intervalo)
    # ------------------------------------------------------------------ #
    def medir_eje_instante(self, eje: str) -> Dict[str, float]:
        lanes = self.lanes_ns if eje == 'ns' else self.lanes_eo
        n = 0
        detenidos = 0
        espera = 0.0
        suma_vel_ms = 0.0
        ocupacion = 0.0
        for ln in lanes:
            k = traci.lane.getLastStepVehicleNumber(ln)
            n += k
            detenidos += traci.lane.getLastStepHaltingNumber(ln)
            espera += traci.lane.getWaitingTime(ln)
            suma_vel_ms += traci.lane.getLastStepMeanSpeed(ln) * k
            ocupacion += traci.lane.getLastStepOccupancy(ln)
        n_lanes = max(1, len(lanes))
        return {
            'n_veh': float(n),
            'cola_veh': float(detenidos),
            'espera_s': float(espera),
            'vel_ms': (suma_vel_ms / n) if n else 0.0,
            'ocupacion': ocupacion / n_lanes,
        }

    def ids_vehiculos_eje(self, eje: str) -> List[str]:
        lanes = self.lanes_ns if eje == 'ns' else self.lanes_eo
        ids: List[str] = []
        for ln in lanes:
            try:
                ids.extend(traci.lane.getLastStepVehicleIDs(ln))
            except Exception:
                continue
        return ids

    def fase_actual(self) -> int:
        return traci.trafficlight.getPhase(self.tls_id)

    def verdes_actuales(self) -> Tuple[float, float]:
        fases = traci.trafficlight.getAllProgramLogics(self.tls_id)[0].phases
        return float(fases[self.idx_fase_ns].duration), float(fases[self.idx_fase_eo].duration)

    # ------------------------------------------------------------------ #
    # Actuación: nuevos verdes manteniendo amarillo/todo-rojo y fase en curso
    # ------------------------------------------------------------------ #
    def aplicar_verdes(self, verde_ns: float, verde_eo: float):
        if not self.preparada:
            raise RuntimeError('InterseccionSUMO.preparar() no fue llamada')
        logic = traci.trafficlight.getAllProgramLogics(self.tls_id)[0]
        for idx, dur in ((self.idx_fase_ns, verde_ns), (self.idx_fase_eo, verde_eo)):
            ph = logic.phases[idx]
            ph.duration = float(dur)
            ph.minDur = float(dur)
            ph.maxDur = float(dur)
        # conservar la fase en curso para no reiniciar el ciclo
        try:
            logic.currentPhaseIndex = traci.trafficlight.getPhase(self.tls_id)
        except Exception:
            pass
        traci.trafficlight.setProgramLogic(self.tls_id, logic)


def construir_estado_eje(acum: Dict[str, float], muestras: int,
                         flujo_veh_min: float, largo_km: float,
                         calc_icv, cola_max: float) -> EstadoEje:
    """Convierte acumulados de un intervalo en EstadoEje (promedios + ICV/PI)."""
    m = max(1, muestras)
    n_veh = acum['n_veh'] / m
    cola = acum['cola_veh'] / m
    espera = acum['espera_s'] / m
    vel_ms = (acum['vel_ms'] / m)
    vel_kmh = vel_ms * 3.6
    ocup = acum['ocupacion'] / m

    resultado_icv = calc_icv.calcular(
        longitud_cola=cola * M_POR_VEHICULO,
        velocidad_promedio=vel_kmh,
        flujo_vehicular=min(flujo_veh_min, FLUJO_SATURACION_VEH_MIN),
    )
    # PI (eficiencia, Cap.6): fracción en movimiento + velocidad normalizada
    frac_mov = ((n_veh - cola) / n_veh) if n_veh > 0 else 1.0
    frac_mov = max(0.0, min(1.0, frac_mov))
    vel_norm = max(0.0, min(1.0, vel_kmh / 50.0))
    pi = 0.5 * frac_mov + 0.5 * vel_norm

    return EstadoEje(
        n_veh=round(n_veh, 3),
        cola_veh=round(cola, 3),
        cola_max_veh=float(cola_max),
        espera_s=round(espera, 2),
        vel_kmh=round(vel_kmh, 2),
        flujo_veh_min=round(flujo_veh_min, 2),
        densidad_veh_km=round(n_veh / largo_km, 2) if largo_km > 0 else 0.0,
        ocupacion=round(ocup, 4),
        icv=round(float(resultado_icv['icv']), 4),
        pi=round(pi, 4),
    )
