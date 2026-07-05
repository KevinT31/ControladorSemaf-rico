"""Integración MQTT con broker Mosquitto REAL (opt-in).

Se salta salvo que exista un broker local y se pida explícitamente:

    $env:NSB_TEST_MQTT = "1"                  # habilita estos tests
    $env:NSB_TEST_MQTT_PORT = "1883"          # opcional (default 1883, sin TLS)

Con TLS (certs de laboratorio ya generados y broker en 8883):

    $env:NSB_TEST_MQTT_TLS = "1"
    $env:NSB_TEST_MQTT_CA = "config/nsb/mosquitto/certs/ca.crt"
    $env:NSB_TEST_MQTT_CERT = "config/nsb/mosquitto/certs/nsb-node-01.crt"
    $env:NSB_TEST_MQTT_KEY = "config/nsb/mosquitto/certs/nsb-node-01.key"
    # la ACL solo permite READ global al observador; el suscriptor del test
    # debe presentar SU cert (CN=nsb-observer):
    $env:NSB_TEST_MQTT_SUB_CERT = "config/nsb/mosquitto/certs/nsb-observer.crt"
    $env:NSB_TEST_MQTT_SUB_KEY = "config/nsb/mosquitto/certs/nsb-observer.key"

Jamás se marca PASS sin broker (spec §7.11, §50).
"""
import json
import os
import time

import pytest

habilitado = os.environ.get("NSB_TEST_MQTT") == "1"

pytestmark = pytest.mark.skipif(
    not habilitado,
    reason="REQUIRES BROKER: exporte NSB_TEST_MQTT=1 con Mosquitto local "
           "(ver docs/nsb_v2_1/mqtt_tls.md)")


def _cfg():
    from nsb.config import TelemetryConfig
    tls = os.environ.get("NSB_TEST_MQTT_TLS") == "1"
    port = int(os.environ.get("NSB_TEST_MQTT_PORT", "8883" if tls else "1883"))
    return TelemetryConfig(
        mqtt_enabled=True,
        mqtt_host="127.0.0.1",
        mqtt_port=port,
        mqtt_tls=tls,
        mqtt_ca_cert=os.environ.get("NSB_TEST_MQTT_CA"),
        mqtt_client_cert=os.environ.get("NSB_TEST_MQTT_CERT"),
        mqtt_client_key=os.environ.get("NSB_TEST_MQTT_KEY"),
    )


def _esperar(cond, timeout_s=5.0):
    limite = time.monotonic() + timeout_s
    while time.monotonic() < limite:
        if cond():
            return True
        time.sleep(0.05)
    return False


def test_publica_decision_y_heartbeat_en_broker_real():
    import paho.mqtt.client as mqtt

    from nsb.comms.mqtt_telemetry import MqttTelemetrySink
    from nsb.telemetry.events import INFO, evento

    cfg = _cfg()
    recibidos = []

    sub = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                      client_id="nsb-observer")
    if cfg.mqtt_tls:
        sub.tls_set(
            ca_certs=cfg.mqtt_ca_cert,
            certfile=os.environ.get("NSB_TEST_MQTT_SUB_CERT",
                                    cfg.mqtt_client_cert),
            keyfile=os.environ.get("NSB_TEST_MQTT_SUB_KEY",
                                   cfg.mqtt_client_key))
    sub.on_message = lambda c, u, m: recibidos.append((m.topic, m.payload))
    sub.connect(cfg.mqtt_host, cfg.mqtt_port)
    sub.subscribe("nsb/nsb-node-01/#", qos=1)
    sub.loop_start()

    sink = MqttTelemetrySink(cfg, "nsb-node-01")
    try:
        assert _esperar(lambda: sink.connected), "el sink no conecto al broker"
        sink.emit(evento("decision", "nsb-node-01", INFO, seq=1,
                         verdict="accept"))
        assert _esperar(lambda: any(
            t == "nsb/nsb-node-01/telemetry/decision" for t, _ in recibidos)), \
            f"decision no llego; recibido: {[t for t, _ in recibidos]}"
        # heartbeat es retained: puede llegar primero el "offline" retenido
        # de una corrida anterior; lo que importa es el "online" fresco.
        heart = [json.loads(p)["status"]
                 for t, p in recibidos if t.endswith("/heartbeat")]
        assert "online" in heart, f"sin heartbeat online; recibido: {heart}"
        assert sink.dropped == 0
    finally:
        sink.close()
        sub.loop_stop()
        sub.disconnect()
