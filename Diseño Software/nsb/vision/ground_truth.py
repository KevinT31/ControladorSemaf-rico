"""Ground truth de visión (spec §17): muestrear, anotar a mano, evaluar.

PROHIBIDO usar SUMO como ground truth de video real (spec §15): el ground
truth proviene de anotación HUMANA sobre frames muestreados.

Flujo:
1. ``nsb gt-sample`` — extrae frames cada N segundos + ``manifest.csv``
   con columnas ``count_ns`` / ``count_eo`` VACÍAS para llenar a mano.
2. Correr la fuente de video con ``--record`` (graba TrafficState).
3. ``nsb gt-eval`` — compara conteos anotados vs. estados grabados por
   cercanía temporal y reporta MAE/RMSE/error por intervalo (spec §17:
   métricas de conteo; mAP de detección exigiría cajas anotadas y queda
   explícitamente fuera hasta que existan).

No se generan cifras sin ejecutar (spec §17): sin anotaciones, gt-eval
falla con mensaje claro en lugar de inventar métricas.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MANIFEST = "manifest.csv"
CAMPOS = ("frame_idx", "t_s", "archivo", "count_ns", "count_eo", "notas")


def sample_frames(video_path: str | Path, out_dir: str | Path,
                  every_s: float = 5.0,
                  max_frames: Optional[int] = None) -> Path:
    """Extrae frames PNG cada ``every_s`` segundos + manifest para anotar.

    Solo requiere OpenCV (import perezoso). Devuelve la ruta del manifest.
    """
    try:
        import cv2
    except ImportError as e:
        raise RuntimeError(f"gt-sample requiere opencv instalado: {e}") from e

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"video no encontrado: {video_path}")
    if every_s <= 0:
        raise ValueError("every_s debe ser > 0")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    paso = max(1, round(fps * every_s))

    filas: List[Dict[str, str]] = []
    n = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if n % paso == 0:
                t_s = n / fps
                nombre = f"frame_{n:07d}.png"
                # imencode+tofile y no imwrite: imwrite falla silenciosamente
                # con rutas no-ASCII en Windows (p. ej. "Diseño Software")
                ok, buf = cv2.imencode(".png", frame)
                if not ok:
                    raise OSError(f"no se pudo codificar {nombre}")
                buf.tofile(str(out / nombre))
                filas.append({"frame_idx": str(n), "t_s": f"{t_s:.3f}",
                              "archivo": nombre,
                              "count_ns": "", "count_eo": "", "notas": ""})
                if max_frames is not None and len(filas) >= max_frames:
                    break
            n += 1
    finally:
        cap.release()

    if not filas:
        raise ValueError(f"el video no produjo frames: {video_path}")

    manifest = out / MANIFEST
    with open(manifest, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)
    return manifest


# ---------------------------------------------------------------------- #
def _cargar_anotaciones(manifest: str | Path) -> List[Tuple[float, int, int]]:
    """Lee (t_s, count_ns, count_eo) de las filas ANOTADAS del manifest."""
    filas = []
    with open(manifest, encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            ns, eo = fila.get("count_ns", ""), fila.get("count_eo", "")
            if ns.strip() == "" or eo.strip() == "":
                continue                     # sin anotar: se omite, no se inventa
            filas.append((float(fila["t_s"]), int(ns), int(eo)))
    return filas


def _cargar_estados(states_jsonl: str | Path) -> List[Tuple[float, int, int]]:
    """Lee (sim_time_s, num_vehicles ns, eo) de un JSONL grabado con --record."""
    estados = []
    with open(states_jsonl, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            d = json.loads(linea)
            if d.get("kind") != "state":
                continue
            data = d.get("data", d)
            t = data.get("sim_time_s")
            aps = data.get("approaches", {})
            if t is None or "NS" not in aps or "EO" not in aps:
                continue
            estados.append((float(t), int(aps["NS"]["num_vehicles"]),
                            int(aps["EO"]["num_vehicles"])))
    return estados


def evaluar_conteos(manifest: str | Path, states_jsonl: str | Path,
                    tol_s: float = 12.5) -> Dict:
    """Métricas de conteo (spec §17): MAE, RMSE y error por intervalo.

    Cada anotación se empareja con el estado más cercano en tiempo de video
    (|Δt| <= tol_s, default = medio intervalo canónico). Sin pares no hay
    métricas: se lanza error en lugar de reportar tablas vacías.
    """
    anotaciones = _cargar_anotaciones(manifest)
    if not anotaciones:
        raise ValueError(
            f"{manifest}: ninguna fila tiene count_ns/count_eo anotados; "
            "anote a mano antes de evaluar (spec §17)")
    estados = _cargar_estados(states_jsonl)
    if not estados:
        raise ValueError(f"{states_jsonl}: sin estados 'state' con approaches")

    pares = []               # (t_anno, err_ns, err_eo)
    for t, ns_gt, eo_gt in anotaciones:
        cercano = min(estados, key=lambda e: abs(e[0] - t))
        if abs(cercano[0] - t) > tol_s:
            continue
        pares.append((t, cercano[1] - ns_gt, cercano[2] - eo_gt))
    if not pares:
        raise ValueError(
            f"ninguna anotación empareja con estados dentro de ±{tol_s}s")

    def _mae(errs):
        return sum(abs(e) for e in errs) / len(errs)

    def _rmse(errs):
        return math.sqrt(sum(e * e for e in errs) / len(errs))

    errs_ns = [e for _, e, _ in pares]
    errs_eo = [e for _, _, e in pares]
    return {
        "n_anotaciones": len(anotaciones),
        "n_emparejadas": len(pares),
        "tol_s": tol_s,
        "ns": {"mae": _mae(errs_ns), "rmse": _rmse(errs_ns)},
        "eo": {"mae": _mae(errs_eo), "rmse": _rmse(errs_eo)},
        "por_intervalo": [
            {"t_s": t, "err_ns": ens, "err_eo": eeo}
            for t, ens, eeo in pares
        ],
    }
