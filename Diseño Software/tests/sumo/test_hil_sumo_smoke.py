"""Smoke test HIL con SUMO REAL (marker sumo): gateway + nodo en el mismo
proceso (hilos separados; traci solo en el hilo del gateway).

Verifica: seq contiguo, veredictos aplicados, cero violaciones de seguridad
y cierre limpio con bye.
"""
import os
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.sumo


def _sumo_disponible() -> bool:
    if not os.environ.get("SUMO_HOME"):
        return False
    try:
        import traci  # noqa: F401
        return True
    except ImportError:
        return False


ESCENARIO = (Path(__file__).resolve().parents[2] / "integracion-sumo" /
             "escenarios" / "nsb-cruz" / "nsb_cruz.sumocfg")


@pytest.mark.skipif(not _sumo_disponible(),
                    reason="SUMO/traci no disponible (SUMO_HOME sin definir)")
@pytest.mark.skipif(not ESCENARIO.exists(),
                    reason="escenario nsb-cruz no generado "
                           "(python generar_escenario.py)")
def test_hil_sumo_ciclo_completo(tmp_path):
    from nsb.config import GatewayConfig, NodeConfig
    from nsb.domain.enums import Mode, SourceKind
    from nsb.hil.gateway import HilGateway
    from nsb.hil.node_client import HilNodeClient
    from nsb.node import NsbNode

    puntos = 6   # 6 × 25 s = 150 s de simulación (smoke rápido)
    gw_cfg = GatewayConfig(
        sumo_cfg=str(ESCENARIO), seed=42,
        control_interval_s=25.0, max_control_points=puntos,
        phase_map={"tls_id": "nsb_cruz_tls", "ns_green_index": 0,
                   "eo_green_index": 3},
        bind_host="127.0.0.1", bind_port=0 or 19533,
        node_timeout_s=10.0,
        record_jsonl=str(tmp_path / "hil.jsonl"))
    gateway = HilGateway(gw_cfg)

    resultado = {}

    def correr_gateway():
        resultado["summary"] = gateway.run()

    hilo_gw = threading.Thread(target=correr_gateway, daemon=True)
    hilo_gw.start()

    node_cfg = NodeConfig(
        mode=Mode.TSC_EMULATED, source=SourceKind.SUMO_HIL,
        telemetry={"jsonl_dir": str(tmp_path / "t")},
        hil={"host": "127.0.0.1", "port": 19533,
             "connect_timeout_s": 5.0, "read_timeout_s": 60.0})
    node = NsbNode.from_config(node_cfg, experiment_id="smoke")
    client_summary = HilNodeClient(node, node_cfg.hil,
                                   node_cfg.node_id).run()
    hilo_gw.join(timeout=120.0)
    node.shutdown()

    assert not hilo_gw.is_alive(), "el gateway no terminó"
    s = resultado["summary"]
    assert s.puntos_control == puntos
    assert s.timeouts == 0
    assert s.decisiones_aplicadas == puntos
    assert client_summary.estados == puntos
    assert client_summary.terminado_por_bye

    # seq contiguo y sin violaciones en la grabación
    from nsb.sources.replay import ReplayStateSource, leer_decisiones
    seqs = [st.seq for st in ReplayStateSource(tmp_path / "hil.jsonl")]
    assert seqs == list(range(puntos))
    decisiones = list(leer_decisiones(tmp_path / "hil.jsonl"))
    assert all(d.verdict.value in ("accept", "clamp") for d in decisiones)
    assert all(not d.safe_mode for d in decisiones)
