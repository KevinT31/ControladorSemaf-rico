#!/usr/bin/env python3
"""
Script para descargar librerías JavaScript localmente
Evita problemas con CDNs bloqueados por navegadores
"""

import urllib.request
import ssl
import os
import sys
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Deshabilitar verificación SSL solo para descarga
ssl._create_default_https_context = ssl._create_unverified_context

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

for url, destino in archivos:
    try:
        print(f"Descargando: {destino.name}...", end=' ')

        # Crear request con User-Agent
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )

        with urllib.request.urlopen(req) as response:
            data = response.read()
            with open(destino, 'wb') as f:
                f.write(data)

        # Verificar que el archivo no sea HTML
        with open(destino, 'rb') as f:
            contenido = f.read(100)
            if b'<!DOCTYPE html>' in contenido or b'<html' in contenido:
                print("ERROR: Recibido HTML en lugar del archivo")
                os.remove(destino)
            else:
                tamaño = os.path.getsize(destino)
                print(f"OK ({tamaño:,} bytes)")
    except Exception as e:
        print(f"ERROR: {e}")

print()
print("✓ Descarga completada")
print()
print("Ahora puedes abrir la interfaz en http://localhost:8000")
