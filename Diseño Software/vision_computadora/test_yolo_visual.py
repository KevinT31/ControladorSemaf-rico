"""
Script de Prueba para YOLO con Visualización
Permite probar la detección de vehículos en tiempo real con YOLO
"""

import sys
import os
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from vision_computadora.procesador_video import ProcesadorVideo
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_con_video(ruta_video: str = None):
    """
    Prueba YOLO con los videos de la carpeta por defecto
    Permite seleccionar el video antes de procesar
    """

    import os
    from pathlib import Path

    # Carpeta fija donde están los videos
    carpeta_videos = Path(r"C:/Users/kevin/OneDrive/Desktop/ControladorSemaforicoTFC2/vision_computadora/videos_prueba")

    print("\n📹 Carpeta de videos:")
    print(carpeta_videos)

    # Verificar que existan videos
    lista_videos = list(carpeta_videos.glob("*.mp4"))

    if not lista_videos:
        print("\n❌ No hay videos en la carpeta")
        print("Coloca tus videos MP4 allí y vuelve a intentar")
        return

    print("\nVideos disponibles:")
    for idx, video in enumerate(lista_videos, start=1):
        print(f"  {idx}. {video.name}")

    # Selección del usuario
    while True:
        try:
            opcion = int(input("\nSelecciona el número de video a procesar: "))
            if 1 <= opcion <= len(lista_videos):
                ruta_seleccionada = lista_videos[opcion - 1]
                break
            print("❌ Opción inválida. Intente de nuevo.")
        except ValueError:
            print("⚠ Solo números por favor.")

    print("\n" + "="*60)
    print("  TEST DE YOLO CON VIDEO")
    print("="*60)
    print(f"Video seleccionado: {ruta_seleccionada.name}")
    print("\nControles:")
    print("  - Presiona 'q' para salir")
    print("  - Presiona 'p' para pausar/reanudar")
    print("="*60 + "\n")

    try:
        # Crear procesador
        procesador = ProcesadorVideo(
            ruta_video=str(ruta_seleccionada),
            modelo_yolo='yolov8n.pt'
        )

        # Procesar con visualización
        resultados = procesador.procesar_con_visualizacion(
            saltar_frames=1,  # Procesar todos los frames
            mostrar_ventana=True,
            guardar_video='datos/videos-procesados/test_yolo_output.mp4'
        )

        # Mostrar estadísticas
        print("\n" + "="*60)
        print("  ESTADÍSTICAS DEL PROCESAMIENTO")
        print("="*60)
        print(f"Frames procesados: {len(resultados)}")

        if resultados:
            vehiculos_total = sum(r.num_vehiculos for r in resultados)
            print(f"Total de vehículos detectados: {vehiculos_total}")
            print(f"Promedio de vehículos por frame: {vehiculos_total / len(resultados):.1f}")

            icvs = [procesador._estimar_icv(r) for r in resultados]
            print(f"ICV promedio: {sum(icvs) / len(icvs):.3f}")

        print("="*60 + "\n")

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nAsegúrate de que el archivo de video existe.")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()



def test_con_camara():
    """
    Prueba YOLO con la cámara web en tiempo real
    """
    print("\n" + "="*60)
    print("  TEST DE YOLO CON CÁMARA WEB")
    print("="*60)
    print("\nControles:")
    print("  - Presiona 'q' para salir")
    print("  - Presiona 'p' para pausar/reanudar")
    print("="*60 + "\n")

    try:
        # Usar cámara (device 0)
        procesador = ProcesadorVideo(
            ruta_video=0,  # 0 = cámara por defecto
            modelo_yolo='yolov8n.pt'
        )

        # Procesar con visualización
        resultados = procesador.procesar_con_visualizacion(
            saltar_frames=1,
            mostrar_ventana=True
        )

        print(f"\n✓ Procesamiento completado: {len(resultados)} frames")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nAsegúrate de que tu cámara web está conectada y accesible.")

def menu_principal():
    """
    Menú principal para elegir qué test ejecutar
    """
    print("\n" + "="*60)
    print("  PRUEBA DE YOLO - SISTEMA DE DETECCIÓN VEHICULAR")
    print("="*60)
    print("\nSelecciona una opción:")
    print("  1. Probar con video existente")
    print("  2. Probar con cámara web")
    print("  3. Salir")
    print("="*60)

    opcion = input("\nOpción: ").strip()

    if opcion == '1':
        test_con_video()
    elif opcion == '2':
        test_con_camara()
    elif opcion == '3':
        print("¡Hasta luego!")
        sys.exit(0)
    else:
        print("Opción inválida")


if __name__ == "__main__":
    # Si se pasa un argumento, usar ese video
    if len(sys.argv) > 1:
        test_con_video(sys.argv[1])
    else:
        # Mostrar menú
        while True:
            try:
                menu_principal()
                input("\nPresiona Enter para volver al menú...")
            except KeyboardInterrupt:
                print("\n\n¡Hasta luego!")
                break
