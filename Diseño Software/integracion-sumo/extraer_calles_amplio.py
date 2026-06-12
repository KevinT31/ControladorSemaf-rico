"""
Script para extraer calles del mapa amplio de Lima y generar GeoJSON
"""
import sys
from pathlib import Path

# Agregar path de integracion-sumo
sys.path.insert(0, str(Path(__file__).parent))

from extraer_calles import extraer_calles_sumo, guardar_geojson

def main():
    print("="*70)
    print("  EXTRAYENDO CALLES DE LIMA AMPLIO PARA VISUALIZACIÓN WEB")
    print("="*70)
    print()
    
    # Rutas
    lima_amplio_dir = Path(__file__).parent / 'escenarios' / 'lima-amplio'
    ruta_net = lima_amplio_dir / 'lima_amplio.net.xml'
    ruta_salida = lima_amplio_dir / 'calles.geojson'
    
    if not ruta_net.exists():
        print(f"❌ ERROR: {ruta_net} no encontrado")
        return False
    
    print(f"📂 Leyendo red SUMO: {ruta_net.name}")
    print(f"   (Esto puede tomar 1-2 minutos para una red grande)")
    print()
    
    try:
        # Extraer calles (limitado a 1000 para rendimiento web)
        geojson = extraer_calles_sumo(str(ruta_net))
        
        # Guardar
        guardar_geojson(geojson, str(ruta_salida))
        
        print()
        print("="*70)
        print(f"✅ EXTRACCIÓN COMPLETADA")
        print("="*70)
        print(f"   Calles extraídas: {len(geojson['features'])}")
        print(f"   Archivo: {ruta_salida}")
        print()
        print("💡 El sistema web ahora usará automáticamente este mapa amplio")
        print("   Solo reinicia el servidor: python iniciar_servidor.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    input("\n Presiona Enter para continuar...")
    sys.exit(0 if success else 1)
