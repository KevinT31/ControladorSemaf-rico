"""Configuración tipada de NSB: YAML + overrides por variables de entorno.

Prioridad (mayor gana): variables de entorno ``NSB_*`` > YAML > defaults.
Se implementa reordenando las fuentes de pydantic-settings para que el
entorno pise lo cargado del YAML (los valores del YAML entran como init
kwargs).

Anidamiento por ``__``: p. ej. ``NSB_HIL__PORT=9500`` pisa ``hil.port``.

La validación de tiempos respeta tanto los límites duros del núcleo
(``LIMITES``) como los techos operativos de ``clamp_tiempos`` (ámbar ≤ 6 s,
todo-rojo ≤ 5 s): una config fuera de esos rangos se rechaza al arrancar en
lugar de producir CLAMP permanente y ruidoso en runtime.

Nunca se leen secretos de estos YAML; ver ``.env.example``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Optional, Tuple, Type
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from nsb.domain.enums import Mode, SourceKind, TimeoutPolicy
from nsb.safety.limits import LIMITES, T_AMBAR_MAX, T_TODO_ROJO_MAX


Port = Annotated[int, Field(ge=1, le=65535)]
PositiveFiniteFloat = Annotated[
    float, Field(gt=0, allow_inf_nan=False)]


class ActuatorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = "simulated"               # simulated | gpio
    pinout_path: Optional[str] = None     # YAML de pines (requerido si gpio)
    render: bool = False                  # render de consola del simulado

    @field_validator("type")
    @classmethod
    def _tipo_conocido(cls, v: str) -> str:
        if v not in ("simulated", "gpio"):
            raise ValueError(f"actuator.type desconocido: {v!r}")
        return v


class HilClientConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = "127.0.0.1"
    port: Port = 9500
    connect_timeout_s: PositiveFiniteFloat = 5.0
    read_timeout_s: PositiveFiniteFloat = 30.0  # gateway marca el ritmo; holgado
    reconnect_max_s: PositiveFiniteFloat = 30.0  # techo del backoff

    @field_validator("host")
    @classmethod
    def _host_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("hil.host no puede estar vacío")
        return v


class TelemetryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jsonl_dir: str = "datos/logs-sistema/nsb"   # relativo a la raíz del proyecto
    http_enabled: bool = False
    http_url: str = "http://127.0.0.1:8000/api/estado-local/ingresar"
    mqtt_enabled: bool = False
    mqtt_host: str = "127.0.0.1"
    mqtt_port: Port = 8883
    mqtt_tls: bool = True
    mqtt_ca_cert: Optional[str] = None
    mqtt_client_cert: Optional[str] = None
    mqtt_client_key: Optional[str] = None

    @field_validator("jsonl_dir", "mqtt_host")
    @classmethod
    def _texto_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("el valor no puede estar vacío")
        return v

    @field_validator("http_url")
    @classmethod
    def _url_http_valida(cls, v: str) -> str:
        partes = urlsplit(v)
        if partes.scheme not in ("http", "https") or not partes.netloc:
            raise ValueError("telemetry.http_url debe ser una URL http(s) válida")
        return v


class SafetyTimingConfig(BaseModel):
    """Tiempos de fase del nodo. Validados contra LIMITES y techos de clamp."""
    model_config = ConfigDict(extra="forbid")

    t_base_verde_ns: float = 30.0
    t_base_verde_eo: float = 30.0
    t_ambar: float = 3.0
    t_todo_rojo: float = 2.0
    t_ciclo: float = 90.0                 # mismo default que el difuso canónico
    max_silence_cycles: Annotated[int, Field(ge=1)] = 3  # sin recs válidas → plan seguro

    @model_validator(mode="after")
    def _dentro_de_limites(self) -> "SafetyTimingConfig":
        errores = []
        for nombre, v in (("t_base_verde_ns", self.t_base_verde_ns),
                          ("t_base_verde_eo", self.t_base_verde_eo)):
            if not (LIMITES.T_VERDE_MIN <= v <= LIMITES.T_VERDE_MAX):
                errores.append(
                    f"{nombre}={v:g}s fuera de [{LIMITES.T_VERDE_MIN:g}, "
                    f"{LIMITES.T_VERDE_MAX:g}]s")
        if not (LIMITES.T_AMBAR_MIN <= self.t_ambar <= T_AMBAR_MAX):
            errores.append(
                f"t_ambar={self.t_ambar:g}s fuera de "
                f"[{LIMITES.T_AMBAR_MIN:g}, {T_AMBAR_MAX:g}]s")
        if not (LIMITES.T_TODO_ROJO_MIN <= self.t_todo_rojo <= T_TODO_ROJO_MAX):
            errores.append(
                f"t_todo_rojo={self.t_todo_rojo:g}s fuera de "
                f"[{LIMITES.T_TODO_ROJO_MIN:g}, {T_TODO_ROJO_MAX:g}]s")
        if not (LIMITES.T_CICLO_MIN <= self.t_ciclo <= LIMITES.T_CICLO_MAX):
            errores.append(
                f"t_ciclo={self.t_ciclo:g}s fuera de "
                f"[{LIMITES.T_CICLO_MIN:g}, {LIMITES.T_CICLO_MAX:g}]s")
        if errores:
            raise ValueError("; ".join(errores))
        return self


class NodeConfig(BaseSettings):
    """Configuración del nodo edge (``python -m nsb run``)."""
    model_config = SettingsConfigDict(
        env_prefix="NSB_", env_nested_delimiter="__", extra="forbid")

    node_id: str = "nsb-node-01"
    intersection_id: str = "interseccion-01"
    mode: Mode = Mode.ADVISORY
    source: SourceKind = SourceKind.MANUAL
    control_interval_s: PositiveFiniteFloat = 25.0  # canónico de la tesis
    # AUTOMATED_DIRECT_LAB: primera compuerta. Las otras dos (flag CLI +
    # variable de entorno de confirmación) viven en authority.direct_lab_gate.
    allow_direct_lab: bool = False
    actuator: ActuatorConfig = Field(default_factory=ActuatorConfig)
    hil: HilClientConfig = Field(default_factory=HilClientConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    safety: SafetyTimingConfig = Field(default_factory=SafetyTimingConfig)
    log_level: str = "INFO"

    @model_validator(mode="after")
    def _gpio_requiere_pinout(self) -> "NodeConfig":
        if (self.actuator.type == "gpio"
                and not (self.actuator.pinout_path or "").strip()):
            raise ValueError("actuator.type=gpio requiere actuator.pinout_path")
        return self

    @field_validator("node_id")
    @classmethod
    def _node_id_seguro(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", v):
            raise ValueError(
                "node_id debe usar 1..128 caracteres ASCII alfanuméricos, "
                "punto, guion o guion bajo")
        return v

    @field_validator("intersection_id")
    @classmethod
    def _intersection_no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("intersection_id no puede estar vacío")
        return v

    @field_validator("log_level")
    @classmethod
    def _log_level_conocido(cls, v: str) -> str:
        nivel = v.upper()
        if nivel not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError(f"log_level desconocido: {v!r}")
        return nivel

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # env ANTES que init => variables NSB_* pisan lo que venga del YAML
        return (env_settings, init_settings, dotenv_settings, file_secret_settings)


class PhaseMapConfig(BaseModel):
    """Mapeo EXPLÍCITO de fases SUMO → modelo NS/EO (decisión del plan:
    declarado en config, nunca inferido por heurística)."""
    model_config = ConfigDict(extra="forbid")

    tls_id: str
    ns_green_index: Annotated[int, Field(ge=0)]
    eo_green_index: Annotated[int, Field(ge=0)]

    @field_validator("tls_id")
    @classmethod
    def _tls_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("phase_map.tls_id no puede estar vacío")
        return v

    @model_validator(mode="after")
    def _indices_distintos(self) -> "PhaseMapConfig":
        if self.ns_green_index == self.eo_green_index:
            raise ValueError("ns_green_index y eo_green_index no pueden coincidir")
        return self


class GatewayConfig(BaseSettings):
    """Configuración del HIL Gateway (``python -m nsb gateway``)."""
    model_config = SettingsConfigDict(
        env_prefix="NSB_GW_", env_nested_delimiter="__", extra="forbid")

    sumo_cfg: str                                  # ruta al .sumocfg
    seed: Annotated[int, Field(ge=0)] = 42
    sumo_binary: str = "sumo"                      # "sumo-gui" para demo visual
    control_interval_s: PositiveFiniteFloat = 25.0
    max_control_points: Annotated[int, Field(ge=1)] = 28   # ≈700 s con 25 s
    phase_map: PhaseMapConfig
    bind_host: str = "127.0.0.1"                   # LAN explícita para la Pi
    bind_port: Port = 9500
    node_timeout_s: PositiveFiniteFloat = 2.0
    timeout_policy: TimeoutPolicy = TimeoutPolicy.FALLBACK
    max_consecutive_timeouts: Annotated[int, Field(ge=1)] = 3
    max_wait_reconnect_s: PositiveFiniteFloat = 60.0
    tick_mode: str = "control_only"                # control_only | per_step
    record_jsonl: Optional[str] = None             # graba TrafficState+Decision
    experiment_id: Optional[str] = None            # autogenerado si None

    @field_validator("sumo_cfg", "sumo_binary", "bind_host")
    @classmethod
    def _gateway_texto_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("el valor no puede estar vacío")
        return v

    @field_validator("tick_mode")
    @classmethod
    def _tick_conocido(cls, v: str) -> str:
        if v not in ("control_only", "per_step"):
            raise ValueError(f"tick_mode desconocido: {v!r}")
        return v

    @field_validator("control_interval_s")
    @classmethod
    def _intervalo_en_segundos_enteros(cls, v: float) -> float:
        if not v.is_integer():
            raise ValueError(
                "gateway.control_interval_s debe ser un número entero de "
                "segundos (SUMO usa step-length=1)")
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (env_settings, init_settings, dotenv_settings, file_secret_settings)


def _cargar_yaml(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config no encontrada: {p}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config inválida (se esperaba mapping YAML): {p}")
    return data


def load_node_config(path: str | Path) -> NodeConfig:
    """Carga node.yaml con overrides de entorno NSB_*."""
    return NodeConfig(**_cargar_yaml(path))


def load_gateway_config(path: str | Path) -> GatewayConfig:
    """Carga gateway.yaml con overrides de entorno NSB_GW_*."""
    return GatewayConfig(**_cargar_yaml(path))
