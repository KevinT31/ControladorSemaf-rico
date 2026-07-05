"""VideoStateSource: agregación por ventana, calidad, EV y solo-ADVISORY.

Sin YOLO ni archivos de video: el proveedor es un iterable de pares
FrameMetrics sintéticos (la interfaz que produce DualRoiVideoProvider).
"""
import pytest

from nsb.cli.main import _parse_roi, main
from nsb.domain.enums import Direction, SourceKind
from nsb.sources.video import VideoStateSource, agregar_ventana
from nsb.vision.provider import FrameMetrics


def _fm(t_s, num=4, stopped=1, queue=10.0, speed=20.0, flow=6.0, ev=0.0):
    return FrameMetrics(t_s=t_s, num_vehicles=num, stopped_vehicles=stopped,
                        queue_m=queue, speed_kmh=speed, flow_veh_min=flow,
                        ev_confidence=ev)


def _fuente(pares, **kw):
    kw.setdefault("experiment_id", "test-video")
    kw.setdefault("control_interval_s", 25.0)
    return VideoStateSource(pares, **kw)


# ------------------------------------------------------------- agregación
def test_agregar_ventana_promedia():
    frames = [_fm(0, num=2, queue=10, speed=30, flow=4),
              _fm(1, num=4, queue=20, speed=10, flow=8)]
    ap = agregar_ventana(frames)
    assert ap.num_vehicles == 3
    assert ap.queue_m == pytest.approx(15.0)
    assert ap.speed_kmh == pytest.approx(20.0)
    assert ap.flow_veh_min == pytest.approx(6.0)


def test_agregar_ventana_velocidad_ignora_frames_sin_movimiento():
    frames = [_fm(0, speed=0.0), _fm(1, speed=30.0)]
    assert agregar_ventana(frames).speed_kmh == pytest.approx(30.0)


def test_agregar_ventana_vacia_es_estado_cero():
    ap = agregar_ventana([])
    assert ap.num_vehicles == 0 and ap.queue_m == 0.0


# ---------------------------------------------------------------- ventanas
def test_ventanas_por_intervalo_y_seq_monotono():
    # frames a 0..70 s cada 5 s → ventanas de 25 s: [0,25), [25,50), [50,75)
    pares = [(_fm(t), _fm(t, num=8)) for t in range(0, 71, 5)]
    estados = list(_fuente(pares))
    assert [e.seq for e in estados] == [0, 1, 2]
    assert [e.sim_time_s for e in estados] == [25.0, 50.0, 75.0]
    assert all(e.source is SourceKind.VIDEO for e in estados)
    # la ROI EO llevaba num=8 en todos los frames
    assert estados[0].approaches[Direction.EO].num_vehicles == 8


def test_ventana_sin_frames_sale_invalida():
    # frames solo en [0,25) y [50,75): la ventana intermedia va vacía
    pares = [(_fm(t), _fm(t)) for t in (0.0, 10.0, 60.0)]
    estados = list(_fuente(pares))
    assert len(estados) == 3
    assert estados[0].quality.valid is True
    assert estados[1].quality.valid is False      # el guard la rechazará
    assert estados[2].quality.valid is True


def test_flags_de_calidad_del_operador():
    pares = [(_fm(0.0), _fm(0.0))]
    e = next(iter(_fuente(pares, camera_moving=True, calibrated=True)))
    assert e.quality.camera_moving is True and e.quality.calibrated is True


def test_proveedor_vacio_lanza():
    with pytest.raises(ValueError, match="ningún frame"):
        list(_fuente([]))


# ---------------------------------------------------------------------- EV
def test_ev_por_encima_del_umbral_genera_evento():
    pares = [(_fm(0.0, ev=0.9), _fm(0.0)), (_fm(1.0, ev=0.7), _fm(1.0))]
    e = next(iter(_fuente(pares)))
    assert e.ev_ns == pytest.approx(0.9)          # máximo de la ventana
    assert e.ev_event is not None
    assert e.ev_event.approach is Direction.NS


def test_ev_debil_no_genera_evento():
    pares = [(_fm(0.0, ev=0.3), _fm(0.0))]
    e = next(iter(_fuente(pares)))
    assert e.ev_ns == pytest.approx(0.3) and e.ev_event is None


# ------------------------------------------------- integración con el nodo
def test_nodo_advisory_consume_fuente_de_video(tmp_path):
    from nsb.config import NodeConfig
    from nsb.node import NsbNode

    pares = [(_fm(float(t)), _fm(float(t))) for t in range(0, 51, 5)]
    cfg = NodeConfig(telemetry={"jsonl_dir": str(tmp_path)})
    node = NsbNode.from_config(cfg, experiment_id="video-unit")
    summary = node.run(_fuente(pares))
    node.shutdown()
    assert summary.estados == 3
    assert summary.verdicts.get("accept", 0) == 3


# ----------------------------------------------------------- CLI / ROI
def test_parse_roi_valida():
    assert _parse_roi("0, 0, 640, 360") == (0, 0, 640, 360)


@pytest.mark.parametrize("texto", ["1,2,3", "a,b,c,d", "0,0,-5,10", "0,0,10,0"])
def test_parse_roi_invalida(texto):
    with pytest.raises(ValueError):
        _parse_roi(texto)


def test_cli_video_rechaza_modo_no_advisory(capsys):
    rc = main(["run", "--source", "video", "--mode", "tsc-emulated",
               "--input", "x.mp4", "--roi-ns", "0,0,10,10",
               "--roi-eo", "0,10,10,10"])
    assert rc == 1
    assert "ADVISORY" in capsys.readouterr().err


def test_cli_video_exige_rois(capsys):
    rc = main(["run", "--source", "video", "--mode", "advisory",
               "--input", "x.mp4"])
    assert rc == 1
    assert "--roi-ns" in capsys.readouterr().err
