"""
Rutas API para Procesamiento de Video con YOLO
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict
import cv2
import asyncio
import logging
import numpy as np
import time
from pathlib import Path
import sys
import io

from modelos.trafico import ResultadoVideo
from modelos.respuestas import MensajeResponse

# NO importar ProcesadorVideo aquí - se hace lazy loading dentro de las funciones
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/video",
    tags=["Procesamiento de Video"]
)

metricas_stream_actual = {
    'num_vehiculos': 0,
    'fps': 0,
    'icv': 0.0,
    'velocidad': 0.0,
    'flujo': 0.0
}


@router.get("/health")
async def health_check():
    """
    Verifica que el endpoint de video está funcionando
    """
    return {
        'status': 'ok',
        'message': 'Video API funcionando correctamente',
        'camara_disponible': True
    }


@router.get("/estado", response_model=Dict)
async def obtener_estado_video():
    """
    Obtiene el estado del procesador de video

    Returns:
        Estado del procesador (activo, modelo usado, etc)
    """
    from servicios.video_service import VideoService
    return VideoService.obtener_estado()


@router.post("/procesar", response_model=ResultadoVideo)
async def procesar_frame_video(frame_data: Dict):
    """
    Procesa un frame de video con YOLO y calcula métricas

    Args:
        frame_data: Diccionario con 'frame' (base64) e 'interseccion_id'

    Returns:
        Resultado del procesamiento con detecciones y métricas
    """
    from servicios.video_service import VideoService

    if 'frame' not in frame_data:
        raise HTTPException(
            status_code=400,
            detail="Campo 'frame' requerido en el body"
        )

    if 'interseccion_id' not in frame_data:
        raise HTTPException(
            status_code=400,
            detail="Campo 'interseccion_id' requerido en el body"
        )

    try:
        resultado = await VideoService.procesar_frame(frame_data)
        return resultado
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando frame: {str(e)}"
        )


@router.post("/activar", response_model=MensajeResponse)
async def activar_procesador(modelo: str = "yolov8n.pt", confianza: float = 0.5):
    """
    Activa el procesador de video con YOLO

    Args:
        modelo: Nombre del modelo YOLO a usar
        confianza: Umbral de confianza para detecciones (0-1)

    Returns:
        Mensaje de confirmación
    """
    from servicios.video_service import VideoService

    if not 0 <= confianza <= 1:
        raise HTTPException(
            status_code=400,
            detail="Confianza debe estar entre 0 y 1"
        )

    try:
        VideoService.activar(modelo, confianza)
        return MensajeResponse(
            mensaje=f"Procesador de video activado con modelo {modelo}",
            datos={'modelo': modelo, 'confianza': confianza}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/desactivar", response_model=MensajeResponse)
async def desactivar_procesador():
    """
    Desactiva el procesador de video

    Returns:
        Mensaje de confirmación
    """
    from servicios.video_service import VideoService

    VideoService.desactivar()
    return MensajeResponse(mensaje="Procesador de video desactivado")


@router.get("/estadisticas", response_model=Dict)
async def obtener_estadisticas():
    """
    Obtiene estadísticas del procesamiento de video

    Returns:
        Estadísticas (frames procesados, FPS promedio, etc)
    """
    from servicios.video_service import VideoService
    return VideoService.obtener_estadisticas()


@router.post("/guardar-analisis", response_model=MensajeResponse)
async def guardar_analisis_csv(datos: Dict):
    """
    Guarda el análisis de video en formato CSV

    Args:
        datos: Diccionario con los datos a exportar

    Returns:
        Mensaje con la ruta del archivo guardado
    """
    from servicios.video_service import VideoService

    try:
        ruta_archivo = VideoService.guardar_analisis_csv(datos)
        return MensajeResponse(
            mensaje=f"Análisis guardado correctamente",
            datos={'archivo': ruta_archivo}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metricas-stream")
async def obtener_metricas_stream():
    """
    Obtiene las métricas actuales del stream de video
    """
    return metricas_stream_actual


@router.get("/frame-camera")
async def frame_camera():
    """
    Devuelve un único frame JPEG de la cámara con anotaciones YOLO y actualiza métricas.

    Uso pensado para polling desde el frontend.
    """
    # Fix para ultralytics - agregar encoding a stdout si no existe
    if not hasattr(sys.stdout, 'encoding'):
        sys.stdout.encoding = 'utf-8'
    if not hasattr(sys.stderr, 'encoding'):
        sys.stderr.encoding = 'utf-8'

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from vision_computadora.procesador_video import ProcesadorVideo

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise HTTPException(status_code=503, detail="Cámara no disponible")

    try:
        ret, frame = cap.read()
        if not ret:
            raise HTTPException(status_code=500, detail="No se pudo leer frame de la cámara")

        # Procesar un único frame. Se crea el procesador con el mismo parámetro que el stream.
        procesador = ProcesadorVideo(
            ruta_video=0,
            pixeles_por_metro=15.0,
            calcular_metricas_cap6=True
        )

        resultado = procesador.procesar_frame(frame, 0)
        frame_anotado = procesador.dibujar_detecciones(frame, resultado, mostrar_info=True)

        # Actualizar métricas globales para que /metricas-stream refleje el último cálculo
        global metricas_stream_actual
        metricas_stream_actual = {
            'num_vehiculos': resultado.num_vehiculos,
            'fps': 0,
            'icv': round(resultado.icv, 3),
            'velocidad': round(resultado.velocidad_promedio, 1),
            'flujo': round(resultado.flujo_vehicular, 1)
        }

        ret, buffer = cv2.imencode('.jpg', frame_anotado, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            raise HTTPException(status_code=500, detail="Fallo al codificar JPEG")

        # Responder como imagen/jpeg de un único frame
        bytes_io = io.BytesIO(buffer.tobytes())
        return StreamingResponse(bytes_io, media_type="image/jpeg")
    finally:
        cap.release()


@router.get("/stream-camera")
async def stream_camera():
    """
    Stream de cámara en tiempo real con detección y métricas
    """
    # Fix para ultralytics - agregar encoding a stdout si no existe
    if not hasattr(sys.stdout, 'encoding'):
        sys.stdout.encoding = 'utf-8'
    if not hasattr(sys.stderr, 'encoding'):
        sys.stderr.encoding = 'utf-8'
    
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from vision_computadora.procesador_video import ProcesadorVideo
    
    async def generate_frames():
        global metricas_stream_actual
        procesador = None
        try:
            logger.info("Iniciando stream de camara...")
            procesador = ProcesadorVideo(
                ruta_video=0,
                pixeles_por_metro=15.0,
                calcular_metricas_cap6=True  # FORZAR métricas avanzadas para consistencia
            )

            if not procesador.video.isOpened():
                logger.error("No se pudo abrir la camara")
                raise Exception("No se pudo abrir la camara")
            
            # Configurar resolución de la cámara para que las métricas se vean bien
            procesador.video.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            procesador.video.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            actual_width = int(procesador.video.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(procesador.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"Resolución de cámara configurada: {actual_width}x{actual_height}")

            frame_num = 0
            fps_counter = 0
            fps_start_time = time.time()
            logger.info("Stream de camara iniciado correctamente")

            while True:
                ret, frame = procesador.video.read()
                if not ret:
                    logger.warning("No se pudo leer frame de la camara")
                    break

                # Log para verificar que estamos procesando
                if frame_num == 0:
                    logger.info(f"Procesando primer frame - Shape: {frame.shape}, Dtype: {frame.dtype}")

                resultado = procesador.procesar_frame(frame, frame_num)

                # Log cada 30 frames para ver que las métricas se están calculando
                if frame_num % 30 == 0:
                    logger.info(f"Frame {frame_num}: Vehículos={resultado.num_vehiculos}, ICV={resultado.icv:.3f}, metricas_cap6={resultado.metricas_cap6 is not None}")

                frame_anotado = procesador.dibujar_detecciones(
                    frame,
                    resultado,
                    mostrar_info=True
                )
                
                # Verificar que el frame anotado tiene contenido
                if frame_num == 0:
                    logger.info(f"Frame anotado - Shape: {frame_anotado.shape}, Min: {frame_anotado.min()}, Max: {frame_anotado.max()}")

                fps_counter += 1
                elapsed = time.time() - fps_start_time
                if elapsed >= 1.0:
                    fps_actual = fps_counter / elapsed
                    metricas_stream_actual = {
                        'num_vehiculos': resultado.num_vehiculos,
                        'fps': int(fps_actual),
                        'icv': round(resultado.icv, 3),
                        'velocidad': round(resultado.velocidad_promedio, 1),
                        'flujo': round(resultado.flujo_vehicular, 1)
                    }
                    fps_counter = 0
                    fps_start_time = time.time()

                ret, buffer = cv2.imencode('.jpg', frame_anotado, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ret:
                    continue

                frame_bytes = buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                frame_num += 1
                await asyncio.sleep(0.033)

        except asyncio.CancelledError:
            logger.info("Stream cancelado por cliente")
        except Exception as e:
            logger.error(f"Error en stream de camara: {e}", exc_info=True)
            raise
        finally:
            if procesador is not None:
                procesador.video.release()
                metricas_stream_actual = {
                    'num_vehiculos': 0,
                    'fps': 0,
                    'icv': 0.0,
                    'velocidad': 0.0,
                    'flujo': 0.0
                }
                logger.info("Stream de camara finalizado")

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/listar-videos-procesados")
async def listar_videos_procesados():
    """
    Lista todos los videos procesados disponibles ordenados
    """
    videos_path = Path(__file__).parent.parent.parent / "datos" / "resultados-video" / "videos-procesados"

    videos_lista = []
    for carpeta in ['basico', 'completo', 'emergencias']:
        carpeta_path = videos_path / carpeta
        if carpeta_path.exists():
            for video_path in sorted(carpeta_path.glob('*.mp4')):
                videos_lista.append({
                    'nombre': video_path.stem,
                    'archivo': video_path.name,
                    'tipo': carpeta,
                    'ruta': str(video_path)
                })

    return {'videos': videos_lista}


@router.get("/stream-video-index/{video_index}")
async def stream_video_index(video_index: int):
    """
    Stream de un video procesado específico por índice en bucle con análisis en tiempo real
    Videos 1 y 3: Empiezan análisis YOLO desde segundo 30, pero video se muestra desde segundo 0
    """
    # Fix para ultralytics - agregar encoding a stdout si no existe
    if not hasattr(sys.stdout, 'encoding'):
        sys.stdout.encoding = 'utf-8'
    if not hasattr(sys.stderr, 'encoding'):
        sys.stderr.encoding = 'utf-8'
    
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from vision_computadora.procesador_video import ProcesadorVideo
    
    videos_path = Path(__file__).parent.parent.parent / "datos" / "videos-prueba"

    videos_encontrados = []
    if videos_path.exists():
        # Buscar videos en todas las subcarpetas recursivamente
        videos_encontrados = sorted(videos_path.glob('**/*.mp4'))

    if video_index < 0 or video_index >= len(videos_encontrados):
        raise HTTPException(status_code=404, detail=f"Video no encontrado. Index: {video_index}, Total videos: {len(videos_encontrados)}")

    video_path = videos_encontrados[video_index]

    async def generate_frames():
        global metricas_stream_actual
        procesador = None
        try:
            logger.info(f"Analizando video: {video_path.name}")

            # Determinar si este video requiere saltar 30 segundos para análisis
            nombre_video = video_path.stem.lower()
            segundos_saltar_analisis = 0
            if 'video1' in nombre_video or 'video3' in nombre_video or 'video_1' in nombre_video or 'video_3' in nombre_video:
                segundos_saltar_analisis = 30
                logger.info(f"⏩ Video {video_index + 1}: Análisis YOLO iniciará desde segundo {segundos_saltar_analisis}")
                logger.info(f"📹 Video mostrado: desde segundo 0 (completo)")

            while True:
                procesador = ProcesadorVideo(
                    ruta_video=str(video_path),
                    pixeles_por_metro=None,  # Autoajuste ppm por resolución
                    calcular_metricas_cap6=True  # FORZAR métricas avanzadas para todos los videos
                )

                if not procesador.video.isOpened():
                    logger.warning(f"No se pudo abrir: {video_path.name}")
                    break

                fps = procesador.video.get(cv2.CAP_PROP_FPS) or 30
                frame_inicio_analisis = int(segundos_saltar_analisis * fps)
                delay = 1.0 / fps

                frame_num = 0
                fps_counter = 0
                fps_start_time = time.time()
                logger.info(f"Inicio de stream - FPS: {fps}")

                while True:
                    ret, frame = procesador.video.read()
                    if not ret:
                        break

                    # ANÁLISIS: Solo hacer detección YOLO después del segundo 30 (videos 1 y 3)
                    if frame_num >= frame_inicio_analisis:
                        resultado = procesador.procesar_frame(frame, frame_num)
                        frame_anotado = procesador.dibujar_detecciones(
                            frame,
                            resultado,
                            mostrar_info=True,
                            modo_simple=False  # Mostrar panel de métricas para ver longitud de cola
                        )

                        # Actualizar métricas solo cuando hay análisis
                        fps_counter += 1
                        elapsed = time.time() - fps_start_time
                        if elapsed >= 1.0:
                            fps_actual = fps_counter / elapsed
                            metricas_stream_actual = {
                                'num_vehiculos': resultado.num_vehiculos,
                                'fps': int(fps_actual),
                                'icv': round(resultado.icv, 3),
                                'velocidad': round(resultado.velocidad_promedio, 1),
                                'flujo': round(resultado.flujo_vehicular, 1)
                            }
                            fps_counter = 0
                            fps_start_time = time.time()
                    else:
                        # ANTES del segundo 30: Mostrar frame SIN overlay ni análisis
                        frame_anotado = frame.copy()
                        
                        # Panel superior simple con mensaje
                        overlay = frame_anotado.copy()
                        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 60), (35, 30, 40), -1)
                        frame_anotado = cv2.addWeighted(overlay, 0.85, frame_anotado, 0.15, 0)
                        
                        segundos_restantes = int((frame_inicio_analisis - frame_num) / fps)
                        cv2.putText(
                            frame_anotado,
                            f"Esperando estabilizacion del video...",
                            (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (255, 255, 255),
                            1
                        )
                        cv2.putText(
                            frame_anotado,
                            f"Analisis YOLO inicia en {segundos_restantes} segundos",
                            (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (246, 92, 139),
                            1
                        )
                        
                        # Métricas en 0 mientras no hay análisis
                        metricas_stream_actual = {
                            'num_vehiculos': 0,
                            'fps': 0,
                            'icv': 0.0,
                            'velocidad': 0.0,
                            'flujo': 0.0
                        }

                    ret, buffer = cv2.imencode('.jpg', frame_anotado, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if not ret:
                        continue

                    frame_bytes = buffer.tobytes()

                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                    frame_num += 1
                    await asyncio.sleep(delay)

                procesador.video.release()

        except asyncio.CancelledError:
            logger.info("Stream cancelado por cliente")
        except Exception as e:
            logger.error(f"Error en stream de video: {e}", exc_info=True)
        finally:
            if procesador is not None:
                procesador.video.release()
                metricas_stream_actual = {
                    'num_vehiculos': 0,
                    'fps': 0,
                    'icv': 0.0,
                    'velocidad': 0.0,
                    'flujo': 0.0
                }

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/stream-processed-loop")
async def stream_processed_loop(video_filter: str = ""):
    """
    Stream en bucle de videos procesados guardados

    Args:
        video_filter: Filtro opcional para buscar videos específicos por nombre
    """
    async def generate_frames():
        videos_path = Path(__file__).parent.parent.parent / "datos" / "resultados-video" / "videos-procesados"

        videos_encontrados = []
        for carpeta in ['basico', 'completo', 'emergencias']:
            carpeta_path = videos_path / carpeta
            if carpeta_path.exists():
                for video in carpeta_path.glob('*.mp4'):
                    if not video_filter or video_filter.lower() in video.stem.lower():
                        videos_encontrados.append(video)

        if not videos_encontrados:
            logger.warning("No se encontraron videos procesados")
            frame_negro = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame_negro, "No hay videos procesados", (100, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame_negro)
            frame_bytes = buffer.tobytes()

            while True:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                await asyncio.sleep(1)
            return

        logger.info(f"Encontrados {len(videos_encontrados)} videos procesados")

        while True:
            for video_path in videos_encontrados:
                logger.info(f"Reproduciendo: {video_path.name}")

                cap = cv2.VideoCapture(str(video_path))
                if not cap.isOpened():
                    logger.warning(f"No se pudo abrir: {video_path.name}")
                    continue

                fps = cap.get(cv2.CAP_PROP_FPS) or 30
                delay = 1.0 / fps

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if not ret:
                        continue

                    frame_bytes = buffer.tobytes()

                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                    await asyncio.sleep(delay)

                cap.release()
                await asyncio.sleep(0.5)

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
