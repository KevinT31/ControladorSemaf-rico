"""Ground truth (spec §17): muestreo de frames y métricas de conteo."""
import csv
import json
import math

import pytest

from nsb.vision.ground_truth import evaluar_conteos, sample_frames


def _manifest(path, filas):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=(
            "frame_idx", "t_s", "archivo", "count_ns", "count_eo", "notas"))
        w.writeheader()
        w.writerows(filas)


def _states(path, estados):
    """estados: [(sim_time_s, ns, eo)] en formato ReplayWriter."""
    with open(path, "w", encoding="utf-8") as f:
        for t, ns, eo in estados:
            f.write(json.dumps({"kind": "state", "data": {
                "sim_time_s": t,
                "approaches": {"NS": {"num_vehicles": ns},
                               "EO": {"num_vehicles": eo}},
            }}) + "\n")


def test_metricas_exactas(tmp_path):
    m = tmp_path / "manifest.csv"
    s = tmp_path / "states.jsonl"
    _manifest(m, [
        {"frame_idx": 0, "t_s": "25.0", "archivo": "a.png",
         "count_ns": "4", "count_eo": "2", "notas": ""},
        {"frame_idx": 1, "t_s": "50.0", "archivo": "b.png",
         "count_ns": "6", "count_eo": "3", "notas": ""},
    ])
    _states(s, [(25.0, 5, 2), (50.0, 4, 5)])
    r = evaluar_conteos(m, s)
    # errores NS: (5-4)=1, (4-6)=-2 → MAE=1.5, RMSE=sqrt(2.5)
    assert r["ns"]["mae"] == pytest.approx(1.5)
    assert r["ns"]["rmse"] == pytest.approx(math.sqrt(2.5))
    # errores EO: 0 y 2 → MAE=1.0
    assert r["eo"]["mae"] == pytest.approx(1.0)
    assert r["n_emparejadas"] == 2


def test_filas_sin_anotar_se_omiten_y_todo_vacio_falla(tmp_path):
    m = tmp_path / "manifest.csv"
    s = tmp_path / "states.jsonl"
    _manifest(m, [{"frame_idx": 0, "t_s": "25.0", "archivo": "a.png",
                   "count_ns": "", "count_eo": "", "notas": ""}])
    _states(s, [(25.0, 5, 2)])
    with pytest.raises(ValueError, match="anote a mano"):
        evaluar_conteos(m, s)


def test_fuera_de_tolerancia_falla(tmp_path):
    m = tmp_path / "manifest.csv"
    s = tmp_path / "states.jsonl"
    _manifest(m, [{"frame_idx": 0, "t_s": "10.0", "archivo": "a.png",
                   "count_ns": "1", "count_eo": "1", "notas": ""}])
    _states(s, [(100.0, 1, 1)])
    with pytest.raises(ValueError, match="empareja"):
        evaluar_conteos(m, s, tol_s=12.5)


def test_sample_frames_video_sintetico(tmp_path):
    """Muestreo real con un video sintético diminuto (requiere cv2)."""
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    video = tmp_path / "mini.mp4"
    vw = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"),
                         10.0, (64, 48))
    assert vw.isOpened(), "cv2 sin soporte mp4v en esta plataforma"
    for i in range(30):                       # 3 s a 10 fps
        frame = np.full((48, 64, 3), i * 8 % 255, dtype=np.uint8)
        vw.write(frame)
    vw.release()

    # el directorio lleva "ñ" a propósito: imwrite falla con rutas no-ASCII
    # en Windows (hallazgo del red team); imencode+tofile no
    out = tmp_path / "gt-año"
    manifest = sample_frames(video, out, every_s=1.0)
    with open(manifest, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    assert len(filas) == 3                    # t = 0, 1, 2 s
    assert all((out / f["archivo"]).exists() for f in filas)
    assert filas[0]["count_ns"] == ""         # columnas para anotar A MANO
