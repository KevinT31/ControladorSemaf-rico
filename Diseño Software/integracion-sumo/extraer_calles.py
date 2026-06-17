"""
Extrae las calles (edges) de una red SUMO y las exporta a GeoJSON en
coordenadas geográficas REALES (lon/lat WGS84) para Leaflet.

CLAVE: el `shape` de un .net.xml está en METROS proyectados (no lon/lat).
Usamos sumolib + la geo-proyección de la red (requiere pyproj) para convertir
cada punto a lon/lat con `net.convertXY2LonLat`. Además los IDs exportados son
los de la red ACTUAL, por lo que casan con la congestión que envía SUMO por
TraCI/libsumo (así el coloreado del mapa funciona).

Uso:
    python extraer_calles.py [lima-centro|lima-amplio] [limite]
"""
import json
import sys
from pathlib import Path

import sumolib

AQUI = Path(__file__).parent

# Archivo de red por escenario
NET_POR_ESCENARIO = {
    'lima-centro': 'lima_centro.net.xml',
    'lima-amplio': 'lima_amplio.net.xml',
    'lima-metropolitano': 'lima_metro.net.xml',
}


# Corredores prioritarios (subcadena de nombre): se incluyen primero en el
# GeoJSON para garantizar que las avenidas con tráfico se coloreen aunque la
# red sea enorme y haya que recortar por rendimiento de Leaflet.
_CORREDORES_PRIORITARIOS = [
    'javier prado', 'arequipa', 'universitaria', 'la marina', 'faucett',
    'angamos', 'benavides', 'brasil', 'venezuela', 'salaverry', 'riva',
    'canaval', 'aramburu', 'tacna', 'abancay', 'colonial', 'argentina',
    'wilson', 'garcilaso', 'grau', 'paseo', 'expresa', 'panamericana',
]


def _es_prioritario(nombre: str) -> bool:
    if not nombre:
        return False
    n = nombre.lower()
    return any(c in n for c in _CORREDORES_PRIORITARIOS)


def extraer(escenario: str, limite: int = 3000) -> dict:
    esc_dir = AQUI / 'escenarios' / escenario
    net_file = esc_dir / NET_POR_ESCENARIO[escenario]
    if not net_file.exists():
        raise FileNotFoundError(f"No existe la red: {net_file}")

    print(f"Leyendo red: {net_file}")
    net = sumolib.net.readNet(str(net_file))

    # Ordenar: primero corredores prioritarios (avenidas), luego el resto
    todos = [e for e in net.getEdges() if not e.getID().startswith(':')]
    todos.sort(key=lambda e: 0 if _es_prioritario(e.getName()) else 1)

    features = []
    for edge in todos:
        shape = edge.getShape()  # lista de (x, y) en metros
        if not shape or len(shape) < 2:
            continue
        # Convertir cada punto a lon/lat real
        coords = []
        for x, y in shape:
            lon, lat = net.convertXY2LonLat(x, y)
            coords.append([round(lon, 6), round(lat, 6)])

        try:
            vmax_kmh = round(edge.getSpeed() * 3.6, 1)
        except Exception:
            vmax_kmh = 50.0

        features.append({
            'type': 'Feature',
            'id': edge.getID(),
            'geometry': {'type': 'LineString', 'coordinates': coords},
            'properties': {
                'id': edge.getID(),
                'nombre': edge.getName() or edge.getID(),
                'longitud': round(edge.getLength(), 2),
                'velocidad_max': vmax_kmh,
                'num_lanes': edge.getLaneNumber(),
            },
        })
        if len(features) >= limite:
            break

    print(f"[OK] {len(features)} calles exportadas (lon/lat reales)")
    return {'type': 'FeatureCollection', 'features': features}


def main():
    escenario = sys.argv[1] if len(sys.argv) > 1 else 'lima-centro'
    limite = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    if escenario not in NET_POR_ESCENARIO:
        print(f"Escenario inválido. Use uno de: {list(NET_POR_ESCENARIO)}")
        sys.exit(1)

    geojson = extraer(escenario, limite)
    salida = AQUI / 'escenarios' / escenario / 'calles.geojson'
    with open(salida, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"[OK] Guardado: {salida}")


if __name__ == '__main__':
    main()
