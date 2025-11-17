# -*- coding: utf-8 -*-
"""
Script Simple para Procesar Videos
Sistema de Control Semafórico - Con Métricas del Capítulo 6

Uso:
    python procesar_video_simple.py ruta_al_video.mp4
"""

import sys
from pathlib import Path
import cv2
import logging

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

print("="*80)
print("PROCESADOR DE VIDEO - Sistema de Control Semaforico")
print("Con metricas del Capitulo 6")
print("="*80)

def buscar_videos():
    """Busca videos en las carpetas del proyecto"""
    carpetas = [
        Path("datos/videos-prueba/analisis-parametros"),
        Path("datos/videos-prueba/deteccion-basica"),
        Path("datos/videos-prueba/deteccion-emergencia"),
        Path("datos"),
    ]

    videos = []
    for carpeta in carpetas:
        if carpeta.exists():
            for ext in ['*.mp4', '*.avi', '*.mov', '*.mkv']:
                videos.extend(carpeta.glob(ext))

    return videos

def main():
    """Función principal"""

    # 1. Seleccionar video
    print("\n[1/4] Seleccionando video...")

    if len(sys.argv) > 1:
        ruta_video = sys.argv[1]
        if not Path(ruta_video).exists():
            print(f"ERROR: Video no encontrado: {ruta_video}")
            return 1
    else:
        videos = buscar_videos()

        if not videos:
            print("\nNo se encontraron videos en las carpetas del proyecto.")
            print("\nColoca videos en:")
            print("  - datos/videos-prueba/analisis-parametros/")
            print("  - datos/videos-prueba/deteccion-basica/")
            print("\nO ejecuta: python procesar_video_simple.py ruta_al_video.mp4")
            return 1

        print(f"\nVideos disponibles ({len(videos)}):\n")
        for i, video in enumerate(videos, 1):
            size_mb = video.stat().st_size / (1024 * 1024)
            print(f"  {i}. {video.name} ({size_mb:.1f} MB)")

        try:
            opcion = int(input(f"\nSelecciona video (1-{len(videos)}): "))
            if 1 <= opcion <= len(videos):
                ruta_video = str(videos[opcion - 1])
            else:
                print("Opcion invalida")
                return 1
        except (ValueError, KeyboardInterrupt):
            print("\nCancelado")
            return 1

    print(f"\nVideo seleccionado: {Path(ruta_video).name}")

    # 2. Importar módulos
    print("\n[2/4] Cargando modulos...")

    try:
        from vision_computadora.procesador_video import ProcesadorVideo
        print("  OK - Modulos cargados")
    except Exception as e:
        print(f"  ERROR al importar modulos: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 3. Crear procesador
    print("\n[3/4] Inicializando procesador...")

    try:
        procesador = ProcesadorVideo(
            ruta_video=ruta_video,
            pixeles_por_metro=15.0,
            calcular_metricas_cap6=True,  # ACTIVAR METRICAS CAP 6
            longitud_carril=200.0
        )

        print(f"  Resolucion: {procesador.ancho}x{procesador.alto}")
        print(f"  FPS: {procesador.fps:.1f}")
        print(f"  Frames totales: {procesador.total_frames}")
        print(f"  Duracion: {procesador.total_frames/procesador.fps:.1f} segundos")
        print(f"  Tracker: {procesador.tracker.tipo_tracker}")
        print(f"  Modelo YOLO: {procesador.version_yolo}")
        print(f"  Metricas Cap 6: ACTIVADAS")

    except Exception as e:
        print(f"  ERROR al crear procesador: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 4. Procesar video frame por frame
    print("\n[4/4] Procesando video...")
    print("\nPresiona 'q' en la ventana para detener")
    print("Presiona 'p' para pausar/continuar")
    print()

    resultados = []
    frame_num = 0
    pausado = False

    # Crear ventana
    nombre_ventana = 'Procesamiento - Presiona Q para salir, P para pausar'
    cv2.namedWindow(nombre_ventana, cv2.WINDOW_NORMAL)

    try:
        while True:
            if not pausado:
                ret, frame = procesador.video.read()
                if not ret:
                    break

                # Procesar frame
                resultado = procesador.procesar_frame(frame, frame_num)
                resultados.append(resultado)

                # Dibujar visualización
                frame_anotado = procesador.dibujar_detecciones(frame, resultado)

                # Mostrar
                cv2.imshow(nombre_ventana, frame_anotado)

                # Progreso cada 30 frames
                if frame_num % 30 == 0:
                    progreso = (frame_num / procesador.total_frames) * 100 if procesador.total_frames > 0 else 0
                    print(f"\rProgreso: {progreso:.1f}% | Frame: {frame_num} | "
                          f"Vehiculos: {resultado.num_vehiculos} | "
                          f"ICV: {resultado.icv:.3f} ({resultado.clasificacion_icv})", end='')

                frame_num += 1

            # Controles de teclado
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n\nDetenido por el usuario")
                break
            elif key == ord('p'):
                pausado = not pausado
                if pausado:
                    print("\n[PAUSADO] Presiona P para continuar")
                else:
                    print("[CONTINUANDO...]")

        cv2.destroyAllWindows()
        procesador.video.release()

    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario")
        cv2.destroyAllWindows()
        procesador.video.release()
    except Exception as e:
        print(f"\n\nERROR durante procesamiento: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()
        procesador.video.release()
        return 1

    # 5. Exportar resultados
    print("\n\n" + "="*80)
    print("EXPORTANDO RESULTADOS")
    print("="*80)

    if resultados:
        # Crear carpeta de salida
        carpeta_salida = Path("datos/resultados-video/exportaciones")
        carpeta_salida.mkdir(parents=True, exist_ok=True)

        nombre_base = Path(ruta_video).stem
        ruta_csv = carpeta_salida / f"analisis_{nombre_base}.csv"

        try:
            procesador.exportar_resultados(resultados, str(ruta_csv))
            print(f"\nOK - Resultados exportados a:")
            print(f"     {ruta_csv}")

            # Mostrar estadísticas
            print("\n" + "="*80)
            print("ESTADISTICAS")
            print("="*80)
            print(f"\nFrames procesados: {len(resultados)}")

            # Estadísticas básicas
            velocidades = [r.velocidad_promedio for r in resultados if r.velocidad_promedio > 0]
            if velocidades:
                import numpy as np
                print(f"Velocidad promedio: {np.mean(velocidades):.2f} km/h")
                print(f"Velocidad max: {np.max(velocidades):.2f} km/h")
                print(f"Velocidad min: {np.min(velocidades):.2f} km/h")

            icvs = [r.icv for r in resultados]
            if icvs:
                import numpy as np
                print(f"\nICV promedio: {np.mean(icvs):.3f}")
                print(f"ICV max: {np.max(icvs):.3f}")
                print(f"ICV min: {np.min(icvs):.3f}")

            # Estadísticas del Capítulo 6
            resultados_cap6 = [r for r in resultados if r.metricas_cap6]
            if resultados_cap6:
                print("\n" + "-"*80)
                print("METRICAS DEL CAPITULO 6")
                print("-"*80)

                import numpy as np
                sc_promedio = np.mean([r.metricas_cap6['stopped_count'] for r in resultados_cap6])
                vavg_promedio = np.mean([r.metricas_cap6['velocidad_promedio_movimiento'] for r in resultados_cap6])
                pi_promedio = np.mean([r.metricas_cap6['parametro_intensidad'] for r in resultados_cap6])
                icv_cap6_promedio = np.mean([r.metricas_cap6['icv'] for r in resultados_cap6])

                print(f"\nStopped Count promedio: {sc_promedio:.1f} vehiculos")
                print(f"Vavg (movimiento) promedio: {vavg_promedio:.2f} km/h")
                print(f"Parametro Intensidad (PI) promedio: {pi_promedio:.3f}")
                print(f"ICV (Cap 6.2.3) promedio: {icv_cap6_promedio:.3f}")

                print(f"\n{len(resultados_cap6)} frames con metricas del Capitulo 6 exportadas")

            print("\n" + "="*80)
            print("PROCESO COMPLETADO EXITOSAMENTE")
            print("="*80)

            return 0

        except Exception as e:
            print(f"\nERROR al exportar: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        print("\nNo hay resultados para exportar")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
