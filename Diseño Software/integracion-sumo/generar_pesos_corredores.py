"""
Genera ficheros de pesos para randomTrips concentrando la demanda en corredores
reales (avenidas). Genérico por escenario.

Uso: python generar_pesos_corredores.py <escenario> <net_file> <prefijo>
"""
import sys
from pathlib import Path
import sumolib

# Corredor (subcadena de nombre) -> peso relativo
CORREDORES = {
    'Javier Prado': 25.0, 'Arequipa': 18.0, 'Universitaria': 18.0,
    'La Marina': 16.0, 'Faucett': 14.0, 'Angamos': 14.0, 'Benavides': 12.0,
    'Brasil': 12.0, 'Venezuela': 12.0, 'Salaverry': 10.0, 'Riva': 8.0,
    'Canaval': 8.0, 'Aramburu': 8.0,
}
PESO_BASE = 1.0
FIN = 3600


def peso(nombre):
    if not nombre:
        return PESO_BASE
    n = nombre.lower()
    for k, w in CORREDORES.items():
        if k.lower() in n:
            return w
    return PESO_BASE


def escribir(ruta, edges):
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('<edgedata>\n')
        f.write(f'    <interval begin="0" end="{FIN}">\n')
        for e in edges:
            if e.getID().startswith(':'):
                continue
            f.write(f'        <edge id="{e.getID()}" value="{peso(e.getName())}"/>\n')
        f.write('    </interval>\n')
        f.write('</edgedata>\n')


def main():
    esc_dir = Path(sys.argv[1])
    net_file = Path(sys.argv[2])
    prefijo = sys.argv[3]
    net = sumolib.net.readNet(str(net_file))
    edges = net.getEdges()
    escribir(esc_dir / f'{prefijo}.src.xml', edges)
    escribir(esc_dir / f'{prefijo}.dst.xml', edges)
    n_corr = sum(1 for e in edges if peso(e.getName()) > PESO_BASE)
    print(f'Pesos escritos en {esc_dir} ({prefijo}). Edges en corredores: {n_corr}/{len(edges)}')


if __name__ == '__main__':
    main()
