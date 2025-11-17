# -*- coding: utf-8 -*-
"""
Script Principal de Ejecución
Sistema de Control Semafórico Adaptativo Inteligente

Ejecutar con: python ejecutar.py
"""

import subprocess
import sys
import os
import webbrowser
from pathlib import Path
import time

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
    ║                                                                   ║
    ║   Universidad: PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ           ║
    ║   Tesis: SISTEMA DE CONTROL ADAPTATIVO DE LA RED SEMAFÓRICA       ║
    ║                                                                   ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def verificar_dependencias():
    """Verifica que las dependencias estén instaladas"""
    print("\n📦 Verificando dependencias...")

    dependencias_criticas = [
        'fastapi',
        'uvicorn',
        'numpy',
        'cv2'
    ]

    faltan = []
    for dep in dependencias_criticas:
        try:
            __import__(dep)
            print(f"  ✓ {dep}")
        except ImportError:
            print(f"  ✗ {dep} (no instalado)")
            faltan.append(dep)

    if faltan:
        print(f"\n⚠️  Faltan dependencias: {', '.join(faltan)}")
        print("Instalando automáticamente...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✓ Dependencias instaladas")
    else:
        print("✓ Todas las dependencias están instaladas")

def mostrar_menu():
    """Muestra el menú de opciones"""
    menu = """
    ═══════════════════════════════════════════════════════════════
    MENÚ PRINCIPAL
    ═══════════════════════════════════════════════════════════════

    1. Iniciar Sistema Completo (Simulador + Dashboard)
    2. Procesar Video con Visualización (Detección + Métricas)
    3. Conectar con SUMO
    4. Ejecutar Pruebas del Sistema
    5. Ver Documentación
    6. Salir

    ═══════════════════════════════════════════════════════════════
    """
    print(menu)

def iniciar_sistema_completo():
    """Inicia el sistema completo con simulador"""
    print("\n🚀 Iniciando Sistema Completo...\n")

    # Cambiar al directorio del servidor
    servidor_path = Path(__file__).parent / 'servidor_backend'
    if not servidor_path.exists():
        servidor_path = Path(__file__).parent / 'servidor-backend'

    print("📡 Iniciando servidor FastAPI...")
    print("🌐 Dashboard: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("\n⏳ Esperando que el servidor arranque...")

    # Iniciar servidor
    try:
        # Esperar un momento y abrir navegador
        import threading
        def abrir_navegador():
            time.sleep(3)
            webbrowser.open('http://localhost:8000')

        threading.Thread(target=abrir_navegador, daemon=True).start()

        # Ejecutar servidor
        subprocess.run([
            sys.executable,
            str(servidor_path / 'main.py')
        ])
    except KeyboardInterrupt:
        print("\n\n✓ Sistema detenido correctamente")

def procesar_video():
    """Procesa un video de intersección con visualización en tiempo real"""
    print("\n" + "="*70)
    print("📹 PROCESADOR DE VIDEO CON VISUALIZACIÓN")
    print("="*70)

    # Buscar videos en múltiples carpetas
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
        print("\n⚠️ No se encontraron videos en las carpetas de prueba.")
        print("\nColoca tus videos en:")
        print("  - datos/videos-prueba/analisis-parametros/")
        print("  - datos/videos-prueba/deteccion-basica/")
        print("  - datos/videos-prueba/deteccion-emergencia/")
        print("\nO especifica la ruta completa:")
        ruta = input("\nRuta del video (0 para cancelar): ").strip()
        if ruta == '0' or not ruta:
            return
        if Path(ruta).exists():
            video_seleccionado = Path(ruta)
        else:
            print("❌ Video no encontrado")
            return
    else:
        print("\n📹 Videos disponibles:\n")
        for i, video in enumerate(videos_encontrados, 1):
            tamaño_mb = video.stat().st_size / (1024 * 1024)
            print(f"  {i}. {video.name} ({tamaño_mb:.1f} MB)")
            print(f"     {video.parent.name}/{video.name}")

        print(f"\n  0. Especificar otra ruta")

        try:
            opcion = input(f"\nSelecciona el video (1-{len(videos_encontrados)}) o 0: ").strip()

            if not opcion:
                return

            opcion = int(opcion)

            if opcion == 0:
                ruta = input("\nRuta completa del video: ").strip()
                if ruta and Path(ruta).exists():
                    video_seleccionado = Path(ruta)
                else:
                    print("❌ Video no encontrado")
                    return
            elif 1 <= opcion <= len(videos_encontrados):
                video_seleccionado = videos_encontrados[opcion - 1]
            else:
                print(f"❌ Opción inválida. Debe ser entre 0 y {len(videos_encontrados)}")
                return
        except ValueError:
            print("❌ Por favor ingresa un número")
            return

    # Seleccionar modo de análisis
    print("\n" + "="*70)
    print("🎯 SELECCIONA EL TIPO DE ANÁLISIS")
    print("="*70)
    print("\n📊 Modos disponibles:\n")
    print("  1. 🚗 DETECCIÓN BÁSICA")
    print("     - Detectar y contar vehículos")
    print("     - Mostrar bounding boxes")
    print("     - Rápido y simple\n")

    print("  2. 📈 ANÁLISIS COMPLETO DE TRÁFICO (Recomendado)")
    print("     - Detección de vehículos")
    print("     - Velocidad REAL (tracking)")
    print("     - ICV (Índice de Congestión)")
    print("     - Flujo vehicular")
    print("     - Longitud de cola")
    print("     - TODAS las métricas\n")

    print("  3. 🚨 DETECCIÓN DE EMERGENCIAS")
    print("     - Detectar vehículos de emergencia")
    print("     - Ambulancias, bomberos, policía")
    print("     - Requiere modelo entrenado\n")

    try:
        modo = input("\nSelecciona el modo (1-3, 0 para cancelar): ").strip()

        if not modo or modo == '0':
            return

        modo = int(modo)

        if modo < 1 or modo > 3:
            print("❌ Opción inválida. Debe ser 1, 2 o 3")
            return

    except ValueError:
        print("❌ Por favor ingresa un número")
        return

    # Preguntar por optimizaciones
    print("\n" + "="*70)
    print("⚡ OPCIONES DE RENDIMIENTO")
    print("="*70)
    print("\n¿Cómo quieres procesar el video?\n")
    print("  1. Tiempo real (más lento, ves el procesamiento mientras ocurre)")
    print("  2. Procesar y reproducir después (RECOMENDADO - más fluido)")
    print("     - Procesa todo primero sin mostrar")
    print("     - Luego reproduce el video a velocidad normal")
    print("     - Se ve mucho más fluido\n")

    try:
        opt_rendimiento = input("\nSelecciona opción (1-2, Enter=1): ").strip()
        if not opt_rendimiento:
            opt_rendimiento = '1'

        opt_rendimiento = int(opt_rendimiento)
        if opt_rendimiento not in [1, 2]:
            opt_rendimiento = 1

    except ValueError:
        opt_rendimiento = 1

    reproducir_despues = (opt_rendimiento == 2)

    # Preguntar por optimizaciones adicionales si es necesario
    args_adicionales = []
    if reproducir_despues:
        args_adicionales.append('--reproducir-despues')

    # Ejecutar procesador con visualización
    print(f"\n▶️ Procesando: {video_seleccionado.name}")

    procesador_path = Path(__file__).parent / 'vision_computadora' / 'procesar_video_con_visualizacion.py'
    if not procesador_path.exists():
        print(f"❌ No se encontró: {procesador_path}")
        return

    try:
        comando = [
            sys.executable,
            str(procesador_path),
            '--video', str(video_seleccionado),
            '--modo', str(modo)
        ] + args_adicionales

        subprocess.run(comando)
    except KeyboardInterrupt:
        print("\n\n⏹️ Procesamiento detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")

def conectar_sumo():
    """Conecta con SUMO"""
    print("\n🎯 Integración con SUMO\n")

    sumo_path = Path(__file__).parent / 'integracion_sumo' / 'escenarios' / 'lima-centro'
    if not sumo_path.exists():
        sumo_path = Path(__file__).parent / 'integracion-sumo' / 'escenarios' / 'lima-centro'
    config_file = sumo_path / 'lima_centro.sumocfg'

    if not config_file.exists():
        print("⚠️  No se encontró configuración de SUMO")
        print(f"\nCopia tu simulación de SUMO a: {sumo_path}")
        print("\nArchivos necesarios:")
        print("  - lima_centro.net.xml")
        print("  - lima_centro.rou.xml")
        print("  - lima_centro.sumocfg")
        return

    print(f"✓ Configuración encontrada: {config_file}")
    print("\n🚀 Iniciando integración con SUMO...")

    conector_path = Path(__file__).parent / 'integracion_sumo' / 'conector_sumo.py'
    if not conector_path.exists():
        conector_path = Path(__file__).parent / 'integracion-sumo' / 'conector_sumo.py'
    try:
        subprocess.run([sys.executable, str(conector_path)])
    except KeyboardInterrupt:
        print("\n✓ Integración SUMO detenida")

def ejecutar_pruebas():
    """Ejecuta las pruebas del sistema"""
    print("\n🧪 Ejecutando Pruebas del Sistema\n")

    pruebas_path = Path(__file__).parent / 'pruebas'

    print("Pruebas disponibles:")
    print("  1. Cálculo de ICV")
    print("  2. Sistema de Lógica Difusa")
    print("  3. Olas Verdes Dinámicas")
    print("  4. Todas las pruebas")

    try:
        opcion = int(input("\nSelecciona la prueba (0 para cancelar): "))

        if opcion == 0:
            return
        elif opcion == 1:
            # Ejecutar prueba de ICV directamente
            sys.path.insert(0, str(Path(__file__).parent))
            from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion
            params = ParametrosInterseccion()
            calculador = CalculadorICV(params)

            print("\n=== PRUEBA: CÁLCULO DE ICV ===\n")
            casos = [
                (10, 55, 10, "Flujo libre"),
                (75, 25, 22, "Congestión moderada"),
                (140, 8, 28, "Atasco severo")
            ]

            for longitud, velocidad, flujo, descripcion in casos:
                resultado = calculador.calcular(longitud, velocidad, flujo)
                print(f"{descripcion}:")
                print(f"  L={longitud}m, V={velocidad}km/h, F={flujo}veh/min")
                print(f"  → ICV = {resultado['icv']} ({resultado['clasificacion'].upper()})")
                print()

        elif opcion == 2:
            # Prueba de lógica difusa
            from nucleo.controlador_difuso import ControladorDifuso
            controlador = ControladorDifuso()

            print("\n=== PRUEBA: SISTEMA DE LÓGICA DIFUSA ===\n")
            casos = [
                (0.15, 10, "ICV bajo, espera corta"),
                (0.50, 50, "ICV medio, espera media"),
                (0.85, 100, "ICV alto, espera larga")
            ]

            for icv, espera, desc in casos:
                resultado = controlador.calcular(icv, espera)
                print(f"{desc}:")
                print(f"  ICV={icv}, Espera={espera}s")
                print(f"  → Tiempo Verde = {resultado['tiempo_verde']}s")
                print()

        elif opcion == 3:
            # Prueba de olas verdes
            print("\n=== PRUEBA: OLAS VERDES DINÁMICAS ===\n")
            subprocess.run([
                sys.executable,
                '-m',
                'nucleo.olas_verdes_dinamicas'
            ])

    except ValueError:
        print("Entrada inválida")
    except Exception as e:
        print(f"Error ejecutando prueba: {e}")

    input("\nPresiona Enter para continuar...")

def ver_documentacion():
    """Abre la documentación"""
    print("\n📊 Documentación del Sistema\n")

    docs_path = Path(__file__).parent / 'documentacion'

    print("Documentación disponible:")
    print(f"  1. Modelo Matemático ICV: {docs_path / '01-modelo-matematico' / 'justificacion-icv.md'}")
    print(f"  2. Arquitectura del Sistema: {docs_path / '02-arquitectura'}")
    print(f"  3. Algoritmos: {docs_path / '03-algoritmos'}")

    print("\nAbriendo carpeta de documentación...")
    import os
    if sys.platform == 'win32':
        os.startfile(docs_path)
    elif sys.platform == 'darwin':
        subprocess.run(['open', docs_path])
    else:
        subprocess.run(['xdg-open', docs_path])

def main():
    """Función principal"""
    imprimir_banner()
    verificar_dependencias()

    while True:
        mostrar_menu()
        try:
            opcion = input("Selecciona una opción: ").strip()

            if opcion == '1':
                iniciar_sistema_completo()
            elif opcion == '2':
                procesar_video()
            elif opcion == '3':
                conectar_sumo()
            elif opcion == '4':
                ejecutar_pruebas()
            elif opcion == '5':
                ver_documentacion()
            elif opcion == '6':
                print("\n👋 ¡Hasta luego!\n")
                break
            else:
                print("\n⚠️  Opción inválida. Intenta de nuevo.\n")

        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    main()
