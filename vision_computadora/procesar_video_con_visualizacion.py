"""
Script para procesar videos con VISUALIZACIÓN EN TIEMPO REAL

Este script procesa un video mostrando:
- Detecciones de vehículos con bounding boxes
- Velocidad REAL calculada con tracking
- ICV REAL calculado con nucleo/
- Flujo vehicular
- Longitud de cola
- Detección de emergencias (si modelo está disponible)

Uso:
    python vision_computadora/procesar_video_con_visualizacion.py

O desde código:
    python vision_computadora/procesar_video_con_visualizacion.py --video mi_video.mp4
"""

import cv2
import sys
from pathlib import Path
import logging
import argparse

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from vision_computadora.procesador_video import ProcesadorVideo

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def seleccionar_video_interactivo():
    """Permite al usuario seleccionar un video de las carpetas de prueba"""
    print("\n" + "="*70)
    print("🎥 PROCESADOR DE VIDEO CON VISUALIZACIÓN EN TIEMPO REAL")
    print("="*70)

    # Buscar videos en las carpetas de prueba
    carpetas_prueba = [
        Path("datos/videos-prueba/deteccion-basica"),
        Path("datos/videos-prueba/analisis-parametros"),
        Path("datos/videos-prueba/deteccion-emergencia"),
        Path("datos")  # Carpeta raíz datos
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
        ruta = input("\nRuta del video: ").strip()
        if ruta and Path(ruta).exists():
            return ruta
        else:
            print("❌ Video no encontrado")
            return None

    print("\n📹 Videos disponibles:\n")
    for i, video in enumerate(videos_encontrados, 1):
        tamaño_mb = video.stat().st_size / (1024 * 1024)
        print(f"  {i}. {video.name} ({tamaño_mb:.1f} MB)")
        print(f"     {video.parent.name}/{video.name}")

    print(f"\n  0. Especificar otra ruta")

    while True:
        try:
            opcion = input(f"\nSelecciona el video (1-{len(videos_encontrados)}) o 0: ").strip()

            if not opcion:
                continue

            opcion = int(opcion)

            if opcion == 0:
                ruta = input("\nRuta completa del video: ").strip()
                if ruta and Path(ruta).exists():
                    return ruta
                else:
                    print("❌ Video no encontrado")
                    continue

            if 1 <= opcion <= len(videos_encontrados):
                return str(videos_encontrados[opcion - 1])
            else:
                print(f"❌ Opción inválida. Debe ser entre 0 y {len(videos_encontrados)}")
        except ValueError:
            print("❌ Por favor ingresa un número")
        except KeyboardInterrupt:
            print("\n\n❌ Cancelado por el usuario")
            return None


def seleccionar_modo_analisis():
    """Permite al usuario seleccionar el tipo de análisis a realizar"""
    print("\n" + "="*70)
    print("🎯 SELECCIONA EL TIPO DE ANÁLISIS")
    print("="*70)
    print("\n📊 Modos disponibles:\n")
    print("  1. 🚗 DETECCIÓN BÁSICA")
    print("     - Detectar y contar vehículos")
    print("     - Mostrar bounding boxes")
    print("     - Rápido y simple\n")

    print("  2. 📈 ANÁLISIS COMPLETO DE TRÁFICO")
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

    while True:
        try:
            opcion = input("\nSelecciona el modo (1-3): ").strip()

            if not opcion:
                continue

            opcion = int(opcion)

            if 1 <= opcion <= 3:
                return opcion
            else:
                print("❌ Opción inválida. Debe ser 1, 2 o 3")
        except ValueError:
            print("❌ Por favor ingresa un número")
        except KeyboardInterrupt:
            print("\n\n❌ Cancelado por el usuario")
            return None


def procesar_video_con_visualizacion(
    ruta_video: str,
    modo: int = 2,
    exportar: bool = True,
    guardar_video: bool = False,
    reproducir_despues: bool = False,
    saltar_frames: int = 1,
    reducir_resolucion: float = 1.0
):
    """
    Procesa un video mostrando la visualización en tiempo real

    Args:
        ruta_video: Ruta al video a procesar
        modo: Tipo de análisis (1=básico, 2=completo, 3=emergencias)
        exportar: Si exportar resultados a CSV/JSON
        guardar_video: Si guardar el video procesado a archivo
        reproducir_despues: Si reproducir el video después de procesarlo (requiere guardar_video=True)
        saltar_frames: Procesar 1 de cada N frames (default=1, sin saltar)
        reducir_resolucion: Factor de reducción (0.5=mitad, 1.0=original)
    """
    modos_nombre = {
        1: "DETECCIÓN BÁSICA",
        2: "ANÁLISIS COMPLETO DE TRÁFICO",
        3: "DETECCIÓN DE EMERGENCIAS"
    }

    print("\n" + "="*70)
    print(f"🚀 INICIANDO: {modos_nombre.get(modo, 'ANÁLISIS')}")
    print("="*70)
    print(f"\n📹 Video: {Path(ruta_video).name}")
    print(f"📊 Modo: {modos_nombre.get(modo, 'Desconocido')}")

    # Mostrar optimizaciones activas
    if saltar_frames > 1 or reducir_resolucion < 1.0 or guardar_video or reproducir_despues:
        print(f"\n⚡ OPTIMIZACIONES:")
        if saltar_frames > 1:
            print(f"  • Procesando 1 de cada {saltar_frames} frames (más rápido)")
        if reducir_resolucion < 1.0:
            print(f"  • Resolución reducida a {reducir_resolucion*100:.0f}%")
        if guardar_video:
            print(f"  • Guardando video procesado")
        if reproducir_despues:
            print(f"  • Reproducirá video al finalizar")

    try:
        # Crear procesador
        print("\n🔧 Inicializando procesador...")
        procesador = ProcesadorVideo(
            ruta_video=ruta_video,
            pixeles_por_metro=15.0  # Ajustar según tu video
        )

        # Para modo emergencias, activar warnings del detector
        if modo == 3:
            procesador.detector_emergencia.silencioso = False
            print("\n⚠️ MODO EMERGENCIAS:")
            print("   - Requiere modelo custom entrenado")
            print("   - Verás instrucciones si el modelo no existe")

        # Calcular dimensiones finales
        ancho_final = int(procesador.ancho * reducir_resolucion)
        alto_final = int(procesador.alto * reducir_resolucion)

        print(f"\n✓ Procesador inicializado")
        print(f"  Resolución original: {procesador.ancho}x{procesador.alto}")
        if reducir_resolucion < 1.0:
            print(f"  Resolución procesamiento: {ancho_final}x{alto_final}")
        print(f"  FPS: {procesador.fps:.1f}")
        print(f"  Frames totales: {procesador.total_frames}")
        if saltar_frames > 1:
            frames_procesar = procesador.total_frames // saltar_frames
            print(f"  Frames a procesar: {frames_procesar} (saltando {saltar_frames-1} de cada {saltar_frames})")
        print(f"  Duración: {procesador.total_frames/procesador.fps:.1f} segundos")

        # Configurar VideoWriter si se va a guardar
        video_writer = None
        ruta_video_procesado = None
        if guardar_video or reproducir_despues:
            modo_nombres_archivo = {1: 'basico', 2: 'completo', 3: 'emergencias'}
            modo_str = modo_nombres_archivo.get(modo, 'analisis')
            carpeta_videos = Path(f"datos/resultados-video/videos-procesados/{modo_str}")
            carpeta_videos.mkdir(parents=True, exist_ok=True)

            nombre_base = Path(ruta_video).stem
            ruta_video_procesado = carpeta_videos / f"{nombre_base}_modo{modo}_procesado.mp4"

            # Codec H264 para mejor compatibilidad
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                str(ruta_video_procesado),
                fourcc,
                procesador.fps,
                (ancho_final, alto_final)
            )
            print(f"\n📹 Guardando video procesado en: {ruta_video_procesado}")

        # Configurar ventana solo si NO vamos a reproducir después
        if not reproducir_despues:
            nombre_ventana = 'Procesamiento de Video - Presiona Q para salir, P para pausar'
            cv2.namedWindow(nombre_ventana, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(nombre_ventana, 1280, 720)

        print("\n" + "="*70)
        if reproducir_despues:
            print("🎬 PROCESANDO VIDEO (SIN VISUALIZACIÓN)")
            print("="*70)
            print("\n⏳ Procesando... El video se reproducirá cuando termine.")
        else:
            print("🎬 PROCESANDO VIDEO")
            print("="*70)
            if not guardar_video:
                print("\n⌨️  CONTROLES: Q=Salir | P/ESPACIO=Pausar")

        print("\n📊 Procesando...")

        resultados = []
        frame_num = 0
        frame_count = 0  # Contador real de frames leídos
        pausado = False
        key = 0xFF  # Inicializar key

        # Reiniciar video
        procesador.video.set(cv2.CAP_PROP_POS_FRAMES, 0)

        while True:
            if not pausado:
                ret, frame = procesador.video.read()
                if not ret:
                    break

                # Saltar frames si está configurado
                if frame_count % saltar_frames != 0:
                    frame_count += 1
                    continue

                # Reducir resolución si está configurado
                if reducir_resolucion < 1.0:
                    frame = cv2.resize(frame, (ancho_final, alto_final))

                # Procesar frame
                resultado = procesador.procesar_frame(frame, frame_num)
                resultados.append(resultado)

                # Dibujar según el modo seleccionado
                frame_anotado = frame.copy()

                if modo == 1:
                    # MODO 1: Solo detección básica
                    frame_anotado = procesador.dibujar_detecciones(
                        frame,
                        resultado,
                        mostrar_info=False  # Solo bounding boxes
                    )
                    # Añadir contador simple
                    cv2.putText(frame_anotado, f"Vehiculos: {resultado.num_vehiculos}",
                               (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

                elif modo == 2:
                    # MODO 2: Análisis completo (sin emergencias)
                    frame_anotado = procesador.dibujar_detecciones(
                        frame,
                        resultado,
                        mostrar_info=True  # Todas las métricas
                    )

                elif modo == 3:
                    # MODO 3: Enfoque en emergencias
                    frame_anotado = procesador.dibujar_detecciones(
                        frame,
                        resultado,
                        mostrar_info=False  # Info básica
                    )

                    # Añadir indicador de emergencia si hay detecciones
                    if resultado.hay_emergencia:
                        h, w = frame_anotado.shape[:2]
                        # Borde rojo parpadeante
                        if frame_num % 10 < 5:  # Parpadeo cada 5 frames
                            cv2.rectangle(frame_anotado, (0, 0), (w-1, h-1), (0, 0, 255), 10)

                        # Texto grande de alerta
                        cv2.putText(frame_anotado, "EMERGENCIA DETECTADA",
                                   (w//2 - 200, 50), cv2.FONT_HERSHEY_SIMPLEX,
                                   1.5, (0, 0, 255), 3)
                    else:
                        cv2.putText(frame_anotado, "Sin emergencias",
                                   (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                                   0.8, (0, 255, 0), 2)

                # Guardar frame procesado si está configurado
                if video_writer is not None:
                    video_writer.write(frame_anotado)

                # Mostrar frame solo si NO se va a reproducir después
                if not reproducir_despues:
                    cv2.imshow(nombre_ventana, frame_anotado)

                # Progreso en consola
                intervalo_progreso = 30 if not reproducir_despues else 10
                if frame_num % intervalo_progreso == 0 or reproducir_despues:
                    progreso = (frame_count / procesador.total_frames) * 100 if procesador.total_frames > 0 else 0

                    if modo == 1:
                        # Modo básico: solo contador
                        print(f"\r  Frame {frame_count}/{procesador.total_frames} ({progreso:.1f}%) - "
                              f"Vehículos detectados: {resultado.num_vehiculos}",
                              end='', flush=True)

                    elif modo == 2:
                        # Modo completo: todas las métricas
                        print(f"\r  Frame {frame_count}/{procesador.total_frames} ({progreso:.1f}%) - "
                              f"Vehículos: {resultado.num_vehiculos} - "
                              f"Velocidad: {resultado.velocidad_promedio:.1f} km/h - "
                              f"ICV: {resultado.icv:.3f} ({resultado.clasificacion_icv})",
                              end='', flush=True)

                    elif modo == 3:
                        # Modo emergencias: enfoque en detección de emergencias
                        estado_emerg = "🚨 EMERGENCIA" if resultado.hay_emergencia else "✓ Normal"
                        print(f"\r  Frame {frame_count}/{procesador.total_frames} ({progreso:.1f}%) - "
                              f"Vehículos: {resultado.num_vehiculos} - "
                              f"Estado: {estado_emerg}",
                              end='', flush=True)

                frame_num += 1
                frame_count += 1

            # Control de teclado solo si se está mostrando ventana
            if not reproducir_despues:
                key = cv2.waitKey(1 if not pausado else 100) & 0xFF

            # Control de teclado solo si no está en modo reproducir_despues
            if not reproducir_despues:
                if key == ord('q') or key == ord('Q'):
                    print("\n\n⏹️  Detenido por el usuario")
                    break
                elif key == ord('p') or key == ord('P') or key == ord(' '):
                    pausado = not pausado
                    if pausado:
                        print("\n\n⏸️  PAUSADO - Presiona P o ESPACIO para continuar")
                    else:
                        print("\n▶️  Reanudado...", end='', flush=True)
            else:
                # En modo reproducir_despues, no hay pause, solo procesa
                pass

        # Cerrar ventana y video
        cv2.destroyAllWindows()
        procesador.video.release()

        # Cerrar VideoWriter si existe
        if video_writer is not None:
            video_writer.release()
            print(f"\n\n✓ Video procesado guardado en: {ruta_video_procesado}")

        print("\n\n" + "="*70)
        print("✅ PROCESAMIENTO COMPLETADO")
        print("="*70)

        # Estadísticas según modo
        if resultados:
            import numpy as np

            print("\n📊 ESTADÍSTICAS:")
            print(f"  Frames procesados: {len(resultados)}")

            # Vehículos (común a todos los modos)
            num_vehiculos = [r.num_vehiculos for r in resultados]
            print(f"  Vehículos promedio: {np.mean(num_vehiculos):.1f}")
            print(f"  Vehículos máximo: {np.max(num_vehiculos)}")

            if modo == 1:
                # MODO BÁSICO: Solo conteo
                print(f"\n  💡 Detección básica completada")
                print(f"     Total de detecciones realizadas en {len(resultados)} frames")

            elif modo == 2:
                # MODO COMPLETO: Todas las métricas
                velocidades = [r.velocidad_promedio for r in resultados if r.velocidad_promedio > 0]
                if velocidades:
                    print(f"\n  Velocidad promedio: {np.mean(velocidades):.1f} km/h [REAL - Tracking]")
                    print(f"  Velocidad máxima: {np.max(velocidades):.1f} km/h")
                    print(f"  Velocidad mínima: {np.min(velocidades):.1f} km/h")

                icvs = [r.icv for r in resultados]
                print(f"\n  ICV promedio: {np.mean(icvs):.3f} [REAL - nucleo/]")
                print(f"  ICV máximo: {np.max(icvs):.3f}")

                # Clasificación
                fluidos = sum(1 for r in resultados if r.icv < 0.3)
                moderados = sum(1 for r in resultados if 0.3 <= r.icv < 0.6)
                congestionados = sum(1 for r in resultados if r.icv >= 0.6)

                print(f"\n  Distribución de congestión:")
                print(f"    Fluido: {fluidos} frames ({fluidos/len(resultados)*100:.1f}%)")
                print(f"    Moderado: {moderados} frames ({moderados/len(resultados)*100:.1f}%)")
                print(f"    Congestionado: {congestionados} frames ({congestionados/len(resultados)*100:.1f}%)")

            elif modo == 3:
                # MODO EMERGENCIAS: Enfoque en detección de emergencias
                emergencias = sum(1 for r in resultados if r.hay_emergencia)
                print(f"\n  🚨 Frames con emergencias: {emergencias} ({emergencias/len(resultados)*100:.1f}%)")
                print(f"  ✅ Frames normales: {len(resultados) - emergencias} ({(len(resultados) - emergencias)/len(resultados)*100:.1f}%)")

                if emergencias > 0:
                    print(f"\n  ⚠️ Se detectaron {emergencias} frames con vehículos de emergencia")
                else:
                    print(f"\n  ✓ No se detectaron vehículos de emergencia en el video")

            # Stats comunes para cálculos
            velocidades = [r.velocidad_promedio for r in resultados if r.velocidad_promedio > 0]
            icvs = [r.icv for r in resultados]
            fluidos = sum(1 for r in resultados if r.icv < 0.3)
            moderados = sum(1 for r in resultados if 0.3 <= r.icv < 0.6)
            congestionados = sum(1 for r in resultados if r.icv >= 0.6)
            emergencias = sum(1 for r in resultados if r.hay_emergencia)

        # Exportar resultados
        if exportar and resultados:
            print("\n📁 Exportando resultados...")

            # Crear carpeta de salida según modo
            modo_nombres = {1: 'basico', 2: 'completo', 3: 'emergencias'}
            modo_str = modo_nombres.get(modo, 'analisis')
            carpeta_salida = Path(f"datos/resultados-video/exportaciones/{modo_str}")
            carpeta_salida.mkdir(parents=True, exist_ok=True)

            # Exportar CSV
            nombre_base = Path(ruta_video).stem
            ruta_csv = carpeta_salida / f"{nombre_base}_modo{modo}_metricas.csv"
            procesador.exportar_resultados(resultados, str(ruta_csv))

            # Exportar estadísticas JSON
            import json
            ruta_json = carpeta_salida / f"{nombre_base}_modo{modo}_stats.json"

            stats = {
                'video': Path(ruta_video).name,
                'modo': modo,
                'modo_nombre': modos_nombre.get(modo, 'Desconocido'),
                'frames_procesados': len(resultados),
                'duracion_segundos': resultados[-1].timestamp if resultados else 0,
                'vehiculos_promedio': float(np.mean(num_vehiculos)),
                'vehiculos_maximo': int(np.max(num_vehiculos)),
                'velocidad_promedio_kmh': float(np.mean(velocidades)) if velocidades else 0,
                'icv_promedio': float(np.mean(icvs)),
                'frames_fluidos': fluidos,
                'frames_moderados': moderados,
                'frames_congestionados': congestionados,
                'emergencias_detectadas': emergencias
            }

            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Resultados exportados:")
            print(f"  CSV: {ruta_csv}")
            print(f"  JSON: {ruta_json}")

        # Reproducir video procesado si está configurado
        if reproducir_despues and ruta_video_procesado and ruta_video_procesado.exists():
            print("\n" + "="*70)
            print("🎬 REPRODUCIENDO VIDEO PROCESADO")
            print("="*70)
            print("\n▶️ Presiona Q para salir de la reproducción\n")

            # Abrir video procesado
            video_reproduccion = cv2.VideoCapture(str(ruta_video_procesado))

            if not video_reproduccion.isOpened():
                print("❌ No se pudo abrir el video procesado")
            else:
                # Ventana de reproducción
                ventana_reproduccion = 'Video Procesado - Presiona Q para salir'
                cv2.namedWindow(ventana_reproduccion, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(ventana_reproduccion, 1280, 720)

                fps_video = video_reproduccion.get(cv2.CAP_PROP_FPS)
                delay = int(1000 / fps_video) if fps_video > 0 else 33  # ~30 FPS por defecto

                while True:
                    ret, frame_repro = video_reproduccion.read()
                    if not ret:
                        break

                    cv2.imshow(ventana_reproduccion, frame_repro)

                    key = cv2.waitKey(delay) & 0xFF
                    if key == ord('q') or key == ord('Q'):
                        break

                video_reproduccion.release()
                cv2.destroyAllWindows()

                print("\n✓ Reproducción finalizada")

        return resultados

    except Exception as e:
        print(f"\n❌ ERROR durante el procesamiento:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Procesar video con visualización en tiempo real'
    )
    parser.add_argument(
        '--video',
        type=str,
        default=None,
        help='Ruta al video a procesar (si no se especifica, se selecciona interactivamente)'
    )
    parser.add_argument(
        '--no-exportar',
        action='store_true',
        help='No exportar resultados a archivos'
    )
    parser.add_argument(
        '--modo',
        type=int,
        default=None,
        choices=[1, 2, 3],
        help='Modo de análisis: 1=básico, 2=completo, 3=emergencias'
    )
    parser.add_argument(
        '--guardar-video',
        action='store_true',
        help='Guardar el video procesado a archivo'
    )
    parser.add_argument(
        '--reproducir-despues',
        action='store_true',
        help='Procesar sin mostrar, luego reproducir video completo (más fluido)'
    )
    parser.add_argument(
        '--saltar-frames',
        type=int,
        default=1,
        help='Procesar 1 de cada N frames (default=1, sin saltar)'
    )
    parser.add_argument(
        '--reducir-resolucion',
        type=float,
        default=1.0,
        help='Factor de reducción de resolución (0.5=mitad, 1.0=original)'
    )

    args = parser.parse_args()

    # Seleccionar video
    if args.video:
        ruta_video = args.video
        if not Path(ruta_video).exists():
            print(f"❌ Video no encontrado: {ruta_video}")
            return 1
    else:
        ruta_video = seleccionar_video_interactivo()
        if not ruta_video:
            return 1

    # Seleccionar modo de análisis
    if args.modo:
        modo = args.modo
    else:
        modo = seleccionar_modo_analisis()
        if not modo:
            return 1

    # Procesar
    resultados = procesar_video_con_visualizacion(
        ruta_video,
        modo=modo,
        exportar=not args.no_exportar,
        guardar_video=args.guardar_video or args.reproducir_despues,  # Auto-guardar si se va a reproducir
        reproducir_despues=args.reproducir_despues,
        saltar_frames=args.saltar_frames,
        reducir_resolucion=args.reducir_resolucion
    )

    if resultados:
        print("\n✅ Proceso completado exitosamente")
        return 0
    else:
        print("\n❌ Proceso falló")
        return 1


if __name__ == "__main__":
    sys.exit(main())
