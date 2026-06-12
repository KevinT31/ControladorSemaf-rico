"""
Genera tráfico realista para Lima con diferentes niveles de congestión
- Zonas de alto tráfico: arterias principales (50% de vehículos)
- Zonas de tráfico medio: calles secundarias (35% de vehículos)
- Zonas vacías o bajo tráfico: calles locales (15% de vehículos)
"""

import random
import xml.etree.ElementTree as ET
from xml.dom import minidom

def prettify_xml(elem):
    """Retorna XML formateado bonito"""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

# Configuración
DURACION_SIMULACION = 3600  # 1 hora
TOTAL_VEHICULOS = 1800  # Promedio de 0.5 vehículos por segundo = tráfico realista urbano

# Distribución de tráfico por zonas
# Alto tráfico: 1 vehículo cada 1.5 segundos
# Medio tráfico: 1 vehículo cada 3 segundos  
# Bajo tráfico: 1 vehículo cada 10 segundos

print("🚗 Generando tráfico realista para Lima...")
print(f"   Total vehículos: {TOTAL_VEHICULOS}")
print(f"   Duración: {DURACION_SIMULACION}s (1 hora)")

# Leer la red para obtener calles
print("📍 Cargando red de calles...")
try:
    tree = ET.parse('lima_amplio.net.xml')
    root = tree.getroot()
    
    # Extraer todas las calles (edges)
    edges = []
    for edge in root.findall('.//edge'):
        edge_id = edge.get('id')
        # Filtrar calles internas de intersecciones
        if edge_id and not edge_id.startswith(':'):
            edges.append(edge_id)
    
    print(f"   ✓ {len(edges)} calles disponibles")
    
except Exception as e:
    print(f"   ✗ Error leyendo red: {e}")
    edges = []

if not edges:
    print("❌ No se pudo cargar la red. Abortando.")
    exit(1)

# Clasificar calles (simulado - en producción usarías atributos reales)
random.shuffle(edges)
num_arterias = int(len(edges) * 0.15)  # 15% arterias principales
num_secundarias = int(len(edges) * 0.35)  # 35% secundarias
# Resto son locales

arterias_principales = edges[:num_arterias]
calles_secundarias = edges[num_arterias:num_arterias + num_secundarias]
calles_locales = edges[num_arterias + num_secundarias:]

print(f"   📊 Clasificación:")
print(f"      - Arterias principales: {len(arterias_principales)} (alto tráfico)")
print(f"      - Calles secundarias: {len(calles_secundarias)} (medio tráfico)")
print(f"      - Calles locales: {len(calles_locales)} (bajo tráfico)")

# Crear archivo XML de viajes
print("🔨 Generando viajes...")
routes_root = ET.Element('routes')

# Tipo de vehículo por defecto
vtype = ET.SubElement(routes_root, 'vType')
vtype.set('id', 'type1')
vtype.set('accel', '2.6')
vtype.set('decel', '4.5')
vtype.set('sigma', '0.5')
vtype.set('length', '5')
vtype.set('maxSpeed', '70')

vehiculos_generados = 0

# Generar vehículos distribuidos en el tiempo
for segundo in range(DURACION_SIMULACION):
    # Probabilidad de generar vehículo varía según la hora
    # Simular pico de tráfico entre 300-900s y 2700-3300s
    
    if (300 <= segundo <= 900) or (2700 <= segundo <= 3300):
        # Horas pico: más vehículos
        prob_vehiculo = 0.8
    elif (0 <= segundo <= 300) or (3300 <= segundo <= 3600):
        # Inicio y final: tráfico creciendo/decreciendo
        prob_vehiculo = 0.4
    else:
        # Horas normales: tráfico medio
        prob_vehiculo = 0.5
    
    if random.random() < prob_vehiculo and vehiculos_generados < TOTAL_VEHICULOS:
        # Decidir tipo de ruta según distribución
        rand = random.random()
        
        if rand < 0.5:  # 50% en arterias principales
            from_edge = random.choice(arterias_principales)
            to_edge = random.choice(arterias_principales)
        elif rand < 0.85:  # 35% en secundarias
            from_edge = random.choice(calles_secundarias)
            to_edge = random.choice(calles_secundarias)
        else:  # 15% en locales
            from_edge = random.choice(calles_locales)
            to_edge = random.choice(calles_locales)
        
        # Evitar rutas inválidas
        if from_edge == to_edge:
            continue
        
        # Crear vehículo
        vehicle = ET.SubElement(routes_root, 'vehicle')
        vehicle.set('id', f'veh_{vehiculos_generados}')
        vehicle.set('type', 'type1')
        vehicle.set('depart', str(segundo))
        vehicle.set('departLane', 'best')
        vehicle.set('departSpeed', 'max')
        
        # Crear ruta
        route = ET.SubElement(vehicle, 'route')
        route.set('edges', f'{from_edge} {to_edge}')
        
        vehiculos_generados += 1
        
        if vehiculos_generados % 200 == 0:
            print(f"   ⏳ {vehiculos_generados}/{TOTAL_VEHICULOS} vehículos generados...")

print(f"   ✓ {vehiculos_generados} vehículos generados")

# Guardar archivo
print("💾 Guardando archivo...")
output_file = 'lima_amplio_realista.rou.xml'
xml_string = prettify_xml(routes_root)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(xml_string)

print(f"✅ Archivo guardado: {output_file}")
print(f"📈 Estadísticas:")
print(f"   - Vehículos totales: {vehiculos_generados}")
print(f"   - Duración: {DURACION_SIMULACION}s")
print(f"   - Densidad promedio: {vehiculos_generados/DURACION_SIMULACION:.2f} veh/s")
print(f"   - Distribución: 50% arterias, 35% secundarias, 15% locales")
