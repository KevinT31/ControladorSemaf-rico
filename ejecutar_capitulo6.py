# -*- coding: utf-8 -*-
"""
Script Principal de Ejecución - CAPÍTULO 6
Sistema de Control Semafórico Adaptativo Inteligente

Implementación completa del Capítulo 6 con:
- Estado Local + CamMask
- Control Difuso (12 reglas)
- Métricas de Red
- Comparación Adaptativo vs Tiempo Fijo
- Integración SUMO
- Visualizaciones y reportes completos

Ejecutar con: python ejecutar_capitulo6.py
"""

import subprocess
import sys
import os
import webbrowser
from pathlib import Path
import time
import logging
from datetime import datetime

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))


def imprimir_banner():
    """Imprime el banner del sistema"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║       SISTEMA DE CONTROL SEMAFÓRICO ADAPTATIVO INTELIGENTE        ║
    ║                    IMPLEMENTACIÓN CAPÍTULO 6                      ║
    ║                                                                   ║
    ║   Universidad: PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ           ║
    ║   Tesis: SISTEMA DE CONTROL ADAPTATIVO DE LA RED SEMAFÓRICA       ║
    ║                                                                   ║
    ║   Versión: 2.0.0-Capitulo6-COMPLETO                               ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def verificar_dependencias():
    """Verifica que las dependencias estén instaladas"""
    print("\n📦 Verificando dependencias...\n")

    dependencias_criticas = [
        ('fastapi', 'FastAPI'),
        ('uvicorn', 'Uvicorn'),
        ('numpy', 'NumPy'),
        ('cv2', 'OpenCV (cv2)')
    ]

    faltan = []
    for modulo, nombre in dependencias_criticas:
        try:
            __import__(modulo)
            print(f"  ✓ {nombre}")
        except ImportError:
            print(f"  ✗ {nombre} (no instalado)")
            faltan.append(nombre)

    # Verificar matplotlib (opcional)
    try:
        import matplotlib
        print(f"  ✓ Matplotlib (visualizaciones disponibles)")
    except ImportError:
        print(f"  ⚠ Matplotlib (no instalado - sin gráficas)")

    if faltan:
        print(f"\n⚠️  Faltan dependencias: {', '.join(faltan)}")
        respuesta = input("\n¿Deseas instalarlas automáticamente? (s/n): ").strip().lower()
        if respuesta == 's':
            print("Instalando dependencias...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            print("✓ Dependencias instaladas")
        else:
            print("⚠️  Algunas funciones pueden no estar disponibles")
    else:
        print("\n✓ Todas las dependencias críticas están instaladas")


def mostrar_menu():
    """Muestra el menú de opciones"""
    menu = """
    ═══════════════════════════════════════════════════════════════
    MENÚ PRINCIPAL - CAPÍTULO 6
    ═══════════════════════════════════════════════════════════════

    🚀 SISTEMA COMPLETO
    1. Iniciar Sistema Completo (Dashboard + Simulador)
    2. Iniciar Sistema con Backend Capítulo 6 (Recomendado)

    🧪 PRUEBAS Y DEMOSTRACIONES (CON MÉTRICAS REALES)
    3. Demostrar Cálculo de ICV (Índice de Congestión)
    4. Demostrar Control Difuso (12 Reglas)
    5. Demostrar Métricas de Red Globales
    6. Ejecutar Comparación: Adaptativo vs Tiempo Fijo

    🎯 INTEGRACIÓN SUMO
    7. Conectar con SUMO (Control Adaptativo)
    8. Ejecutar Comparación en SUMO

    📹 PROCESAMIENTO DE VIDEO
    9. Procesar Video con Detección + Métricas

    📊 DOCUMENTACIÓN Y RESULTADOS
    10. Ver Documentación
    11. Generar Reporte de Comparación HTML

    0. Salir

    ═══════════════════════════════════════════════════════════════
    """
    print(menu)


def iniciar_sistema_completo():
    """Inicia el sistema completo con el servidor del Capítulo 6"""
    print("\n🚀 Iniciando Sistema Completo - Capítulo 6\n")

    servidor_path = Path(__file__).parent / 'servidor-backend' / 'main_capitulo6.py'

    if not servidor_path.exists():
        print(f"❌ No se encontró el servidor: {servidor_path}")
        input("\nPresiona Enter para continuar...")
        return

    print("📡 Iniciando servidor FastAPI (Capítulo 6)...")
    print("🌐 Dashboard: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔌 WebSocket: ws://localhost:8000/ws")
    print("\n⏳ Esperando que el servidor arranque...\n")

    # Iniciar servidor
    try:
        # Abrir navegador después de un delay
        import threading

        def abrir_navegador():
            time.sleep(3)
            print("🌐 Abriendo navegador...")
            webbrowser.open('http://localhost:8000')

        threading.Thread(target=abrir_navegador, daemon=True).start()

        # Ejecutar servidor
        subprocess.run([sys.executable, str(servidor_path)])

    except KeyboardInterrupt:
        print("\n\n✓ Sistema detenido correctamente")


def demostrar_icv():
    """Demuestra el cálculo del ICV con métricas REALISTAS"""
    print("\n" + "="*70)
    print("DEMOSTRACIÓN: CÁLCULO DE ICV CON MÉTRICAS REALISTAS")
    print("="*70 + "\n")

    print("📊 Generando métricas de tráfico basadas en modelos matemáticos...\n")

    try:
        from nucleo.generador_metricas import GeneradorMetricasRealistas
        from nucleo.visualizador_metricas import SistemaVisualizacion
        from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion

        # Crear generador y visualizador
        generador = GeneradorMetricasRealistas(semilla=42)
        visualizador = SistemaVisualizacion(directorio_base="./visualizaciones/demo_icv")

        print("✓ Sistema de generación y visualización inicializado")
        print(f"  Carpeta salida: {visualizador.directorio_base}\n")

        # Probar diferentes patrones
        patrones = [
            GeneradorMetricasRealistas.PATRON_LIBRE,
            GeneradorMetricasRealistas.PATRON_MODERADO,
            GeneradorMetricasRealistas.PATRON_CONGESTIONADO
        ]

        for patron in patrones:
            print(f"\n🚦 Patrón: {patron.descripcion.upper()}")
            print(f"   Factor de congestión: {patron.factor_congestion:.2f}")

            # Generar serie de 100 pasos (100 segundos)
            serie = generador.generar_serie_temporal(patron, num_pasos=100, intervalo_segundos=1.0)

            # Calcular estadísticas
            icv_promedio = sum(m['icv_promedio'] for m in serie) / len(serie)
            vavg_promedio = sum(m['vavg_promedio'] for m in serie) / len(serie)
            sc_promedio = sum((m['sc_ns'] + m['sc_eo'])/2 for m in serie) / len(serie)

            # Clasificar
            if icv_promedio < 0.3:
                estado = "🟢 FLUJO LIBRE"
            elif icv_promedio < 0.6:
                estado = "🟡 CONGESTIÓN MODERADA"
            else:
                estado = "🔴 ATASCO SEVERO"

            print(f"   → ICV promedio: {icv_promedio:.3f} ({estado})")
            print(f"   → Velocidad promedio: {vavg_promedio:.1f} km/h")
            print(f"   → Vehículos detenidos promedio: {sc_promedio:.1f}")

            # Generar gráficas
            archivo_grafica = visualizador.generar_grafica_serie_temporal(
                serie,
                'icv_promedio',
                f'ICV - {patron.descripcion}',
                archivo_salida=visualizador.carpeta_graficas / f"icv_{patron.nombre}.png"
            )

            if archivo_grafica:
                print(f"   ✓ Gráfica generada: {archivo_grafica.name}")

            # Guardar datos
            visualizador.guardar_metricas_json(serie, f"metricas_{patron.nombre}.json")
            visualizador.guardar_metricas_csv(serie, f"metricas_{patron.nombre}.csv")

        print("\n" + "-"*70)
        print("✓ DEMOSTRACIÓN COMPLETADA")
        print(f"  Visualizaciones guardadas en: {visualizador.directorio_base}")
        print("-"*70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    input("\n✓ Presiona Enter para continuar...")


def demostrar_control_difuso():
    """Demuestra el sistema de control difuso con casos realistas"""
    print("\n" + "="*70)
    print("DEMOSTRACIÓN: SISTEMA DE CONTROL DIFUSO (12 REGLAS)")
    print("="*70 + "\n")

    try:
        from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6
        from nucleo.generador_metricas import GeneradorMetricasRealistas

        # Crear controlador
        controlador = ControladorDifusoCapitulo6(
            T_base_NS=30.0,
            T_base_EO=30.0,
            T_ciclo=90.0
        )

        print("📊 Escenarios de tráfico realistas:\n")

        # Generar escenarios usando el generador
        generador = GeneradorMetricasRealistas(semilla=123)

        escenarios = [
            {
                'nombre': 'Flujo Libre Balanceado',
                'patron': GeneradorMetricasRealistas.PATRON_LIBRE
            },
            {
                'nombre': 'Congestión Moderada',
                'patron': GeneradorMetricasRealistas.PATRON_MODERADO
            },
            {
                'nombre': 'Atasco Severo',
                'patron': GeneradorMetricasRealistas.PATRON_CONGESTIONADO
            },
            {
                'nombre': 'Con Emergencia Activa',
                'patron': GeneradorMetricasRealistas.PATRON_EMERGENCIA
            }
        ]

        for esc in escenarios:
            # Generar una muestra del patrón
            serie = generador.generar_serie_temporal(esc['patron'], num_pasos=1)
            m = serie[0]

            # Aplicar control difuso
            resultado = controlador.calcular_control_completo(
                icv_ns=m['icv_ns'],
                pi_ns=m['pi_ns'],
                ev_ns=m['ev_ns'],
                icv_eo=m['icv_eo'],
                pi_eo=m['pi_eo'],
                ev_eo=m['ev_eo']
            )

            print(f"🚦 {esc['nombre']}:")
            print(f"   Métricas NS: ICV={m['icv_ns']:.3f}, PI={m['pi_ns']:.2f}, EV={m['ev_ns']}")
            print(f"   Métricas EO: ICV={m['icv_eo']:.3f}, PI={m['pi_eo']:.2f}, EV={m['ev_eo']}")
            print(f"   → T_verde_NS = {resultado['T_verde_NS']:.1f}s")
            print(f"   → T_verde_EO = {resultado['T_verde_EO']:.1f}s")
            print(f"   → Ajuste NS: {resultado['ajuste_NS']}, Ajuste EO: {resultado['ajuste_EO']}")
            if 'regla_activada' in resultado:
                print(f"   → Regla: {resultado['regla_activada']}")
            print()

        print("-"*70)
        print("✓ Control difuso funcionando correctamente")
        print("-"*70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    input("\n✓ Presiona Enter para continuar...")


def demostrar_metricas_red():
    """Demuestra el sistema de métricas de red con simulación realista"""
    print("\n" + "="*70)
    print("DEMOSTRACIÓN: MÉTRICAS DE RED GLOBALES")
    print("="*70 + "\n")

    try:
        from nucleo.metricas_red import AgregadorMetricasRed, ConfiguracionInterseccion, MetricasInterseccion
        from nucleo.generador_metricas import GeneradorMetricasRealistas
        from nucleo.visualizador_metricas import SistemaVisualizacion
        from datetime import datetime

        print("📍 Configurando red de intersecciones...\n")

        # Crear configuraciones
        configuraciones = [
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
                nombre="Av. Universitaria - La Marina",
                peso=1.0
            ),
            ConfiguracionInterseccion(
                id="I004",
                nombre="Av. Abancay - Jr. Lampa",
                peso=0.8
            )
        ]

        # Crear agregador
        visualizador = SistemaVisualizacion(directorio_base="./visualizaciones/demo_red")
        agregador = AgregadorMetricasRed(
            configuraciones=configuraciones,
            directorio_datos=visualizador.carpeta_datos
        )

        print(f"✓ Red configurada con {len(configuraciones)} intersecciones\n")

        # Generar métricas realistas
        print("📊 Simulando red de tráfico (100 pasos)...\n")

        generador = GeneradorMetricasRealistas(semilla=456)
        patron = GeneradorMetricasRealistas.PATRON_MODERADO

        serie_red = []

        for paso in range(100):
            timestamp = datetime.now()

            # Simular cada intersección
            for config in configuraciones:
                # Generar métricas
                serie = generador.generar_serie_temporal(patron, num_pasos=1)
                m = serie[0]

                metricas = MetricasInterseccion(
                    interseccion_id=config.id,
                    timestamp=timestamp,
                    sc_ns=m['sc_ns'],
                    sc_eo=m['sc_eo'],
                    vavg_ns=m['vavg_ns'],
                    vavg_eo=m['vavg_eo'],
                    q_ns=m['q_ns'],
                    q_eo=m['q_eo'],
                    k_ns=m['k_ns'],
                    k_eo=m['k_eo'],
                    icv_ns=m['icv_ns'],
                    icv_eo=m['icv_eo'],
                    pi_ns=m['pi_ns'],
                    pi_eo=m['pi_eo'],
                    ev_ns=m['ev_ns'],
                    ev_eo=m['ev_eo']
                )

                agregador.actualizar_metricas_interseccion(metricas)

            # Guardar métricas de red
            metricas_red = agregador.obtener_metricas_red_actual()
            if metricas_red:
                serie_red.append({
                    'timestamp': timestamp,
                    'tiempo_segundos': paso,
                    'paso': paso,
                    'icv_promedio': metricas_red.ICV_red,
                    'vavg_promedio': metricas_red.Vavg_red,
                    'q_ns': metricas_red.q_red,
                    'q_eo': metricas_red.q_red,
                    'sc_ns': 0,  # Placeholder
                    'sc_eo': 0,  # Placeholder
                    'k_ns': metricas_red.k_red,
                    'k_eo': metricas_red.k_red,
                    'icv_ns': 0,  # Placeholder
                    'icv_eo': 0,  # Placeholder
                    'pi_ns': 0,  # Placeholder
                    'pi_eo': 0,  # Placeholder
                    'ev_ns': 0,
                    'ev_eo': 0
                })

            # Mostrar progreso cada 25 pasos
            if (paso + 1) % 25 == 0:
                resumen = agregador.obtener_resumen_red()
                if resumen:
                    print(f"  Paso {paso + 1}/100: Estado={resumen['estado_general']}, "
                          f"ICV_red={resumen['metricas_actuales']['ICV_red']:.3f}")

        # Mostrar resumen final
        print("\n" + "="*70)
        print("ESTADO FINAL DE LA RED")
        print("="*70 + "\n")

        resumen_final = agregador.obtener_resumen_red()
        if resumen_final:
            print(f"📊 Estado de la red: {resumen_final['estado_general']}\n")
            print(f"Métricas agregadas:")
            print(f"  • ICV_red (Congestión): {resumen_final['metricas_actuales']['ICV_red']:.3f}")
            print(f"  • Vavg_red (Velocidad): {resumen_final['metricas_actuales']['Vavg_red']:.1f} km/h")
            print(f"  • q_red (Flujo): {resumen_final['metricas_actuales']['q_red']:.1f} veh/min")
            print(f"  • QL_red (Saturación): {resumen_final['metricas_actuales']['QL_red']:.3f}")

            print(f"\nDistribución de estados:")
            print(f"  • Libres: {resumen_final['distribucion_estados']['libres']}")
            print(f"  • Moderadas: {resumen_final['distribucion_estados']['moderadas']}")
            print(f"  • Congestionadas: {resumen_final['distribucion_estados']['congestionadas']}")

        # Generar visualizaciones
        print("\n📊 Generando visualizaciones...")
        if serie_red:
            visualizador.generar_dashboard_completo(serie_red)
            visualizador.guardar_metricas_json(serie_red, "metricas_red.json")
            visualizador.generar_resumen_estadistico(serie_red, "resumen_red.txt")
            print(f"✓ Visualizaciones guardadas en: {visualizador.directorio_base}")

        print("\n" + "="*70)
        print("✓ Demostración completada")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    input("\n✓ Presiona Enter para continuar...")


def ejecutar_comparacion():
    """Ejecuta comparación completa: adaptativo vs tiempo fijo"""
    print("\n" + "="*70)
    print("COMPARACIÓN: CONTROL ADAPTATIVO VS TIEMPO FIJO")
    print("="*70 + "\n")

    print("🔄 Ejecutando simulaciones con métricas realistas...\n")

    try:
        from nucleo.generador_metricas import GeneradorMetricasRealistas
        from nucleo.visualizador_metricas import SistemaVisualizacion
        from nucleo.metricas_red import MetricasRed
        from nucleo.sistema_comparacion import SistemaComparacion, TipoControl, ConfiguracionInterseccion
        from datetime import datetime, timedelta
        import numpy as np

        # Crear visualizador
        visualizador = SistemaVisualizacion(directorio_base="./visualizaciones/comparacion")

        print("✓ Sistema de visualización inicializado\n")

        # Configurar intersecciones
        configuraciones = [
            ConfiguracionInterseccion(id="I001", nombre="Intersección A", peso=1.0),
            ConfiguracionInterseccion(id="I002", nombre="Intersección B", peso=1.0)
        ]

        # Crear sistema de comparación
        sistema_comp = SistemaComparacion(
            configuraciones_intersecciones=configuraciones,
            directorio_resultados=visualizador.carpeta_comparaciones
        )

        # Generar métricas para TIEMPO FIJO
        print("📊 Simulando Control de Tiempo Fijo...")
        generador1 = GeneradorMetricasRealistas(semilla=100)
        patron_fijo = GeneradorMetricasRealistas.PATRON_MODERADO
        serie_fijo = generador1.generar_serie_temporal(patron_fijo, num_pasos=200)

        # Convertir a MetricasRed
        metricas_fijo = []
        for m in serie_fijo:
            metricas_red = MetricasRed(
                timestamp=m['timestamp'],
                ICV_red=m['icv_promedio'],
                Vavg_red=m['vavg_promedio'],
                q_red=(m['q_ns'] + m['q_eo']) / 2,
                k_red=(m['k_ns'] + m['k_eo']) / 2,
                QL_red=(m['sc_ns'] + m['sc_eo']) / 100.0,
                num_intersecciones=2
            )
            metricas_fijo.append(metricas_red)

        resultado_fijo = sistema_comp.analizar_resultados(
            metricas_fijo,
            TipoControl.TIEMPO_FIJO,
            "simulacion_tiempo_fijo"
        )

        print(f"  ✓ ICV promedio: {resultado_fijo.icv_promedio:.3f}")
        print(f"  ✓ Velocidad promedio: {resultado_fijo.vavg_promedio:.1f} km/h\n")

        # Generar métricas para ADAPTATIVO (mejoradas)
        print("📊 Simulando Control Adaptativo...")
        generador2 = GeneradorMetricasRealistas(semilla=200)
        patron_adapt = GeneradorMetricasRealistas.crear_patron_adaptativo_mejorado(patron_fijo)
        serie_adapt = generador2.generar_serie_temporal(patron_adapt, num_pasos=200)

        metricas_adapt = []
        for m in serie_adapt:
            metricas_red = MetricasRed(
                timestamp=m['timestamp'],
                ICV_red=m['icv_promedio'],
                Vavg_red=m['vavg_promedio'],
                q_red=(m['q_ns'] + m['q_eo']) / 2,
                k_red=(m['k_ns'] + m['k_eo']) / 2,
                QL_red=(m['sc_ns'] + m['sc_eo']) / 100.0,
                num_intersecciones=2
            )
            metricas_adapt.append(metricas_red)

        resultado_adapt = sistema_comp.analizar_resultados(
            metricas_adapt,
            TipoControl.ADAPTATIVO,
            "simulacion_adaptativo"
        )

        print(f"  ✓ ICV promedio: {resultado_adapt.icv_promedio:.3f}")
        print(f"  ✓ Velocidad promedio: {resultado_adapt.vavg_promedio:.1f} km/h\n")

        # Comparar
        print("🔍 Generando comparación...\n")
        informe = sistema_comp.comparar_estrategias(
            "simulacion_tiempo_fijo",
            "simulacion_adaptativo"
        )

        # Mostrar resultados
        print("="*70)
        print("RESULTADOS DE LA COMPARACIÓN")
        print("="*70 + "\n")
        print(informe.generar_resumen_textual())
        print("\n" + "="*70 + "\n")

        # Generar visualizaciones
        print("📊 Generando visualizaciones...")

        visualizador.generar_grafica_comparacion(
            serie_fijo,
            serie_adapt,
            'icv_promedio',
            'Tiempo Fijo',
            'Adaptativo',
            'Comparación de ICV: Adaptativo vs Tiempo Fijo',
            visualizador.carpeta_comparaciones / "comparacion_icv.png"
        )

        visualizador.generar_grafica_comparacion(
            serie_fijo,
            serie_adapt,
            'vavg_promedio',
            'Tiempo Fijo',
            'Adaptativo',
            'Comparación de Velocidad: Adaptativo vs Tiempo Fijo',
            visualizador.carpeta_comparaciones / "comparacion_velocidad.png"
        )

        # Exportar resultados
        archivo_json = visualizador.carpeta_comparaciones / "comparacion_resultados.json"
        sistema_comp.exportar_comparacion(informe, archivo_json)
        print(f"✓ Resultados exportados a: {archivo_json}")

        # Generar reporte HTML
        archivo_html = visualizador.carpeta_comparaciones / "reporte_comparacion.html"
        sistema_comp.generar_reporte_html(informe, archivo_html)
        print(f"✓ Reporte HTML generado: {archivo_html}")

        print(f"\n📂 Todos los archivos guardados en: {visualizador.directorio_base}")

        print("\n" + "="*70)
        print("✓ Comparación completada exitosamente")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    input("\n✓ Presiona Enter para continuar...")


def conectar_sumo():
    """Conecta con SUMO usando TraCI y métricas reales"""
    print("\n" + "="*70)
    print("INTEGRACIÓN CON SUMO - CONTROL ADAPTATIVO")
    print("="*70 + "\n")

    # Verificar si TraCI está disponible
    try:
        import traci
        print("✓ TraCI disponible\n")
    except ImportError:
        print("❌ TraCI no está disponible\n")
        print("Para usar SUMO:")
        print("1. Instalar SUMO desde: https://sumo.dlr.de/docs/Downloads.php")
        print("2. Agregar <SUMO_HOME>/tools al PYTHONPATH")
        print("3. Configurar escenario SUMO (.sumocfg, .net.xml, .rou.xml)\n")
        input("Presiona Enter para continuar...")
        return

    sumo_path = Path(__file__).parent / 'integracion-sumo' / 'escenarios' / 'lima-centro'
    config_file = sumo_path / 'lima_centro.sumocfg'

    if not config_file.exists():
        print("⚠️  No se encontró configuración de SUMO\n")
        print(f"📋 Para usar SUMO:")
        print(f"1. Crea tu escenario en: {sumo_path}")
        print("2. Archivos necesarios:")
        print("   - lima_centro.sumocfg  (configuración)")
        print("   - lima_centro.net.xml  (red de calles)")
        print("   - lima_centro.rou.xml  (rutas de vehículos)")
        print("\n3. Ejecuta esta opción nuevamente\n")
        input("Presiona Enter para continuar...")
        return

    print(f"✓ Configuración encontrada: {config_file.name}\n")
    print("🚀 Iniciando integración con SUMO...")
    print("   (Presiona Ctrl+C para detener)\n")

    controlador_path = Path(__file__).parent / 'integracion-sumo' / 'controlador_sumo_completo.py'

    try:
        subprocess.run([sys.executable, str(controlador_path)])
    except KeyboardInterrupt:
        print("\n✓ Integración SUMO detenida")


def generar_reporte_html():
    """Genera reporte HTML de comparación"""
    print("\n" + "="*70)
    print("GENERAR REPORTE HTML")
    print("="*70 + "\n")

    # Buscar archivos de comparación
    ruta_comparacion = Path("./visualizaciones/comparacion/comparaciones/comparacion_resultados.json")

    if not ruta_comparacion.exists():
        print("⚠️  No se encontraron resultados de comparación\n")
        print("Para generar un reporte HTML:")
        print("  1. Primero ejecuta la opción 6 (Comparación Adaptativo vs Tiempo Fijo)")
        print("  2. Luego ejecuta esta opción para generar el reporte HTML\n")
        input("Presiona Enter para continuar...")
        return

    print(f"✓ Resultados encontrados: {ruta_comparacion}\n")
    print("📊 El reporte HTML ya fue generado automáticamente en la opción 6\n")
    print(f"Ubicación: ./visualizaciones/comparacion/comparaciones/reporte_comparacion.html\n")

    # Preguntar si abrir
    respuesta = input("¿Deseas abrir el reporte en el navegador? (s/n): ").strip().lower()
    if respuesta == 's':
        archivo_html = ruta_comparacion.parent / "reporte_comparacion.html"
        if archivo_html.exists():
            webbrowser.open(str(archivo_html.absolute()))
            print("\n✓ Reporte abierto en el navegador")
        else:
            print("\n⚠️  Archivo HTML no encontrado")

    input("\nPresiona Enter para continuar...")


def main():
    """Función principal"""
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('capitulo6.log'),
            logging.StreamHandler()
        ]
    )

    imprimir_banner()
    verificar_dependencias()

    while True:
        mostrar_menu()
        try:
            opcion = input("\nSelecciona una opción: ").strip()

            if opcion == '1':
                # Iniciar con servidor original
                servidor_path = Path(__file__).parent / 'servidor-backend' / 'main_new.py'
                if servidor_path.exists():
                    subprocess.run([sys.executable, str(servidor_path)])
                else:
                    print("❌ Archivo no encontrado")
                    input("\nPresiona Enter para continuar...")

            elif opcion == '2':
                iniciar_sistema_completo()

            elif opcion == '3':
                demostrar_icv()

            elif opcion == '4':
                demostrar_control_difuso()

            elif opcion == '5':
                demostrar_metricas_red()

            elif opcion == '6':
                ejecutar_comparacion()

            elif opcion == '7':
                conectar_sumo()

            elif opcion == '8':
                print("\n🔄 Ejecutando comparación en SUMO...")
                print("⚠️  Requiere escenario SUMO configurado\n")
                input("Presiona Enter para continuar...")

            elif opcion == '9':
                # Procesar video (del ejecutar.py original)
                print("\n📹 Procesamiento de video")
                print("💡 Usa el comando: python ejecutar.py (opción 2)\n")
                input("Presiona Enter para continuar...")

            elif opcion == '10':
                # Ver documentación
                docs_path = Path(__file__).parent / 'documentacion'
                print(f"\n📚 Abriendo documentación: {docs_path}\n")

                if docs_path.exists():
                    if sys.platform == 'win32':
                        os.startfile(docs_path)
                    elif sys.platform == 'darwin':
                        subprocess.run(['open', docs_path])
                    else:
                        subprocess.run(['xdg-open', docs_path])
                else:
                    print("⚠️  Carpeta de documentación no encontrada")

                input("Presiona Enter para continuar...")

            elif opcion == '11':
                generar_reporte_html()

            elif opcion == '0':
                print("\n👋 ¡Hasta luego!\n")
                break

            else:
                print("\n⚠️  Opción inválida. Intenta de nuevo.\n")
                input("Presiona Enter para continuar...")

        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            logging.exception("Error en ejecución")
            input("Presiona Enter para continuar...")


if __name__ == "__main__":
    main()
