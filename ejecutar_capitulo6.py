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

Ejecutar con: python ejecutar_capitulo6.py
"""

import subprocess
import sys
import os
import webbrowser
from pathlib import Path
import time
import logging

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


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
    ║   Versión: 2.0.0-Capitulo6                                        ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def verificar_dependencias():
    """Verifica que las dependencias estén instaladas"""
    print("\n📦 Verificando dependencias...")

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
        print("✓ Todas las dependencias están instaladas")


def mostrar_menu():
    """Muestra el menú de opciones"""
    menu = """
    ═══════════════════════════════════════════════════════════════
    MENÚ PRINCIPAL - CAPÍTULO 6
    ═══════════════════════════════════════════════════════════════

    🚀 SISTEMA COMPLETO
    1. Iniciar Sistema Completo (Dashboard + Simulador)
    2. Iniciar Sistema con Backend Capítulo 6 (Recomendado)

    🧪 PRUEBAS Y DEMOSTRACIONES
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
    """Demuestra el cálculo del ICV"""
    print("\n" + "="*70)
    print("DEMOSTRACIÓN: CÁLCULO DE ICV (Índice de Congestión Vehicular)")
    print("="*70 + "\n")

    sys.path.insert(0, str(Path(__file__).parent))

    from nucleo.estado_local import EstadoLocalInterseccion, ParametrosInterseccion

    # Crear estado local
    params = ParametrosInterseccion(
        id_interseccion="DEMO",
        nombre="Intersección de Demostración"
    )
    estado = EstadoLocalInterseccion(params)

    print("📊 Escenarios de prueba:\n")

    escenarios = [
        {
            'nombre': 'Flujo Libre',
            'sc': 5.0,
            'vavg': 50.0,
            'q': 12.0,
            'k': 0.03
        },
        {
            'nombre': 'Congestión Moderada',
            'sc': 25.0,
            'vavg': 25.0,
            'q': 20.0,
            'k': 0.08
        },
        {
            'nombre': 'Atasco Severo',
            'sc': 45.0,
            'vavg': 8.0,
            'q': 28.0,
            'k': 0.13
        }
    ]

    for esc in escenarios:
        # Calcular ICV usando la fórmula del Capítulo 6
        w1, w2, w3, w4 = 0.4, 0.3, 0.2, 0.1
        sc_norm = min(esc['sc'] / params.SC_MAX, 1.0)
        v_norm = 1.0 - min(esc['vavg'] / params.V_MAX, 1.0)
        k_norm = min(esc['k'] / params.k_MAX, 1.0)
        q_norm = 1.0 - min(esc['q'] / params.q_MAX, 1.0)

        icv = w1*sc_norm + w2*v_norm + w3*k_norm + w4*q_norm

        # Clasificar
        if icv < 0.3:
            clasificacion = "FLUJO LIBRE"
            color = "🟢"
        elif icv < 0.6:
            clasificacion = "CONGESTIÓN MODERADA"
            color = "🟡"
        else:
            clasificacion = "ATASCO SEVERO"
            color = "🔴"

        print(f"{color} {esc['nombre']}:")
        print(f"   SC={esc['sc']:.0f}, Vavg={esc['vavg']:.0f} km/h, q={esc['q']:.0f} veh/min, k={esc['k']:.3f}")
        print(f"   → ICV = {icv:.3f} ({clasificacion})")
        print()

    input("\n✓ Presiona Enter para continuar...")


def demostrar_control_difuso():
    """Demuestra el sistema de control difuso"""
    print("\n" + "="*70)
    print("DEMOSTRACIÓN: SISTEMA DE CONTROL DIFUSO (12 REGLAS)")
    print("="*70 + "\n")

    sys.path.insert(0, str(Path(__file__).parent))

    from nucleo.controlador_difuso_capitulo6 import ControladorDifusoCapitulo6

    # Crear controlador
    controlador = ControladorDifusoCapitulo6(
        T_base_NS=30.0,
        T_base_EO=30.0,
        T_ciclo=90.0
    )

    print("📊 Escenarios de prueba:\n")

    escenarios = [
        {
            'nombre': 'Tráfico Balanceado - Flujo Libre',
            'icv_ns': 0.2, 'pi_ns': 0.8, 'ev_ns': 0,
            'icv_eo': 0.15, 'pi_eo': 0.85, 'ev_eo': 0
        },
        {
            'nombre': 'NS Congestionado, EO Fluido',
            'icv_ns': 0.75, 'pi_ns': 0.3, 'ev_ns': 0,
            'icv_eo': 0.2, 'pi_eo': 0.75, 'ev_eo': 0
        },
        {
            'nombre': 'Emergencia en NS',
            'icv_ns': 0.5, 'pi_ns': 0.5, 'ev_ns': 1,
            'icv_eo': 0.4, 'pi_eo': 0.6, 'ev_eo': 0
        },
        {
            'nombre': 'Ambas Direcciones Congestionadas',
            'icv_ns': 0.7, 'pi_ns': 0.25, 'ev_ns': 0,
            'icv_eo': 0.65, 'pi_eo': 0.3, 'ev_eo': 0
        }
    ]

    for esc in escenarios:
        resultado = controlador.calcular_control_completo(
            icv_ns=esc['icv_ns'],
            pi_ns=esc['pi_ns'],
            ev_ns=esc['ev_ns'],
            icv_eo=esc['icv_eo'],
            pi_eo=esc['pi_eo'],
            ev_eo=esc['ev_eo']
        )

        print(f"🚦 {esc['nombre']}:")
        print(f"   NS: ICV={esc['icv_ns']:.2f}, PI={esc['pi_ns']:.2f}, EV={esc['ev_ns']}")
        print(f"   EO: ICV={esc['icv_eo']:.2f}, PI={esc['pi_eo']:.2f}, EV={esc['ev_eo']}")
        print(f"   → T_verde_NS = {resultado['T_verde_NS']:.1f}s")
        print(f"   → T_verde_EO = {resultado['T_verde_EO']:.1f}s")
        print()

    input("\n✓ Presiona Enter para continuar...")


def demostrar_metricas_red():
    """Demuestra el sistema de métricas de red"""
    print("\n" + "="*70)
    print("DEMOSTRACIÓN: MÉTRICAS DE RED GLOBALES")
    print("="*70 + "\n")

    sys.path.insert(0, str(Path(__file__).parent))

    from nucleo.metricas_red import AgregadorMetricasRed, ConfiguracionInterseccion, MetricasInterseccion
    from datetime import datetime
    import random

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
            peso=1.0
        ),
        ConfiguracionInterseccion(
            id="I003",
            nombre="Av. Universitaria - La Marina",
            peso=0.8
        )
    ]

    # Crear agregador
    agregador = AgregadorMetricasRed(configuraciones=configuraciones)

    print(f"📍 Intersecciones monitoreadas: {len(configuraciones)}\n")

    # Simular 10 actualizaciones
    for paso in range(10):
        for config in configuraciones:
            # Simular métricas
            metricas = MetricasInterseccion(
                interseccion_id=config.id,
                timestamp=datetime.now(),
                sc_ns=random.uniform(10, 40),
                sc_eo=random.uniform(10, 40),
                vavg_ns=random.uniform(20, 50),
                vavg_eo=random.uniform(20, 50),
                q_ns=random.uniform(10, 25),
                q_eo=random.uniform(10, 25),
                k_ns=random.uniform(0.03, 0.1),
                k_eo=random.uniform(0.03, 0.1),
                icv_ns=random.uniform(0.2, 0.7),
                icv_eo=random.uniform(0.2, 0.7),
                pi_ns=random.uniform(0.3, 0.9),
                pi_eo=random.uniform(0.3, 0.9)
            )

            agregador.actualizar_metricas_interseccion(metricas)

    # Mostrar resumen
    resumen = agregador.obtener_resumen_red()

    if resumen:
        print(f"Estado General de la Red: {resumen['estado_general']}\n")
        print("Métricas Agregadas:")
        print(f"  • ICV_red (Congestión): {resumen['metricas_actuales']['ICV_red']:.3f}")
        print(f"  • Vavg_red (Velocidad): {resumen['metricas_actuales']['Vavg_red']:.1f} km/h")
        print(f"  • q_red (Flujo): {resumen['metricas_actuales']['q_red']:.1f} veh/min")
        print(f"\nDistribución de Estados:")
        print(f"  • Fluidas: {resumen['distribucion_estados']['libres']}")
        print(f"  • Moderadas: {resumen['distribucion_estados']['moderadas']}")
        print(f"  • Congestionadas: {resumen['distribucion_estados']['congestionadas']}")

    input("\n✓ Presiona Enter para continuar...")


def ejecutar_comparacion():
    """Ejecuta comparación adaptativo vs tiempo fijo"""
    print("\n" + "="*70)
    print("COMPARACIÓN: CONTROL ADAPTATIVO VS TIEMPO FIJO")
    print("="*70 + "\n")

    print("🔄 Ejecutando simulaciones paralelas...\n")

    # Ejecutar módulo de comparación directamente
    subprocess.run([
        sys.executable,
        '-m',
        'nucleo.sistema_comparacion'
    ])

    input("\n✓ Presiona Enter para continuar...")


def conectar_sumo():
    """Conecta con SUMO"""
    print("\n" + "="*70)
    print("INTEGRACIÓN CON SUMO")
    print("="*70 + "\n")

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
        print("\n3. Ejecuta esta opción nuevamente")
        input("\nPresiona Enter para continuar...")
        return

    print(f"✓ Configuración encontrada: {config_file}\n")
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

    print("Esta opción genera un reporte HTML completo con:")
    print("  • Comparación de métricas")
    print("  • Gráficas de rendimiento")
    print("  • Mejoras porcentuales")
    print("  • Análisis estadístico\n")

    print("⚠️  Primero debes ejecutar una comparación (opción 6)\n")

    input("Presiona Enter para continuar...")


def main():
    """Función principal"""
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
                print("⚠️  Usa el ejecutar.py original para esta función\n")
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

        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            logging.exception("Error en ejecución")


if __name__ == "__main__":
    main()
