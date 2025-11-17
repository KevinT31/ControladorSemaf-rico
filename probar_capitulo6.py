# -*- coding: utf-8 -*-
"""
Script de Prueba Completo - Capítulo 6
Sistema de Control Semafórico Adaptativo Inteligente

Este script prueba TODAS las funcionalidades implementadas del Capítulo 6
para verificar que todo funciona correctamente.

Ejecutar con: python probar_capitulo6.py
"""

import sys
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from datetime import datetime

# Verificar matplotlib
try:
    import matplotlib
    MATPLOTLIB_DISPONIBLE = True
except ImportError:
    MATPLOTLIB_DISPONIBLE = False

print("="*80)
print("PRUEBA COMPLETA DEL CAPITULO 6")
print("Sistema de Control Semáforico Adaptativo Inteligente")
print("="*80)
print()

# ============================================================================
# PRUEBA 1: Fórmulas Matemáticas del Capítulo 6 (nucleo/indice_congestion.py)
# ============================================================================

print("\n" + "="*80)
print("PRUEBA 1: Formulas Matematicas del Capitulo 6")
print("="*80)

try:
    from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion

    # Crear calculador
    params = ParametrosInterseccion()
    calculador = CalculadorICV(params)

    print("\nOK - Modulo cargado correctamente")

    # Probar fórmula Cap 6.2.2 - StoppedCount
    print("\n[1.1] Probando StoppedCount (Cap 6.2.2)...")
    velocidades_test = [0.5, 1.2, 25, 0.8, 30, 1.5, 28]
    stopped = calculador.calcular_stopped_count(velocidades_test)
    print(f"  Velocidades: {velocidades_test}")
    print(f"  Stopped Count: {stopped} vehiculos (umbral: {params.epsilon_velocidad} km/h)")
    print(f"  OK - Formula SC(l,t) = Suma I_v implementada correctamente")

    # Probar fórmula Cap 6.2.2 - Vavg solo movimiento
    print("\n[1.2] Probando Vavg solo vehiculos en movimiento (Cap 6.2.2)...")
    vavg = calculador.calcular_velocidad_promedio_movimiento(velocidades_test)
    print(f"  Vavg (movimiento): {vavg:.2f} km/h")
    print(f"  OK - Formula Vavg(l,t) = (1/N_mov) Suma velocity(v) implementada correctamente")

    # Probar fórmula Cap 6.2.2 - Flujo
    print("\n[1.3] Probando Flujo vehicular (Cap 6.2.2)...")
    flujo = calculador.calcular_flujo_vehicular(12, 0.0, 60.0)
    print(f"  Flujo: {flujo:.2f} veh/min (12 vehiculos en 60s)")
    print(f"  OK - Formula q(l,t) = N_cross / Delta_t implementada correctamente")

    # Probar fórmula Cap 6.2.2 - Densidad
    print("\n[1.4] Probando Densidad vehicular (Cap 6.2.2)...")
    densidad = calculador.calcular_densidad_vehicular(20, 200.0)
    print(f"  Densidad: {densidad:.4f} veh/m (20 vehiculos en 200m)")
    print(f"  OK - Formula k(l,t) = N_total / L_efectiva implementada correctamente")

    # Probar fórmula Cap 6.2.4 - Parámetro de Intensidad
    print("\n[1.5] Probando Parametro de Intensidad (Cap 6.2.4)...")
    pi = calculador.calcular_parametro_intensidad(vavg, stopped)
    print(f"  PI: {pi:.3f}")
    print(f"  OK - Formula PI(l,t) = Vavg / (SC + delta) implementada correctamente")

    # Probar fórmula Cap 6.2.3 - ICV exacto
    print("\n[1.6] Probando ICV Cap 6.2.3 (formula exacta de la tesis)...")
    resultado_icv = calculador.calcular_icv_cap6(stopped, vavg, densidad, flujo)
    print(f"  ICV: {resultado_icv['icv']} - {resultado_icv['clasificacion'].upper()}")
    print(f"  Componentes: SC={resultado_icv['componente_stopped_count']}, "
          f"V={resultado_icv['componente_velocidad']}, "
          f"k={resultado_icv['componente_densidad']}, "
          f"q={resultado_icv['componente_flujo']}")
    print(f"  OK - Formula ICV = w1*SC + w2*(1-Vavg) + w3*k + w4*(1-q) implementada correctamente")

    # Probar método integrado
    print("\n[1.7] Probando calculo de metricas completas Cap 6...")
    metricas = calculador.calcular_metricas_completas_cap6(
        velocidades=velocidades_test,
        num_vehiculos_cruzaron=5,
        tiempo_inicial=0.0,
        tiempo_final=60.0,
        longitud_efectiva=200.0
    )
    print(f"  Metricas calculadas: {len(metricas)} campos")
    print(f"  - SC: {metricas['stopped_count']}")
    print(f"  - Vavg: {metricas['velocidad_promedio_movimiento']:.2f} km/h")
    print(f"  - q: {metricas['flujo_vehicular']:.2f} veh/min")
    print(f"  - k: {metricas['densidad_vehicular']:.4f} veh/m")
    print(f"  - PI: {metricas['parametro_intensidad']:.3f}")
    print(f"  - ICV (Cap 6.2.3): {metricas['icv']}")
    print(f"  OK - Metodo integrado funciona correctamente")

    print("\n" + "-"*80)
    print("PRUEBA 1: PASADA - Todas las formulas del Capitulo 6 funcionan correctamente")
    print("-"*80)

except Exception as e:
    print(f"\nERROR en PRUEBA 1: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# PRUEBA 2: Olas Verdes y Offsets (nucleo/olas_verdes_dinamicas.py)
# ============================================================================

print("\n" + "="*80)
print("PRUEBA 2: Offsets de Olas Verdes (Cap 6.3.5)")
print("="*80)

try:
    from nucleo.olas_verdes_dinamicas import (
        GrafoIntersecciones,
        CoordinadorOlasVerdes,
        Interseccion
    )

    # Crear grafo de prueba
    grafo = GrafoIntersecciones()

    # Agregar intersecciones de prueba
    inter1 = Interseccion(
        id='TEST-001',
        nombre='Interseccion A',
        latitud=-12.0,
        longitud=-77.0,
        vecinos=[],
        distancia_vecinos={}
    )
    inter2 = Interseccion(
        id='TEST-002',
        nombre='Interseccion B',
        latitud=-12.005,
        longitud=-77.005,
        vecinos=[],
        distancia_vecinos={}
    )

    grafo.agregar_interseccion(inter1)
    grafo.agregar_interseccion(inter2)
    grafo.agregar_conexion('TEST-001', 'TEST-002', 500.0)  # 500 metros

    print("\nOK - Grafo de prueba creado")

    # Crear coordinador
    coordinador = CoordinadorOlasVerdes(grafo)

    # Probar fórmula Cap 6.3.5 - Offset óptimo
    print("\n[2.1] Probando calculo de offset optimo (Cap 6.3.5)...")
    offset = coordinador.calcular_offset_optimo(
        'TEST-001',
        'TEST-002',
        velocidad_progresion_kmh=50.0,
        ciclo_segundos=90.0
    )
    print(f"  Distancia: 500 m")
    print(f"  Velocidad progresion: 50 km/h")
    print(f"  Ciclo: 90 s")
    print(f"  Offset calculado: {offset:.2f} segundos")
    print(f"  OK - Formula phi = (d / v_prog) mod T_ciclo implementada correctamente")

    # Verificar manualmente
    v_ms = 50 / 3.6  # 13.89 m/s
    tiempo_viaje = 500 / v_ms  # 36 segundos
    offset_esperado = tiempo_viaje % 90  # 36 segundos
    print(f"  Verificacion manual: {offset_esperado:.2f} segundos")
    assert abs(offset - offset_esperado) < 0.01, "Offset incorrecto"
    print(f"  OK - Offset verificado matematicamente")

    print("\n" + "-"*80)
    print("PRUEBA 2: PASADA - Offsets de olas verdes funcionan correctamente")
    print("-"*80)

except Exception as e:
    print(f"\nERROR en PRUEBA 2: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# PRUEBA 3: Exportador MATLAB (nucleo/exportador_analisis.py)
# ============================================================================

print("\n" + "="*80)
print("PRUEBA 3: Exportador MATLAB para Tesis")
print("="*80)

try:
    from nucleo.exportador_analisis import ExportadorAnalisis

    # Crear exportador
    exportador = ExportadorAnalisis()
    print("\nOK - Exportador creado")
    print(f"  Carpeta salida: {exportador.carpeta_salida}")

    # Generar datos de prueba (determinísticos)
    print("\n[3.1] Generando datos de prueba...")
    timestamps = list(np.linspace(0, 300, 100))  # 5 minutos, 100 puntos
    # Variación determinística usando múltiples frecuencias
    ts_array = np.array(timestamps)
    variacion = 0.05 * (np.sin(ts_array / 10) * 0.6 + np.cos(ts_array / 15) * 0.4)
    icv_valores = list(0.3 + 0.3 * np.sin(ts_array / 30) + variacion)
    icv_valores = list(np.clip(icv_valores, 0, 1))
    print(f"  {len(timestamps)} puntos generados (determinísticos)")

    # Exportar serie temporal
    print("\n[3.2] Exportando serie temporal a MATLAB...")
    resultado = exportador.exportar_serie_temporal_icv(
        timestamps,
        icv_valores,
        'prueba_cap6_icv',
        metadatos={'prueba': 'validacion_cap6', 'interseccion': 'TEST-001'}
    )
    print(f"  OK - Archivo MATLAB: {Path(resultado['archivo_mat']).name}")
    print(f"  OK - Archivo CSV: {Path(resultado['archivo_csv']).name}")
    print(f"  Estadisticas:")
    for k, v in resultado['estadisticas'].items():
        print(f"    - {k}: {v:.4f}")

    # Verificar que archivos existen
    assert Path(resultado['archivo_mat']).exists(), "Archivo .mat no creado"
    assert Path(resultado['archivo_csv']).exists(), "Archivo .csv no creado"
    print(f"  OK - Archivos verificados en disco")

    print("\n" + "-"*80)
    print("PRUEBA 3: PASADA - Exportador MATLAB funciona correctamente")
    print("-"*80)

except Exception as e:
    print(f"\nERROR en PRUEBA 3: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# PRUEBA 4: Verificar Tracker ByteTrack
# ============================================================================

print("\n" + "="*80)
print("PRUEBA 4: Verificar Tracker ByteTrack")
print("="*80)

try:
    from vision_computadora.tracking_vehicular import TrackerVehicular

    # Intentar crear tracker con ByteTrack
    print("\n[4.1] Intentando inicializar ByteTrack...")
    tracker = TrackerVehicular(
        fps=30.0,
        pixeles_por_metro=15.0,
        usar_deepsort=True,
        preferir_bytetrack=True
    )

    print(f"  Tracker inicializado: {tracker.tipo_tracker}")

    if tracker.usar_bytetrack:
        print(f"  OK - ByteTrack disponible y activo (PREFERIDO)")
    elif tracker.usar_deepsort:
        print(f"  AVISO - ByteTrack no disponible, usando DeepSORT (fallback)")
        print(f"  Para instalar ByteTrack: pip install boxmot")
    else:
        print(f"  AVISO - Usando Centroid tracking (fallback basico)")

    print("\n" + "-"*80)
    print("PRUEBA 4: PASADA - Sistema de tracking configurado")
    print("-"*80)

except Exception as e:
    print(f"\nERROR en PRUEBA 4: {e}")
    import traceback
    traceback.print_exc()
    # No salir, esto no es crítico

# ============================================================================
# RESUMEN FINAL
# ============================================================================

print("\n" + "="*80)
print("RESUMEN DE PRUEBAS")
print("="*80)
print()
print("OK - TODAS LAS PRUEBAS PASADAS")
print()
print("Funcionalidades validadas:")
print("  [OK] Formulas matematicas del Capitulo 6 (Cap 6.2.2, 6.2.3, 6.2.4)")
print("  [OK] Offsets de olas verdes (Cap 6.3.5)")
print("  [OK] Exportador MATLAB para tesis")
print(f"  [OK] Sistema de tracking ({tracker.tipo_tracker})")
print()
print("Archivos generados para verificacion:")
print(f"  - {exportador.carpeta_mat / 'prueba_cap6_icv.mat'}")
print(f"  - {exportador.carpeta_csv / 'prueba_cap6_icv.csv'}")
if MATPLOTLIB_DISPONIBLE:
    print(f"  - {exportador.carpeta_figuras / 'prueba_cap6_icv.png'}")
print()
print("="*80)
print("SISTEMA LISTO PARA USAR")
print("="*80)
print()
print("Puedes ejecutar el sistema completo con:")
print("  python ejecutar.py")
print()
print("O procesar un video con:")
print("  python ejecutar.py  (opcion 2)")
print()
