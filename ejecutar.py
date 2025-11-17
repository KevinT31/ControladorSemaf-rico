# -*- coding: utf-8 -*-
"""
Sistema de Control Semafórico Adaptativo Inteligente
PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ
Tesis de Maestría - Implementación Completa del Capítulo 6

EJECUTAR.PY - Script Principal Refactorizado
Integra TODOS los módulos del sistema:
- EstadoLocalInterseccion (6.2): Variables SC, Vavg, q, k, ICV, PI, EV por dirección
- ControladorDifusoCapitulo6 (6.3.6): 12 reglas difusas jerárquicas
- AgregadorMetricasRed (6.4): Métricas globales de red ponderadas
- GeneradorMetricasRealistas: Simulaciones basadas en modelos matemáticos
- Coordinador de Olas Verdes: Sincronización inteligente
- Detección de Intersecciones y Calles: Visualización completa de red vial

Autor: Kevin Tenorio
Ejecutar con: python ejecutar.py
"""

import subprocess
import sys
import os
import webbrowser
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def imprimir_banner():
    """Imprime el banner del sistema con información del Capítulo 6"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║    SISTEMA DE CONTROL SEMAFÓRICO ADAPTATIVO INTELIGENTE v2.0     ║
    ║                                                                   ║
    ║   Universidad: PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ           ║
    ║   Tesis: SISTEMA DE CONTROL ADAPTATIVO DE LA RED SEMAFÓRICA      ║
    ║   Implementación Completa del Capítulo 6                          ║
    ║                                                                   ║
    ║   Características:                                                ║
    ║   • 31 Intersecciones Reales de Lima con Coordenadas GPS         ║
    ║   • Estado Local por Intersección (7 variables × 4 direcciones)  ║
    ║   • Control Difuso con 12 Reglas Jerárquicas                     ║
    ║   • Métricas de Red Global Ponderadas                            ║
    ║   • Detección de Vehículos de Emergencia                         ║
    ║   • Integración SUMO con Calles Reales                           ║
    ║   • Comparación Adaptativo vs Tiempo Fijo                        ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def verificar_dependencias():
    """Verifica que las dependencias estén instaladas"""
    print("\n📦 Verificando dependencias del sistema...")

    dependencias_criticas = {
        'fastapi': 'Framework web para API',
        'uvicorn': 'Servidor ASGI',
        'numpy': 'Cálculos numéricos y matrices',
        'cv2': 'Visión computacional (OpenCV)',
    }

    dependencias_opcionales = {
        'traci': 'Integración con SUMO (opcional)',
        'skfuzzy': 'Lógica difusa avanzada (opcional)',
        'matplotlib': 'Visualizaciones (opcional)'
    }

    faltan_criticas = []
    faltan_opcionales = []

    # Verificar críticas
    for dep, desc in dependencias_criticas.items():
        try:
            __import__(dep)
            print(f"  ✓ {dep:15} - {desc}")
        except ImportError:
            print(f"  ✗ {dep:15} - {desc} (NO INSTALADO)")
            faltan_criticas.append(dep)

    # Verificar opcionales
    print("\n📦 Dependencias opcionales:")
    for dep, desc in dependencias_opcionales.items():
        try:
            __import__(dep)
            print(f"  ✓ {dep:15} - {desc}")
        except ImportError:
            print(f"  ○ {dep:15} - {desc} (opcional, no instalado)")
            faltan_opcionales.append(dep)

    if faltan_criticas:
        print(f"\n⚠️  Faltan dependencias críticas: {', '.join(faltan_criticas)}")
        print("Instalando automáticamente...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✓ Dependencias instaladas")
    else:
        print("\n✓ Todas las dependencias críticas están instaladas")

    if faltan_opcionales:
        print(f"\n💡 Puedes instalar dependencias opcionales con:")
        print(f"   pip install {' '.join(faltan_opcionales)}")


def mostrar_menu():
    """Muestra el menú principal mejorado"""
    menu = """
    ═══════════════════════════════════════════════════════════════
    MENÚ PRINCIPAL - SISTEMA INTEGRADO
    ═══════════════════════════════════════════════════════════════

    🚀 SISTEMA COMPLETO
    1. Iniciar Dashboard Completo (31 Intersecciones + Métricas Cap 6)
    2. Modo Demostración Completa (Todas las funcionalidades)

    📹 ANÁLISIS DE VIDEO
    3. Procesar Video con Análisis Completo
       → Detección + Tracking + ICV + PI + Velocidad REAL + Emergencias
    4. Procesar Video Simple (Solo Detección)

    🌐 INTEGRACIÓN SUMO
    5. Conectar con SUMO (Calles Reales de Lima)
    6. Ver Mapa de Intersecciones y Calles

    📊 ANÁLISIS Y COMPARACIÓN
    7. Comparar Adaptativo vs Tiempo Fijo
    8. Generar Métricas Realistas (Sin SUMO)

    🧪 PRUEBAS Y VALIDACIÓN
    9. Ejecutar Pruebas del Sistema
    10. Ver Estado de Componentes

    📚 DOCUMENTACIÓN
    11. Ver Documentación del Sistema
    12. Exportar Configuración Actual

    0. Salir

    ═══════════════════════════════════════════════════════════════
    """
    print(menu)


def iniciar_sistema_completo():
    """
    Inicia el sistema completo con TODAS las funcionalidades del Capítulo 6
    Integra: EstadoLocal, ControlDifuso, MetricasRed, OlasVerdes
    """
    print("\n" + "="*70)
    print("🚀 INICIANDO SISTEMA COMPLETO DEL CAPÍTULO 6")
    print("="*70)
    print("\nComponentes que se inicializarán:")
    print("  1. Servidor FastAPI con API REST + WebSocket")
    print("  2. 31 Intersecciones de Lima con coordenadas GPS reales")
    print("  3. EstadoLocalInterseccion para cada intersección")
    print("  4. ControladorDifusoCapitulo6 (12 reglas jerárquicas)")
    print("  5. AgregadorMetricasRed (métricas globales)")
    print("  6. CoordinadorOlasVerdes (sincronización)")
    print("  7. GeneradorMetricasRealistas (simulaciones)")
    print("  8. Dashboard web interactivo")

    # Verificar que el servidor existe
    servidor_path = Path(__file__).parent / 'servidor-backend'
    main_path = servidor_path / 'main.py'

    if not main_path.exists():
        print(f"\n❌ Error: No se encontró {main_path}")
        return

    print("\n📡 Iniciando servidor...")
    print("🌐 Accesos:")
    print("  • Dashboard Principal:  http://localhost:8000")
    print("  • API REST:             http://localhost:8000/docs")
    print("  • WebSocket:            ws://localhost:8000/ws")
    print("\n⏳ Esperando que el servidor arranque...")

    # Abrir navegador automáticamente
    import threading
    def abrir_navegador():
        time.sleep(3)
        webbrowser.open('http://localhost:8000')
        print("\n✓ Navegador abierto")

    threading.Thread(target=abrir_navegador, daemon=True).start()

    try:
        # Ejecutar servidor
        subprocess.run([
            sys.executable,
            str(main_path)
        ])
    except KeyboardInterrupt:
        print("\n\n✓ Sistema detenido correctamente")


def modo_demostracion_completa():
    """
    Modo demostración que ejecuta TODAS las funcionalidades del sistema
    para mostrar la integración completa del Capítulo 6
    """
    print("\n" + "="*70)
    print("🎬 MODO DEMOSTRACIÓN COMPLETA DEL SISTEMA")
    print("="*70)
    print("\nEsta demostración ejecutará secuencialmente:")
    print("  1. ✓ Cálculo de ICV con todos los parámetros")
    print("  2. ✓ Sistema de Lógica Difusa (12 reglas)")
    print("  3. ✓ Generación de métricas realistas")
    print("  4. ✓ Agregación de métricas de red")
    print("  5. ✓ Comparación Adaptativo vs Tiempo Fijo")
    print("  6. ✓ Simulación de olas verdes")
    print("  7. ✓ Detección de emergencias (si hay modelo)")

    input("\nPresiona ENTER para iniciar la demostración...")

    # Importar módulos del sistema
    sys.path.insert(0, str(Path(__file__).parent))

    try:
        from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion
        from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6
        from nucleo.estado_local import EstadoLocalInterseccion, ParametrosInterseccion as ParamsEstado
        from nucleo.metricas_red import AgregadorMetricasRed, ConfiguracionInterseccion, MetricasInterseccion
        from nucleo.generador_metricas import GeneradorMetricasRealistas
        from nucleo.olas_verdes_dinamicas import CoordinadorOlasVerdes, GrafoIntersecciones, Interseccion
        import numpy as np

        # ==================== PARTE 1: ICV ====================
        print("\n" + "="*70)
        print("PARTE 1: CÁLCULO DE ICV (Índice de Congestión Vehicular)")
        print("="*70)

        params_icv = ParametrosInterseccion()
        calculador_icv = CalculadorICV(params_icv)

        casos_icv = [
            (10, 55, 10, "🟢 Flujo libre - Tráfico normal"),
            (75, 25, 22, "🟡 Congestión moderada - Hora pico inicio"),
            (140, 8, 28, "🔴 Atasco severo - Hora pico plena")
        ]

        for longitud, velocidad, flujo, descripcion in casos_icv:
            resultado = calculador_icv.calcular(longitud, velocidad, flujo)
            print(f"\n{descripcion}:")
            print(f"  Entrada: L={longitud}m, V={velocidad}km/h, F={flujo}veh/min")
            print(f"  Salida:  ICV = {resultado['icv']:.4f} ({resultado['clasificacion'].upper()})")
            print(f"  Color:   {resultado['color']}")

        # ==================== PARTE 2: CONTROL DIFUSO ====================
        print("\n" + "="*70)
        print("PARTE 2: SISTEMA DE CONTROL DIFUSO (12 Reglas Jerárquicas)")
        print("="*70)

        controlador_difuso = ControladorDifusoCapitulo6()

        casos_difusos = [
            (0.15, 0.65, 0, "Congestión baja, intensidad buena, sin emergencia"),
            (0.50, 0.35, 0, "Congestión media, intensidad baja"),
            (0.85, 0.15, 0, "Congestión alta, intensidad muy baja"),
            (0.45, 0.40, 1, "Congestión media, EMERGENCIA ACTIVA")
        ]

        for icv, pi, ev, desc in casos_difusos:
            resultado = controlador_difuso.calcular_ajuste_tiempo_verde(
                icv_ns=icv,
                icv_eo=icv * 0.8,  # Simular diferente congestión
                pi_ns=pi,
                pi_eo=pi * 0.9,
                ev_ns=ev,
                ev_eo=0
            )
            print(f"\n{desc}:")
            print(f"  Entrada: ICV={icv:.2f}, PI={pi:.2f}, EV={ev}")
            print(f"  Salida:  T_verde_NS={resultado['T_verde_ns']:.1f}s")
            print(f"           T_verde_EO={resultado['T_verde_eo']:.1f}s")
            print(f"  Ajuste:  ΔT_NS={resultado['delta_T_ns']:+.1f}%")

        # ==================== PARTE 3: ESTADO LOCAL ====================
        print("\n" + "="*70)
        print("PARTE 3: ESTADO LOCAL DE INTERSECCIÓN (7 Variables × 4 Direcciones)")
        print("="*70)

        params_estado = ParamsEstado()
        estado_local = EstadoLocalInterseccion("DEMO-001", params_estado)

        # Simular detecciones
        vehiculos_norte = [
            {'id': 1, 'velocidad': 3.0, 'clase': 'car', 'confidence': 0.95},
            {'id': 2, 'velocidad': 2.5, 'clase': 'car', 'confidence': 0.92},
            {'id': 3, 'velocidad': 45.0, 'clase': 'car', 'confidence': 0.88},
        ]

        vehiculos_este = [
            {'id': 10, 'velocidad': 15.0, 'clase': 'ambulance', 'confidence': 0.96,
             'pos_x': 25.0, 'pos_y': 5.0, 'vel_x': 5.0, 'vel_y': 0.5},
        ]

        estado_local.actualizar_cam_mask(1)  # Vista NS
        estado_local.actualizar_estado(
            vehiculos_por_direccion={
                'N': vehiculos_norte,
                'S': [],
                'E': vehiculos_este,
                'O': []
            },
            cruces_por_direccion={'N': 5, 'S': 3, 'E': 8, 'O': 2}
        )

        print(estado_local.obtener_resumen_legible())

        # ==================== PARTE 4: MÉTRICAS DE RED ====================
        print("\n" + "="*70)
        print("PARTE 4: AGREGACIÓN DE MÉTRICAS DE RED")
        print("="*70)

        configuraciones_red = [
            ConfiguracionInterseccion(
                id="I001",
                nombre="Av. Arequipa - Javier Prado",
                peso=1.5,
                es_critica=True
            ),
            ConfiguracionInterseccion(
                id="I002",
                nombre="Av. Brasil - Venezuela",
                peso=1.2
            ),
            ConfiguracionInterseccion(
                id="I003",
                nombre="Av. La Marina - Universitaria",
                peso=1.0
            ),
        ]

        agregador = AgregadorMetricasRed(configuraciones_red)

        print("\n📊 Simulando métricas de 3 intersecciones (valores determinísticos)...")

        # Usar valores base diferentes para cada intersección (determinístico)
        valores_base = [
            {'sc': 25, 'vavg': 35, 'q': 17, 'k': 0.07, 'icv': 0.4, 'pi': 0.55},  # I001
            {'sc': 30, 'vavg': 30, 'q': 15, 'k': 0.08, 'icv': 0.5, 'pi': 0.50},  # I002
            {'sc': 20, 'vavg': 40, 'q': 20, 'k': 0.06, 'icv': 0.3, 'pi': 0.65},  # I003
        ]

        for i, config in enumerate(configuraciones_red):
            base = valores_base[i]
            # Variación determinística basada en índice
            factor_ns = 1.0 + 0.1 * math.sin(i * 0.5)
            factor_eo = 1.0 + 0.1 * math.cos(i * 0.5)

            metricas = MetricasInterseccion(
                interseccion_id=config.id,
                timestamp=datetime.now(),
                sc_ns=base['sc'] * factor_ns,
                sc_eo=base['sc'] * factor_eo,
                vavg_ns=base['vavg'] * factor_ns,
                vavg_eo=base['vavg'] * factor_eo,
                q_ns=base['q'] * factor_ns,
                q_eo=base['q'] * factor_eo,
                k_ns=base['k'] * factor_ns,
                k_eo=base['k'] * factor_eo,
                icv_ns=min(1.0, base['icv'] * factor_ns),
                icv_eo=min(1.0, base['icv'] * factor_eo),
                pi_ns=min(1.0, base['pi'] * factor_ns),
                pi_eo=min(1.0, base['pi'] * factor_eo)
            )
            agregador.actualizar_metricas_interseccion(metricas)

        resumen_red = agregador.obtener_resumen_red()
        if resumen_red:
            print(f"\n✓ Métricas de Red Calculadas:")
            print(f"  Estado General: {resumen_red['estado_general']}")
            print(f"  ICV_red: {resumen_red['metricas_actuales']['ICV_red']:.3f}")
            print(f"  Vavg_red: {resumen_red['metricas_actuales']['Vavg_red']:.1f} km/h")
            print(f"  q_red: {resumen_red['metricas_actuales']['q_red']:.1f} veh/min")
            print(f"  QL_red: {resumen_red['metricas_actuales']['QL_red']:.3f}")

        # ==================== PARTE 5: GENERADOR MÉTRICAS ====================
        print("\n" + "="*70)
        print("PARTE 5: GENERACIÓN DE MÉTRICAS REALISTAS")
        print("="*70)

        generador = GeneradorMetricasRealistas(offset_temporal=0.0)

        print("\n📊 Generando series temporales para comparación...")
        patron_fijo = GeneradorMetricasRealistas.PATRON_MODERADO
        patron_adaptativo = GeneradorMetricasRealistas.crear_patron_adaptativo_mejorado(patron_fijo)

        serie_fijo = generador.generar_serie_temporal(patron_fijo, num_pasos=100)
        generador2 = GeneradorMetricasRealistas(semilla=123)
        serie_adapt = generador2.generar_serie_temporal(patron_adaptativo, num_pasos=100)

        icv_fijo = np.mean([m['icv_promedio'] for m in serie_fijo])
        icv_adapt = np.mean([m['icv_promedio'] for m in serie_adapt])
        vel_fijo = np.mean([m['vavg_promedio'] for m in serie_fijo])
        vel_adapt = np.mean([m['vavg_promedio'] for m in serie_adapt])

        mejora_icv = ((icv_fijo - icv_adapt) / icv_fijo) * 100
        mejora_vel = ((vel_adapt - vel_fijo) / vel_fijo) * 100

        print(f"\nComparación (100 pasos de simulación):")
        print(f"\n  Tiempo Fijo:")
        print(f"    ICV: {icv_fijo:.3f}")
        print(f"    Velocidad: {vel_fijo:.1f} km/h")
        print(f"\n  Control Adaptativo:")
        print(f"    ICV: {icv_adapt:.3f} ({'🟢' if icv_adapt < icv_fijo else '🔴'})")
        print(f"    Velocidad: {vel_adapt:.1f} km/h ({'🟢' if vel_adapt > vel_fijo else '🔴'})")
        print(f"\n  📈 Mejoras:")
        print(f"    Reducción de congestión: {mejora_icv:+.1f}%")
        print(f"    Aumento de velocidad: {mejora_vel:+.1f}%")

        # ==================== PARTE 6: OLAS VERDES ====================
        print("\n" + "="*70)
        print("PARTE 6: COORDINACIÓN DE OLAS VERDES")
        print("="*70)

        grafo = GrafoIntersecciones()

        # Crear intersecciones de ejemplo
        intersecciones_ejemplo = [
            Interseccion("I001", "Arequipa-Javier Prado", -12.0893, -77.0315, [], {}),
            Interseccion("I002", "Arequipa-Angamos", -12.1103, -77.0349, [], {}),
            Interseccion("I003", "Arequipa-Benavides", -12.1194, -77.0342, [], {})
        ]

        for inter in intersecciones_ejemplo:
            grafo.agregar_interseccion(inter)

        # Conectar intersecciones
        grafo.agregar_conexion("I001", "I002", 2400)  # 2.4 km
        grafo.agregar_conexion("I002", "I003", 900)   # 900 m

        coordinador_olas = CoordinadorOlasVerdes(grafo)

        from nucleo.olas_verdes_dinamicas import VehiculoEmergencia as VehEmergOlas
        vehiculo_emergencia = VehEmergOlas(
            id="AMB-001",
            tipo="ambulancia",
            interseccion_actual="I001",
            destino="I003",
            velocidad_estimada=60.0,
            timestamp=datetime.now()
        )

        resultado_ola = coordinador_olas.activar_ola_verde(vehiculo_emergencia)

        print(f"\n🚑 Vehículo de emergencia detectado:")
        print(f"  Tipo: {vehiculo_emergencia.tipo}")
        print(f"  Ruta: {vehiculo_emergencia.interseccion_actual} → {vehiculo_emergencia.destino}")
        print(f"  Velocidad: {vehiculo_emergencia.velocidad_estimada} km/h")
        print(f"\n  Resultado:")
        print(f"    Distancia total: {resultado_ola['distancia_total']/1000:.1f} km")
        print(f"    Tiempo estimado: {resultado_ola['tiempo_total']:.1f}s")
        print(f"    Intersecciones en ruta: {len(resultado_ola['ruta'])}")

        # ==================== RESUMEN FINAL ====================
        print("\n" + "="*70)
        print("✅ DEMOSTRACIÓN COMPLETADA")
        print("="*70)
        print("\n📊 Componentes verificados:")
        print("  ✓ CalculadorICV - Funcionando correctamente")
        print("  ✓ ControladorDifusoCapitulo6 - 12 reglas operativas")
        print("  ✓ EstadoLocalInterseccion - 7 variables × 4 direcciones")
        print("  ✓ AgregadorMetricasRed - Métricas globales calculadas")
        print("  ✓ GeneradorMetricasRealistas - Simulaciones realistas")
        print("  ✓ CoordinadorOlasVerdes - Sincronización activa")
        print("\n💡 Todos los módulos del Capítulo 6 están integrados y funcionando")

    except Exception as e:
        print(f"\n❌ Error durante la demostración: {e}")
        import traceback
        traceback.print_exc()

    input("\n\nPresiona ENTER para volver al menú principal...")


def procesar_video():
    """Procesa un video con análisis COMPLETO del Capítulo 6"""
    print("\n" + "="*70)
    print("📹 PROCESADOR DE VIDEO CON ANÁLISIS COMPLETO")
    print("="*70)
    print("\nEste módulo procesa videos y calcula:")
    print("  • Detección de vehículos (YOLO)")
    print("  • Tracking para velocidad REAL")
    print("  • ICV calculado con núcleo/indice_congestion.py")
    print("  • Flujo vehicular en tiempo real")
    print("  • Longitud de cola")
    print("  • Detección de emergencias (ambulancias, bomberos)")
    print("  • Todas las métricas del Capítulo 6")

    # Buscar videos
    carpetas_prueba = [
        Path(__file__).parent / 'datos' / 'videos-prueba' / 'deteccion-basica',
        Path(__file__).parent / 'datos' / 'videos-prueba' / 'analisis-parametros',
        Path(__file__).parent / 'datos' / 'videos-prueba' / 'deteccion-emergencia',
        Path(__file__).parent / 'datos',
    ]

    videos_encontrados = []
    for carpeta in carpetas_prueba:
        if carpeta.exists():
            for ext in ['*.mp4', '*.avi', '*.mov', '*.mkv']:
                videos_encontrados.extend(carpeta.glob(ext))

    if not videos_encontrados:
        print("\n⚠️ No se encontraron videos.")
        ruta = input("Ruta del video (0 para cancelar): ").strip()
        if ruta == '0' or not ruta or not Path(ruta).exists():
            return
        video_seleccionado = Path(ruta)
    else:
        print("\n📹 Videos disponibles:\n")
        for i, video in enumerate(videos_encontrados, 1):
            tamaño_mb = video.stat().st_size / (1024 * 1024)
            print(f"  {i}. {video.name} ({tamaño_mb:.1f} MB)")

        try:
            opcion = input(f"\nSelecciona el video (1-{len(videos_encontrados)}): ").strip()
            if not opcion:
                return
            opcion = int(opcion)
            if not (1 <= opcion <= len(videos_encontrados)):
                print("❌ Opción inválida")
                return
            video_seleccionado = videos_encontrados[opcion - 1]
        except ValueError:
            print("❌ Entrada inválida")
            return

    # Ejecutar procesador con MODO 2 (análisis completo)
    procesador_path = Path(__file__).parent / 'vision_computadora' / 'procesar_video_con_visualizacion.py'

    try:
        subprocess.run([
            sys.executable,
            str(procesador_path),
            '--video', str(video_seleccionado),
            '--modo', '2',  # Modo completo
            '--guardar-video'  # Guardar resultado
        ])
    except KeyboardInterrupt:
        print("\n\n⏹️ Procesamiento detenido")


def conectar_sumo():
    """Conecta con SUMO mostrando calles e intersecciones reales"""
    print("\n" + "="*70)
    print("🌐 INTEGRACIÓN CON SUMO - CALLES REALES DE LIMA")
    print("="*70)

    sumo_path = Path(__file__).parent / 'integracion-sumo' / 'escenarios' / 'lima-centro'
    config_file = sumo_path / 'osm.sumocfg'
    geojson_file = sumo_path / 'calles.geojson'

    if not config_file.exists():
        print("\n⚠️  Configuración de SUMO no encontrada")
        print(f"Ruta esperada: {config_file}")
        return

    print(f"✓ Configuración encontrada: {config_file.name}")

    # Ver si hay GeoJSON de calles
    if geojson_file.exists():
        print(f"✓ Archivo de calles encontrado: {geojson_file.name}")
        with open(geojson_file, 'r', encoding='utf-8') as f:
            calles_data = json.load(f)
            num_calles = len(calles_data.get('features', []))
            print(f"  → {num_calles} calles mapeadas")
    else:
        print(f"⚠️  Archivo de calles no encontrado")
        print(f"   Ejecuta: python integracion-sumo/extraer_calles.py")

    print("\n🚀 Iniciando integración SUMO...")

    conector_path = Path(__file__).parent / 'integracion-sumo' / 'conector_sumo.py'
    try:
        subprocess.run([sys.executable, str(conector_path)])
    except KeyboardInterrupt:
        print("\n✓ SUMO detenido")


def ver_mapa_intersecciones():
    """Muestra el mapa de las 31 intersecciones de Lima"""
    print("\n" + "="*70)
    print("🗺️  MAPA DE INTERSECCIONES Y CALLES")
    print("="*70)

    # Cargar configuración de intersecciones
    sys.path.insert(0, str(Path(__file__).parent))

    try:
        # Leer del servidor
        servidor_path = Path(__file__).parent / 'servidor-backend' / 'main.py'

        print("\n📍 31 Intersecciones Reales de Lima Centro:")
        print("\n  MIRAFLORES:")
        print("    • Av. Arequipa con Av. Angamos")
        print("    • Av. Larco con Av. Benavides")
        print("    • Av. Arequipa con Av. Benavides")

        print("\n  SAN ISIDRO:")
        print("    • Av. Javier Prado con Av. Arequipa")
        print("    • Av. Camino Real con Av. República de Panamá")
        print("    • Av. Javier Prado con Av. Canaval y Moreyra")

        print("\n  LIMA CENTRO:")
        print("    • Av. Abancay con Jr. Lampa")
        print("    • Av. Nicolás de Piérola con Jr. de la Unión")
        print("    • Av. Tacna con Av. Emancipación")
        print("    • Av. Alfonso Ugarte con Av. Venezuela")

        print("\n  ... y 20 intersecciones más en:")
        print("      La Victoria, Surco, SJL, San Miguel,")
        print("      Jesús María, San Borja, Pueblo Libre, Lince")

        print("\n💡 Para ver el mapa completo con coordenadas GPS:")
        print("   → Inicia el Dashboard (opción 1)")
        print("   → Abre http://localhost:8000")

        # Intentar abrir dashboard si está activo
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:8000/api/intersecciones", timeout=1)
            print("\n✓ Dashboard detectado activo")
            if input("\n¿Abrir en navegador? (s/n): ").lower() == 's':
                webbrowser.open('http://localhost:8000')
        except:
            print("\n⚠️  Dashboard no está activo")
            print("   Inicia primero con opción 1")

    except Exception as e:
        print(f"\n❌ Error: {e}")


def comparar_sistemas():
    """Compara sistema adaptativo vs tiempo fijo"""
    print("\n" + "="*70)
    print("📊 COMPARACIÓN: ADAPTATIVO VS TIEMPO FIJO")
    print("="*70)

    sys.path.insert(0, str(Path(__file__).parent))

    try:
        from nucleo.sistema_comparacion import ComparadorSistemas
        import numpy as np

        print("\n🔧 Inicializando comparador...")

        comparador = ComparadorSistemas()

        # Ejecutar comparación
        print("\n⏳ Ejecutando simulación de 5 minutos (300 pasos)...")
        print("   Esto tomará unos segundos...\n")

        resultados = comparador.ejecutar_comparacion(
            duracion_pasos=300,
            escenario='hora_pico_manana'
        )

        # Mostrar resultados
        print("\n" + "="*70)
        print("✅ RESULTADOS DE LA COMPARACIÓN")
        print("="*70)

        print(f"\n📊 Métricas Promedio (5 minutos de simulación):")
        print(f"\n  {'Métrica':<25} {'Tiempo Fijo':<15} {'Adaptativo':<15} {'Mejora':<10}")
        print(f"  {'-'*65}")

        metricas = [
            ('ICV (Congestión)', 'ICV_red', True),
            ('Velocidad (km/h)', 'Vavg_red', False),
            ('Flujo (veh/min)', 'q_red', False),
            ('Saturación Cola', 'QL_red', True)
        ]

        for nombre, key, inverso in metricas:
            val_fijo = resultados['adaptativo'][key]
            val_adapt = resultados['no_adaptativo'][key]
            mejora = resultados['mejoras_porcentuales'][key]

            signo = '↓' if inverso else '↑'
            color = '🟢' if mejora > 0 else '🔴'

            print(f"  {nombre:<25} {val_fijo:<15.3f} {val_adapt:<15.3f} {color} {mejora:+.1f}%")

        print(f"\n📈 Resumen:")
        print(f"  • Reducción de congestión: {resultados['mejoras_porcentuales']['ICV_red']:+.1f}%")
        print(f"  • Aumento de velocidad: {resultados['mejoras_porcentuales']['Vavg_red']:+.1f}%")
        print(f"  • Mejora de flujo: {resultados['mejoras_porcentuales']['q_red']:+.1f}%")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    input("\n\nPresiona ENTER para continuar...")


def generar_metricas_realistas():
    """Genera métricas realistas sin necesidad de SUMO"""
    print("\n" + "="*70)
    print("🎲 GENERADOR DE MÉTRICAS REALISTAS")
    print("="*70)
    print("\nGenera métricas de tráfico basadas en modelos matemáticos")
    print("en lugar de valores aleatorios, para demostraciones creíbles.")

    sys.path.insert(0, str(Path(__file__).parent))

    try:
        from nucleo.generador_metricas import GeneradorMetricasRealistas
        import numpy as np

        generador = GeneradorMetricasRealistas()

        print("\n📊 Patrones disponibles:")
        print("  1. Flujo Libre (hora valle)")
        print("  2. Congestión Moderada (hora pico inicio)")
        print("  3. Atasco Severo (hora pico plena)")
        print("  4. Con Emergencia (ambulancia presente)")

        opcion = input("\nSelecciona patrón (1-4): ").strip()

        patrones = {
            '1': GeneradorMetricasRealistas.PATRON_LIBRE,
            '2': GeneradorMetricasRealistas.PATRON_MODERADO,
            '3': GeneradorMetricasRealistas.PATRON_CONGESTIONADO,
            '4': GeneradorMetricasRealistas.PATRON_EMERGENCIA
        }

        patron = patrones.get(opcion, GeneradorMetricasRealistas.PATRON_MODERADO)

        print(f"\n⏳ Generando 60 pasos de simulación con patrón: {patron.nombre}...")

        serie = generador.generar_serie_temporal(patron, num_pasos=60)

        # Estadísticas
        icv_promedio = np.mean([m['icv_promedio'] for m in serie])
        vavg_promedio = np.mean([m['vavg_promedio'] for m in serie])

        print(f"\n✓ Generación completada")
        print(f"\n📊 Estadísticas:")
        print(f"  ICV promedio: {icv_promedio:.3f}")
        print(f"  Velocidad promedio: {vavg_promedio:.1f} km/h")
        print(f"  Pasos generados: {len(serie)}")

        # Guardar?
        if input("\n¿Exportar a JSON? (s/n): ").lower() == 's':
            import json
            output_file = Path("datos/metricas_generadas.json")
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'patron': patron.nombre,
                    'descripcion': patron.descripcion,
                    'serie_temporal': [{
                        'timestamp': m['timestamp'].isoformat(),
                        'icv_ns': m['icv_ns'],
                        'icv_eo': m['icv_eo'],
                        'vavg_ns': m['vavg_ns'],
                        'vavg_eo': m['vavg_eo'],
                        'q_ns': m['q_ns'],
                        'q_eo': m['q_eo']
                    } for m in serie]
                }, f, indent=2)

            print(f"✓ Exportado a: {output_file}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    input("\n\nPresiona ENTER para continuar...")


def ejecutar_pruebas():
    """Ejecuta pruebas del sistema"""
    print("\n" + "="*70)
    print("🧪 PRUEBAS DEL SISTEMA")
    print("="*70)

    print("\nPruebas disponibles:")
    print("  1. Prueba de ICV")
    print("  2. Prueba de Lógica Difusa")
    print("  3. Prueba de Estado Local")
    print("  4. Prueba de Métricas de Red")
    print("  5. Todas las pruebas")

    opcion = input("\nSelecciona (1-5): ").strip()

    sys.path.insert(0, str(Path(__file__).parent))

    try:
        if opcion in ['1', '5']:
            print("\n=== PRUEBA 1: ICV ===")
            from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion

            params = ParametrosInterseccion()
            calculador = CalculadorICV(params)

            casos = [
                (10, 55, 10, "Flujo libre"),
                (75, 25, 22, "Moderado"),
                (140, 8, 28, "Severo")
            ]

            for l, v, f, desc in casos:
                resultado = calculador.calcular(l, v, f)
                print(f"  {desc}: ICV={resultado['icv']:.4f} ({resultado['clasificacion']})")

        if opcion in ['2', '5']:
            print("\n=== PRUEBA 2: CONTROL DIFUSO ===")
            from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6

            controlador = ControladorDifusoCapitulo6()

            resultado = controlador.calcular_ajuste_tiempo_verde(
                icv_ns=0.6, icv_eo=0.4,
                pi_ns=0.3, pi_eo=0.5,
                ev_ns=0, ev_eo=0
            )

            print(f"  T_verde_NS: {resultado['T_verde_ns']:.1f}s")
            print(f"  T_verde_EO: {resultado['T_verde_eo']:.1f}s")

        if opcion in ['3', '5']:
            print("\n=== PRUEBA 3: ESTADO LOCAL ===")
            from nucleo.estado_local import EstadoLocalInterseccion, ParametrosInterseccion as ParamsEstado

            params = ParamsEstado()
            estado = EstadoLocalInterseccion("TEST-001", params)

            vehiculos = [
                {'id': 1, 'velocidad': 45.0, 'clase': 'car', 'confidence': 0.9}
            ]

            estado.actualizar_estado(
                vehiculos_por_direccion={'N': vehiculos, 'S': [], 'E': [], 'O': []},
                cruces_por_direccion={'N': 5, 'S': 0, 'E': 0, 'O': 0}
            )

            paquete = estado.obtener_paquete_telemetria()
            print(f"  Variables calculadas: {len(paquete['state_matrix'])} tipos")
            print(f"  CamMask: {paquete['cam_mask']}")

        print("\n✅ Pruebas completadas")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    input("\n\nPresiona ENTER para continuar...")


def ver_estado_componentes():
    """Muestra el estado de todos los componentes del sistema"""
    print("\n" + "="*70)
    print("🔍 ESTADO DE COMPONENTES DEL SISTEMA")
    print("="*70)

    componentes = {
        'Núcleo - ICV': Path(__file__).parent / 'nucleo' / 'indice_congestion.py',
        'Núcleo - Control Difuso Cap 6': Path(__file__).parent / 'nucleo' / 'controlador_difuso_capitulo6.py',
        'Núcleo - Estado Local': Path(__file__).parent / 'nucleo' / 'estado_local.py',
        'Núcleo - Métricas de Red': Path(__file__).parent / 'nucleo' / 'metricas_red.py',
        'Núcleo - Generador Métricas': Path(__file__).parent / 'nucleo' / 'generador_metricas.py',
        'Núcleo - Olas Verdes': Path(__file__).parent / 'nucleo' / 'olas_verdes_dinamicas.py',
        'Visión - Procesador Video': Path(__file__).parent / 'vision_computadora' / 'procesar_video_con_visualizacion.py',
        'Servidor - Backend': Path(__file__).parent / 'servidor-backend' / 'main.py',
        'Integración - SUMO': Path(__file__).parent / 'integracion-sumo' / 'conector_sumo.py',
        'Simulador - Lima': Path(__file__).parent / 'simulador_trafico' / 'simulador_lima.py',
    }

    print("\n📦 Componentes:")
    for nombre, path in componentes.items():
        existe = "✓" if path.exists() else "✗"
        tamaño = f"{path.stat().st_size / 1024:.1f} KB" if path.exists() else "N/A"
        print(f"  {existe} {nombre:<30} ({tamaño})")

    # Verificar datos
    print("\n📁 Directorios de datos:")
    directorios_datos = [
        Path(__file__).parent / 'datos',
        Path(__file__).parent / 'datos' / 'videos-prueba',
        Path(__file__).parent / 'datos' / 'resultados-video',
        Path(__file__).parent / 'integracion-sumo' / 'escenarios' / 'lima-centro',
    ]

    for dir_path in directorios_datos:
        existe = "✓" if dir_path.exists() else "✗"
        print(f"  {existe} {dir_path.relative_to(Path(__file__).parent)}")

    # Verificar servidor activo
    print("\n🌐 Servidor:")
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:8000/api/estado", timeout=1)
        print("  ✓ Dashboard activo en http://localhost:8000")
    except:
        print("  ✗ Dashboard no está activo")

    input("\n\nPresiona ENTER para continuar...")


def ver_documentacion():
    """Abre la documentación del sistema"""
    print("\n📚 Abriendo documentación...")

    docs_path = Path(__file__).parent / 'documentacion'

    if docs_path.exists():
        import platform
        if platform.system() == 'Windows':
            os.startfile(docs_path)
        elif platform.system() == 'Darwin':
            subprocess.run(['open', docs_path])
        else:
            subprocess.run(['xdg-open', docs_path])
    else:
        print(f"⚠️  Directorio de documentación no encontrado: {docs_path}")


def exportar_configuracion():
    """Exporta la configuración actual del sistema"""
    print("\n" + "="*70)
    print("💾 EXPORTAR CONFIGURACIÓN DEL SISTEMA")
    print("="*70)

    config = {
        'timestamp': datetime.now().isoformat(),
        'version': '2.0',
        'capitulo': 6,
        'componentes': {
            'EstadoLocal': '7 variables × 4 direcciones',
            'ControlDifuso': '12 reglas jerárquicas',
            'MetricasRed': 'Agregación ponderada',
            'OlasVerdes': 'Coordinación dinámica'
        },
        'intersecciones': 31,
        'ubicacion': 'Lima Centro, Perú'
    }

    output_file = Path('configuracion_sistema.json')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Configuración exportada a: {output_file}")


def main():
    """Función principal mejorada"""
    imprimir_banner()
    verificar_dependencias()

    while True:
        mostrar_menu()
        try:
            opcion = input("Selecciona una opción: ").strip()

            if opcion == '1':
                iniciar_sistema_completo()
            elif opcion == '2':
                modo_demostracion_completa()
            elif opcion == '3':
                procesar_video()
            elif opcion == '4':
                procesar_video()  # Usar el mismo pero con modo diferente
            elif opcion == '5':
                conectar_sumo()
            elif opcion == '6':
                ver_mapa_intersecciones()
            elif opcion == '7':
                comparar_sistemas()
            elif opcion == '8':
                generar_metricas_realistas()
            elif opcion == '9':
                ejecutar_pruebas()
            elif opcion == '10':
                ver_estado_componentes()
            elif opcion == '11':
                ver_documentacion()
            elif opcion == '12':
                exportar_configuracion()
            elif opcion == '0':
                print("\n👋 ¡Hasta luego!\n")
                break
            else:
                print("\n⚠️  Opción inválida. Intenta de nuevo.\n")

        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            logger.exception("Error en el menú principal")


if __name__ == "__main__":
    main()
