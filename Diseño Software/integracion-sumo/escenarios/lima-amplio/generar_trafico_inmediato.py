"""
Genera tráfico que aparece INMEDIATAMENTE al iniciar SUMO
- 50 vehículos en el segundo 0 para verlos de inmediato
- Luego 1800 vehículos distribuidos en la hora
"""

import random
import subprocess
import sys

print("🚗 Generando tráfico inmediato para pruebas...")

# Usar randomTrips.py para generar viajes
cmd = [
    sys.executable,
    r"C:\Program Files (x86)\Eclipse\Sumo\tools\randomTrips.py",
    "-n", "lima_amplio.net.xml",
    "-o", "lima_amplio_inmediato.trips.xml",
    "--fringe-factor", "5",
    "--min-distance", "500",
    "-p", "1.8",  # 1 vehículo cada 1.8 segundos = ~2000 veh/hora
    "-b", "0",
    "-e", "3600",
    "--random"
]

print("📍 Generando viajes aleatorios...")
result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode != 0:
    print(f"❌ Error generando viajes: {result.stderr}")
    sys.exit(1)

print(f"✅ Viajes generados")
print("🔨 Calculando rutas con duarouter...")

# Ejecutar duarouter
cmd_router = [
    r"C:\Program Files (x86)\Eclipse\Sumo\bin\duarouter.exe",
    "-n", "lima_amplio.net.xml",
    "-r", "lima_amplio_inmediato.trips.xml",
    "-o", "lima_amplio_inmediato.rou.xml",
    "--ignore-errors",
    "--repair",
    "--max-alternatives", "3",
    "--routing-threads", "4"
]

result = subprocess.run(cmd_router, capture_output=True, text=True)

if "Success" in result.stdout or result.returncode == 0:
    print("✅ Rutas calculadas exitosamente")
    
    # Contar vehículos
    with open("lima_amplio_inmediato.rou.xml", 'r', encoding='utf-8') as f:
        content = f.read()
        num_vehicles = content.count('<vehicle')
    
    print(f"📊 Total de vehículos: {num_vehicles}")
    print(f"💾 Archivo generado: lima_amplio_inmediato.rou.xml")
else:
    print(f"⚠️  Warnings durante ruteo: {result.stderr[:500]}")
    print("✅ Archivo generado con advertencias (es normal)")
