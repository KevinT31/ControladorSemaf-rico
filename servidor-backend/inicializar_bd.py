"""
Script para inicializar la base de datos y poblar las intersecciones de Lima

Ejecutar:
    python servidor-backend/inicializar_bd.py
"""

import sys
from pathlib import Path

# Agregar rutas al path
sys.path.insert(0, str(Path(__file__).parent))

from modelos_bd import init_db, SessionLocal
from modelos_bd.interseccion import InterseccionDB, ConexionInterseccionDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def poblar_intersecciones():
    """
    Puebla la base de datos con las 31 intersecciones de Lima Centro
    """
    # Intersecciones del sistema (datos de intersecciones_lima.js)
    intersecciones_data = [
        # Centro Histórico
        {'id': 'LC-001', 'nombre': 'Av. Abancay con Jr. Lampa', 'latitud': -12.0464, 'longitud': -77.0324, 'num_carriles': 6, 'zona': 'Centro Histórico'},
        {'id': 'LC-002', 'nombre': 'Av. Abancay con Jr. Carabaya', 'latitud': -12.0472, 'longitud': -77.0318, 'num_carriles': 6, 'zona': 'Centro Histórico'},
        {'id': 'LC-003', 'nombre': 'Av. Tacna con Jr. Quilca', 'latitud': -12.0478, 'longitud': -77.0342, 'num_carriles': 6, 'zona': 'Centro Histórico'},
        {'id': 'LC-004', 'nombre': 'Plaza Grau (convergencia)', 'latitud': -12.0512, 'longitud': -77.0325, 'num_carriles': 8, 'zona': 'Centro Histórico'},

        # Av. Arequipa (Corredor)
        {'id': 'LC-005', 'nombre': 'Av. Arequipa con Av. Javier Prado', 'latitud': -12.0889, 'longitud': -77.0354, 'num_carriles': 6, 'zona': 'San Isidro'},
        {'id': 'LC-006', 'nombre': 'Av. Arequipa con Av. Angamos', 'latitud': -12.1067, 'longitud': -77.0358, 'num_carriles': 6, 'zona': 'Miraflores'},
        {'id': 'LC-007', 'nombre': 'Av. Arequipa con Av. Benavides', 'latitud': -12.1245, 'longitud': -77.0362, 'num_carriles': 6, 'zona': 'Miraflores'},
        {'id': 'LC-008', 'nombre': 'Av. Arequipa con Av. Larco', 'latitud': -12.1189, 'longitud': -77.0289, 'num_carriles': 4, 'zona': 'Miraflores'},

        # Miraflores
        {'id': 'LC-009', 'nombre': 'Óvalo Gutiérrez', 'latitud': -12.0956, 'longitud': -77.0334, 'num_carriles': 6, 'zona': 'Miraflores'},
        {'id': 'LC-010', 'nombre': 'Av. Pardo con Av. Benavides', 'latitud': -12.1278, 'longitud': -77.0289, 'num_carriles': 6, 'zona': 'Miraflores'},
        {'id': 'LC-011', 'nombre': 'Av. Larco con Calle Schell', 'latitud': -12.1234, 'longitud': -77.0256, 'num_carriles': 4, 'zona': 'Miraflores'},

        # San Isidro
        {'id': 'LC-012', 'nombre': 'Av. Javier Prado con Av. República de Panamá', 'latitud': -12.0956, 'longitud': -77.0445, 'num_carriles': 8, 'zona': 'San Isidro'},
        {'id': 'LC-013', 'nombre': 'Av. Camino Real con Av. Javier Prado', 'latitud': -12.0912, 'longitud': -77.0467, 'num_carriles': 6, 'zona': 'San Isidro'},
        {'id': 'LC-014', 'nombre': 'Av. Angamos con Av. República de Panamá', 'latitud': -12.1089, 'longitud': -77.0423, 'num_carriles': 6, 'zona': 'San Isidro'},

        # La Molina / Surco
        {'id': 'LC-015', 'nombre': 'Av. Javier Prado con Av. La Molina', 'latitud': -12.0734, 'longitud': -76.9823, 'num_carriles': 8, 'zona': 'La Molina'},
        {'id': 'LC-016', 'nombre': 'Av. La Molina con Av. Flora Tristán', 'latitud': -12.0856, 'longitud': -76.9712, 'num_carriles': 6, 'zona': 'La Molina'},
        {'id': 'LC-017', 'nombre': 'Av. Primavera con Av. Velasco Astete', 'latitud': -12.1012, 'longitud': -76.9889, 'num_carriles': 6, 'zona': 'Surco'},

        # San Juan de Lurigancho
        {'id': 'LC-018', 'nombre': 'Av. Próceres con Av. Los Jardines', 'latitud': -11.9956, 'longitud': -77.0112, 'num_carriles': 6, 'zona': 'SJL'},
        {'id': 'LC-019', 'nombre': 'Av. Gran Chimú con Av. Próceres', 'latitud': -11.9823, 'longitud': -77.0089, 'num_carriles': 4, 'zona': 'SJL'},
        {'id': 'LC-020', 'nombre': 'Av. Wiesse con Av. Próceres', 'latitud': -12.0045, 'longitud': -76.9978, 'num_carriles': 6, 'zona': 'SJL'},

        # Los Olivos / Independencia
        {'id': 'LC-021', 'nombre': 'Av. Universitaria con Av. Naranjal', 'latitud': -11.9789, 'longitud': -77.0645, 'num_carriles': 8, 'zona': 'Los Olivos'},
        {'id': 'LC-022', 'nombre': 'Av. Universitaria con Av. Antúnez de Mayolo', 'latitud': -11.9923, 'longitud': -77.0623, 'num_carriles': 6, 'zona': 'Los Olivos'},
        {'id': 'LC-023', 'nombre': 'Av. Túpac Amaru con Av. Universitaria', 'latitud': -12.0156, 'longitud': -77.0589, 'num_carriles': 8, 'zona': 'Independencia'},

        # Jesús María / Lince
        {'id': 'LC-024', 'nombre': 'Av. Brasil con Av. 28 de Julio', 'latitud': -12.0723, 'longitud': -77.0456, 'num_carriles': 6, 'zona': 'Jesús María'},
        {'id': 'LC-025', 'nombre': 'Av. Arenales con Av. Petit Thouars', 'latitud': -12.0834, 'longitud': -77.0378, 'num_carriles': 4, 'zona': 'Lince'},
        {'id': 'LC-026', 'nombre': 'Av. Arequipa con Av. Arenales', 'latitud': -12.0801, 'longitud': -77.0356, 'num_carriles': 6, 'zona': 'Lince'},

        # Callao
        {'id': 'LC-027', 'nombre': 'Av. La Marina con Av. Venezuela', 'latitud': -12.0567, 'longitud': -77.0923, 'num_carriles': 8, 'zona': 'Callao'},
        {'id': 'LC-028', 'nombre': 'Av. Colonial con Av. Faucett', 'latitud': -12.0523, 'longitud': -77.0889, 'num_carriles': 6, 'zona': 'Callao'},
        {'id': 'LC-029', 'nombre': 'Av. La Marina con Av. Bocanegra', 'latitud': -12.0634, 'longitud': -77.1012, 'num_carriles': 6, 'zona': 'Callao'},

        # Surquillo / Barranco
        {'id': 'LC-030', 'nombre': 'Av. Angamos con Av. Tomás Marsano', 'latitud': -12.1134, 'longitud': -77.0278, 'num_carriles': 6, 'zona': 'Surquillo'},
        {'id': 'LC-031', 'nombre': 'Av. República de Panamá con Av. Paseo de la República', 'latitud': -12.1345, 'longitud': -77.0189, 'num_carriles': 4, 'zona': 'Barranco'},
    ]

    db = SessionLocal()
    try:
        # Verificar si ya hay datos
        count = db.query(InterseccionDB).count()
        if count > 0:
            logger.info(f"Base de datos ya contiene {count} intersecciones. Omitiendo población.")
            return

        # Insertar intersecciones
        for data in intersecciones_data:
            interseccion = InterseccionDB(**data)
            db.add(interseccion)

        db.commit()
        logger.info(f"✅ {len(intersecciones_data)} intersecciones insertadas correctamente")

        # Crear algunas conexiones de ejemplo (red vial simplificada)
        conexiones_ejemplo = [
            # Av. Arequipa (corredor)
            ('LC-005', 'LC-006', 2000),  # Javier Prado → Angamos
            ('LC-006', 'LC-007', 2100),  # Angamos → Benavides
            ('LC-006', 'LC-008', 800),   # Angamos → Larco

            # Centro Histórico
            ('LC-001', 'LC-002', 150),
            ('LC-002', 'LC-003', 200),
            ('LC-003', 'LC-004', 400),

            # San Isidro
            ('LC-012', 'LC-013', 600),
            ('LC-012', 'LC-014', 1500),
        ]

        for origen, destino, distancia in conexiones_ejemplo:
            conexion = ConexionInterseccionDB(
                interseccion_origen_id=origen,
                interseccion_destino_id=destino,
                distancia_metros=distancia,
                bidireccional=1
            )
            db.add(conexion)

        db.commit()
        logger.info(f"✅ {len(conexiones_ejemplo)} conexiones insertadas correctamente")

    except Exception as e:
        logger.error(f"Error poblando intersecciones: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Función principal"""
    print("\n" + "="*70)
    print("🗄️  INICIALIZACIÓN DE BASE DE DATOS")
    print("="*70 + "\n")

    # 1. Crear tablas
    print("📋 Creando tablas...")
    init_db()

    # 2. Poblar intersecciones
    print("\n📍 Poblando intersecciones de Lima...")
    poblar_intersecciones()

    print("\n" + "="*70)
    print("✅ Base de datos inicializada correctamente")
    print("="*70 + "\n")

    # Verificar
    db = SessionLocal()
    try:
        count_intersecciones = db.query(InterseccionDB).count()
        count_conexiones = db.query(ConexionInterseccionDB).count()

        print(f"📊 Resumen:")
        print(f"   - Intersecciones: {count_intersecciones}")
        print(f"   - Conexiones: {count_conexiones}")
        print(f"\n💾 Archivo: base-datos/semaforos.db\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
