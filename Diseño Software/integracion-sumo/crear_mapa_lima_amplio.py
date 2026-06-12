"""
Script para crear un mapa más amplio de Lima usando SUMO y OpenStreetMap

Este script descarga y procesa un área más grande de Lima Centro,
incluyendo distritos como Miraflores, San Isidro, Lince, Jesus Maria, etc.
"""

import subprocess
import sys
from pathlib import Path
import os


def verificar_sumo():
    """Verifica que SUMO esté instalado"""
    try:
        result = subprocess.run(
            ['sumo', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"✓ SUMO encontrado: {result.stdout.split()[3]}")
        return True
    except Exception as e:
        print(f"❌ SUMO no encontrado. Instala desde: https://sumo.dlr.de/docs/Downloads.php")
        print(f"   Error: {e}")
        return False


def descargar_mapa_osm(bbox, output_file):
    """
    Descarga mapa de OpenStreetMap usando bbox (bounding box)
    
    Args:
        bbox: Tupla (min_lon, min_lat, max_lon, max_lat)
        output_file: Ruta donde guardar el archivo OSM
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    
    # URL de API de Overpass (OpenStreetMap)
    overpass_url = "https://overpass-api.de/api/map"
    bbox_str = f"?bbox={min_lon},{min_lat},{max_lon},{max_lat}"
    
    print(f"\n📥 Descargando mapa de Lima desde OpenStreetMap...")
    print(f"   Área: {bbox}")
    print(f"   URL: {overpass_url}{bbox_str}")
    
    try:
        import urllib.request
        
        # Descargar
        urllib.request.urlretrieve(
            overpass_url + bbox_str,
            output_file
        )
        
        # Verificar tamaño
        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"✓ Mapa descargado: {output_file} ({size_mb:.2f} MB)")
        return True
        
    except Exception as e:
        print(f"❌ Error descargando: {e}")
        print("\n💡 ALTERNATIVA:")
        print("   1. Ir a: https://www.openstreetmap.org/export")
        print("   2. Seleccionar área de Lima manualmente")
        print("   3. Hacer clic en 'Export'")
        print(f"   4. Guardar como: {output_file}")
        return False


def convertir_osm_a_sumo(osm_file, net_file):
    """
    Convierte archivo OSM a red SUMO (.net.xml)
    
    Args:
        osm_file: Archivo .osm de entrada
        net_file: Archivo .net.xml de salida
    """
    print(f"\n🔧 Convirtiendo OSM a red SUMO...")
    
    try:
        cmd = [
            'netconvert',
            '--osm-files', str(osm_file),
            '--output-file', str(net_file),
            '--geometry.remove',              # Simplificar geometría
            '--ramps.guess',                  # Detectar rampas
            '--junctions.join',               # Unir intersecciones cercanas
            '--tls.guess-signals',            # Detectar semáforos automáticamente
            '--tls.default-type', 'actuated', # Semáforos actuados
            '--remove-edges.isolated',        # Remover edges aislados
            '--keep-edges.by-vclass', 'passenger',  # Solo vías para autos
            '--remove-edges.by-type', 'highway.footway,highway.path,highway.cycleway',
            '--verbose'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            size_mb = os.path.getsize(net_file) / (1024 * 1024)
            print(f"✓ Red SUMO creada: {net_file} ({size_mb:.2f} MB)")
            
            # Contar semáforos
            import xml.etree.ElementTree as ET
            tree = ET.parse(net_file)
            root = tree.getroot()
            num_tls = len(root.findall('tlLogic'))
            print(f"✓ Semáforos detectados: {num_tls}")
            
            return True
        else:
            print(f"❌ Error en netconvert:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def generar_trafico(net_file, route_file, num_vehiculos=1000, tiempo_sim=3600):
    """
    Genera tráfico aleatorio
    
    Args:
        net_file: Archivo de red .net.xml
        route_file: Archivo de rutas de salida .rou.xml
        num_vehiculos: Número de vehículos a generar
        tiempo_sim: Tiempo de simulación en segundos
    """
    print(f"\n🚗 Generando tráfico ({num_vehiculos} vehículos)...")
    
    try:
        # Calcular período de inserción
        periodo = max(1, tiempo_sim / num_vehiculos)
        
        cmd = [
            'python',
            '-c',
            f'''
import sys
sys.path.append(r"{os.environ.get('SUMO_HOME', 'C:/Program Files/Eclipse/Sumo')}/tools")
from randomTrips import main
sys.argv = [
    "randomTrips.py",
    "-n", r"{net_file}",
    "-o", r"{route_file}",
    "-e", "{tiempo_sim}",
    "-p", "{periodo:.2f}",
    "--fringe-factor", "5",
    "--trip-attributes", 'departLane="best" departSpeed="max"'
]
main()
'''
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 or os.path.exists(route_file):
            print(f"✓ Tráfico generado: {route_file}")
            return True
        else:
            print(f"❌ Error generando tráfico:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def crear_configuracion_sumo(net_file, route_file, config_file):
    """
    Crea archivo de configuración .sumocfg
    
    Args:
        net_file: Archivo de red
        route_file: Archivo de rutas
        config_file: Archivo de configuración de salida
    """
    print(f"\n📝 Creando configuración SUMO...")
    
    config_xml = f'''<?xml version="1.0" encoding="UTF-8"?>

<sumoConfiguration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                   xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">

    <input>
        <net-file value="{net_file.name}"/>
        <route-files value="{route_file.name}"/>
    </input>

    <time>
        <begin value="0"/>
        <end value="3600"/>
        <step-length value="1.0"/>
    </time>

    <processing>
        <time-to-teleport value="-1"/>
        <ignore-route-errors value="true"/>
        <tls.actuated.jam-threshold value="30"/>
    </processing>

    <routing>
        <device.rerouting.adaptation-steps value="18"/>
        <device.rerouting.adaptation-interval value="10"/>
    </routing>

    <report>
        <verbose value="true"/>
        <duration-log.statistics value="true"/>
        <no-step-log value="true"/>
    </report>

    <gui_only>
        <gui-settings-file value="view.xml"/>
        <start value="true"/>
        <quit-on-end value="false"/>
    </gui_only>

</sumoConfiguration>
'''
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_xml)
    
    print(f"✓ Configuración creada: {config_file}")


def crear_vista_gui(view_file):
    """Crea archivo de configuración de vista para SUMO-GUI"""
    
    view_xml = '''<?xml version="1.0" encoding="UTF-8"?>

<viewsettings>
    <scheme name="real world">
        <opengl anitialiase="1" dither="1"/>
    </scheme>
    
    <delay value="100"/>
    <viewport zoom="1000" x="283000" y="8662000"/>
    <scheme name="real world"/>
</viewsettings>
'''
    
    with open(view_file, 'w', encoding='utf-8') as f:
        f.write(view_xml)
    
    print(f"✓ Vista GUI creada: {view_file}")


def main():
    """Función principal"""
    print("="*70)
    print("  CREADOR DE MAPA SUMO - LIMA AMPLIO")
    print("="*70)
    
    # Verificar SUMO
    if not verificar_sumo():
        return
    
    # Definir directorios
    base_dir = Path(__file__).parent
    escenarios_dir = base_dir / 'escenarios'
    lima_amplio_dir = escenarios_dir / 'lima-amplio'
    lima_amplio_dir.mkdir(parents=True, exist_ok=True)
    
    # Definir archivos
    osm_file = lima_amplio_dir / 'lima_amplio.osm'
    net_file = lima_amplio_dir / 'lima_amplio.net.xml'
    route_file = lima_amplio_dir / 'lima_amplio.rou.xml'
    config_file = lima_amplio_dir / 'lima_amplio.sumocfg'
    view_file = lima_amplio_dir / 'view.xml'
    
    # Bbox más amplio de Lima (cubre más distritos)
    # Centro de Lima, Miraflores, San Isidro, Lince, Jesus Maria, Magdalena
    bbox_amplio = (
        -77.0700,  # min_lon (oeste)
        -12.1200,  # min_lat (sur)
        -77.0100,  # max_lon (este)
        -12.0400   # max_lat (norte)
    )
    
    print(f"\n📍 Área seleccionada:")
    print(f"   Distritos: Lima Centro, Miraflores, San Isidro, Lince, Jesús María")
    print(f"   Coordenadas: {bbox_amplio}")
    
    # Paso 1: Descargar mapa (opcional si ya existe)
    if not osm_file.exists():
        print(f"\n{'='*70}")
        print("PASO 1: DESCARGAR MAPA DE OPENSTREETMAP")
        print('='*70)
        
        if not descargar_mapa_osm(bbox_amplio, osm_file):
            print("\n⚠️  No se pudo descargar automáticamente.")
            print("📝 DESCARGA MANUAL:")
            print("   1. Ir a: https://www.openstreetmap.org/export")
            print(f"   2. Ingresar coordenadas:")
            print(f"      - Izquierda: {bbox_amplio[0]}")
            print(f"      - Abajo: {bbox_amplio[1]}")
            print(f"      - Derecha: {bbox_amplio[2]}")
            print(f"      - Arriba: {bbox_amplio[3]}")
            print(f"   3. Hacer clic en 'Export'")
            print(f"   4. Guardar como: {osm_file}")
            input("\n   Presiona ENTER cuando hayas descargado el archivo...")
            
            if not osm_file.exists():
                print("❌ Archivo no encontrado. Abortando.")
                return
    else:
        print(f"\n✓ Archivo OSM ya existe: {osm_file}")
    
    # Paso 2: Convertir a red SUMO
    if not net_file.exists():
        print(f"\n{'='*70}")
        print("PASO 2: CONVERTIR A RED SUMO")
        print('='*70)
        
        if not convertir_osm_a_sumo(osm_file, net_file):
            print("❌ Error en conversión. Abortando.")
            return
    else:
        print(f"\n✓ Red SUMO ya existe: {net_file}")
    
    # Paso 3: Generar tráfico
    if not route_file.exists():
        print(f"\n{'='*70}")
        print("PASO 3: GENERAR TRÁFICO")
        print('='*70)
        
        if not generar_trafico(net_file, route_file, num_vehiculos=1500, tiempo_sim=3600):
            print("⚠️  No se pudo generar tráfico automáticamente.")
            print("   Puedes usar el mapa sin tráfico o generarlo manualmente.")
    else:
        print(f"\n✓ Tráfico ya existe: {route_file}")
    
    # Paso 4: Crear configuración
    print(f"\n{'='*70}")
    print("PASO 4: CREAR CONFIGURACIÓN")
    print('='*70)
    
    crear_configuracion_sumo(net_file, route_file, config_file)
    crear_vista_gui(view_file)
    
    # Extraer calles para el frontend
    print(f"\n{'='*70}")
    print("PASO 5: EXTRAER CALLES PARA VISUALIZACIÓN WEB")
    print('='*70)
    
    try:
        sys.path.insert(0, str(base_dir))
        from extraer_calles import extraer_calles_sumo, guardar_geojson
        
        geojson = extraer_calles_sumo(net_file)
        geojson_file = lima_amplio_dir / 'calles.geojson'
        guardar_geojson(geojson, geojson_file)
        
    except Exception as e:
        print(f"⚠️  No se pudo extraer calles: {e}")
    
    # Resumen final
    print(f"\n{'='*70}")
    print("✅ PROCESO COMPLETADO")
    print('='*70)
    print(f"\n📁 Archivos generados en: {lima_amplio_dir}")
    print(f"   - {net_file.name}")
    print(f"   - {route_file.name}")
    print(f"   - {config_file.name}")
    print(f"   - view.xml")
    print(f"   - calles.geojson")
    
    print(f"\n🚀 Para ejecutar:")
    print(f"   cd {lima_amplio_dir}")
    print(f"   sumo-gui -c {config_file.name}")
    
    print(f"\n📝 Para usar en el sistema:")
    print(f"   1. Edita servidor-backend/main.py")
    print(f"   2. Cambia 'lima-centro' por 'lima-amplio' en la ruta de configuración")
    print(f"   3. Reinicia el servidor")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

