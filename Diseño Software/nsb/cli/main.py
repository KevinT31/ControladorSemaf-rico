"""CLI de NSB v2.1.

Subcomandos F1: run (nodo), record (grabar fuente manual a JSONL),
digest (digest determinista de decisiones de una corrida).
F2 añade: gateway, bench, demo.

Códigos de salida: 0 = éxito; 1 = error de configuración/uso; 2 = fallo de
ejecución. Nunca se ocultan errores (spec §38).
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import nsb._bootstrap  # noqa: F401

from nsb import __version__
from nsb.domain.enums import Mode, SourceKind

logger = logging.getLogger("nsb.cli")

# CLI usa guiones; los enums usan guion bajo
_MODOS_CLI = {
    "advisory": Mode.ADVISORY,
    "tsc-emulated": Mode.TSC_EMULATED,
    "automated-direct-lab": Mode.AUTOMATED_DIRECT_LAB,
}


def _configurar_logging(nivel: str) -> None:
    """Handlers UTF-8: los logs del núcleo usan emojis (⛔🛟) que revientan
    en consolas Windows cp1252 si no se fuerza el encoding."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")
            except (ValueError, OSError):
                pass
    logging.basicConfig(
        level=getattr(logging, nivel.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nsb", description="NSB v2.1 — Nodo Semafórico de Borde")
    p.add_argument("--version", action="version",
                   version=f"nsb {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="ejecutar el nodo con una fuente")
    run.add_argument("--config", default="config/nsb/node.yaml",
                     help="ruta a node.yaml")
    run.add_argument("--mode", choices=sorted(_MODOS_CLI),
                     help="override del modo (direct-lab exige triple compuerta)")
    run.add_argument("--source", choices=["manual", "replay"],
                     help="override de la fuente (hil/video en fases F2/F4)")
    run.add_argument("--input", help="JSONL de entrada (source=replay)")
    run.add_argument("--escenario", default="uniforme",
                     help="escenario de la fuente manual")
    run.add_argument("--pasos", type=int, default=40,
                     help="puntos de control de la fuente manual")
    run.add_argument("--record", help="grabar states+decisiones a este JSONL")
    run.add_argument("--render", action="store_true",
                     help="render de consola del actuador simulado")
    run.add_argument("--experiment-id", default=None)

    rec = sub.add_parser("record",
                         help="grabar una fuente manual a JSONL (sin decidir)")
    rec.add_argument("--escenario", default="uniforme")
    rec.add_argument("--pasos", type=int, default=40)
    rec.add_argument("--out", required=True, help="ruta JSONL de salida")
    rec.add_argument("--experiment-id", default="manual-record")
    rec.add_argument("--intervalo", type=float, default=25.0)

    dig = sub.add_parser("digest",
                         help="digest SHA-256 determinista de las decisiones "
                              "de una corrida grabada")
    dig.add_argument("jsonl", help="archivo JSONL grabado con --record")

    return p


# ---------------------------------------------------------------------- #
def _cmd_record(args) -> int:
    from nsb.sources.manual import ManualTestStateSource
    from nsb.sources.replay import ReplayWriter

    fuente = ManualTestStateSource(
        escenario=args.escenario, pasos=args.pasos,
        experiment_id=args.experiment_id,
        control_interval_s=args.intervalo)
    writer = ReplayWriter(args.out)
    n = 0
    try:
        for st in fuente:
            writer.write_state(st)
            n += 1
    finally:
        writer.close()
    print(f"grabados {n} TrafficState -> {args.out}")
    return 0


def _cmd_digest(args) -> int:
    from nsb.sources.replay import digest_decisiones

    if not Path(args.jsonl).exists():
        print(f"ERROR: no existe {args.jsonl}", file=sys.stderr)
        return 1
    print(digest_decisiones(args.jsonl))
    return 0


def _cmd_run(args) -> int:
    from nsb.config import load_node_config
    from nsb.node import NsbNode
    from nsb.sources.manual import ManualTestStateSource
    from nsb.sources.replay import ReplayStateSource, ReplayWriter

    try:
        cfg = load_node_config(args.config)
    except (OSError, ValueError) as e:
        print(f"ERROR de configuración: {e}", file=sys.stderr)
        return 1

    cli_mode: Optional[Mode] = _MODOS_CLI[args.mode] if args.mode else None
    source_kind = SourceKind(args.source) if args.source else cfg.source

    if source_kind is SourceKind.REPLAY:
        if not args.input:
            print("ERROR: source=replay requiere --input", file=sys.stderr)
            return 1
        fuente = ReplayStateSource(args.input)
        exp_id = f"replay-{Path(args.input).stem}"
    elif source_kind is SourceKind.MANUAL:
        exp_id = args.experiment_id or "manual-run"
        fuente = ManualTestStateSource(
            escenario=args.escenario, pasos=args.pasos,
            experiment_id=exp_id,
            control_interval_s=cfg.control_interval_s)
    else:
        print(f"ERROR: fuente {source_kind.value} disponible en fases "
              f"posteriores (F2: sumo_hil, F4: video)", file=sys.stderr)
        return 1

    try:
        node = NsbNode.from_config(
            cfg, cli_mode=cli_mode,
            experiment_id=args.experiment_id or exp_id,
            render_override=True if args.render else None)
    except PermissionError as e:
        print(f"DENEGADO: {e}", file=sys.stderr)
        return 1

    writer = ReplayWriter(args.record) if args.record else None
    try:
        summary = node.run(fuente, writer=writer)
    except Exception as e:
        logger.exception("fallo de ejecución")
        print(f"ERROR de ejecución: {e}", file=sys.stderr)
        return 2
    finally:
        node.shutdown()

    print(f"modo             : {node.mode.value}")
    print(f"estados          : {summary.estados}")
    print(f"veredictos       : {summary.verdicts}")
    print(f"rechazos guard   : {summary.rechazos_guard}")
    print(f"violaciones gate : {summary.violaciones_gate}")
    print(f"safe_mode final  : {summary.safe_mode_final}")
    if summary.record_path:
        from nsb.sources.replay import digest_decisiones
        print(f"grabado          : {summary.record_path}")
        print(f"digest decisiones: {digest_decisiones(summary.record_path)}")
    if summary.events_path:
        print(f"eventos          : {summary.events_path}")
    return 0


def main(argv: Optional[list] = None) -> int:
    args = _parser().parse_args(argv)
    _configurar_logging(getattr(args, "log_level", "INFO"))
    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "record":
        return _cmd_record(args)
    if args.cmd == "digest":
        return _cmd_digest(args)
    return 1
