"""Protocolo HIL contra el nodo REAL por TCP 127.0.0.1, sin SUMO: un
FakeGateway in-process ensaya el contrato (handshake, states, malformed,
seq raros, bye) y los fallos de red (spec §33-D)."""
import json
import socket
import threading
import time

import pytest

from nsb.config import HilClientConfig, NodeConfig
from nsb.domain.contracts import DecisionEnvelope
from nsb.domain.enums import Mode, SourceKind, WireType
from nsb.domain.wire import WireEnvelope, decode, encode
from nsb.hil.node_client import HilNodeClient
from nsb.node import NsbNode

from tests.conftest import make_state


class FakeGateway:
    """Servidor TCP mínimo que guioniza mensajes hacia el nodo real."""

    def __init__(self):
        self._listen = socket.create_server(("127.0.0.1", 0))
        self._listen.settimeout(10.0)
        self.port = self._listen.getsockname()[1]
        self._conn = None
        self._buffer = b""
        self.decisiones = []

    def accept_y_handshake(self, experiment_id="exp-fake"):
        conn, _ = self._listen.accept()
        conn.settimeout(10.0)
        self._conn = conn
        hello = self._recv()
        assert hello.type is WireType.HELLO
        self._send(WireEnvelope(type=WireType.HELLO_ACK,
                                experiment_id=experiment_id,
                                payload={"seed": 0, "control_interval_s": 25.0}))

    def _send(self, env: WireEnvelope):
        self._conn.sendall(encode(env))

    def send_raw(self, data: bytes):
        self._conn.sendall(data)

    def _recv(self) -> WireEnvelope:
        while b"\n" not in self._buffer:
            chunk = self._conn.recv(65536)
            if not chunk:
                raise ConnectionError("nodo cerró")
            self._buffer += chunk
        linea, self._buffer = self._buffer.split(b"\n", 1)
        return decode(linea)

    def send_state(self, state):
        self._send(WireEnvelope(type=WireType.STATE, seq=state.seq,
                                experiment_id=state.experiment_id,
                                payload=state.model_dump(mode="json")))

    def recv_decision(self) -> DecisionEnvelope:
        while True:
            env = self._recv()
            if env.type is WireType.DECISION:
                d = DecisionEnvelope.model_validate(env.payload)
                self.decisiones.append(d)
                return d
            # heartbeats u otros: ignorar

    def bye(self):
        self._send(WireEnvelope(type=WireType.BYE, payload={}))

    def drop(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._buffer = b""

    def close(self):
        self.drop()
        self._listen.close()


@pytest.fixture
def nodo_hil(tmp_path):
    """Nodo real + cliente HIL corriendo en un hilo, conectado al fake."""
    gw = FakeGateway()
    cfg = NodeConfig(mode=Mode.TSC_EMULATED, source=SourceKind.SUMO_HIL,
                     telemetry={"jsonl_dir": str(tmp_path / "t")},
                     hil={"host": "127.0.0.1", "port": gw.port,
                          "connect_timeout_s": 2.0, "read_timeout_s": 5.0,
                          "reconnect_max_s": 1.0})
    node = NsbNode.from_config(cfg, experiment_id="exp-fake")
    client = HilNodeClient(node, cfg.hil, cfg.node_id)
    hilo = threading.Thread(target=client.run, daemon=True)
    hilo.start()
    yield gw, node, client, hilo
    gw.close()
    hilo.join(timeout=5.0)
    node.shutdown()


class TestProtocoloHil:
    def test_flujo_normal(self, nodo_hil):
        gw, node, client, hilo = nodo_hil
        gw.accept_y_handshake()
        for k in range(3):
            gw.send_state(make_state(seq=k, experiment_id="exp-fake"))
            d = gw.recv_decision()
            assert d.seq == k
            assert d.verdict.value == "accept"
        gw.bye()
        hilo.join(timeout=5.0)
        assert not hilo.is_alive()
        assert client._summary.terminado_por_bye

    def test_state_malformado_no_tumba_al_nodo(self, nodo_hil):
        gw, node, client, hilo = nodo_hil
        gw.accept_y_handshake()
        gw.send_raw(b"esto no es json\n")
        gw.send_raw(json.dumps({
            "type": "state", "seq": 0,
            "payload": {"basura": True}}).encode() + b"\n")
        # NaN serializado (json de Python lo permite): frontera debe rechazar
        st = make_state(seq=0, experiment_id="exp-fake")
        payload = st.model_dump(mode="json")
        payload["ev_ns"] = float("nan")
        gw.send_raw(json.dumps({"type": "state", "seq": 0,
                                "payload": payload}).encode() + b"\n")
        # Tras la basura, un state válido sigue funcionando
        gw.send_state(make_state(seq=1, experiment_id="exp-fake"))
        d = gw.recv_decision()
        assert d.seq == 1
        gw.bye()
        hilo.join(timeout=5.0)
        assert client._summary.errores_protocolo >= 3

    def test_duplicado_y_fuera_de_orden_rechazados(self, nodo_hil):
        gw, node, client, hilo = nodo_hil
        gw.accept_y_handshake()
        gw.send_state(make_state(seq=5, experiment_id="exp-fake"))
        assert gw.recv_decision().verdict.value == "accept"
        gw.send_state(make_state(seq=5, experiment_id="exp-fake"))   # dup
        d_dup = gw.recv_decision()
        assert d_dup.verdict.value == "reject"
        gw.send_state(make_state(seq=2, experiment_id="exp-fake"))   # viejo
        d_old = gw.recv_decision()
        assert d_old.verdict.value == "reject"
        gw.bye()
        hilo.join(timeout=5.0)

    def test_reconexion_tras_caida(self, nodo_hil):
        gw, node, client, hilo = nodo_hil
        gw.accept_y_handshake()
        gw.send_state(make_state(seq=0, experiment_id="exp-fake"))
        gw.recv_decision()

        gw.drop()                       # caída del enlace
        gw.accept_y_handshake()         # el nodo debe reconectar (backoff 1s)

        # Tras la caída el TSC local está en modo seguro (spec §26-B)
        assert node.authority.tsc.safe_mode
        # ...y una recomendación aceptada lo saca
        gw.send_state(make_state(seq=1, experiment_id="exp-fake"))
        d = gw.recv_decision()
        assert d.seq == 1 and d.verdict.value == "accept"
        assert not node.authority.tsc.safe_mode
        assert client._summary.reconexiones == 1
        gw.bye()
        hilo.join(timeout=5.0)
