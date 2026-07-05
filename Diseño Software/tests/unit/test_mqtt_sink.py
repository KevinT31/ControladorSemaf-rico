"""MqttTelemetrySink: ruteo de tópicos, no-bloqueo y fail-fast de TLS.

Todos los tests usan un cliente FALSO inyectado: no requieren broker ni red.
La verificación end-to-end con Mosquitto real está en
tests/integration/test_mqtt_local.py (opt-in por variable de entorno).
"""
import json

import pytest

from nsb.comms.mqtt_telemetry import MqttTelemetrySink, _validar_tls
from nsb.config import TelemetryConfig
from nsb.telemetry.events import INFO, evento


class _PublishInfo:
    def __init__(self, rc=0):
        self.rc = rc

    def wait_for_publish(self, timeout=None):
        pass


class FakeClient:
    """Registra llamadas; simula paho sin tocar la red."""

    def __init__(self, publish_rc=0, publish_exc=None):
        self.published = []            # (topic, payload, qos, retain)
        self.will = None
        self.publish_rc = publish_rc
        self.publish_exc = publish_exc
        self.loop_started = False
        self.disconnected = False
        self.on_connect = None
        self.on_disconnect = None

    def will_set(self, topic, payload=None, qos=0, retain=False):
        self.will = (topic, payload, qos, retain)

    def max_queued_messages_set(self, n):
        pass

    def reconnect_delay_set(self, mn, mx):
        pass

    def connect_async(self, host, port, keepalive=60):
        pass

    def loop_start(self):
        self.loop_started = True

    def loop_stop(self):
        self.loop_started = False

    def publish(self, topic, payload=None, qos=0, retain=False):
        if self.publish_exc is not None:
            raise self.publish_exc
        self.published.append((topic, payload, qos, retain))
        return _PublishInfo(self.publish_rc)

    def disconnect(self):
        self.disconnected = True


def _cfg(**kw):
    base = dict(mqtt_enabled=True, mqtt_tls=False,
                mqtt_host="127.0.0.1", mqtt_port=1883)
    base.update(kw)
    return TelemetryConfig(**base)


def _sink(client=None, **cfg_kw):
    # connect_wait_s=0: el FakeClient jamás "conecta"; no esperar en tests
    return MqttTelemetrySink(_cfg(**cfg_kw), "nodo-01",
                             client=client or FakeClient(),
                             connect_wait_s=0)


# ---------------------------------------------------------------- tópicos
def test_decision_va_a_telemetry_y_resto_a_events():
    fake = FakeClient()
    s = _sink(fake)
    s.emit(evento("decision", "nodo-01", INFO, seq=7))
    s.emit(evento("mode_change", "nodo-01", INFO))
    topics = [t for t, *_ in fake.published]
    assert topics == ["nsb/nodo-01/telemetry/decision",
                      "nsb/nodo-01/events/mode_change"]


def test_payload_es_el_evento_serializado():
    fake = FakeClient()
    s = _sink(fake)
    ev = evento("decision", "nodo-01", INFO, seq=3, verdict="accept")
    s.emit(ev)
    _, payload, qos, _ = fake.published[0]
    assert qos == 0                        # best-effort, jamás espera ACK
    d = json.loads(payload)
    assert d["seq"] == 3 and d["data"]["verdict"] == "accept"


# ------------------------------------------------------- heartbeat / will
def test_last_will_offline_retained_configurado():
    fake = FakeClient()
    _sink(fake)
    topic, payload, qos, retain = fake.will
    assert topic == "nsb/nodo-01/heartbeat" and retain is True
    assert json.loads(payload)["status"] == "offline"


def test_on_connect_publica_online_retained():
    fake = FakeClient()
    s = _sink(fake)

    class _RC:
        is_failure = False

    s._on_connect(fake, None, {}, _RC())
    assert s.connected is True
    topic, payload, _, retain = fake.published[-1]
    assert topic == "nsb/nodo-01/heartbeat" and retain is True
    assert json.loads(payload)["status"] == "online"


def test_close_publica_offline_y_para_el_loop():
    fake = FakeClient()
    s = _sink(fake)
    s.close()
    assert json.loads(fake.published[-1][1])["status"] == "offline"
    assert fake.loop_started is False and fake.disconnected is True


# --------------------------------------------------------- nunca bloquea
def test_publish_sin_conexion_descarta_sin_lanzar():
    fake = FakeClient(publish_rc=4)        # MQTT_ERR_NO_CONN
    s = _sink(fake)
    for i in range(3):
        s.emit(evento("decision", "nodo-01", INFO, seq=i))
    assert s.dropped == 3                  # descartado, no encolado ni esperado


def test_publish_que_lanza_no_propaga_al_control():
    fake = FakeClient(publish_exc=RuntimeError("boom interno de paho"))
    s = _sink(fake)
    s.emit(evento("decision", "nodo-01", INFO))   # no debe lanzar
    assert s.dropped == 1


# ------------------------------------------------------ fail-fast de TLS
def test_tls_sin_ca_falla_al_construir():
    with pytest.raises(ValueError, match="mqtt_ca_cert"):
        _validar_tls(_cfg(mqtt_tls=True))


def test_cert_cliente_sin_clave_falla(tmp_path):
    ca = tmp_path / "ca.crt"
    ca.write_text("x", encoding="utf-8")
    cert = tmp_path / "c.crt"
    cert.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="juntos"):
        _validar_tls(_cfg(mqtt_tls=True, mqtt_ca_cert=str(ca),
                          mqtt_client_cert=str(cert)))


def test_ruta_ca_inexistente_falla():
    with pytest.raises(ValueError, match="no existe"):
        _validar_tls(_cfg(mqtt_tls=True, mqtt_ca_cert="no/existe/ca.crt"))


def test_tls_desactivado_no_exige_certs():
    _validar_tls(_cfg(mqtt_tls=False))     # no lanza


# ------------------------------------------------- integración con nodo
def test_node_fanout_jsonl_y_mqtt(tmp_path):
    """_emit publica en ambos sinks; shutdown cierra el MQTT."""
    from nsb.config import NodeConfig
    from nsb.node import NsbNode

    fake = FakeClient()
    cfg = NodeConfig(telemetry={"jsonl_dir": str(tmp_path)})
    node = NsbNode.from_config(cfg, experiment_id="test-mqtt")
    node._mqtt = MqttTelemetrySink(_cfg(), "nodo-01", client=fake,
                                   connect_wait_s=0)

    node._emit(evento("mode_change", "nodo-01", INFO))
    assert any(t == "nsb/nodo-01/events/mode_change"
               for t, *_ in fake.published)
    node.shutdown()
    assert fake.disconnected is True
