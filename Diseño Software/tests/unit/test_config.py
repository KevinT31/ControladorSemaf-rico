"""Tests de carga/validación de configuración NSB."""
import pytest

from nsb.config import (
    GatewayConfig,
    NodeConfig,
    SafetyTimingConfig,
    load_gateway_config,
    load_node_config,
)
from nsb.domain.enums import Mode, TimeoutPolicy


class TestNodeConfig:
    def test_defaults_seguros(self):
        cfg = NodeConfig()
        assert cfg.mode is Mode.ADVISORY          # el default NO actúa
        assert cfg.allow_direct_lab is False      # direct-lab off por defecto
        assert cfg.actuator.type == "simulated"
        assert cfg.control_interval_s == 25.0     # canónico de la tesis

    def test_yaml_repo_carga(self):
        cfg = load_node_config("config/nsb/node.yaml")
        assert cfg.node_id == "nsb-node-01"
        assert cfg.allow_direct_lab is False

    def test_yaml_pi_carga(self):
        cfg = load_node_config("config/nsb/node.pi.yaml")
        assert cfg.actuator.type == "gpio"
        assert cfg.actuator.pinout_path

    def test_env_override_pisa_yaml(self, monkeypatch):
        monkeypatch.setenv("NSB_NODE_ID", "nodo-desde-env")
        monkeypatch.setenv("NSB_HIL__PORT", "9999")
        cfg = load_node_config("config/nsb/node.yaml")
        assert cfg.node_id == "nodo-desde-env"
        assert cfg.hil.port == 9999

    def test_gpio_sin_pinout_falla(self):
        with pytest.raises(ValueError, match="pinout_path"):
            NodeConfig(actuator={"type": "gpio"})

    def test_actuador_desconocido_falla(self):
        with pytest.raises(ValueError):
            NodeConfig(actuator={"type": "laser"})

    def test_campo_extra_falla(self):
        with pytest.raises(ValueError):
            NodeConfig(campo_que_no_existe=1)


class TestSafetyTimingConfig:
    def test_verde_fuera_de_limites_falla(self):
        with pytest.raises(ValueError, match="t_base_verde_ns"):
            SafetyTimingConfig(t_base_verde_ns=200.0)
        with pytest.raises(ValueError, match="t_base_verde_eo"):
            SafetyTimingConfig(t_base_verde_eo=5.0)

    def test_ambar_respeta_techo_de_clamp(self):
        # clamp_tiempos del núcleo recorta ámbar a <=6 s: una config de 8 s
        # produciría CLAMP permanente => se rechaza al arrancar.
        with pytest.raises(ValueError, match="t_ambar"):
            SafetyTimingConfig(t_ambar=8.0)
        with pytest.raises(ValueError, match="t_ambar"):
            SafetyTimingConfig(t_ambar=1.0)   # < mínimo obligatorio 3 s

    def test_todo_rojo_respeta_techo_de_clamp(self):
        with pytest.raises(ValueError, match="t_todo_rojo"):
            SafetyTimingConfig(t_todo_rojo=7.0)
        with pytest.raises(ValueError, match="t_todo_rojo"):
            SafetyTimingConfig(t_todo_rojo=0.5)

    def test_valores_canonicos_pasan(self):
        cfg = SafetyTimingConfig()   # 30/30/3/2 = CONFIG_SEGURA de la tesis
        assert cfg.t_ambar == 3.0


class TestGatewayConfig:
    def test_yaml_repo_carga(self):
        cfg = load_gateway_config("config/nsb/gateway.yaml")
        assert cfg.seed == 42
        assert cfg.timeout_policy is TimeoutPolicy.FALLBACK
        assert cfg.bind_host == "127.0.0.1"
        assert cfg.phase_map.ns_green_index != cfg.phase_map.eo_green_index

    def test_indices_de_fase_iguales_falla(self):
        with pytest.raises(ValueError, match="no pueden coincidir"):
            GatewayConfig(sumo_cfg="x.sumocfg",
                          phase_map={"tls_id": "t", "ns_green_index": 0,
                                     "eo_green_index": 0})

    def test_tick_mode_invalido_falla(self):
        with pytest.raises(ValueError):
            GatewayConfig(sumo_cfg="x.sumocfg", tick_mode="turbo",
                          phase_map={"tls_id": "t", "ns_green_index": 0,
                                     "eo_green_index": 2})

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("NSB_GW_SEED", "7")
        cfg = load_gateway_config("config/nsb/gateway.yaml")
        assert cfg.seed == 7
