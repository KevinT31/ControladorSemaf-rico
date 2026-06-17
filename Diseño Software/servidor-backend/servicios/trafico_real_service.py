"""
Tráfico REAL del mundo (HERE Traffic API v7) como capa independiente del
tráfico simulado de SUMO. Permite comparar/validar la simulación contra el
estado real de las avenidas de Lima.

La API key se lee (en este orden):
  1. variable de entorno HERE_API_KEY
  2. archivo servidor-backend/here_api_key.txt

Endpoint que la usa: /api/trafico-real  (definido en rutas/trafico_real.py)
"""
import os
import json
import logging
import urllib.request
import urllib.parse
from pathlib import Path

logger = logging.getLogger(__name__)

# bbox por defecto = área del escenario metropolitano (oeste→este, sur→norte)
BBOX_DEFECTO = (-77.105, -12.130, -77.000, -12.030)  # (west, south, east, north)

_HERE_FLOW_URL = "https://data.traffic.hereapi.com/v7/flow"


def _leer_api_key():
    key = os.environ.get('HERE_API_KEY')
    if key and key.strip():
        return key.strip()
    archivo = Path(__file__).parent.parent / 'here_api_key.txt'
    if archivo.exists():
        txt = archivo.read_text(encoding='utf-8').strip()
        if txt and 'PEGA_AQUI' not in txt:
            return txt
    return None


def _color_por_jam(jam):
    """jamFactor HERE: 0=fluido ... 10=bloqueado -> verde/amarillo/rojo."""
    if jam is None:
        return '#94a3b8'
    if jam < 4:
        return '#10b981'   # verde
    if jam < 8:
        return '#f59e0b'   # amarillo
    return '#ef4444'       # rojo


def obtener_trafico_real(bbox=None) -> dict:
    """Consulta HERE y devuelve segmentos con geometría y color.

    Returns: {'disponible': bool, 'segmentos': [{coords:[[lat,lon]...], jam, color, velocidad}], 'mensaje':...}
    """
    key = _leer_api_key()
    if not key:
        return {'disponible': False, 'segmentos': [],
                'mensaje': 'Falta API key de HERE (env HERE_API_KEY o here_api_key.txt)'}

    w, s, e, n = bbox or BBOX_DEFECTO
    params = {
        'in': f'bbox:{w},{s},{e},{n}',
        'locationReferencing': 'shape',
        'apiKey': key,
    }
    url = f"{_HERE_FLOW_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as ex:
        detalle = ''
        try:
            detalle = ex.read().decode('utf-8')[:200]
        except Exception:
            pass
        logger.error(f"HERE HTTP {ex.code}: {detalle}")
        return {'disponible': False, 'segmentos': [],
                'mensaje': f'HERE respondió {ex.code}. Revisa la API key o el área. {detalle}'}
    except Exception as ex:
        logger.error(f"Error consultando HERE: {ex}")
        return {'disponible': False, 'segmentos': [], 'mensaje': f'Error consultando HERE: {ex}'}

    segmentos = []
    for r in data.get('results', []):
        cf = r.get('currentFlow', {}) or {}
        jam = cf.get('jamFactor')
        vel_ms = cf.get('speed')  # HERE entrega la velocidad en m/s
        vel = round(vel_ms * 3.6, 1) if isinstance(vel_ms, (int, float)) else None  # -> km/h
        shape = (r.get('location', {}) or {}).get('shape', {}) or {}
        coords = []
        for link in shape.get('links', []) or []:
            for p in link.get('points', []) or []:
                lat, lng = p.get('lat'), p.get('lng')
                if lat is not None and lng is not None:
                    coords.append([lat, lng])
        if len(coords) < 2:
            continue
        segmentos.append({
            'coords': coords,
            'jam': jam,
            'velocidad': vel,
            'color': _color_por_jam(jam),
        })

    return {
        'disponible': True,
        'segmentos': segmentos,
        'num_segmentos': len(segmentos),
        'fuente': 'here_v7',
    }
