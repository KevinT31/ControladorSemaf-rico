"""HIL Gateway (spec §13): lazo step-synchronous PC ↔ nodo.

SUMO NO avanza mientras espera la decisión del nodo — eso es lo que hace al
lazo verdaderamente step-synchronous (a diferencia de "SUMO corre libre y la
Pi responde cuando puede", prohibido por la spec).

Determinismo: seed de SUMO + escenario sin rerouting + digest del escenario
en el experiment_id + cero RNG/reloj de pared en la ruta de decisión.

Política de timeout (D-C): ``fallback`` mantiene el plan vigente (y aplica
CONFIG_SEGURA tras N timeouts consecutivos); ``fail_fast`` aborta la corrida
con código ≠ 0 (campañas de métricas).
"""
from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from nsb.config import GatewayConfig
from nsb.domain.contracts import DecisionEnvelope
from nsb.domain.enums import Mode, TimeoutPolicy, Verdict, WireType
from nsb.domain.wire import WireDecodeError, WireEnvelope
from nsb.hil.protocol import ChannelClosed, LineChannel
from nsb.hil.sumo_bridge import SumoBridge, digest_escenario
from nsb.sources.replay import ReplayWriter
from nsb.tsc.emulator import PLAN_SEGURO

logger = logging.getLogger(__name__)


class GatewayAbort(RuntimeError):
    """Corrida abortada (fail-fast o error de protocolo irrecuperable)."""


@dataclass
class GatewaySummary:
    experiment_id: str = ""
    puntos_control: int = 0
    decisiones_aplicadas: int = 0
    timeouts: int = 0
    reconexiones: int = 0
    rechazos: int = 0
    stale_descartados: int = 0
    verdicts: Dict[str, int] = field(default_factory=dict)
    record_path: Optional[str] = None


class HilGateway:
    """Servidor TCP + lazo de control step-synchronous."""

    def __init__(self, cfg: GatewayConfig):
        self._cfg = cfg
        digest = digest_escenario(cfg)
        self._experiment_id = (
            cfg.experiment_id
            or f"hil-s{cfg.seed}-{digest[:8]}")
        self._digest = digest
        self._bridge = SumoBridge(cfg)
        self._listen: Optional[socket.socket] = None
        self._channel: Optional[LineChannel] = None
        self._node_id: str = "?"
        self._summary = GatewaySummary(experiment_id=self._experiment_id)

    # ------------------------------------------------------------------ #
    def run(self) -> GatewaySummary:
        cfg = self._cfg
        writer = ReplayWriter(cfg.record_jsonl) if cfg.record_jsonl else None
        self._listen = socket.create_server(
            (cfg.bind_host, cfg.bind_port), reuse_port=False)
        self._listen.settimeout(cfg.max_wait_reconnect_s)
        logger.info("gateway escuchando en %s:%s (experiment=%s)",
                    cfg.bind_host, cfg.bind_port, self._experiment_id)
        try:
            self._esperar_nodo()
            self._bridge.start()
            self._lazo(writer)
            self._despedir()
        finally:
            if writer is not None:
                self._summary.record_path = str(writer._path)
                writer.close()
            self._cerrar()
        return self._summary

    # ------------------------------------------------------------------ #
    def _esperar_nodo(self) -> None:
        """Accept + handshake (inicio y reconexiones)."""
        assert self._listen is not None
        try:
            sock, addr = self._listen.accept()
        except socket.timeout:
            raise GatewayAbort(
                f"ningún nodo se conectó en {self._cfg.max_wait_reconnect_s}s")
        self._channel = LineChannel(sock)
        hello = self._channel.recv(timeout_s=10.0)
        if hello.type is not WireType.HELLO:
            raise GatewayAbort(f"se esperaba hello, llegó {hello.type}")
        self._node_id = str(hello.payload.get("node_id", "?"))
        self._channel.send(WireEnvelope(
            type=WireType.HELLO_ACK,
            experiment_id=self._experiment_id,
            payload={
                "control_interval_s": self._cfg.control_interval_s,
                "seed": self._cfg.seed,
                "scenario_digest": self._digest,
                "next_seq": self._summary.puntos_control,
            }))
        logger.info("nodo conectado: %s desde %s", self._node_id, addr)

    def _reconectar(self) -> bool:
        """Espera reconexión tras caída. True si hay canal nuevo."""
        if self._channel is not None:
            self._channel.close()
            self._channel = None
        logger.warning("conexión perdida; esperando reconexión (max %.0fs)",
                       self._cfg.max_wait_reconnect_s)
        try:
            self._esperar_nodo()
        except GatewayAbort:
            return False
        self._summary.reconexiones += 1
        return True

    # ------------------------------------------------------------------ #
    def _lazo(self, writer: Optional[ReplayWriter]) -> None:
        cfg = self._cfg
        pasos_por_punto = max(1, int(round(cfg.control_interval_s)))
        timeouts_consecutivos = 0

        for k in range(cfg.max_control_points):
            if cfg.tick_mode == "per_step":
                for _ in range(pasos_por_punto):
                    sim_time = self._bridge.avanzar(1)
                    self._enviar_tick(sim_time)
            else:
                self._bridge.avanzar(pasos_por_punto)
            state = self._bridge.extraer_estado(
                self._experiment_id, seq=k,
                intersection_id=cfg.phase_map.tls_id)
            if writer is not None:
                writer.write_state(state)

            decision = self._intercambiar(state)
            self._summary.puntos_control += 1

            if decision is None:                       # timeout definitivo
                self._summary.timeouts += 1
                timeouts_consecutivos += 1
                if cfg.timeout_policy is TimeoutPolicy.FAIL_FAST:
                    raise GatewayAbort(
                        f"timeout del nodo en seq={k} (política fail-fast)")
                if timeouts_consecutivos >= cfg.max_consecutive_timeouts:
                    logger.warning(
                        "%d timeouts consecutivos: aplicando CONFIG_SEGURA "
                        "a SUMO", timeouts_consecutivos)
                    self._bridge.aplicar_plan(PLAN_SEGURO)
                continue

            timeouts_consecutivos = 0
            v = decision.verdict.value
            self._summary.verdicts[v] = self._summary.verdicts.get(v, 0) + 1
            if writer is not None:
                writer.write_decision(decision)

            if decision.verdict in (Verdict.ACCEPT, Verdict.CLAMP) \
                    and decision.plan_aplicado is not None \
                    and decision.mode is not Mode.ADVISORY:
                self._bridge.aplicar_plan(decision.plan_aplicado)
                self._summary.decisiones_aplicadas += 1
            elif decision.verdict is Verdict.REJECT:
                self._summary.rechazos += 1
                if decision.safe_mode:
                    self._bridge.aplicar_plan(PLAN_SEGURO)

    def _intercambiar(self, state) -> Optional[DecisionEnvelope]:
        """Envía un state y espera SU decisión (mismo seq) hasta el deadline.
        Devuelve None en timeout; absorbe duplicados/stale; reconecta si el
        canal cae (el seq en vuelo se da por perdido → None)."""
        assert self._channel is not None
        env = WireEnvelope(
            type=WireType.STATE, experiment_id=self._experiment_id,
            seq=state.seq, payload=state.model_dump(mode="json"))
        try:
            self._channel.send(env)
        except ChannelClosed:
            return None if not self._reconectar() else None

        deadline = time.monotonic() + self._cfg.node_timeout_s
        while True:
            restante = deadline - time.monotonic()
            if restante <= 0:
                logger.warning("timeout esperando decision de seq=%s", state.seq)
                return None
            try:
                resp = self._channel.recv(timeout_s=restante)
            except socket.timeout:
                logger.warning("timeout esperando decision de seq=%s", state.seq)
                return None
            except ChannelClosed:
                self._reconectar()
                return None
            except WireDecodeError as e:
                logger.error("mensaje malformado del nodo: %s", e)
                self._enviar_error(f"malformed:{e}")
                continue

            if resp.type is WireType.HEARTBEAT:
                try:
                    self._channel.send(WireEnvelope(type=WireType.HEARTBEAT_ACK))
                except ChannelClosed:
                    self._reconectar()
                    return None
                continue
            if resp.type is not WireType.DECISION:
                logger.warning("tipo inesperado %s; descartado", resp.type)
                continue

            try:
                decision = DecisionEnvelope.model_validate(resp.payload)
            except Exception as e:
                logger.error("DecisionEnvelope inválido: %s", e)
                self._enviar_error(f"bad_decision:{e}")
                continue

            if (resp.experiment_id != self._experiment_id
                    or resp.seq != decision.seq
                    or decision.experiment_id != self._experiment_id):
                self._enviar_error("protocol_violation:envelope_inconsistente")
                raise GatewayAbort(
                    "DecisionEnvelope inconsistente con su envelope HIL")

            if decision.seq == state.seq:
                return decision
            if decision.seq < state.seq:
                # decisión tardía de un seq ya vencido: descartar y seguir
                self._summary.stale_descartados += 1
                logger.warning("decision tardía seq=%s descartada "
                               "(esperando %s)", decision.seq, state.seq)
                continue
            # seq futuro: violación de protocolo
            self._enviar_error(
                f"protocol_violation:seq_futuro:{decision.seq}")
            raise GatewayAbort(
                f"el nodo respondió seq futuro {decision.seq} "
                f"(esperado {state.seq})")

    # ------------------------------------------------------------------ #
    def _enviar_tick(self, sim_time_s: float) -> None:
        """Envía un tick de espejo; una caída se reconecta para el próximo."""
        if self._channel is None:
            return
        try:
            self._channel.send(WireEnvelope(
                type=WireType.TICK,
                experiment_id=self._experiment_id,
                payload={"sim_time_s": sim_time_s},
            ))
        except ChannelClosed:
            self._reconectar()

    def _enviar_error(self, motivo: str) -> None:
        try:
            if self._channel is not None:
                self._channel.send(WireEnvelope(
                    type=WireType.ERROR, payload={"reason": motivo}))
        except ChannelClosed:
            pass

    def _despedir(self) -> None:
        try:
            if self._channel is not None:
                self._channel.send(WireEnvelope(
                    type=WireType.BYE,
                    payload={
                        "puntos_control": self._summary.puntos_control,
                        "timeouts": self._summary.timeouts,
                        "verdicts": self._summary.verdicts,
                    }))
        except ChannelClosed:
            pass

    def _cerrar(self) -> None:
        if self._channel is not None:
            self._channel.close()
        if self._listen is not None:
            self._listen.close()
        self._bridge.close()
