"""Telemetría HTTP: contrato del backend y entrega asíncrona."""
import json
import threading

import pytest

from nsb.config import NodeConfig
from nsb.domain.enums import Mode
from nsb.node import NsbNode
from nsb.telemetry.http_sink import HttpSink, paquete_estado_local

from tests.conftest import make_state


def test_paquete_usa_matriz_que_espera_estado_global():
    paquete = paquete_estado_local(make_state(seq=0), rec=None)
    matriz = paquete["state_matrix"]

    assert set(matriz) == {"SC", "Vavg", "q", "k", "ICV", "PI", "EV"}
    assert all(len(valores) == 4 for valores in matriz.values())
    assert matriz["SC"] == [4, 4, 2, 2]  # orden N, S, E, O
    assert paquete["emergency_vehicles"] == []


def test_http_enabled_se_conecta_al_nodo_sin_bloquear(monkeypatch, tmp_path):
    recibido = []
    listo = threading.Event()

    class Respuesta:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def urlopen(req, timeout):
        recibido.append(json.loads(req.data))
        listo.set()
        return Respuesta()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    cfg = NodeConfig(
        mode=Mode.ADVISORY,
        telemetry={
            "jsonl_dir": str(tmp_path / "eventos"),
            "http_enabled": True,
            "http_url": "http://127.0.0.1:8000/api/estado-local/ingresar",
        },
    )
    node = NsbNode.from_config(cfg, experiment_id="http-test")
    try:
        node.process_one(make_state(seq=0))
        assert listo.wait(2.0), "el worker HTTP no procesó la telemetría"
    finally:
        node.shutdown()

    assert recibido[0]["intersection_id"] == "int-test"
    assert recibido[0]["state_matrix"]["SC"] == [4, 4, 2, 2]


@pytest.mark.parametrize("invalido", [0, -1, True, 1.5])
def test_http_sink_rechaza_tamano_de_cola_invalido(invalido):
    with pytest.raises(ValueError, match="max_queued"):
        HttpSink("http://127.0.0.1", max_queued=invalido)
