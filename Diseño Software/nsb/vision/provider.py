"""Proveedor de métricas por frame para la fuente de video (spec §15).

Reutiliza ``vision_computadora.procesador_video.ProcesadorVideo`` (YOLO +
ByteTrack/DeepSORT + colas reales) SIN modificarlo: un único decodificado
del video alimenta dos instancias, una por ROI (NS y EO), cada una con su
propio tracker. El costo es cargar el modelo YOLO dos veces (aceptable para
procesamiento offline ADVISORY; documentado en limitations).

cv2 / ultralytics / ProcesadorVideo se importan PEREZOSAMENTE: importar este
módulo jamás falla en plataformas sin visión (mismo patrón que GPIO, §23).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Tuple

logger = logging.getLogger(__name__)

Roi = Tuple[int, int, int, int]          # (x, y, w, h) en píxeles


@dataclass(frozen=True)
class FrameMetrics:
    """Métricas crudas de UN frame en UNA ROI (sin ICV: eso lo hace el nodo)."""
    t_s: float                    # tiempo de video (frame / fps)
    num_vehicles: int
    stopped_vehicles: int
    queue_m: float
    speed_kmh: float
    flow_veh_min: float
    ev_confidence: float          # 0.0 = sin emergencia detectada


def _ev_confidence(detecciones) -> float:
    """Confianza máxima de las detecciones de emergencia, acotada a [0,1]."""
    mejor = 0.0
    for d in detecciones or ():
        c = getattr(d, "confianza", getattr(d, "confidence", 1.0))
        try:
            mejor = max(mejor, float(c))
        except (TypeError, ValueError):
            mejor = max(mejor, 1.0)
    return min(1.0, mejor)


def _finito(x, nombre: str) -> float:
    """Sanea NaN/inf del pipeline de visión → 0.0 con warning.

    Un frame degenerado no debe tumbar toda la corrida: los contratos NSB
    rechazan no-finitos (D-G) y aquí la política es descartar el valor,
    no el video completo (hallazgo del red team F3/F4)."""
    v = float(x)
    if not math.isfinite(v) or v < 0.0:
        logger.warning("visión produjo %s=%r; se registra 0.0", nombre, x)
        return 0.0
    return v


def _a_metrics(resultado, t_s: float) -> FrameMetrics:
    """ResultadoFrame (pipeline existente) → FrameMetrics NSB."""
    return FrameMetrics(
        t_s=t_s,
        num_vehicles=int(resultado.num_vehiculos),
        stopped_vehicles=int(resultado.cola_vehiculos_count),
        queue_m=_finito(resultado.longitud_cola, "queue_m"),
        speed_kmh=_finito(resultado.velocidad_promedio, "speed_kmh"),
        flow_veh_min=_finito(resultado.flujo_vehicular, "flow_veh_min"),
        ev_confidence=(_ev_confidence(resultado.detecciones_emergencia)
                       if resultado.hay_emergencia else 0.0),
    )


class DualRoiVideoProvider:
    """Itera el video UNA vez y produce pares (metrics_ns, metrics_eo)."""

    def __init__(self, video_path: str | Path, roi_ns: Roi, roi_eo: Roi,
                 stride: int = 15, modelo_yolo: str = "yolov8n.pt",
                 px_per_m: Optional[float] = None):
        try:
            import cv2  # import perezoso
            from vision_computadora.procesador_video import ProcesadorVideo
        except ImportError as e:
            raise RuntimeError(
                "la fuente de video requiere opencv+ultralytics instalados "
                f"(pip install -r requirements.txt): {e}") from e

        self._path = Path(video_path)
        if not self._path.exists():
            raise FileNotFoundError(f"video no encontrado: {self._path}")
        if stride < 1:
            raise ValueError(f"stride debe ser >= 1, no {stride}")
        self._stride = stride

        # Captura propia (decodificado único); las capturas internas de los
        # ProcesadorVideo se liberan: solo usamos su procesar_frame().
        self._cap = cv2.VideoCapture(str(self._path))
        self.fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

        kwargs = {"modelo_yolo": modelo_yolo}
        if px_per_m is not None:
            kwargs["pixeles_por_metro"] = px_per_m
        self._pv_ns = ProcesadorVideo(str(self._path), roi=roi_ns, **kwargs)
        self._pv_eo = ProcesadorVideo(str(self._path), roi=roi_eo, **kwargs)
        for pv in (self._pv_ns, self._pv_eo):
            pv.video.release()

        logger.info("DualRoiVideoProvider: %s fps=%.1f frames=%d stride=%d",
                    self._path.name, self.fps, self.total_frames, stride)

    def __iter__(self) -> Iterator[Tuple[FrameMetrics, FrameMetrics]]:
        n = 0
        while True:
            ret, frame = self._cap.read()
            if not ret:
                break
            if n % self._stride == 0:
                t_s = n / self.fps
                r_ns = self._pv_ns.procesar_frame(frame, n)
                r_eo = self._pv_eo.procesar_frame(frame, n)
                yield _a_metrics(r_ns, t_s), _a_metrics(r_eo, t_s)
            n += 1

    def close(self) -> None:
        try:
            self._cap.release()
        except Exception:
            pass
