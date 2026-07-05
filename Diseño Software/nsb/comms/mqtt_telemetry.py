"""Sink MQTT de telemetría con TLS/mTLS de laboratorio (spec §28, D-02, D-F).

Plano de TELEMETRÍA únicamente: el lazo HIL usa TCP JSON-lines dedicado y los
comandos van por la API existente. Este sink publica los mismos eventos que el
JSONL local (que sigue siendo la fuente de verdad).

Reglas de diseño:

* paho-mqtt se importa PEREZOSAMENTE (jamás a nivel de módulo): la base
  funciona sin el paquete cuando ``mqtt_enabled=false``.
* La telemetría JAMÁS bloquea el control: ``publish`` QoS 0 best-effort, el
  hilo de red es el de paho (``loop_start``), reconexión automática con
  backoff, y cualquier excepción se degrada a log + contador de descartes.
* Config inválida (TLS sin CA, cert sin clave, rutas inexistentes) falla al
  CONSTRUIR el sink — errores de configuración se detectan al arrancar, no
  en runtime silencioso. La red caída, en cambio, se tolera siempre.
* Identidad por nodo (spec §28): ``client_id = node_id``; con mTLS el broker
  puede usar el CN del certificado como usuario para la ACL por tópico.

Tópicos publicados:

    nsb/{node_id}/heartbeat              retained: online/offline (+ Last Will)
    nsb/{node_id}/telemetry/decision     un mensaje por decisión del nodo
    nsb/{node_id}/events/{event}         resto de eventos (mode_change, ...)

Este módulo no suscribe NADA: ninguna vía MQTT puede elevar el modo (D-H).
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from nsb.config import TelemetryConfig
from nsb.telemetry.events import TelemetryEvent

logger = logging.getLogger(__name__)

KEEPALIVE_S = 30
RECONNECT_MIN_S = 1
RECONNECT_MAX_S = 30
MAX_QUEUED = 1000
# Esperas ACOTADAS fuera del lazo de control: una vez al arrancar (conexión
# inicial) y una al cerrar (drenar la cola saliente). Sin esto, en corridas
# cortas los primeros/últimos eventos QoS 0 se pierden por carrera.
CONNECT_WAIT_S = 2.0
CLOSE_FLUSH_S = 2.0


def _validar_tls(cfg: TelemetryConfig) -> None:
    """Fail-fast de configuración TLS (antes de tocar la red)."""
    if not cfg.mqtt_tls:
        return
    if not cfg.mqtt_ca_cert:
        raise ValueError(
            "telemetry.mqtt_tls=true requiere mqtt_ca_cert (CA de laboratorio); "
            "genere los certificados con scripts/nsb/mqtt/gen_lab_certs.ps1")
    if bool(cfg.mqtt_client_cert) != bool(cfg.mqtt_client_key):
        raise ValueError(
            "mqtt_client_cert y mqtt_client_key deben especificarse juntos (mTLS)")
    for nombre, ruta in (("mqtt_ca_cert", cfg.mqtt_ca_cert),
                         ("mqtt_client_cert", cfg.mqtt_client_cert),
                         ("mqtt_client_key", cfg.mqtt_client_key)):
        if ruta and not Path(ruta).exists():
            raise ValueError(f"telemetry.{nombre}: no existe {ruta}")


def _crear_cliente(cfg: TelemetryConfig, node_id: str):
    """Crea el cliente paho real (import perezoso — spec §23 aplica igual)."""
    try:
        import paho.mqtt.client as mqtt
    except ImportError as e:
        raise ValueError(
            "telemetry.mqtt_enabled=true pero paho-mqtt no está instalado "
            "(pip install paho-mqtt)") from e

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=node_id,
        protocol=mqtt.MQTTv311,
        clean_session=True,
    )
    if cfg.mqtt_tls:
        client.tls_set(
            ca_certs=cfg.mqtt_ca_cert,
            certfile=cfg.mqtt_client_cert,
            keyfile=cfg.mqtt_client_key,
        )
    return client


def _payload_heartbeat(status: str, node_id: str) -> str:
    return json.dumps({
        "status": status,
        "node_id": node_id,
        "ts_iso": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    })


class MqttTelemetrySink:
    """Publicador best-effort de ``TelemetryEvent`` hacia un broker MQTT."""

    def __init__(self, cfg: TelemetryConfig, node_id: str, client=None,
                 connect_wait_s: float = CONNECT_WAIT_S):
        _validar_tls(cfg)
        self._node = node_id
        self._prefix = f"nsb/{node_id}"
        self._conectado = threading.Event()
        self._dropped = 0
        self._aviso_emitido = False

        self._client = client if client is not None else _crear_cliente(cfg, node_id)
        # Last Will retained: si el proceso muere, el broker marca offline
        self._client.will_set(f"{self._prefix}/heartbeat",
                              payload=_payload_heartbeat("offline", node_id),
                              qos=1, retain=True)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.max_queued_messages_set(MAX_QUEUED)
        self._client.reconnect_delay_set(RECONNECT_MIN_S, RECONNECT_MAX_S)
        # connect_async + loop_start: nunca bloquea aunque el broker no exista
        self._client.connect_async(cfg.mqtt_host, cfg.mqtt_port,
                                   keepalive=KEEPALIVE_S)
        self._client.loop_start()
        # Espera acotada de la conexión inicial (solo ARRANQUE, no control):
        # evita perder los primeros eventos en corridas cortas. Si el broker
        # no está, se continúa sin conexión (best-effort).
        if connect_wait_s > 0 and not self._conectado.wait(connect_wait_s):
            logger.warning("MQTT: sin conexion tras %.1fs; se continua sin "
                           "broker (best-effort)", connect_wait_s)

    # --------------------------------------------------------------- #
    # Callbacks de paho (corren en el hilo de red de paho, no en el de
    # control; solo tocan flags y publish, jamás el estado del nodo).
    def _on_connect(self, client, userdata, flags, reason_code,
                    properties=None) -> None:
        if not reason_code.is_failure:
            self._conectado.set()
            logger.info("MQTT conectado (%s)", self._prefix)
            client.publish(f"{self._prefix}/heartbeat",
                           _payload_heartbeat("online", self._node),
                           qos=1, retain=True)
        else:
            self._conectado.clear()
            logger.warning("MQTT conexion rechazada: %s", reason_code)

    def _on_disconnect(self, client, userdata, disconnect_flags,
                       reason_code, properties=None) -> None:
        self._conectado.clear()
        logger.warning("MQTT desconectado (%s); reconexion automatica",
                       reason_code)

    # --------------------------------------------------------------- #
    @property
    def connected(self) -> bool:
        return self._conectado.is_set()

    @property
    def dropped(self) -> int:
        """Eventos que no pudieron publicarse (broker caído, error interno)."""
        return self._dropped

    def _topic(self, event: TelemetryEvent) -> str:
        if event.event == "decision":
            return f"{self._prefix}/telemetry/decision"
        return f"{self._prefix}/events/{event.event}"

    def emit(self, event: TelemetryEvent) -> None:
        """Publica QoS 0 sin esperar. Nunca lanza hacia el lazo de control."""
        try:
            info = self._client.publish(self._topic(event),
                                        event.model_dump_json(), qos=0)
            if info.rc != 0:  # p. ej. MQTT_ERR_NO_CONN: descartar, no esperar
                self._dropped += 1
                if not self._aviso_emitido:
                    logger.warning(
                        "MQTT sin conexion (rc=%s); eventos descartados — la "
                        "telemetria local JSONL continua", info.rc)
                    self._aviso_emitido = True
        except Exception:
            self._dropped += 1
            if not self._aviso_emitido:
                logger.exception("MQTT publish fallo; eventos descartados")
                self._aviso_emitido = True

    def close(self) -> None:
        """Despedida best-effort: offline retained + drenado acotado + stop.

        El ``wait_for_publish`` del offline (QoS 1, el último de la cola)
        fuerza a drenar en orden los QoS 0 previos antes de parar el hilo de
        red; sin él, los últimos eventos de una corrida corta se pierden y el
        broker dispara el Last Will pese al cierre limpio."""
        try:
            info = self._client.publish(f"{self._prefix}/heartbeat",
                                        _payload_heartbeat("offline", self._node),
                                        qos=1, retain=True)
            try:
                info.wait_for_publish(timeout=CLOSE_FLUSH_S)
            except Exception:
                pass   # sin conexión: no hay nada que drenar
            self._client.disconnect()   # DISCONNECT limpio suprime el Last Will
            self._client.loop_stop()
        except Exception:
            logger.debug("MQTT close: fallo ignorado", exc_info=True)
