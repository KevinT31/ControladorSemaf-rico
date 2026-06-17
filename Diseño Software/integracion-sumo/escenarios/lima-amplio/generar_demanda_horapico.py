"""
Genera ficheros de pesos para randomTrips que concentran la demanda en los
CORREDORES REALES más congestionados de Lima en hora punta (tarde 18:00-20:00):
Javier Prado, Av. Arequipa, Angamos, Benavides, Salaverry, Canaval y Moreyra.

Fuente del patrón: reportes de tráfico de Lima (El Comercio / Infobae / La
República): Javier Prado pasa de ~17 a ~65 min en hora punta; picos 7-8:30 y
18:30-20:00. Modelamos el pico vespertino como flujo intenso de paso por esas
arterias (origen/destino ponderado hacia ellas -> SUMO rutea a lo largo).

Salida: <prefix>.src.xml y <prefix>.dst.xml para `randomTrips --weights-prefix`.
"""
import sys
from pathlib import Path

import sumolib

AQUI = Path(__file__).parent
NET = AQUI / 'lima_amplio.net.xml'

# Corredores congestionados (subcadena de nombre) y su peso relativo
CORREDORES = {
    'Javier Prado': 25.0,
    'Arequipa': 18.0,
    'Angamos': 14.0,
    'Benavides': 12.0,
    'Salaverry': 10.0,
    'Canaval': 10.0,
    'Aramburu': 8.0,
}
PESO_BASE = 1.0          # resto de calles
FIN = 3600


def peso_edge(nombre: str) -> float:
    if not nombre:
        return PESO_BASE
    n = nombre.lower()
    for clave, w in CORREDORES.items():
        if clave.lower() in n:
            return w
    return PESO_BASE


def escribir_pesos(ruta: Path, edges):
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('<edgedata>\n')
        f.write(f'    <interval begin="0" end="{FIN}">\n')
        for e in edges:
            if e.getID().startswith(':'):
                continue
            f.write(f'        <edge id="{e.getID()}" value="{peso_edge(e.getName())}"/>\n')
        f.write('    </interval>\n')
        f.write('</edgedata>\n')


def main():
    prefijo = sys.argv[1] if len(sys.argv) > 1 else 'horapico'
    net = sumolib.net.readNet(str(NET))
    edges = net.getEdges()
    src = AQUI / f'{prefijo}.src.xml'
    dst = AQUI / f'{prefijo}.dst.xml'
    escribir_pesos(src, edges)
    escribir_pesos(dst, edges)
    n_corr = sum(1 for e in edges if peso_edge(e.getName()) > PESO_BASE)
    print(f'Pesos escritos: {src.name}, {dst.name}')
    print(f'Edges en corredores priorizados: {n_corr} / {len(edges)}')


if __name__ == '__main__':
    main()
