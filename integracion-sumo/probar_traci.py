"""
Script para probar la conexión TraCI y extracción de datos de SUMO

Este script demuestra cómo extraer datos sintéticos realistas de SUMO
para alimentar el sistema de control semafórico.
"""

import sys
from pathlib import Path
import time

# Agregar ruta al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import traci
    TRACI_DISPONIBLE = True
    print("✅ TraCI disponible")
except ImportError:
    TRACI_DISPONIBLE = False
    print("❌ TraCI NO disponible")
    print("\n📦 Para instalarlo:")
    print("   1. Asegúrate de tener SUMO instalado")
    print("   2. Agrega <SUMO_HOME>/tools al PYTHONPATH")
    print("   3. O instala: pip install traci")
    sys.exit(1)

from conector_sumo import ConectorSUMO


def probar_conexion_traci():
    """Prueba conectar a SUMO y extraer datos"""
    
    print("\n" + "="*70)
    print("🚦 PRUEBA DE CONEXIÓN TraCI - EXTRACCIÓN DE DATOS SINTÉTICOS")
    print("="*70)
    
    # Buscar configuración
    base_dir = Path(__file__).parent / 'escenarios'
    config_amplio = base_dir / 'lima-amplio' / 'lima_amplio.sumocfg'
    config_centro = base_dir / 'lima-centro' / 'osm.sumocfg'
    
    config_path = None
    if config_amplio.exists():
        config_path = config_amplio
        print(f"\n📍 Usando: Lima Amplio ({config_amplio})")
    elif config_centro.exists():
        config_path = config_centro
        print(f"\n📍 Usando: Lima Centro ({config_centro})")
    else:
        print("\n❌ No se encontró configuración SUMO")
        print(f"   Buscado en:")
        print(f"   - {config_amplio}")
        print(f"   - {config_centro}")
        return
    
    # Conectar
    print("\n🔌 Conectando a SUMO...")
    conector = ConectorSUMO(
        ruta_config_sumo=str(config_path),
        usar_gui=False  # Sin GUI para esta prueba
    )
    
    try:
        conector.conectar()
        print("✅ Conexión exitosa")
        
        # Obtener información de semáforos
        print(f"\n🚦 Semáforos detectados: {len(conector.intersecciones)}")
        for i, (id_sem, info) in enumerate(conector.intersecciones.items(), 1):
            if i <= 5:  # Mostrar solo los primeros 5
                print(f"   {i}. {id_sem}")
        if len(conector.intersecciones) > 5:
            print(f"   ... y {len(conector.intersecciones) - 5} más")
        
        # Simular algunos pasos y extraer datos
        print(f"\n⏱️  Ejecutando simulación continua (presiona Ctrl+C para detener)...")
        print("\n" + "-"*70)
        print("EXTRACCIÓN DE DATOS SINTÉTICOS")
        print("-"*70)
        
        # Contar vehículos totales
        vehiculos_totales_detectados = 0
        datos_extraidos = 0
        paso = 0
        
        while True:  # Bucle infinito - detener con Ctrl+C
            # Avanzar simulación
            continuar = conector.simular_paso()
            if not continuar:
                print("\n⚠️  Simulación terminó (sin más vehículos)")
                break
            
            paso += 1
            
            # Cada 10 pasos, extraer y mostrar datos
            if paso % 10 == 0:
                # Obtener estado de TODAS las calles
                estados = conector.obtener_estado_calles(limite=5000)
                
                # Filtrar calles con tráfico
                calles_con_trafico = [c for c in estados if c['vehiculos'] > 0]
                vehiculos_totales = sum(c['vehiculos'] for c in calles_con_trafico)
                vehiculos_totales_detectados = max(vehiculos_totales_detectados, vehiculos_totales)
                
                print(f"\n⏱️  Segundo {paso}:")
                print(f"   📊 Calles totales: {len(estados)}")
                print(f"   🚗 Calles con tráfico: {len(calles_con_trafico)}")
                print(f"   🚙 Vehículos circulando: {vehiculos_totales}")
                
                # Mostrar datos de calles con tráfico
                if calles_con_trafico:
                    datos_extraidos += 1
                    print("\n   ✅ DATOS EXTRAÍDOS:")
                    for i, calle in enumerate(calles_con_trafico[:5], 1):
                        print(f"      {i}. {calle['id'][:30]:30} | "
                              f"Veh: {calle['vehiculos']:2} | "
                              f"Vel: {calle['velocidad']:5.1f} km/h | "
                              f"Cong: {calle['congestion']:.2f}")
                    if len(calles_con_trafico) > 5:
                        print(f"      ... y {len(calles_con_trafico) - 5} calles más con tráfico")
                else:
                    print("   ⏳ Esperando que entren vehículos...")
        
        # Resumen
        print("\n" + "="*70)
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        print("="*70)
        print("\n📊 Estadísticas de extracción:")
        print(f"   🚦 Semáforos detectados: {len(conector.intersecciones)}")
        print(f"   🚗 Máximo de vehículos simultáneos: {vehiculos_totales_detectados}")
        print(f"   📈 Momentos con datos extraídos: {datos_extraidos}")
        print("\n✅ Capacidades demostradas:")
        print("   ✅ Conexión TraCI establecida")
        print("   ✅ Detección de semáforos en la red")
        print("   ✅ Extracción de datos de tráfico por calle:")
        print("      - Número de vehículos")
        print("      - Velocidad promedio (km/h)")
        print("      - Nivel de ocupación (%)")
        print("      - Índice de congestión (0-1)")
        
        print("\n💡 USO EN TU SISTEMA:")
        print("   Este tipo de datos REEMPLAZA los datos aleatorios")
        print("   generados por random(), dando datos sintéticos")
        print("   mucho más realistas que respetan:")
        print("   - Topología real de Lima")
        print("   - Dinámica de tráfico vehicular")
        print("   - Efectos de semáforos")
        print("   - Propagación de congestión")
        
        print("\n🎓 PARA TU TESIS:")
        print("   'El sistema extrae datos sintéticos de SUMO mediante")
        print("   TraCI, obteniendo métricas realistas de tráfico que")
        print("   alimentan el controlador difuso con información más")
        print("   fidedigna que datos puramente aleatorios.'")
        
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Desconectar
        print("\n🔌 Desconectando...")
        conector.desconectar()
        print("✅ Desconectado correctamente")


if __name__ == "__main__":
    try:
        probar_conexion_traci()
    except KeyboardInterrupt:
        print("\n\n⏹️  Prueba interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
