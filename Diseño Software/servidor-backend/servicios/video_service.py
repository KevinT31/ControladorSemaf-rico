"""
Servicio para Procesamiento de Video con YOLO
"""

from typing import Dict
import logging
from datetime import datetime
from pathlib import Path

from .estado_global import estado_sistema

logger = logging.getLogger(__name__)


class VideoService:
    """Servicio para procesamiento de video"""

    @staticmethod
    def obtener_estado() -> Dict:
        """Retorna el estado del procesador de video"""
        if estado_sistema.procesador_video:
            return {
                'activo': True,
                'modelo': 'yolov8n.pt',
                'frames_procesados': estado_sistema.video_frame_count
            }
        return {'activo': False}

    @staticmethod
    async def procesar_frame(frame_data: Dict) -> Dict:
        """Procesa un frame de video con YOLO"""
        import base64
        import numpy as np
        import cv2

        # Inicializar procesador si no existe
        if not estado_sistema.procesador_video:
            VideoService.activar('yolov8n.pt', 0.5)

        procesador = estado_sistema.procesador_video

        # Decodificar frame
        frame_base64 = frame_data['frame'].split(',')[1] if ',' in frame_data['frame'] else frame_data['frame']
        frame_bytes = base64.b64decode(frame_base64)
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Procesar frame
        frame_num = estado_sistema.video_frame_count
        estado_sistema.video_frame_count += 1

        resultado = procesador.procesar_frame(frame, frame_num)

        # Calcular ICV
        calculador = estado_sistema.calculador_icv
        resultado_icv = calculador.calcular(
            longitud_cola=resultado.longitud_cola,
            velocidad_promedio=resultado.velocidad_promedio,
            flujo_vehicular=resultado.flujo_estimado
        )

        # Formatear detecciones
        detecciones_formateadas = []
        for vehiculo in resultado.vehiculos_detectados:
            detecciones_formateadas.append({
                'clase': vehiculo.get('clase', 'vehiculo'),
                'confianza': vehiculo.get('confianza', 0.0),
                'bbox': vehiculo.get('bbox', [0, 0, 0, 0])
            })

        return {
            'detecciones': detecciones_formateadas,
            'num_vehiculos': resultado.num_vehiculos,
            'frame_procesado': frame_data.get('frame'),
            'metricas': {
                'icv': resultado_icv['icv'],
                'clasificacion': resultado_icv['clasificacion'],
                'flujo': resultado.flujo_estimado,
                'velocidad': resultado.velocidad_promedio,
                'cola': resultado.longitud_cola,
                'num_vehiculos': resultado.num_vehiculos
            }
        }

    @staticmethod
    def activar(modelo: str, confianza: float):
        """Activa el procesador de video"""
        import sys
        from pathlib import Path

        vision_path = Path(__file__).parent.parent.parent / 'vision_computadora'
        sys.path.insert(0, str(vision_path))

        from procesador_video import ProcesadorVideo

        estado_sistema.procesador_video = ProcesadorVideo(
            modelo=modelo,
            confianza=confianza
        )
        logger.info(f"Procesador de video activado: {modelo}")

    @staticmethod
    def desactivar():
        """Desactiva el procesador de video"""
        estado_sistema.procesador_video = None
        logger.info("Procesador de video desactivado")

    @staticmethod
    def obtener_estadisticas() -> Dict:
        """Obtiene estadísticas del procesamiento"""
        return {
            'frames_procesados': estado_sistema.video_frame_count,
            'activo': estado_sistema.procesador_video is not None
        }

    @staticmethod
    def guardar_analisis_csv(datos: Dict) -> str:
        """Guarda análisis en CSV"""
        import pandas as pd

        ruta_base = Path(__file__).parent.parent.parent / 'datos' / 'videos-procesados'
        ruta_base.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f"analisis_{timestamp}.csv"
        ruta_completa = ruta_base / nombre_archivo

        df = pd.DataFrame(datos)
        df.to_csv(ruta_completa, index=False)

        logger.info(f"Análisis guardado en: {ruta_completa}")
        return str(ruta_completa)
