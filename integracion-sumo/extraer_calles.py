"""
Extrae calles (edges) de la red SUMO y las convierte a formato GeoJSON
para visualización en el mapa web con Leaflet.
"""

import xml.etree.ElementTree as ET
import json
from pathlib import Path
import gzip


def extraer_calles_sumo(ruta_net_xml):
    """
    Extrae todas las calles (edges) de un archivo .net.xml de SUMO

    Args:
        ruta_net_xml: Ruta al archivo osm.net.xml o osm.net.xml.gz

    Returns:
        Dict con GeoJSON de las calles
    """
    print(f"Leyendo red SUMO: {ruta_net_xml}")

    # Leer archivo (puede estar comprimido)
    ruta = Path(ruta_net_xml)
    if ruta.suffix == '.gz':
        with gzip.open(ruta, 'rt', encoding='utf-8') as f:
            tree = ET.parse(f)
    else:
        tree = ET.parse(ruta)

    root = tree.getroot()

    # Extraer todas las calles (edges)
    calles = []
    edges_procesados = 0

    for edge in root.findall('edge'):
        edge_id = edge.get('id')

        # Filtrar edges internos (de junctions)
        if edge_id and edge_id.startswith(':'):
            continue

        # Obtener el lane principal (normalmente el primero)
        lane = edge.find('lane')
        if lane is None:
            continue

        # Obtener la forma (coordenadas) del lane
        shape = lane.get('shape')
        if not shape:
            continue

        # Convertir coordenadas de SUMO a lat/lon
        coords = []
        for punto in shape.split():
            try:
                x, y = punto.split(',')
                x, y = float(x), float(y)

                # En SUMO con OSM, las coordenadas ya están en lon,lat
                # pero en el formato x,y de SUMO
                # Para OSM: x=lon, y=lat (aproximado, puede necesitar conversión)
                coords.append([y, x])  # Leaflet usa [lat, lon]
            except:
                continue

        if len(coords) < 2:
            continue

        # Obtener información adicional
        longitud = float(lane.get('length', 0))
        velocidad_max = float(lane.get('speed', 13.89))  # m/s
        num_lanes = len(edge.findall('lane'))

        # Obtener nombre de la calle si está disponible
        nombre = edge.get('name', edge_id)

        calles.append({
            'id': edge_id,
            'nombre': nombre,
            'coords': coords,
            'longitud': round(longitud, 2),
            'velocidad_max': round(velocidad_max * 3.6, 1),  # Convertir a km/h
            'num_lanes': num_lanes
        })

        edges_procesados += 1

        # Limitar a las primeras 500 calles para no sobrecargar el mapa
        if edges_procesados >= 500:
            break

    print(f"[OK] Extraidas {len(calles)} calles de la red SUMO")

    return {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'id': calle['id'],
                'geometry': {
                    'type': 'LineString',
                    'coordinates': [[c[1], c[0]] for c in calle['coords']]  # [lon, lat] para GeoJSON
                },
                'properties': {
                    'id': calle['id'],
                    'nombre': calle['nombre'],
                    'longitud': calle['longitud'],
                    'velocidad_max': calle['velocidad_max'],
                    'num_lanes': calle['num_lanes']
                }
            }
            for calle in calles
        ]
    }


def guardar_geojson(geojson, ruta_salida):
    """Guarda el GeoJSON en un archivo"""
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    print(f"[OK] GeoJSON guardado en: {ruta_salida}")


if __name__ == "__main__":
    # Ruta al archivo de red SUMO
    ruta_net = Path(__file__).parent / 'escenarios' / 'lima-centro' / 'osm.net.xml'

    if not ruta_net.exists():
        # Intentar con la versión comprimida
        ruta_net = ruta_net.with_suffix('.xml.gz')
        if not ruta_net.exists():
            print(f"[ERROR] No se encontro el archivo de red SUMO")
            exit(1)

    # Extraer calles
    geojson = extraer_calles_sumo(ruta_net)

    # Guardar GeoJSON
    ruta_salida = Path(__file__).parent / 'escenarios' / 'lima-centro' / 'calles.geojson'
    guardar_geojson(geojson, ruta_salida)

    print(f"\n[OK] Proceso completado")
    print(f"  - Calles extraidas: {len(geojson['features'])}")
    print(f"  - Archivo generado: {ruta_salida}")
    print(f"\nAhora puedes usar este archivo en la interfaz web para visualizar las calles.")
