#!/usr/bin/env python3
"""
Script para descargar librerías JavaScript localmente usando requests
"""

import sys
import os
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util import Retry
except ImportError:
    print("ERROR: Instala requests con: pip install requests")
    sys.exit(1)

# Configurar sesión con reintentos
session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Headers
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*'
})

# Definir rutas
BASE_DIR = Path(__file__).parent.parent / 'interfaz-web' / 'libs'

# Crear directorios
(BASE_DIR / 'leaflet' / 'images').mkdir(parents=True, exist_ok=True)
(BASE_DIR / 'chart').mkdir(parents=True, exist_ok=True)
(BASE_DIR / 'fontawesome' / 'webfonts').mkdir(parents=True, exist_ok=True)
(BASE_DIR / 'particles').mkdir(parents=True, exist_ok=True)

# URLs de descarga
archivos = [
    # Leaflet
    ('https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js',
     BASE_DIR / 'leaflet' / 'leaflet.js'),
    ('https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css',
     BASE_DIR / 'leaflet' / 'leaflet.css'),
    ('https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-icon.png',
     BASE_DIR / 'leaflet' / 'images' / 'marker-icon.png'),
    ('https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-icon-2x.png',
     BASE_DIR / 'leaflet' / 'images' / 'marker-icon-2x.png'),
    ('https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-shadow.png',
     BASE_DIR / 'leaflet' / 'images' / 'marker-shadow.png'),
    ('https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/layers.png',
     BASE_DIR / 'leaflet' / 'images' / 'layers.png'),
    ('https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/layers-2x.png',
     BASE_DIR / 'leaflet' / 'images' / 'layers-2x.png'),

    # Chart.js
    ('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js',
     BASE_DIR / 'chart' / 'chart.umd.min.js'),

    # Particles.js
    ('https://cdn.jsdelivr.net/npm/particles.js@2.0.0/particles.min.js',
     BASE_DIR / 'particles' / 'particles.min.js'),

    # Font Awesome
    ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
     BASE_DIR / 'fontawesome' / 'all.min.css'),
    ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2',
     BASE_DIR / 'fontawesome' / 'webfonts' / 'fa-solid-900.woff2'),
    ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2',
     BASE_DIR / 'fontawesome' / 'webfonts' / 'fa-regular-400.woff2'),
    ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2',
     BASE_DIR / 'fontawesome' / 'webfonts' / 'fa-brands-400.woff2'),
]

print("Descargando librerías JavaScript localmente...")
print(f"Directorio base: {BASE_DIR}")
print()

exitosos = 0
fallidos = 0

for url, destino in archivos:
    try:
        print(f"Descargando: {destino.name}...", end=' ', flush=True)

        response = session.get(url, timeout=30, verify=False)
        response.raise_for_status()

        with open(destino, 'wb') as f:
            f.write(response.content)

        # Verificar que el archivo no sea HTML
        with open(destino, 'rb') as f:
            contenido = f.read(200)
            if b'<!DOCTYPE html>' in contenido or b'<html' in contenido:
                print("ERROR: Recibido HTML")
                os.remove(destino)
                fallidos += 1
            else:
                tamaño = len(response.content)
                print(f"OK ({tamaño:,} bytes)")
                exitosos += 1
    except Exception as e:
        print(f"ERROR: {e}")
        fallidos += 1

print()
print(f"Descarga completada: {exitosos} exitosos, {fallidos} fallidos")
print()

if exitosos > 0:
    print("Ahora recarga la página (Ctrl+F5) en http://localhost:8000")
else:
    print("NOTA: Si las descargas fallan por firewall/proxy,")
    print("      desactiva temporalmente Tracking Prevention en tu navegador")
    print("      o usa otro navegador (Chrome/Firefox)")
