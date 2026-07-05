"""Genera el escenario SUMO mínimo de NSB: un cruce único NS/EO (D-12).

    python generar_escenario.py [--seed 42]

Produce (VERSIONAR los 4 en git — el digest del escenario forma parte del
experiment_id de las corridas HIL):

  nsb_cruz.net.xml   red: cruce de 4 brazos con TLS "nsb_cruz_tls"
  nsb_cruz.rou.xml   demanda determinista por flows (NS más cargado que EO)
  nsb_cruz.tls.xml   programa TLS EXPLÍCITO de 6 fases espejo de la FSM NSB:
                     0=NS verde, 1=NS ámbar, 2=todo-rojo,
                     3=EO verde, 4=EO ámbar, 5=todo-rojo
  nsb_cruz.sumocfg   configuración (sin rerouting; seed va por CLI)

Requiere SUMO instalado (netconvert en el PATH o SUMO_HOME).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent

NOD_XML = """<nodes>
    <node id="C" x="0" y="0" type="traffic_light" tl="nsb_cruz_tls"/>
    <node id="N" x="0" y="200"/>
    <node id="S" x="0" y="-200"/>
    <node id="E" x="200" y="0"/>
    <node id="O" x="-200" y="0"/>
</nodes>
"""

EDG_XML = """<edges>
    <edge id="NC" from="N" to="C" numLanes="1" speed="13.89"/>
    <edge id="CN" from="C" to="N" numLanes="1" speed="13.89"/>
    <edge id="SC" from="S" to="C" numLanes="1" speed="13.89"/>
    <edge id="CS" from="C" to="S" numLanes="1" speed="13.89"/>
    <edge id="EC" from="E" to="C" numLanes="1" speed="13.89"/>
    <edge id="CE" from="C" to="E" numLanes="1" speed="13.89"/>
    <edge id="OC" from="O" to="C" numLanes="1" speed="13.89"/>
    <edge id="CO" from="C" to="O" numLanes="1" speed="13.89"/>
</edges>
"""

# Demanda determinista: NS claramente más cargado que EO para que el control
# adaptativo tenga margen de mejora observable. Sin RNG propio: la inserción
# exacta la gobierna la seed de SUMO.
ROU_XML = """<routes>
    <vType id="auto" accel="2.6" decel="4.5" length="5" maxSpeed="13.89"/>

    <flow id="f_NS" type="auto" begin="0" end="3600" vehsPerHour="500"
          from="NC" to="CS" departPos="base"/>
    <flow id="f_SN" type="auto" begin="0" end="3600" vehsPerHour="450"
          from="SC" to="CN" departPos="base"/>
    <flow id="f_EO" type="auto" begin="0" end="3600" vehsPerHour="180"
          from="EC" to="CO" departPos="base"/>
    <flow id="f_OE" type="auto" begin="0" end="3600" vehsPerHour="150"
          from="OC" to="CE" departPos="base"/>
    <flow id="f_NE" type="auto" begin="0" end="3600" vehsPerHour="80"
          from="NC" to="CE" departPos="base"/>
    <flow id="f_SO" type="auto" begin="0" end="3600" vehsPerHour="70"
          from="SC" to="CO" departPos="base"/>
</routes>
"""

SUMOCFG = """<configuration>
    <input>
        <net-file value="nsb_cruz.net.xml"/>
        <route-files value="nsb_cruz.rou.xml"/>
        <additional-files value="nsb_cruz.tls.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <step-length value="1"/>
    </time>
    <processing>
        <time-to-teleport value="300"/>
    </processing>
    <report>
        <no-warnings value="true"/>
        <duration-log.disable value="true"/>
        <no-step-log value="true"/>
    </report>
</configuration>
"""


def _netconvert() -> str:
    """Localiza netconvert (PATH o SUMO_HOME)."""
    from shutil import which
    exe = which("netconvert")
    if exe:
        return exe
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        cand = Path(sumo_home) / "bin" / (
            "netconvert.exe" if os.name == "nt" else "netconvert")
        if cand.exists():
            return str(cand)
    raise FileNotFoundError(
        "netconvert no encontrado (¿SUMO instalado y SUMO_HOME definido?)")


def generar_red() -> Path:
    nod = AQUI / "nsb_cruz.nod.xml"
    edg = AQUI / "nsb_cruz.edg.xml"
    net = AQUI / "nsb_cruz.net.xml"
    nod.write_text(NOD_XML, encoding="utf-8")
    edg.write_text(EDG_XML, encoding="utf-8")
    subprocess.run(
        [_netconvert(), "--node-files", str(nod), "--edge-files", str(edg),
         "--output-file", str(net), "--no-turnarounds", "true"],
        check=True, capture_output=True, text=True)
    return net


def generar_programa_tls(net_path: Path) -> Path:
    """Programa TLS explícito de 6 fases, espejo de la FSM del nodo.

    El orden de los links del TLS lo decide netconvert: se lee con sumolib
    y se construye el estado por link según el edge de ORIGEN (N/S → grupo
    NS; E/O → grupo EO). Nada se asume a mano.
    """
    import sumolib

    net = sumolib.net.readNet(str(net_path))
    tls = net.getTLS("nsb_cruz_tls")
    conexiones = tls.getConnections()   # [(inLane, outLane, linkIndex)]
    n_links = len(conexiones)

    grupo_por_indice = {}
    for in_lane, _out_lane, idx in conexiones:
        origen = in_lane.getEdge().getID()
        grupo_por_indice[idx] = "NS" if origen in ("NC", "SC") else "EO"

    def estado(verde: str | None, ambar: str | None) -> str:
        chars = []
        for i in range(n_links):
            g = grupo_por_indice[i]
            if verde == g:
                chars.append("G")
            elif ambar == g:
                chars.append("y")
            else:
                chars.append("r")
        return "".join(chars)

    fases = [
        (30, estado("NS", None)),   # 0: NS verde
        (3,  estado(None, "NS")),   # 1: NS ámbar
        (2,  estado(None, None)),   # 2: todo-rojo
        (30, estado("EO", None)),   # 3: EO verde
        (3,  estado(None, "EO")),   # 4: EO ámbar
        (2,  estado(None, None)),   # 5: todo-rojo
    ]
    lineas = ['<additional>',
              '    <tlLogic id="nsb_cruz_tls" type="static" '
              'programID="nsb" offset="0">']
    for dur, st in fases:
        lineas.append(f'        <phase duration="{dur}" state="{st}"/>')
    lineas += ['    </tlLogic>', '</additional>', '']
    out = AQUI / "nsb_cruz.tls.xml"
    out.write_text("\n".join(lineas), encoding="utf-8")
    return out


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_known_args()
    net = generar_red()
    tls = generar_programa_tls(net)
    (AQUI / "nsb_cruz.rou.xml").write_text(ROU_XML, encoding="utf-8")
    (AQUI / "nsb_cruz.sumocfg").write_text(SUMOCFG, encoding="utf-8")
    print(f"escenario generado en {AQUI}")
    print(f"  red      : {net.name}")
    print(f"  tls      : {tls.name} (6 fases: 0=NSverde 1=NSambar "
          f"2=rojo 3=EOverde 4=EOambar 5=rojo)")
    print("  demanda  : nsb_cruz.rou.xml (flows deterministas)")
    print("  config   : nsb_cruz.sumocfg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
