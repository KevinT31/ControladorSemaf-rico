"""Puente SUMO del gateway: arranque con seed, extracción de TrafficState
por dirección y aplicación de planes.

Reutiliza el patrón PROBADO de `integracion-sumo/comparacion_sumo.py`
(_mapear_semaforos / _demanda_fase / setProgramLogic preservando la fase en
curso) — ver auditoría. El ICV/PI NO se calculan aquí: el gateway extrae
mediciones CRUDAS y el nodo edge computa (ese es el punto del HIL).

Todo traci vive en el hilo principal del gateway (D-03): traci es
monoconexión y bloqueante.
"""
from __future__ import annotations

import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

from nsb.config import GatewayConfig
from nsb.domain.contracts import ApproachState, PlanSemaforico, TrafficState
from nsb.domain.enums import Direction, SourceKind
from nsb.domain.wire import now_iso

logger = logging.getLogger(__name__)

LONGITUD_VEHICULO_M = 7.5   # mismo factor que comparacion_sumo (_demanda_fase)


def _importar_traci():
    """Importa traci con SUMO_HOME/tools en sys.path (patrón del repo)."""
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        tools = str(Path(sumo_home) / "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
    import traci  # noqa: PLC0415
    return traci


def digest_escenario(cfg: GatewayConfig) -> str:
    """SHA-256 combinado de sumocfg + net + rou + additional: si alguien
    edita el escenario, las corridas dejan de ser comparables y SE NOTA."""
    base = Path(cfg.sumo_cfg).parent
    h = hashlib.sha256()
    for patron in ("*.sumocfg", "*.net.xml", "*.rou.xml", "*.tls.xml"):
        for p in sorted(base.glob(patron)):
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


class SumoBridge:
    """Encapsula la sesión traci del gateway (una intersección, D-A)."""

    def __init__(self, cfg: GatewayConfig):
        self._cfg = cfg
        self._traci = _importar_traci()
        self._logic = None
        self._lanes: Dict[Direction, List[str]] = {}
        self._sim_time = 0.0

    # ------------------------------------------------------------------ #
    def start(self) -> None:
        cfg = self._cfg
        if not Path(cfg.sumo_cfg).exists():
            raise FileNotFoundError(
                f"escenario no encontrado: {cfg.sumo_cfg} "
                f"(¿ejecutaste generar_escenario.py?)")
        self._traci.start([
            cfg.sumo_binary, "-c", cfg.sumo_cfg,
            "--seed", str(cfg.seed),
            "--step-length", "1",
            "--start", "--quit-on-end",
            "--no-warnings", "true",
        ])
        self._mapear_tls()
        logger.info("SUMO iniciado: %s (seed=%s, tls=%s)",
                    cfg.sumo_cfg, cfg.seed, cfg.phase_map.tls_id)

    def close(self) -> None:
        try:
            self._traci.close()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    def _mapear_tls(self) -> None:
        """Carga la logic del TLS y deriva los carriles entrantes de cada
        dirección desde los índices de fase DECLARADOS en gateway.yaml."""
        t = self._traci
        pm = self._cfg.phase_map
        tls_ids = t.trafficlight.getIDList()
        if pm.tls_id not in tls_ids:
            raise ValueError(
                f"tls_id {pm.tls_id!r} no existe en el escenario; hay: {tls_ids}")

        programa = t.trafficlight.getProgram(pm.tls_id)
        logics = t.trafficlight.getAllProgramLogics(pm.tls_id)
        self._logic = next(logic for logic in logics if logic.programID == programa)

        n_fases = len(self._logic.phases)
        for nombre, idx in (("ns_green_index", pm.ns_green_index),
                            ("eo_green_index", pm.eo_green_index)):
            if idx >= n_fases:
                raise ValueError(f"{nombre}={idx} fuera de rango "
                                 f"(el programa tiene {n_fases} fases)")

        links = t.trafficlight.getControlledLinks(pm.tls_id)

        def lanes_de_fase(idx_fase: int) -> List[str]:
            estado = self._logic.phases[idx_fase].state
            lanes: List[str] = []
            for j, grupo_links in enumerate(links):
                if j < len(estado) and estado[j] in "Gg":
                    for (lane_in, _lane_out, _via) in grupo_links:
                        if lane_in not in lanes:
                            lanes.append(lane_in)
            return lanes

        self._lanes[Direction.NS] = lanes_de_fase(pm.ns_green_index)
        self._lanes[Direction.EO] = lanes_de_fase(pm.eo_green_index)
        if not self._lanes[Direction.NS] or not self._lanes[Direction.EO]:
            raise ValueError(
                "mapeo de fases sin carriles: revisar ns/eo_green_index")
        logger.info("carriles NS=%s EO=%s",
                    self._lanes[Direction.NS], self._lanes[Direction.EO])

    # ------------------------------------------------------------------ #
    def avanzar(self, pasos: int) -> float:
        """Avanza `pasos` de simulación (1 s cada uno). Devuelve sim_time."""
        t = self._traci
        for _ in range(pasos):
            t.simulationStep()
        self._sim_time = float(t.simulation.getTime())
        return self._sim_time

    def extraer_estado(self, experiment_id: str, seq: int,
                       intersection_id: str) -> TrafficState:
        """Mediciones CRUDAS por dirección (mismas magnitudes que
        _demanda_fase: cola por detenidos×7.5 m, velocidad de movimiento,
        flujo por presencia, conteos)."""
        t = self._traci

        def acceso(lanes: List[str]) -> ApproachState:
            n_total = 0
            detenidos = 0
            vels: List[float] = []
            for ln in lanes:
                n = t.lane.getLastStepVehicleNumber(ln)
                n_total += n
                h = t.lane.getLastStepHaltingNumber(ln)
                detenidos += h
                vp = t.lane.getLastStepMeanSpeed(ln) * 3.6
                if vp > 0:
                    vels.append(vp)
            vel_mov = sum(vels) / len(vels) if vels else 0.0
            paso_s = max(1.0, float(t.simulation.getDeltaT()))
            flujo = (n_total / paso_s) * 60.0
            return ApproachState(
                queue_m=detenidos * LONGITUD_VEHICULO_M,
                speed_kmh=vel_mov,
                flow_veh_min=min(flujo, 60.0),
                num_vehicles=n_total,
                stopped_vehicles=detenidos,
            )

        return TrafficState(
            experiment_id=experiment_id,
            intersection_id=intersection_id,
            source=SourceKind.SUMO_HIL,
            seq=seq,
            sim_time_s=self._sim_time,
            wall_time_iso=now_iso(),
            control_interval_s=self._cfg.control_interval_s,
            approaches={
                Direction.NS: acceso(self._lanes[Direction.NS]),
                Direction.EO: acceso(self._lanes[Direction.EO]),
            },
        )

    def aplicar_plan(self, plan: PlanSemaforico) -> None:
        """Aplica los tiempos de verde al TLS con setProgramLogic,
        preservando la fase en curso (patrón _redistribuir_verde)."""
        t = self._traci
        pm = self._cfg.phase_map

        for idx, dur in ((pm.ns_green_index, plan.t_verde_ns),
                         (pm.eo_green_index, plan.t_verde_eo)):
            fase = self._logic.phases[idx]
            fase.duration = float(dur)
            fase.minDur = float(dur)
            fase.maxDur = float(dur)
        try:
            self._logic.currentPhaseIndex = t.trafficlight.getPhase(pm.tls_id)
        except Exception:
            pass
        t.trafficlight.setProgramLogic(pm.tls_id, self._logic)
        logger.debug("plan aplicado a SUMO: NS=%.1fs EO=%.1fs",
                     plan.t_verde_ns, plan.t_verde_eo)
