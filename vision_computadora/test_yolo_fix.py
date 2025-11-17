"""
Script de prueba para YOLO con fix definitivo para PyTorch 2.6+
"""

import sys
import os
from pathlib import Path

# Configurar para cargar modelos sin restricciones
os.environ['TORCH_WEIGHTS_ONLY'] = '0'

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import warnings
warnings.filterwarnings('ignore')

def configurar_torch_para_yolo():
    """Configura PyTorch para cargar YOLO correctamente"""
    try:
        import torch

        print("Configurando PyTorch para YOLO...")

        # Método 1: Añadir clases seguras específicas
        try:
            from ultralytics.nn.tasks import DetectionModel
            from ultralytics.nn.modules import Conv, C2f, SPPF, Detect

            torch.serialization.add_safe_globals([
                DetectionModel, Conv, C2f, SPPF, Detect,
                type, dict, list, tuple, set, frozenset
            ])
            print("✓ Clases de ultralytics añadidas como seguras")
        except Exception as e:
            print(f"⚠ No se pudieron añadir clases específicas: {e}")

        # Método 2: Configurar contexto global
        try:
            # Para versiones más nuevas de PyTorch
            torch.serialization._set_default_safe_globals()
        except:
            pass

        print("✓ PyTorch configurado")

    except Exception as e:
        print(f"⚠ Error configurando PyTorch: {e}")


def test_yolo_simple():
    """Prueba simple de carga de YOLO"""
    print("\n" + "="*60)
    print("  TEST DE YOLO - FIX DEFINITIVO")
    print("="*60 + "\n")

    try:
        from ultralytics import YOLO
        import torch

        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA disponible: {torch.cuda.is_available()}")

        # Configurar PyTorch
        configurar_torch_para_yolo()

        print("\nIntentando cargar modelo YOLO...")
        modelo = YOLO('yolov8n.pt')
        print("✓ ¡Modelo YOLO cargado exitosamente!")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nINSTRUCCIONES PARA SOLUCIONAR:")
        print("1. Actualiza ultralytics: pip install --upgrade ultralytics")
        print("2. O usa versión anterior de torch: pip install torch==2.5.1")
        return False


def test_yolo_con_video(ruta_video):
    """Prueba YOLO con un video"""
    if not test_yolo_simple():
        return

    print("\n" + "="*60)
    print(f"  Procesando: {Path(ruta_video).name}")
    print("="*60 + "\n")

    try:
        from ultralytics import YOLO
        import cv2

        # Configurar PyTorch
        configurar_torch_para_yolo()

        # Cargar modelo
        modelo = YOLO('yolov8n.pt')

        # Abrir video
        cap = cv2.VideoCapture(ruta_video)
        if not cap.isOpened():
            print(f"❌ No se puede abrir el video: {ruta_video}")
            return

        print("✓ Video abierto correctamente")
        print("Presiona 'q' para salir\n")

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # Procesar solo algunos frames
            if frame_count % 5 == 0:
                # Detectar con YOLO
                resultados = modelo(frame, verbose=False)

                # Dibujar resultados
                frame_anotado = resultados[0].plot()

                # Mostrar
                cv2.imshow('YOLO - Detección', frame_anotado)

                # Contar vehículos
                vehiculos = 0
                for det in resultados[0].boxes:
                    clase = int(det.cls[0])
                    if clase in [2, 3, 5, 7]:  # car, motorcycle, bus, truck
                        vehiculos += 1

                print(f"Frame {frame_count}: {vehiculos} vehículos detectados", end='\r')

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        print(f"\n\n✓ Procesamiento completado: {frame_count} frames")

    except Exception as e:
        print(f"\n❌ Error procesando video: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test YOLO con fix para PyTorch 2.6+')
    parser.add_argument('video', nargs='?', help='Ruta al video (opcional)')
    parser.add_argument('--test', action='store_true', help='Solo probar carga del modelo')

    args = parser.parse_args()

    if args.test or not args.video:
        # Solo probar carga
        if test_yolo_simple():
            print("\n" + "="*60)
            print("  ✓ YOLO FUNCIONA CORRECTAMENTE")
            print("="*60)
            print("\nPara procesar un video:")
            print("  python test_yolo_fix.py ruta/al/video.mp4")
    else:
        # Probar con video
        test_yolo_con_video(args.video)
