"""Benchmark reproducible (spec §31): latencias reales del núcleo de
decisión sobre el corpus golden versionado + métricas de sistema.

Los resultados se etiquetan con la plataforma REAL donde corrieron
(Windows/Pi): jamás se extrapolan (spec §4, D-11).
"""
from __future__ import annotations

import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from nsb import __version__
from nsb.core.adapters import AdaptadorDifuso, AdaptadorICV
from nsb.core.pipeline import DecisionPipeline
from nsb.domain.contracts import ApproachState
from nsb.domain.enums import Mode
from nsb.sources.manual import ManualTestStateSource
from nsb.telemetry.system_metrics import percentiles, snapshot


def _cargar_corpus_state(corpus_path: Path) -> list:
    casos = []
    with open(corpus_path, encoding="utf-8") as f:
        for linea in f:
            reg = json.loads(linea)
            if reg["kind"] == "state":
                casos.append(reg["in"])
    return casos


def run_bench(corpus_path: str, out_path: str, repeticiones: int = 5) -> dict:
    corpus = Path(corpus_path)
    if not corpus.exists():
        raise FileNotFoundError(
            f"corpus no encontrado: {corpus} "
            f"(generar con tests/golden/generar_corpus.py)")

    icv = AdaptadorICV()
    difuso = AdaptadorDifuso()
    pipeline = DecisionPipeline(icv, difuso, Mode.ADVISORY)

    casos = _cargar_corpus_state(corpus)
    estados = list(ManualTestStateSource("congestion_ns", pasos=100))

    # --- latencia ICV+PI (por acceso) ---
    lat_icv = []
    for _ in range(repeticiones):
        for caso in casos:
            a = ApproachState(**caso)
            t0 = time.perf_counter()
            icv.indicadores(a)
            lat_icv.append((time.perf_counter() - t0) * 1000.0)

    # --- latencia inferencia difusa (una dirección) ---
    lat_difuso = []
    for _ in range(repeticiones):
        for i in range(0, len(casos), 4):
            t0 = time.perf_counter()
            difuso.controlador.calcular_ajuste_verde(0.5, 0.5, 0.0)
            lat_difuso.append((time.perf_counter() - t0) * 1000.0)

    # --- latencia pipeline completo (TrafficState → Recommendation) ---
    lat_pipeline = []
    for _ in range(repeticiones):
        for st in estados:
            t0 = time.perf_counter()
            pipeline.recommend(st)
            lat_pipeline.append((time.perf_counter() - t0) * 1000.0)

    sistema = snapshot()
    resultado = {
        "bench": "nsb-core-latency",
        "version_nsb": __version__,
        "ejecutado_en": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "plataforma": {
            "sistema": platform.system(),
            "maquina": platform.machine(),
            "procesador": platform.processor(),
            "python": sys.version.split()[0],
            "nota": ("MEDIDO en esta plataforma; NO extrapolable a otra "
                     "(Pi 4B se mide en la Pi 4B)"),
        },
        "sistema": sistema.model_dump(),
        "latencias_ms": {
            "icv_pi_por_acceso": percentiles(lat_icv),
            "inferencia_difusa": percentiles(lat_difuso),
            "pipeline_completo": percentiles(lat_pipeline),
        },
    }

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(resultado, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    return resultado
