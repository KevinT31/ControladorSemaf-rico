"""Composición del nodo NSB: config → fuente → autoridad → telemetría.

`NsbNode.from_config` construye el grafo de objetos una sola vez (el modo se
resuelve aquí con la triple compuerta y ya no puede elevarse — D-H).
`run()` consume una fuente de estados de forma secuencial y determinista.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from nsb.actuation.simulated import SimulatedActuator
from nsb.authority.direct_lab_gate import resolve_mode
from nsb.authority.modes import Authority
from nsb.config import NodeConfig
from nsb.core.adapters import AdaptadorDifuso, AdaptadorICV
from nsb.core.pipeline import DecisionPipeline
from nsb.domain.contracts import TrafficState
from nsb.domain.enums import Mode, PhaseId
from nsb.safety.message_guard import MessageGuard
from nsb.sources.base import TrafficStateSource
from nsb.sources.replay import ReplayWriter
from nsb.telemetry.events import CRITICAL, INFO, WARNING, evento
from nsb.telemetry.jsonl_sink import JsonlSink
from nsb.tsc.clock import Clock, SimClock
from nsb.tsc.emulator import TscEmulator
from nsb.tsc.fsm import PhaseFSM

logger = logging.getLogger(__name__)


@dataclass
class RunSummary:
    """Resumen verificable de una corrida del nodo."""
    estados: int = 0
    verdicts: Dict[str, int] = field(default_factory=dict)
    rechazos_guard: int = 0
    violaciones_gate: int = 0
    safe_mode_final: bool = False
    record_path: Optional[str] = None
    events_path: Optional[str] = None


class NsbNode:
    """Nodo semafórico de borde (una intersección)."""

    def __init__(self, cfg: NodeConfig, authority: Authority,
                 clock: Clock, sink: Optional[JsonlSink],
                 mqtt_sink=None):
        self._cfg = cfg
        self._authority = authority
        self._clock = clock
        self._sink = sink
        self._mqtt = mqtt_sink   # MqttTelemetrySink opcional (D-F, spec §28)

    # ------------------------------------------------------------------ #
    @classmethod
    def from_config(cls, cfg: NodeConfig,
                    cli_mode: Optional[Mode] = None,
                    clock: Optional[Clock] = None,
                    experiment_id: str = "local",
                    render_override: Optional[bool] = None) -> "NsbNode":
        mode = resolve_mode(cfg.mode, cfg.allow_direct_lab, cli_mode,
                            cfg.node_id)

        reloj: Clock = clock if clock is not None else SimClock()

        icv = AdaptadorICV()
        difuso = AdaptadorDifuso(
            t_base_ns=cfg.safety.t_base_verde_ns,
            t_base_eo=cfg.safety.t_base_verde_eo,
            t_ambar=cfg.safety.t_ambar,
            t_todo_rojo=cfg.safety.t_todo_rojo,
            t_ciclo=cfg.safety.t_ciclo,
        )
        pipeline = DecisionPipeline(icv=icv, difuso=difuso, mode=mode)

        from nsb.domain.contracts import PlanSemaforico
        plan_base = PlanSemaforico(
            t_verde_ns=cfg.safety.t_base_verde_ns,
            t_verde_eo=cfg.safety.t_base_verde_eo,
            t_ambar=cfg.safety.t_ambar,
            t_todo_rojo=cfg.safety.t_todo_rojo,
        )
        fsm = PhaseFSM(clock=reloj, plan_inicial=plan_base,
                       fase_inicial=PhaseId.NS_VERDE)
        tsc = TscEmulator(
            fsm=fsm, mode=mode,
            max_silence_cycles=cfg.safety.max_silence_cycles,
            defer_during_preempt=(mode is not Mode.AUTOMATED_DIRECT_LAB),
        )
        guard = MessageGuard()

        actuator = None
        if mode is not Mode.ADVISORY:
            if cfg.actuator.type == "gpio":
                # Import perezoso: JAMÁS a nivel de módulo (spec §23)
                from nsb.actuation.gpio import GPIOActuator
                actuator = GPIOActuator(pinout_path=cfg.actuator.pinout_path)
            else:
                render = (render_override if render_override is not None
                          else cfg.actuator.render)
                actuator = SimulatedActuator(render=render)

        authority = Authority(mode=mode, pipeline=pipeline, tsc=tsc,
                              guard=guard, actuator=actuator)

        sink = JsonlSink(cfg.telemetry.jsonl_dir, cfg.node_id,
                         experiment_id=experiment_id)
        mqtt_sink = None
        if cfg.telemetry.mqtt_enabled:
            # Import perezoso: la base no exige paho-mqtt (spec §23 análogo).
            # Config TLS inválida falla AQUÍ (arranque), no en runtime.
            from nsb.comms.mqtt_telemetry import MqttTelemetrySink
            mqtt_sink = MqttTelemetrySink(cfg.telemetry, cfg.node_id)
        node = cls(cfg, authority, reloj, sink, mqtt_sink=mqtt_sink)
        node._emit(evento("node_start", cfg.node_id, INFO,
                          mode=mode.value, source=cfg.source.value,
                          actuator=cfg.actuator.type))
        if mode is Mode.AUTOMATED_DIRECT_LAB:
            node._emit(evento("direct_lab_activated", cfg.node_id, CRITICAL,
                              data_note="modo autonomo experimental de "
                                        "laboratorio ACTIVO"))
        return node

    # ------------------------------------------------------------------ #
    @property
    def authority(self) -> Authority:
        return self._authority

    @property
    def mode(self) -> Mode:
        return self._authority.mode

    @property
    def mqtt_sink(self):
        """Sink MQTT opcional (None si mqtt_enabled=false)."""
        return self._mqtt

    def _emit(self, ev) -> None:
        if self._sink is not None:
            self._sink.emit(ev)
        if self._mqtt is not None:
            self._mqtt.emit(ev)   # best-effort; jamás lanza (comms.mqtt)

    # ------------------------------------------------------------------ #
    def process_one(self, state: TrafficState,
                    edad_s: Optional[float] = None):
        """Procesa un TrafficState: avanza reloj, decide, actúa, telemetriza."""
        if state.sim_time_s is not None and isinstance(self._clock, SimClock):
            if not self._clock.set_time(state.sim_time_s):
                logger.warning("sim_time retrocedio (%.1f); ignorado",
                               state.sim_time_s)

        rec, decision = self._authority.process_state(state, edad_s=edad_s)

        severidad = INFO if decision.verdict.value in ("accept", "clamp") else WARNING
        self._emit(evento(
            "decision", self._cfg.node_id, severidad,
            experiment_id=state.experiment_id, seq=state.seq,
            recommendation_id=decision.recommendation_id,
            verdict=decision.verdict.value,
            reasons=decision.reasons,
            phase=decision.applied_phase.phase_id.value,
            safe_mode=decision.safe_mode,
            icv_ns=rec.computed.icv_ns if rec else None,
            icv_eo=rec.computed.icv_eo if rec else None,
            processing_ms=decision.processing_ms,
        ))
        return rec, decision

    def run(self, source: TrafficStateSource,
            writer: Optional[ReplayWriter] = None,
            max_states: Optional[int] = None) -> RunSummary:
        """Consume la fuente hasta agotarla (o max_states)."""
        summary = RunSummary()
        try:
            for state in source:
                if max_states is not None and summary.estados >= max_states:
                    break
                rec, decision = self.process_one(state)
                summary.estados += 1
                v = decision.verdict.value
                summary.verdicts[v] = summary.verdicts.get(v, 0) + 1
                if not decision.recommendation_id and v == "reject":
                    summary.rechazos_guard += 1
                if writer is not None:
                    writer.write_state(state)
                    if rec is not None:
                        writer.write_recommendation(rec)
                    writer.write_decision(decision)
        finally:
            source.close()
            summary.violaciones_gate = self._authority.gate.violaciones_totales
            summary.safe_mode_final = self._authority.tsc.safe_mode
            if writer is not None:
                summary.record_path = str(writer._path)
                writer.close()
            if self._sink is not None and self._sink.path is not None:
                summary.events_path = str(self._sink.path)
            self._emit(evento(
                "node_stop", self._cfg.node_id, INFO,
                estados=summary.estados,
                verdicts=summary.verdicts,
                violaciones_gate=summary.violaciones_gate,
                mqtt_connected=(self._mqtt.connected if self._mqtt else None),
                mqtt_dropped=(self._mqtt.dropped if self._mqtt else None)))
        return summary

    def shutdown(self) -> None:
        self._authority.shutdown()
        if self._mqtt is not None:
            self._mqtt.close()
        if self._sink is not None:
            self._sink.close()
