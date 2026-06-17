"""
Routing de emergencia CONSCIENTE DE LA CONGESTIÓN sobre la red real de SUMO.

Idea (separación de capas):
- El tráfico (congestión por calle) es una capa GLOBAL e independiente.
- La ruta de un vehículo de emergencia se DERIVA de ese tráfico: elige el
  camino más rápido dada la congestión actual y coordina (ola verde) los
  semáforos que quedan en ese camino.

Implementación: se ajustan los tiempos de viaje de los edges con tráfico
(`adaptTraveltime`) según la velocidad real medida, y luego `findRoute` calcula
la mejor ruta evitando la congestión. Todo con libsumo (la red ya está cargada
en el proceso; no se recarga con sumolib para no duplicar memoria).
"""
import logging
from .estado_global import estado_sistema
from .sumo_service import _get_traci

logger = logging.getLogger(__name__)

# Caches construidos una vez por conexión (la topología no cambia en una corrida)
_cache = {
    'key': None,
    'edge_xy': {},      # edge_id -> (x, y) punto medio (para "edge más cercano")
    'lane_tls': {},     # lane_id -> tls_id (para detectar controladores en ruta)
}


def _clave_conexion(conector):
    return id(conector)


def _construir_indices(traci, conector):
    """Construye, una sola vez, los índices de geometría y semáforos."""
    if _cache['key'] == _clave_conexion(conector) and _cache['edge_xy']:
        return

    edge_xy = {}
    for lane in traci.lane.getIDList():
        if lane.startswith(':'):
            continue
        try:
            edge = traci.lane.getEdgeID(lane)
            if edge in edge_xy:
                continue
            shape = traci.lane.getShape(lane)
            if shape:
                edge_xy[edge] = shape[len(shape) // 2]  # punto medio
        except Exception:
            continue

    lane_tls = {}
    for tls in traci.trafficlight.getIDList():
        try:
            for lane in traci.trafficlight.getControlledLanes(tls):
                lane_tls[lane] = tls
        except Exception:
            continue

    _cache['key'] = _clave_conexion(conector)
    _cache['edge_xy'] = edge_xy
    _cache['lane_tls'] = lane_tls
    logger.info(f"Índices ruta-emergencia: {len(edge_xy)} edges, {len(lane_tls)} lanes con TLS")


def _edge_mas_cercano(traci, lon, lat):
    """Edge cuyo punto medio está más cerca del (lon, lat) dado."""
    try:
        x, y = traci.simulation.convertGeo(lon, lat, fromGeo=True)
    except Exception:
        return None
    mejor, best = None, 1e30
    for eid, (ex, ey) in _cache['edge_xy'].items():
        d = (ex - x) ** 2 + (ey - y) ** 2
        if d < best:
            best, mejor = d, eid
    return mejor


def _ajustar_tiempos_por_congestion(traci):
    """Sube el tiempo de viaje de los edges con tráfico según su velocidad real,
    para que findRoute prefiera caminos despejados (congestion-aware)."""
    activos = set()
    try:
        for vid in traci.vehicle.getIDList():
            eid = traci.vehicle.getRoadID(vid)
            if eid and not eid.startswith(':'):
                activos.add(eid)
    except Exception:
        return 0
    ajustados = 0
    for eid in activos:
        try:
            v = traci.edge.getLastStepMeanSpeed(eid)       # m/s
            longitud = traci.lane.getLength(eid + '_0')
            tt = longitud / max(v, 0.3)                     # s (alto si v baja)
            traci.edge.adaptTraveltime(eid, tt)
            ajustados += 1
        except Exception:
            continue
    return ajustados


def calcular_ruta_emergencia(origen_lonlat, destino_lonlat):
    """Calcula la ruta de emergencia congestion-aware.

    Args:
        origen_lonlat, destino_lonlat: tuplas (lon, lat).

    Returns:
        dict con geometry [[lon,lat]...] siguiendo calles, semaforos (TLS en la
        ruta), edges, distancia (m) y tiempo (s), o None.
    """
    conector = getattr(estado_sistema, 'conector_sumo', None)
    if not conector or not getattr(conector, 'conectado', False):
        return None
    traci = _get_traci()
    _construir_indices(traci, conector)

    o = _edge_mas_cercano(traci, *origen_lonlat)
    d = _edge_mas_cercano(traci, *destino_lonlat)
    if not o or not d:
        return None

    _ajustar_tiempos_por_congestion(traci)

    try:
        ruta = traci.simulation.findRoute(o, d)
    except Exception as e:
        logger.warning(f"findRoute falló: {e}")
        return None

    edges = [e for e in getattr(ruta, 'edges', []) if not e.startswith(':')]
    if not edges:
        return None

    # Geometría en lon/lat siguiendo las calles
    coords = []
    for eid in edges:
        try:
            shape = traci.lane.getShape(eid + '_0')
            for x, y in shape:
                lon, lat = traci.simulation.convertGeo(x, y)
                coords.append([round(lon, 6), round(lat, 6)])
        except Exception:
            continue

    # Semáforos (controladores) que quedan en la ruta -> ola verde, con su
    # posición geográfica para marcarlos en el mapa.
    semaforos = []
    vistos_tls = set()
    for eid in edges:
        try:
            tls = _cache['lane_tls'].get(eid + '_0')
            if not tls or tls in vistos_tls:
                continue
            vistos_tls.add(tls)
            lon = lat = None
            try:
                x, y = traci.junction.getPosition(tls)
                lon, lat = traci.simulation.convertGeo(x, y)
            except Exception:
                pass
            semaforos.append({'id': tls, 'lon': lon, 'lat': lat})
        except Exception:
            continue

    return {
        'edges': edges,
        'geometry': coords,
        'semaforos': semaforos,
        'num_semaforos': len(semaforos),
        'distancia_m': round(getattr(ruta, 'length', 0.0), 1),
        'tiempo_s': round(getattr(ruta, 'travelTime', 0.0), 1),
        'fuente': 'sumo_congestion_aware'
    }
