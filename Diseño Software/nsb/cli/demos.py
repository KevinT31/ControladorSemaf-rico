"""Demos reproducibles de la spec §43 ejecutables sin hardware.

Cada demo imprime su procedimiento, el resultado observado y el estado
honesto (VERIFIED aquí = ejecutada con éxito en ESTA máquina).

Demos que requieren hardware físico (4: LEDs TSC, 5-físico: LEDs direct-lab)
se documentan en docs/nsb_v2_1/experiments.md con su estado
REQUIRES HARDWARE / NOT RUN. La demo 8 (pérdida MQTT) corre SIN broker a
propósito: demuestra que el control no depende de la telemetría.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from nsb.config import NodeConfig
from nsb.domain.enums import Mode, SourceKind, Verdict
from nsb.faults.injectors import SabotagePipeline
from nsb.faults.plan import FaultPlan
from nsb.node import NsbNode
from nsb.sources.manual import ManualTestStateSource
from nsb.sources.replay import ReplayStateSource, ReplayWriter, digest_decisiones


def _node(mode: Mode, tmp: Path, exp: str) -> NsbNode:
    cfg = NodeConfig(mode=mode, source=SourceKind.MANUAL,
                     telemetry={"jsonl_dir": str(tmp / "telemetria")})
    return NsbNode.from_config(cfg, experiment_id=exp)


def demo_1(tmp: Path) -> bool:
    """ADVISORY + Replay: grabar una fuente y re-decidir en shadow mode."""
    print("DEMO 1 — ADVISORY + Replay")
    grabacion = tmp / "demo1.jsonl"
    w = ReplayWriter(grabacion)
    for st in ManualTestStateSource("congestion_ns", pasos=20,
                                    experiment_id="demo1"):
        w.write_state(st)
    w.close()
    node = _node(Mode.ADVISORY, tmp, "demo1")
    summary = node.run(ReplayStateSource(grabacion))
    node.shutdown()
    ok = (summary.estados == 20 and summary.verdicts.get("accept") == 20
          and summary.violaciones_gate == 0)
    print(f"  20 estados replayed, veredictos={summary.verdicts}, "
          f"sin actuación (advisory) -> {'OK' if ok else 'FALLO'}")
    return ok


def demo_2(tmp: Path) -> bool:
    """TSC_EMULATED + SimulatedActuator."""
    print("DEMO 2 — TSC_EMULATED + SimulatedActuator")
    node = _node(Mode.TSC_EMULATED, tmp, "demo2")
    summary = node.run(ManualTestStateSource("uniforme", pasos=20,
                                             experiment_id="demo2"))
    applies = node.authority._actuator.applies
    node.shutdown()
    ok = summary.estados == 20 and applies == 20 and \
        summary.violaciones_gate == 0
    print(f"  20 estados, {applies} actuaciones simuladas, "
          f"0 violaciones -> {'OK' if ok else 'FALLO'}")
    return ok


def demo_5(tmp: Path) -> bool:
    """AUTOMATED_DIRECT_LAB con actuador simulado (triple compuerta)."""
    import os
    print("DEMO 5 — AUTOMATED_DIRECT_LAB (simulado; LEDs = requiere Pi)")
    cfg = NodeConfig(mode=Mode.AUTOMATED_DIRECT_LAB, allow_direct_lab=True,
                     source=SourceKind.MANUAL,
                     telemetry={"jsonl_dir": str(tmp / "t5")})
    os.environ["NSB_CONFIRM_DIRECT_LAB"] = cfg.node_id
    try:
        node = NsbNode.from_config(cfg, cli_mode=Mode.AUTOMATED_DIRECT_LAB,
                                   experiment_id="demo5")
    finally:
        del os.environ["NSB_CONFIRM_DIRECT_LAB"]
    summary = node.run(ManualTestStateSource("congestion_eo", pasos=15,
                                             experiment_id="demo5"))
    node.shutdown()
    ok = (node.mode is Mode.AUTOMATED_DIRECT_LAB and summary.estados == 15
          and summary.violaciones_gate == 0)
    print(f"  triple compuerta verificada, {summary.estados} estados, "
          f"0 violaciones -> {'OK' if ok else 'FALLO'}")
    return ok


def demo_6(tmp: Path) -> bool:
    """Verde solicitado de 200 s → CLAMP a 120 s con corrección trazable."""
    print("DEMO 6 — verde 200 s → CLAMP")
    node = _node(Mode.TSC_EMULATED, tmp, "demo6")
    node.authority._pipeline = SabotagePipeline(
        node.authority._pipeline, FaultPlan({3: ["verde_200"]}))
    clamps = []
    for st in ManualTestStateSource("uniforme", pasos=6,
                                    experiment_id="demo6"):
        _, d = node.process_one(st)
        if d.verdict is Verdict.CLAMP:
            clamps.append(d)
    node.shutdown()
    ok = (len(clamps) == 1 and clamps[0].plan_aplicado.t_verde_ns == 120.0)
    if ok:
        c = clamps[0].corrections[0]
        print(f"  solicitado={c['solicitado']}s aplicado={c['aplicado']}s "
              f"motivo={c['motivo']!r} -> OK")
    else:
        print("  FALLO: no se observó el CLAMP esperado")
    return ok


def demo_7(tmp: Path) -> bool:
    """Doble verde conflictivo → SafetyGate fuerza todo-rojo."""
    from nsb.domain.enums import SignalColor, SignalGroup
    from nsb.safety.gate import TODO_ROJO
    print("DEMO 7 — verdes conflictivos → SafetyGate")
    node = _node(Mode.TSC_EMULATED, tmp, "demo7")
    _, d = node.process_one(next(iter(
        ManualTestStateSource("uniforme", pasos=1, experiment_id="demo7"))))
    conflicto = {SignalGroup.NORTE: SignalColor.VERDE,
                 SignalGroup.SUR: SignalColor.VERDE,
                 SignalGroup.ESTE: SignalColor.VERDE,
                 SignalGroup.OESTE: SignalColor.VERDE}
    d_corrupta = d.model_copy(update={
        "applied_phase": d.applied_phase.model_copy(
            update={"signal_groups": conflicto})})
    resultado = node.authority._actuar(d_corrupta)
    estado_fisico = node.authority._actuator.state()
    node.shutdown()
    ok = (resultado.safe_mode and estado_fisico == TODO_ROJO
          and node.authority.gate.violaciones_totales == 1)
    print(f"  inyectados 4 verdes -> gate bloqueó y aplicó TODO-ROJO "
          f"-> {'OK' if ok else 'FALLO'}")
    return ok


def demo_8(tmp: Path) -> bool:
    """Pérdida MQTT → el control NO se ve afectado (fail-safe §26-A)."""
    print("DEMO 8 — pérdida MQTT (broker inaccesible; el control continúa)")
    cfg = NodeConfig(mode=Mode.TSC_EMULATED, source=SourceKind.MANUAL,
                     telemetry={"jsonl_dir": str(tmp / "telemetria"),
                                "mqtt_enabled": True, "mqtt_tls": False,
                                "mqtt_host": "127.0.0.1",
                                "mqtt_port": 18830})  # puerto muerto a propósito
    node = NsbNode.from_config(cfg, experiment_id="demo8")
    summary = node.run(ManualTestStateSource("uniforme", pasos=10,
                                             experiment_id="demo8"))
    conectado = node.mqtt_sink.connected
    dropped = node.mqtt_sink.dropped
    node.shutdown()
    ok = (summary.estados == 10 and not conectado and dropped > 0
          and summary.verdicts.get("reject", 0) == 0
          and summary.violaciones_gate == 0
          and not summary.safe_mode_final)
    print(f"  broker caido: conectado={conectado}, descartados={dropped}, "
          f"veredictos={summary.verdicts} -> {'OK' if ok else 'FALLO'}")
    print("  (entrega real con broker TLS verificada en "
          "tests/integration/test_mqtt_local.py)")
    return ok


def demo_9(tmp: Path) -> bool:
    """Pérdida de fuente (silencio) → CONFIG_SEGURA (fail-safe §26-G)."""
    print("DEMO 9 — silencio del edge → plan seguro")
    from nsb.faults.injectors import CorruptingSource
    node = _node(Mode.TSC_EMULATED, tmp, "demo9")
    # Estados 5..9 corruptos (NaN) = 5 ciclos sin recomendación válida
    plan = FaultPlan({k: ["nan_queue"] for k in range(5, 10)})
    fuente = CorruptingSource(
        ManualTestStateSource("uniforme", pasos=10, experiment_id="demo9"),
        plan)
    summary = node.run(fuente)
    node.shutdown()
    ok = summary.safe_mode_final and summary.verdicts.get("reject", 0) >= 3
    print(f"  5 ciclos corruptos -> safe_mode={summary.safe_mode_final}, "
          f"veredictos={summary.verdicts} -> {'OK' if ok else 'FALLO'}")
    return ok


def demo_10(tmp: Path) -> bool:
    """EV en fase incompatible → ámbar → todo-rojo → verde compatible."""
    print("DEMO 10 — EV en fase incompatible (secuencia segura)")
    from nsb.domain.enums import PhaseId
    from nsb.tsc.fsm import secuencia_es_segura
    node = _node(Mode.TSC_EMULATED, tmp, "demo10")
    transiciones = [node.authority.tsc.fsm.fase]
    node.authority.tsc.fsm._on_transition = \
        lambda a, b: transiciones.append(b)
    summary = node.run(ManualTestStateSource("emergencia_eo", pasos=25,
                                             experiment_id="demo10"))
    node.shutdown()
    ok = (PhaseId.EO_VERDE in transiciones
          and secuencia_es_segura(transiciones)
          and summary.violaciones_gate == 0)
    print(f"  transiciones={[t.value for t in transiciones[:8]]}... "
          f"secuencia segura={secuencia_es_segura(transiciones)} "
          f"-> {'OK' if ok else 'FALLO'}")
    return ok


def demo_12(tmp: Path) -> bool:
    """Replay determinista: dos corridas ⇒ digests idénticos."""
    print("DEMO 12 — replay determinista")
    digests = []
    for i in (1, 2):
        node = _node(Mode.TSC_EMULATED, tmp, f"demo12-{i}")
        w = ReplayWriter(tmp / f"demo12_{i}.jsonl")
        node.run(ManualTestStateSource("congestion_ns", pasos=25,
                                       experiment_id="demo12"),
                 writer=w)
        node.shutdown()
        digests.append(digest_decisiones(tmp / f"demo12_{i}.jsonl"))
    ok = digests[0] == digests[1]
    print(f"  digest corrida 1 == corrida 2: {ok} ({digests[0][:16]}…)")
    return ok


DEMOS = {1: demo_1, 2: demo_2, 5: demo_5, 6: demo_6, 7: demo_7,
         8: demo_8, 9: demo_9, 10: demo_10, 12: demo_12}


def run_demo(numero: int) -> int:
    if numero not in DEMOS:
        disponibles = sorted(DEMOS)
        print(f"demo {numero} no ejecutable localmente; disponibles: "
              f"{disponibles}. Las demos 3 (HIL SUMO) usan 'nsb gateway'+"
              f"'nsb run --source hil'; 4/5-físico requieren Raspberry Pi; "
              f"11 requiere video (F4).")
        return 1
    with tempfile.TemporaryDirectory(prefix="nsb-demo-") as tmp:
        ok = DEMOS[numero](Path(tmp))
    print(f"DEMO {numero}: {'VERIFIED' if ok else 'FAILED'}")
    return 0 if ok else 2
