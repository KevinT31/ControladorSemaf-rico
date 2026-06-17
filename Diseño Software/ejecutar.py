# -*- coding: utf-8 -*-
"""
Sistema de Control Semafórico Adaptativo Inteligente
PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ

EJECUTAR.PY - Script Principal
Integra TODOS los módulos del sistema:

Ejecutar con: python ejecutar.py
"""
import subprocess
import sys
import os
import webbrowser
import time
import json
import logging
import math
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Configurar encoding 
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
    """Imprime el banner del sistema"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║    SISTEMA DE CONTROL SEMAFÓRICO ADAPTATIVO INTELIGENTE           ║
    ║                                                                   ║
    ║   Universidad: PONTIFICIA UNIVERSIDAD CATÓLICA DEL PERÚ           ║
    ║   Tesis: SISTEMA DE CONTROL ADAPTATIVO DE LA RED SEMAFÓRICA       ║ 
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def limpiar_puerto_8000():
    """Limpia el puerto 8000 antes de iniciar el servidor"""
    try:
        import psutil
        procesos_terminados = 0

        print("\n🔍 Verificando puerto 8000...")
        for conn in psutil.net_connections():
            if conn.laddr.port == 8000:
                try:
                    proceso = psutil.Process(conn.pid)
                    nombre = proceso.name()
                    print(f"   [!] Terminando proceso: {nombre} (PID: {conn.pid})")
                    proceso.kill()
                    procesos_terminados += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        if procesos_terminados > 0:
            print(f"   [OK] {procesos_terminados} proceso(s) terminado(s)")
            print("   Esperando 2 segundos...")
            time.sleep(2)
        else:
            print("   [OK] Puerto 8000 libre")
    except ImportError:
        # Si no tiene psutil, intentar matar todos los python.exe
        print("   [!] Limpiando todos los procesos Python...")
        if sys.platform == 'win32':
            os.system('taskkill /F /IM python.exe /T 2>nul')
            time.sleep(2)


def iniciar_sistema_completo():
    """
    Inicia el sistema completo con TODAS las funcionalidades del Capítulo 6
    Integra: EstadoLocal, ControlDifuso, MetricasRed, OlasVerdes
    """
    # PRIMERO: Limpiar el puerto 8000
    limpiar_puerto_8000()

    # Verificar que el servidor existe
    servidor_path = Path(__file__).parent / 'servidor-backend'
    main_path = servidor_path / 'main.py'

    if not main_path.exists():
        print(f"\n❌ Error: No se encontró {main_path}")
        return

    print("\n📡 Iniciando servidor...")
    print("Accesos:")
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


def verificar_dependencias():
    """Verifica que las dependencias estén instaladas"""

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
            print("\n✓ Todas las dependencias están instaladas")

        if faltan_opcionales:
            print(f"\n💡 Puedes instalar dependencias opcionales con:")
            print(f"   pip install {' '.join(faltan_opcionales)}")


def mostrar_menu():
    """Muestra el menú principal mejorado"""
    menu = """

    1. Iniciar Dashboard
    2. Procesar Video con Análisis Completo
    3. Conectar con SUMO (Calles Reales de Lima)
    4. Comparar Adaptativo vs Tiempo Fijo
    5. Ejecutar Pruebas del Sistema
    6. Ver Estado de Componentes
    7. Ver Documentación del Sistema
    8. Exportar Configuración Actual

    0. Salir
    """
    print(menu)


    


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

    # Buscar videos (incluye videos-prueba/ y sus subcarpetas, recursivo)
    base_videos = Path(__file__).parent / 'datos' / 'videos-prueba'
    carpetas_prueba = [
        base_videos,
        Path(__file__).parent / 'datos',
    ]

    videos_encontrados = []
    exts = ['*.mp4', '*.avi', '*.mov', '*.mkv']
    # Búsqueda recursiva dentro de videos-prueba (donde se guardan los videos)
    if base_videos.exists():
        for ext in exts:
            videos_encontrados.extend(base_videos.rglob(ext))
    # Y videos sueltos en datos/
    for ext in exts:
        videos_encontrados.extend((Path(__file__).parent / 'datos').glob(ext))
    # Eliminar duplicados preservando orden
    videos_encontrados = list(dict.fromkeys(videos_encontrados))

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
    """Abre SUMO-GUI con los escenarios lima_amplio y lima_centro según elección."""
    print("\n" + "="*70)
    print("🌐 SUMO-GUI - SELECCIÓN DE ESCENARIO")
    print("="*70)

    base_path = Path(__file__).parent
    escenarios_path = base_path / 'integracion-sumo' / 'escenarios'
    # Detectar config de Lima Amplio: preferir lima_amplio.sumocfg, si no, cualquier *.sumocfg en carpeta
    amplio_dir = escenarios_path / 'lima-amplio'
    amplio_cfg = None
    if amplio_dir.exists():
        preferida = amplio_dir / 'lima_amplio.sumocfg'
        if preferida.exists():
            amplio_cfg = preferida
        else:
            # Buscar primera .sumocfg disponible
            candidatos = list(amplio_dir.glob('*.sumocfg'))
            if candidatos:
                amplio_cfg = candidatos[0]

    # Detectar config de Lima Centro: preferir lima_centro.sumocfg, si no, usar osm.sumocfg o cualquier *.sumocfg
    centro_dir = escenarios_path / 'lima-centro'
    centro_cfg = None
    if centro_dir.exists():
        preferidas = [
            centro_dir / 'lima_centro.sumocfg',
            centro_dir / 'osm.sumocfg'
        ]
        centro_cfg = next((p for p in preferidas if p.exists()), None)
        if centro_cfg is None:
            candidatos = list(centro_dir.glob('*.sumocfg'))
            if candidatos:
                centro_cfg = candidatos[0]

    disponibles = []
    if amplio_cfg and amplio_cfg.exists():
        disponibles.append(('1', 'Lima Amplio', amplio_cfg))
    if centro_cfg and centro_cfg.exists():
        disponibles.append(('2', 'Lima Centro', centro_cfg))

    if not disponibles:
        print("\n❌ No se encontraron archivos .sumocfg en 'integracion-sumo/escenarios'.")
        print("   Esperado: 'lima_amplio.sumocfg' y/o 'lima_centro.sumocfg'.")
        return

    print("\nEscenarios disponibles:")
    for key, nombre, ruta in disponibles:
        print(f"  {key}. {nombre} → {ruta}")
    if len(disponibles) == 2:
        print("  3. Abrir ambos")

    eleccion = input("\nElige el escenario (1-3): ").strip()
    if eleccion not in [d[0] for d in disponibles] + (['3'] if len(disponibles) == 2 else []):
        print("❌ Opción inválida")
        return

    def abrir_sumo(cfg_path: Path):
        try:
            print(f"\n🚀 Abriendo SUMO-GUI: {cfg_path.name}")
            # Resolver el binario de forma robusta (sumo-gui no suele estar en PATH).
            try:
                import sumolib
                binario = sumolib.checkBinary('sumo-gui')
            except Exception:
                binario = 'sumo-gui'
            subprocess.Popen([binario, '-c', str(cfg_path), '--start'])
        except Exception as e:
            print(f"❌ Error al abrir SUMO-GUI: {e}")
            print("   Verifica que SUMO esté instalado y SUMO_HOME configurado.")

    if eleccion == '3':
        abrir_sumo(disponibles[0][2])
        abrir_sumo(disponibles[1][2])
    else:
        # Abrir el seleccionado
        for key, _, ruta in disponibles:
            if eleccion == key:
                abrir_sumo(ruta)
                break

    print("\n✓ Operación completada. (SUMO-GUI abierto)")


    


def comparar_sistemas():
    """Compara sistema adaptativo vs tiempo fijo"""
    print("\n" + "="*70)
    print("📊 COMPARACIÓN: ADAPTATIVO VS TIEMPO FIJO")
    print("="*70)

    sys.path.insert(0, str(Path(__file__).parent))

    try:
        from nucleo.sistema_comparacion import (
            SistemaComparacion, TipoControl, ConfiguracionInterseccion
        )

        print("\n🔧 Inicializando comparador...")

        # Localizar escenario SUMO real. Preferir el caso HORA PUNTA realista
        # (corredores reales de Lima: Javier Prado, Arequipa, Angamos...),
        # luego alta demanda en lima-centro, luego escenarios normales.
        integ = Path(__file__).parent / 'integracion-sumo'
        cfg_horapico = integ / 'escenarios' / 'lima-amplio' / 'horapico.sumocfg'
        cfg_comp = integ / 'escenarios' / 'lima-centro' / 'comparacion.sumocfg'
        cfg_centro = integ / 'escenarios' / 'lima-centro' / 'osm.sumocfg'
        cfg_amplio = integ / 'escenarios' / 'lima-amplio' / 'lima_amplio.sumocfg'
        ruta_cfg = next((c for c in (cfg_horapico, cfg_comp, cfg_centro, cfg_amplio) if c.exists()), None)

        if ruta_cfg is None:
            print("\n❌ No se encontró un escenario SUMO (.sumocfg) construido.")
            print("   Construye la red real primero (Fase 1).")
            input("\n\nPresiona ENTER para continuar...")
            return

        # El análisis trabaja sobre las métricas de red; no requiere configs aquí
        sistema = SistemaComparacion([])
        sys.path.insert(0, str(integ))

        # Ejecutar DOS simulaciones REALES de SUMO (sin datos sintéticos):
        #   - Tiempo fijo: semáforos estáticos con verde fijo
        #   - Adaptativo: control ICV + difusa Mamdani (Cap. 6) por dirección.
        # Palancas afinadas: gamma=5 (agresividad), alpha=0.35 (suavizado),
        # intervalo=25s. Óptimo hallado en lima-amplio hora punta.
        pasos = 700
        print(f"\n⏳ Ejecutando 2 simulaciones SUMO reales de {pasos} pasos sobre:")
        print(f"   {ruta_cfg.parent.name} ({ruta_cfg.name})")
        print("   (puede tardar ~1-2 min; los datos provienen de SUMO, no son sintéticos)...\n")

        from comparacion_sumo import ejecutar_comparacion_real
        metricas_fijo, metricas_adapt, resumen = ejecutar_comparacion_real(
            str(ruta_cfg), pasos=pasos, intervalo_control=25, gamma=5.0, alpha=0.35
        )

        res_fijo = sistema.analizar_resultados(metricas_fijo, TipoControl.TIEMPO_FIJO, "sim_tiempo_fijo")
        res_adapt = sistema.analizar_resultados(metricas_adapt, TipoControl.ADAPTATIVO, "sim_adaptativo")

        informe = sistema.comparar_estrategias("sim_tiempo_fijo", "sim_adaptativo")

        # Mostrar resultados
        print("\n" + "="*70)
        print("✅ RESULTADOS DE LA COMPARACIÓN")
        print("="*70)

        print(f"\n📊 Métricas Promedio (5 minutos de simulación):")
        print(f"\n  {'Métrica':<25} {'Tiempo Fijo':<15} {'Adaptativo':<15} {'Mejora':<10}")
        print(f"  {'-'*65}")

        def pct(mej):
            return f"{mej:+.1f}%"

        print(f"  {'ICV (Congestión)':<25} {res_fijo.icv_promedio:<15.3f} {res_adapt.icv_promedio:<15.3f} {pct(informe.mejora_icv)}")
        print(f"  {'Velocidad (km/h)':<25} {res_fijo.vavg_promedio:<15.3f} {res_adapt.vavg_promedio:<15.3f} {pct(informe.mejora_velocidad)}")
        print(f"  {'Flujo (veh/min)':<25} {res_fijo.q_promedio:<15.3f} {res_adapt.q_promedio:<15.3f} {pct(informe.mejora_flujo)}")
        print(f"  {'Saturación Cola':<25} {res_fijo.porcentaje_tiempo_congestionado:<15.3f} {res_adapt.porcentaje_tiempo_congestionado:<15.3f} ")

        # Métricas de desempeño global (las más representativas para semáforos)
        rf, ra = resumen['fijo'], resumen['adaptativo']
        thr_mej = ((ra['throughput'] - rf['throughput']) / rf['throughput'] * 100) if rf['throughput'] else 0.0
        dem_mej = ((rf['demora_media_s'] - ra['demora_media_s']) / rf['demora_media_s'] * 100) if rf['demora_media_s'] else 0.0
        print(f"\n  {'Throughput (veh)':<25} {rf['throughput']:<15d} {ra['throughput']:<15d} {pct(thr_mej)}")
        print(f"  {'Demora media (s/veh)':<25} {rf['demora_media_s']:<15.2f} {ra['demora_media_s']:<15.2f} {pct(dem_mej)}")

        print(f"\n📈 Resumen:")
        print(f"  • Reducción de congestión: {pct(informe.mejora_icv)}")
        print(f"  • Aumento de velocidad: {pct(informe.mejora_velocidad)}")
        print(f"  • Mejora de flujo: {pct(informe.mejora_flujo)}")
        print(f"  • Más vehículos procesados (throughput): {pct(thr_mej)}")
        print(f"  • Reducción de demora por vehículo: {pct(dem_mej)}")

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

            resultado = controlador.calcular_control_completo(
                icv_ns=0.6, pi_ns=0.3, ev_ns=0,
                icv_eo=0.4, pi_eo=0.5, ev_eo=0
            )

            print(f"  T_verde_NS: {resultado['NS']['T_verde']:.1f}s")
            print(f"  T_verde_EO: {resultado['EO']['T_verde']:.1f}s")

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
    """Abre el README del sistema en el visor predeterminado"""
    print("\nAbriendo README del sistema...")

    readme_path = Path(__file__).parent / 'README.md'

    if readme_path.exists():
        import platform
        try:
            if platform.system() == 'Windows':
                os.startfile(str(readme_path))
            elif platform.system() == 'Darwin':
                subprocess.run(['open', str(readme_path)])
            else:
                subprocess.run(['xdg-open', str(readme_path)])
            print(f"✓ Abierto: {readme_path}")
        except Exception as e:
            print(f"❌ No se pudo abrir el README automáticamente: {e}")
            print(f"   Ruta: {readme_path}")
    else:
        print("❌ README.md no encontrado en la raíz del proyecto")


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
                procesar_video()
            elif opcion == '3':
                conectar_sumo()
            elif opcion == '4':
                comparar_sistemas()
            elif opcion == '5':
                ejecutar_pruebas()
            elif opcion == '6':
                ver_estado_componentes()
            elif opcion == '7':
                ver_documentacion()
            elif opcion == '8':
                exportar_configuracion()
            elif opcion == '0':
                print("\n👋 ¡Hasta luego!\n")
                break
            else:
                print("\n⚠️  Opción inválida. Intenta de nuevo.\n")

        except KeyboardInterrupt:
            print("\n\n ¡Hasta luego!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            logger.exception("Error en el menú principal")


if __name__ == "__main__":
    main()
