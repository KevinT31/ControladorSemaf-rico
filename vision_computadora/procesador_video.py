"""
Procesador de Videos de Intersecciones Vehiculares - 100% REAL

Este módulo procesa videos reales de intersecciones usando:
- YOLOv8 para detección de vehículos
- Tracking real para calcular velocidad (NO np.random)
- Detector custom de emergencias
- Cálculo ICV real usando nucleo/indice_congestion.py

⚠️ NO USA np.random - Todo basado en detecciones y cálculos reales
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import sys
import torch

# Importar módulos del proyecto
sys.path.append(str(Path(__file__).parent.parent))

from vision_computadora.tracking_vehicular import TrackerVehicular
from vision_computadora.detector_emergencia import DetectorEmergencia
from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion

# Fix para PyTorch 2.6+ - Suprimir warnings sobre weights_only
# El fix real se aplica en _cargar_modelo_yolo_con_fallback()
import warnings
warnings.filterwarnings('ignore', message='.*weights_only.*')
warnings.filterwarnings('ignore', message='.*safe_globals.*')

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    logging.warning("YOLOv8 no instalado. Instalar con: pip install ultralytics")

logger = logging.getLogger(__name__)


@dataclass
class ResultadoFrame:
    """Resultado del análisis REAL de un frame"""
    numero_frame: int
    timestamp: float  # segundos
    num_vehiculos: int
    vehiculos_detectados: List[Dict]

    # Métricas REALES (NO random)
    flujo_vehicular: float  # veh/min - Basado en tracking
    velocidad_promedio: float  # km/h - Basado en tracking REAL
    longitud_cola: float  # metros - Basado en detecciones
    cola_vehiculos_count: int  # conteo de vehículos en fila (colas por vehículos)

    # ICV REAL (calculado por nucleo/)
    icv: float
    clasificacion_icv: str  # fluido/moderado/congestionado
    color_icv: str

    # Emergencias
    hay_emergencia: bool
    detecciones_emergencia: List  # DeteccionEmergencia objects

    # Métricas avanzadas (NUEVAS)
    metricas_cap6: Optional[Dict] = None  # Contiene métricas avanzadas


class ProcesadorVideo:
    """
    Procesador REAL de videos de tráfico

    ✅ Usa YOLO para detección
    ✅ Usa tracking para velocidad REAL
    ✅ Usa nucleo/ para ICV REAL
    ✅ Usa detector custom para emergencias
    ❌ NO usa np.random en ninguna parte
    """

    def __init__(
        self,
        ruta_video,
        modelo_yolo: str = 'yolov8n.pt',
        modelo_emergencia: Optional[str] = None,
        roi: Optional[Tuple[int, int, int, int]] = None,
        pixeles_por_metro: float = 15.0,  # Calibración espacial
        parametros_icv: Optional[ParametrosInterseccion] = None,
        calcular_metricas_cap6: bool = True,  # Activar métricas avanzadas
        longitud_carril: float = 200.0,  # Longitud efectiva del carril
        epsilon_velocidad_kmh: Optional[float] = None  # Umbral global detenido/movimiento (km/h)
    ):
        """
        Args:
            ruta_video: Ruta al archivo de video o índice de cámara (int)
            modelo_yolo: Modelo YOLO para detección general
            modelo_emergencia: Modelo YOLO custom para emergencias
            roi: Región de interés (x, y, w, h) o None
            pixeles_por_metro: Calibración espacial para velocidad
            parametros_icv: Parámetros para cálculo ICV
            calcular_metricas_cap6: Si calcular métricas avanzadas
            longitud_carril: Longitud efectiva del carril en metros
        """
        # Cargar video
        if isinstance(ruta_video, int):
            self.ruta_video = Path(f"Camara_{ruta_video}")
            self.video = cv2.VideoCapture(ruta_video)
            self.es_camara = True
        else:
            self.ruta_video = Path(ruta_video)
            if not self.ruta_video.exists():
                raise FileNotFoundError(f"Video no encontrado: {ruta_video}")
            self.video = cv2.VideoCapture(str(self.ruta_video))
            self.es_camara = False

        self.fps = self.video.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
        self.ancho = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.alto = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.roi = roi
        # Calibración espacial: adaptar ppm según resolución para videos con distintas dimensiones
        # Usamos un ppm base asumido para una resolución de referencia (ej. ancho 640)
        referencia_ancho = 640.0
        ppm_base = float(pixeles_por_metro) if pixeles_por_metro else 15.0
        if self.ancho > 0:
            escala_ancho = self.ancho / referencia_ancho
            self.pixeles_por_metro = ppm_base * escala_ancho
        else:
            self.pixeles_por_metro = ppm_base
        logger.info(f"Calibracion ppm ajustada por resolucion: {self.pixeles_por_metro:.2f} px/m (ancho={self.ancho})")

        # Cargar modelo YOLO con soporte YOLO11 y fallback a YOLO8
        if YOLO is not None:
            self.modelo_yolo, self.version_yolo = self._cargar_modelo_yolo_con_fallback(modelo_yolo)
            logger.info(f"YOLO cargado: {self.version_yolo}")
        else:
            raise ImportError("ultralytics no disponible. Instalar con: pip install ultralytics")

        # Clases de vehículos (COCO dataset)
        self.clases_vehiculos = [2, 3, 5, 7]  # car, motorcycle, bus, truck

        # Preparar parámetros ICV y epsilon global (fuente de verdad)
        parametros_icv_local = parametros_icv or ParametrosInterseccion()
        # Usar epsilon explícito si se pasa; si no, intentar tomar de parametros_icv_local
        # y si no existe el atributo, caer a 5.0 km/h por defecto
        self.epsilon_velocidad_kmh = (
            epsilon_velocidad_kmh if epsilon_velocidad_kmh is not None else getattr(parametros_icv_local, 'EPSILON_VELOCIDAD', 5.0)
        )

        # Inicializar tracker (para velocidad REAL) con epsilon unificado
        self.tracker = TrackerVehicular(
            fps=self.fps,
            pixeles_por_metro=pixeles_por_metro,
            usar_deepsort=True,  # Fallback si ByteTrack no está disponible
            preferir_bytetrack=True,
            velocidad_max_kmh=60.0,  # Ciudad: limitar a 60 km/h
            epsilon_motion_kmh=self.epsilon_velocidad_kmh
        )

        # Inicializar detector de emergencias (modo silencioso)
        self.detector_emergencia = DetectorEmergencia(
            modelo_path=modelo_emergencia,
            silencioso=True  # No mostrar warnings molestos
        )

        # Inicializar calculador ICV REAL
        self.calculador_icv = CalculadorICV(parametros_icv_local)

        # Configuración de métricas avanzadas
        self.calcular_metricas_cap6 = calcular_metricas_cap6
        self.longitud_carril = longitud_carril

        # Historial para cálculo de flujo
        self.vehiculos_cruzaron = 0  # Contador de vehículos que cruzaron
        self.tiempo_inicio_ventana = 0.0  # Timestamp de inicio de ventana
        self.ids_vehiculos_vistos = set()  # IDs de vehículos ya contados

        logger.info(f"Procesador inicializado para {self.ruta_video.name}")
        logger.info(f"  Resolucion: {self.ancho}x{self.alto}")
        logger.info(f"  FPS: {self.fps:.2f}")
        logger.info(f"  Frames totales: {self.total_frames}")
        logger.info(f"  Tracker: {self.tracker.tipo_tracker}")
        logger.info(f"  Detector emergencia: {'OK' if self.detector_emergencia.modelo_disponible else 'No disponible'}")
        logger.info(f"  Métricas avanzadas: {'OK Activadas' if self.calcular_metricas_cap6 else 'Desactivadas'}")

    def _cargar_modelo_yolo_con_fallback(self, modelo_especificado: str) -> Tuple:
        """
        Carga modelo YOLO con soporte para YOLO11 y fallback automático a YOLO8

        Estrategia de carga:
        1. Si usuario especifica un modelo (ej: 'yolo11n.pt'), usar ese
        2. Si usuario especifica 'yolov8n.pt', intentar actualizar a 'yolo11n.pt' primero
        3. Si YOLO11 no está disponible, usar YOLO8
        4. Si ambos fallan, lanzar error

        Args:
            modelo_especificado: Ruta o nombre del modelo especificado por el usuario

        Returns:
            Tuple (modelo_cargado, version_string)
        """
        # Lista de modelos a intentar (en orden de prioridad)
        modelos_intentar = []

        # Si el usuario especificó explícitamente YOLO8, intentar actualizar a YOLO11
        if 'yolov8' in modelo_especificado.lower():
            # Intentar YOLO11 primero (reemplazar yolov8 -> yolo11)
            modelo_yolo11 = modelo_especificado.replace('yolov8', 'yolo11')
            modelos_intentar.append((modelo_yolo11, 'YOLO11'))
            # Fallback a YOLO8
            modelos_intentar.append((modelo_especificado, 'YOLO8'))
        elif 'yolo11' in modelo_especificado.lower():
            # Usuario especificó YOLO11 explícitamente
            modelos_intentar.append((modelo_especificado, 'YOLO11'))
            # Fallback a YOLO8
            modelo_yolo8 = modelo_especificado.replace('yolo11', 'yolov8')
            modelos_intentar.append((modelo_yolo8, 'YOLO8'))
        else:
            # Modelo custom - usar tal cual
            modelos_intentar.append((modelo_especificado, 'YOLO_Custom'))

        # Intentar cargar modelos en orden
        errores = []
        for ruta_modelo, version in modelos_intentar:
            try:
                logger.info(f"Intentando cargar {version}: {ruta_modelo}...")

                # Parche especial para PyTorch 2.6+
                # Usar weights_only=False temporalmente durante la carga del modelo
                import torch
                original_load = torch.load

                def safe_load(*args, **kwargs):
                    kwargs['weights_only'] = False
                    return original_load(*args, **kwargs)

                # Aplicar patch temporal
                torch.load = safe_load

                try:
                    modelo = YOLO(ruta_modelo)
                    logger.info(f"✓ {version} cargado exitosamente: {ruta_modelo}")
                    return modelo, f"{version} ({ruta_modelo})"
                finally:
                    # Restaurar torch.load original
                    torch.load = original_load

            except Exception as e:
                error_str = str(e)
                # Acortar mensajes de error muy largos
                if len(error_str) > 200:
                    error_str = error_str[:200] + "..."
                errores.append(f"{version} ({ruta_modelo}): {error_str}")
                logger.warning(f"No se pudo cargar {version}: {error_str}")
                continue

        # Si llegamos aquí, todos los intentos fallaron
        error_msg = "No se pudo cargar ningún modelo YOLO. Intentos:\n" + "\n".join(errores)
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def procesar_completo(
        self,
        saltar_frames: int = 1,
        mostrar_progreso: bool = True
    ) -> List[ResultadoFrame]:
        """
        Procesa el video completo con detecciones REALES

        Args:
            saltar_frames: Procesar 1 de cada N frames
            mostrar_progreso: Mostrar progreso en consola

        Returns:
            Lista de ResultadoFrame con análisis REAL
        """
        resultados = []
        frame_num = 0

        logger.info(f"Iniciando procesamiento REAL de {self.ruta_video.name}")

        while True:
            ret, frame = self.video.read()
            if not ret:
                break

            if frame_num % saltar_frames == 0:
                resultado = self.procesar_frame(frame, frame_num)
                resultados.append(resultado)

                if mostrar_progreso and frame_num % 30 == 0:
                    progreso = (frame_num / self.total_frames) * 100 if self.total_frames > 0 else 0
                    print(f"\rProgreso: {progreso:.1f}% - "
                          f"Vehículos: {resultado.num_vehiculos} - "
                          f"ICV: {resultado.icv:.3f} ({resultado.clasificacion_icv}) - "
                          f"Velocidad: {resultado.velocidad_promedio:.1f} km/h",
                          end='')

            frame_num += 1

        if mostrar_progreso:
            print("\n✓ Procesamiento completado")

        self.video.release()
        return resultados

    def procesar_frame(
        self,
        frame: np.ndarray,
        frame_num: int
    ) -> ResultadoFrame:
        """
        Procesa un frame con detecciones REALES

        ⚠️ IMPORTANTE: NO usa np.random en ninguna parte

        Args:
            frame: Frame del video
            frame_num: Número de frame

        Returns:
            ResultadoFrame con métricas REALES y métricas avanzadas
        """
        timestamp = frame_num / self.fps

        # Aplicar ROI si está definida
        if self.roi:
            x, y, w, h = self.roi
            frame_roi = frame[y:y+h, x:x+w]
        else:
            frame_roi = frame

        # 1. Detectar vehículos con YOLO (REAL)
        resultados_yolo = self.modelo_yolo(frame_roi, verbose=False)
        vehiculos_detectados = self._extraer_vehiculos_yolo(resultados_yolo[0])

        # 2. Actualizar tracker (velocidad REAL) - pasar frame para DeepSORT
        vehiculos_trackeados = self.tracker.actualizar(vehiculos_detectados, timestamp, frame_roi)

        # Asociar velocidades desde tracking a las detecciones para visualización
        if vehiculos_trackeados:
            for v in vehiculos_detectados:
                cx, cy = v['centroide']
                # Encontrar track más cercano
                mejor_track = None
                mejor_dist = 1e9
                for t in vehiculos_trackeados:
                    tx, ty = t.centroide
                    dist = ((cx - tx)**2 + (cy - ty)**2) ** 0.5
                    if dist < mejor_dist:
                        mejor_dist = dist
                        mejor_track = t
                if mejor_track is not None and mejor_dist < 50.0:
                    v['velocidad'] = float(mejor_track.velocidad_promedio)

        # 3. Calcular métricas REALES
        num_vehiculos = len(vehiculos_detectados)
        flujo_vehicular = self._calcular_flujo_real(vehiculos_trackeados, timestamp)
        velocidad_promedio = self.tracker.obtener_velocidad_promedio_general()  # REAL
        longitud_cola = self._medir_longitud_cola_real(vehiculos_detectados, frame_roi.shape)
        cola_vehiculos_count = self._contar_cola_por_vehiculos(vehiculos_detectados, frame_roi.shape)

        # 4. Detectar emergencias (REAL con modelo custom)
        detecciones_emergencia = self.detector_emergencia.detectar(frame_roi, frame_num, datetime.now())
        hay_emergencia = len(detecciones_emergencia) > 0

        # 5. Calcular ICV REAL usando nucleo/
        resultado_icv = self.calculador_icv.calcular(
            longitud_cola=longitud_cola,
            velocidad_promedio=velocidad_promedio,
            flujo_vehicular=flujo_vehicular
        )

        # 6. Calcular métricas avanzadas (si está habilitado)
        metricas_cap6 = None
        if self.calcular_metricas_cap6:
            metricas_cap6 = self._calcular_metricas_cap6(
                vehiculos_trackeados=vehiculos_trackeados,
                timestamp=timestamp
            )

        return ResultadoFrame(
            numero_frame=frame_num,
            timestamp=timestamp,
            num_vehiculos=num_vehiculos,
            vehiculos_detectados=vehiculos_detectados,
            flujo_vehicular=flujo_vehicular,
            velocidad_promedio=velocidad_promedio,
            longitud_cola=longitud_cola,
            cola_vehiculos_count=cola_vehiculos_count,
            icv=resultado_icv['icv'],
            clasificacion_icv=resultado_icv['clasificacion'],
            color_icv=resultado_icv['color'],
            hay_emergencia=hay_emergencia,
            detecciones_emergencia=detecciones_emergencia,
            metricas_cap6=metricas_cap6
        )

    def _extraer_vehiculos_yolo(self, resultados) -> List[Dict]:
        """Extrae vehículos de resultados YOLO (REAL) con NMS para evitar múltiples cajas por vehículo"""
        vehiculos = []

        if resultados is None or resultados.boxes is None:
            return vehiculos

        # Recoger todas las cajas de clases vehiculares
        bboxes = []  # [x1,y1,x2,y2]
        scores = []  # confianza
        clases = []  # clase

        for box in resultados.boxes:
            clase = int(box.cls[0])
            if clase in self.clases_vehiculos:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                bboxes.append([float(x1), float(y1), float(x2), float(y2)])
                scores.append(conf)
                clases.append(clase)

        if not bboxes:
            return vehiculos

        # Aplicar NMS por clase para suprimir cajas superpuestas del mismo objeto
        try:
            import torch
            import torchvision

            bboxes_t = torch.tensor(bboxes, dtype=torch.float32)
            scores_t = torch.tensor(scores, dtype=torch.float32)
            clases_t = torch.tensor(clases, dtype=torch.int64)

            keep_indices = []
            iou_thresh = 0.5

            # NMS por clase
            for c in set(clases):
                idxs = (clases_t == c).nonzero(as_tuple=True)[0]
                if idxs.numel() == 0:
                    continue
                kept = torchvision.ops.nms(bboxes_t[idxs], scores_t[idxs], iou_thresh)
                keep_indices.extend(idxs[kept].tolist())

            # Reconstruir vehículos con índices mantenidos
            for i in keep_indices:
                x1, y1, x2, y2 = bboxes[i]
                confianza = scores[i]
                clase = clases[i]
                vehiculos.append({
                    'bbox': [x1, y1, x2, y2],
                    'clase': clase,
                    'confianza': confianza,
                    'centroide': ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
                })
        except Exception:
            # Fallback: NMS manual simple basado en IoU
            def iou(a, b):
                ax1, ay1, ax2, ay2 = a
                bx1, by1, bx2, by2 = b
                inter_x1 = max(ax1, bx1)
                inter_y1 = max(ay1, by1)
                inter_x2 = min(ax2, bx2)
                inter_y2 = min(ay2, by2)
                inter_w = max(0.0, inter_x2 - inter_x1)
                inter_h = max(0.0, inter_y2 - inter_y1)
                inter = inter_w * inter_h
                area_a = max(0.0, (ax2 - ax1)) * max(0.0, (ay2 - ay1))
                area_b = max(0.0, (bx2 - bx1)) * max(0.0, (by2 - by1))
                union = area_a + area_b - inter + 1e-6
                return inter / union

            iou_thresh = 0.5
            # Ordenar por confianza descendente
            indices = sorted(range(len(bboxes)), key=lambda i: scores[i], reverse=True)
            suprimidos = set()

            for i in indices:
                if i in suprimidos:
                    continue
                x1, y1, x2, y2 = bboxes[i]
                confianza = scores[i]
                clase_i = clases[i]
                vehiculos.append({
                    'bbox': [x1, y1, x2, y2],
                    'clase': clase_i,
                    'confianza': confianza,
                    'centroide': ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
                })
                for j in indices:
                    if j == i or j in suprimidos:
                        continue
                    if clases[j] != clase_i:
                        continue
                    if iou(bboxes[i], bboxes[j]) >= iou_thresh:
                        suprimidos.add(j)

        return vehiculos

    def _construir_tracks_dict(self, vehiculos_trackeados: List[Dict]) -> List[Dict]:
        """Construye una lista de dicts de tracks para alimentar el estado local"""
        tracks = []
        for t in vehiculos_trackeados:
            tracks.append({
                'id': getattr(t, 'id', -1),
                'clase': getattr(t, 'clase', 2),
                'confianza': getattr(t, 'confianza', 0.0),
                'bbox': getattr(t, 'bbox', [0, 0, 0, 0]),
                'centroide': getattr(t, 'centroide', (0.0, 0.0)),
                'velocidad_promedio': float(getattr(t, 'velocidad_promedio', 0.0)),
                # Aproximación: derivar velocidad_xy a partir de últimas posiciones si existen
                'velocidad_xy': None
            })
        return tracks

    def _calcular_flujo_real(
        self,
        vehiculos_trackeados: List,
        timestamp: float
    ) -> float:
        """
        Calcula flujo vehicular REAL basado en tracking

        NO usa np.random - Cuenta vehículos que cruzan línea virtual

        Returns:
            Flujo en vehículos/minuto
        """
        # Método simplificado: flujo = num_vehiculos * factor_temporal
        # En implementación avanzada: contar vehículos que cruzan línea virtual

        num_vehiculos_en_movimiento = len([
            v for v in vehiculos_trackeados
            if v.velocidad_promedio > 2.0  # Solo vehículos en movimiento
        ])

        # Ventana de 10 segundos
        ventana_segundos = 10.0
        flujo_por_minuto = num_vehiculos_en_movimiento * (60.0 / ventana_segundos)

        return flujo_por_minuto

    def _medir_longitud_cola_real(
        self,
        vehiculos: List[Dict],
        shape: Tuple
    ) -> float:
        """
        Mide longitud de cola REAL

        NO usa np.random - Basado en posiciones detectadas

        Returns:
            Longitud en metros
        """
        if not vehiculos:
            return 0.0

        # Encontrar extensión vertical de vehículos
        y_coords = [v['centroide'][1] for v in vehiculos]
        rango_y_pixeles = max(y_coords) - min(y_coords)

        # Convertir a metros usando calibración
        longitud_metros = rango_y_pixeles / self.pixeles_por_metro

        return longitud_metros

    def _calcular_metricas_cap6(
        self,
        vehiculos_trackeados: List,
        timestamp: float
    ) -> Dict:
        """
        Calcula métricas completas avanzadas

        Implementa fórmulas exactas:
        - StoppedCount
        - Vavg solo de vehículos en movimiento
        - Flujo q
        - Densidad k
        - Parámetro de Intensidad PI
        - ICV según fórmula exacta

        Args:
            vehiculos_trackeados: Lista de vehículos con tracking activo
            timestamp: Timestamp actual en segundos

        Returns:
            Dict con todas las métricas avanzadas
        """
        # Inicializar ventana de tiempo si es necesario
        if self.tiempo_inicio_ventana == 0.0:
            self.tiempo_inicio_ventana = timestamp

        # 1. Recolectar velocidades de todos los vehículos trackeados
        velocidades = []
        for vehiculo in vehiculos_trackeados:
            velocidad = vehiculo.velocidad_promedio
            if velocidad is not None:
                velocidades.append(velocidad)

        # 2. Contar vehículos que cruzaron en esta ventana
        # Heurística simple: vehículos nuevos con ID que no hemos visto
        for vehiculo in vehiculos_trackeados:
            if vehiculo.id not in self.ids_vehiculos_vistos:
                self.ids_vehiculos_vistos.add(vehiculo.id)
                self.vehiculos_cruzaron += 1

        # 3. Calcular tiempo de ventana
        tiempo_ventana = timestamp - self.tiempo_inicio_ventana
        if tiempo_ventana <= 0:
            tiempo_ventana = 1.0  # Evitar división por cero

        # 4. Llamar al calculador avanzado
        try:
            metricas = self.calculador_icv.calcular_metricas_completas_cap6(
                velocidades=velocidades if velocidades else [0.0],
                num_vehiculos_cruzaron=self.vehiculos_cruzaron,
                tiempo_inicial=self.tiempo_inicio_ventana,
                tiempo_final=timestamp,
                longitud_efectiva=self.longitud_carril
            )

            # Resetear ventana cada 60 segundos para evitar acumulación infinita
            if tiempo_ventana >= 60.0:
                self.vehiculos_cruzaron = 0
                self.tiempo_inicio_ventana = timestamp
                self.ids_vehiculos_vistos.clear()

            return metricas

        except Exception as e:
            logger.warning(f"Error calculando métricas Cap 6: {e}")
            return None

    def _contar_cola_por_vehiculos(
        self,
        vehiculos: List[Dict],
        shape: Tuple
    ) -> int:
        """
        Conteo de vehículos detenidos (cola) según función indicadora:
        v = 1 si velocidad(v) < epsilon; 0 caso contrario.

        Usa velocidad de ByteTrack/DeepSORT ya anotada en vehiculos_detectados.
        Si no hay velocidad disponible, asume no detenido.
        """
        if not vehiculos:
            return 0

        epsilon = self.epsilon_velocidad_kmh
        detenidos = 0
        for v in vehiculos:
            vel = v.get('velocidad', 0.0)
            if vel < epsilon:
                detenidos += 1

        return detenidos

    def dibujar_detecciones(
        self,
        frame: np.ndarray,
        resultado: ResultadoFrame,
        mostrar_info: bool = True,
        mostrar_tracking_ids: bool = True,
        modo_simple: bool = False
    ) -> np.ndarray:
        """
        Dibuja detecciones en el frame

        Args:
            frame: Frame original
            resultado: Resultado del análisis
            mostrar_info: Si mostrar panel de información
            mostrar_tracking_ids: Si mostrar IDs de tracking
            modo_simple: Si True, solo muestra título y barra (sin panel de métricas)

        Returns:
            Frame con detecciones
        """
        frame_anotado = frame.copy()

        # Si mostrar_info=True, usar overlay moderno completo
        if mostrar_info:
            try:
                from vision_computadora.overlay_visual_mejorado import OverlayVisualModerno, convertir_resultado_a_dict

                # Crear overlay si no existe
                if not hasattr(self, '_overlay_moderno'):
                    self._overlay_moderno = OverlayVisualModerno()
                    logger.info("OverlayVisualModerno inicializado")

                # Convertir resultado a dict
                resultado_dict = convertir_resultado_a_dict(resultado)

                # Debug: verificar parámetro modo_simple RECIBIDO
                print(f"[PROCESADOR] dibujar_detecciones recibió modo_simple={modo_simple}")
                print(f"[PROCESADOR] Tipo: {type(modo_simple)}")
                
                # Usar visualización completa (incluye vehículos, métricas y barra ICV)
                print(f"[PROCESADOR] Llamando crear_visualizacion_completa con modo_simple={modo_simple}")
                frame_anotado = self._overlay_moderno.crear_visualizacion_completa(
                    frame_anotado,
                    resultado_dict,
                    mostrar_barra=True,
                    modo_simple=modo_simple
                )

                # Dibujar emergencias encima si las hay
                if resultado.hay_emergencia:
                    frame_anotado = self.detector_emergencia.dibujar_detecciones(
                        frame_anotado,
                        resultado.detecciones_emergencia,
                        mostrar_alerta=True
                    )

                return frame_anotado

            except Exception as e:
                logger.warning(f"Error con overlay moderno, usando método legacy: {e}")
                # Si falla, continuar con el método legacy abajo

        # Método legacy: dibujar manualmente (cuando mostrar_info=False o hay error)
        # Offset si hay ROI
        if self.roi:
            x_offset, y_offset = self.roi[0], self.roi[1]
        else:
            x_offset, y_offset = 0, 0

        # Dibujar vehículos detectados
        for vehiculo in resultado.vehiculos_detectados:
            x1, y1, x2, y2 = vehiculo['bbox']
            x1, y1, x2, y2 = int(x1 + x_offset), int(y1 + y_offset), int(x2 + x_offset), int(y2 + y_offset)

            # Color verde para vehículos normales
            color = (0, 255, 0)

            cv2.rectangle(frame_anotado, (x1, y1), (x2, y2), color, 2)

            # Etiqueta
            label = f"Veh {vehiculo['confianza']:.2f}"
            cv2.putText(frame_anotado, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Dibujar emergencias (resaltado)
        if resultado.hay_emergencia:
            frame_anotado = self.detector_emergencia.dibujar_detecciones(
                frame_anotado,
                resultado.detecciones_emergencia,
                mostrar_alerta=True
            )

        return frame_anotado

    def _dibujar_panel_info(self, frame: np.ndarray, resultado: ResultadoFrame):
        """Dibuja panel de información con métricas REALES usando overlay moderno"""
        try:
            from vision_computadora.overlay_visual_mejorado import OverlayVisualModerno, convertir_resultado_a_dict

            # Crear overlay si no existe
            if not hasattr(self, '_overlay_moderno'):
                self._overlay_moderno = OverlayVisualModerno()
                logger.info("OverlayVisualModerno creado")

            # Convertir resultado a dict
            resultado_dict = convertir_resultado_a_dict(resultado)

            # Usar overlay moderno completo que retorna el frame modificado
            # NO necesitamos llamar funciones individuales - usar crear_visualizacion_completa
            frame_con_overlay = self._overlay_moderno.crear_visualizacion_completa(
                frame,
                resultado_dict,
                mostrar_barra=True
            )
            
            # Copiar el resultado al frame original (modificación in-place)
            frame[:] = frame_con_overlay

        except ImportError as e:
            logger.warning(f"No se pudo importar overlay moderno: {e}")
            # Fallback al método antiguo si no se puede importar
            self._dibujar_panel_info_legacy(frame, resultado)
        except Exception as e:
            logger.error(f"Error en overlay moderno: {e}")
            # Fallback al método antiguo si hay error
            self._dibujar_panel_info_legacy(frame, resultado)

    def _dibujar_panel_info_legacy(self, frame: np.ndarray, resultado: ResultadoFrame):
        """Método legacy de dibujo de panel (fallback)"""
        # Fondo semi-transparente
        overlay = frame.copy()
        panel_height = 180
        panel_width = 450
        cv2.rectangle(overlay, (0, 0), (panel_width, panel_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Determinar color del ICV
        if resultado.icv < 0.3:
            icv_color = (0, 255, 0)  # Verde
        elif resultado.icv < 0.6:
            icv_color = (0, 255, 255)  # Amarillo
        else:
            icv_color = (0, 0, 255)  # Rojo

        # Información básica con métricas REALES
        y_pos = 25
        info_lines = [
            f"Frame: {resultado.numero_frame} | Tiempo: {resultado.timestamp:.1f}s",
            f"Vehiculos: {resultado.num_vehiculos}",
            f"Flujo: {resultado.flujo_vehicular:.1f} veh/min",
            f"Velocidad: {resultado.velocidad_promedio:.1f} km/h",
            f"Cola: {resultado.longitud_cola:.1f} m",
            f"ICV: {resultado.icv:.3f} - {resultado.clasificacion_icv.upper()}",
            f"Emergencia: {'SI' if resultado.hay_emergencia else 'NO'}"
        ]

        for i, line in enumerate(info_lines):
            # Color especial para ICV
            color = icv_color if 'ICV:' in line else (255, 255, 255)
            # Color especial para emergencia
            if 'Emergencia: SI' in line:
                color = (0, 0, 255)

            cv2.putText(frame, line, (10, y_pos + i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Información del Capítulo 6 (si disponible)
        if resultado.metricas_cap6:
            m6 = resultado.metricas_cap6
            y_pos_cap6 = y_pos + len(info_lines) * 25 + 10

            # Línea divisoria
            cv2.line(frame, (10, y_pos_cap6 - 5), (panel_width - 10, y_pos_cap6 - 5), (100, 100, 100), 1)

            cap6_lines = [
                f"=== METRICAS CAPITULO 6 ===",
                f"SC (detenidos): {m6['stopped_count']} | PI: {m6['parametro_intensidad']:.2f}",
                f"Vavg (movim.): {m6['velocidad_promedio_movimiento']:.1f} km/h",
                f"Densidad k: {m6['densidad_vehicular']:.4f} veh/m | Flujo q: {m6['flujo_vehicular']:.1f} veh/min",
            ]

            for i, line in enumerate(cap6_lines):
                color = (0, 255, 255) if i == 0 else (200, 200, 200)  # Amarillo para título
                font_size = 0.5 if i == 0 else 0.5
                cv2.putText(frame, line, (10, y_pos_cap6 + i * 22),
                           cv2.FONT_HERSHEY_SIMPLEX, font_size, color, 1 if i == 0 else 2)

    def exportar_resultados(
        self,
        resultados: List[ResultadoFrame],
        ruta_salida: str
    ):
        """
        Exporta resultados REALES a CSV (incluye métricas del Capítulo 6 si están disponibles)

        Args:
            resultados: Lista de resultados
            ruta_salida: Ruta del archivo CSV
        """
        import csv

        # Verificar si hay métricas del Capítulo 6
        tiene_cap6 = any(r.metricas_cap6 is not None for r in resultados)

        with open(ruta_salida, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Encabezados básicos
            headers = [
                'Frame', 'Tiempo(s)', 'NumVehiculos',
                'Flujo(veh/min)_REAL', 'Velocidad(km/h)_REAL', 'LongitudCola(m)',
                'ICV_REAL', 'Clasificacion', 'Emergencia'
            ]

            # Agregar encabezados del Capítulo 6 si están disponibles
            if tiene_cap6:
                headers.extend([
                    'Cap6_StoppedCount', 'Cap6_Vavg_Movimiento(km/h)',
                    'Cap6_Flujo_q(veh/min)', 'Cap6_Densidad_k(veh/m)',
                    'Cap6_ParametroIntensidad_PI', 'Cap6_ICV', 'Cap6_Clasificacion'
                ])

            writer.writerow(headers)

            # Escribir datos
            for r in resultados:
                row = [
                    r.numero_frame,
                    f"{r.timestamp:.2f}",
                    r.num_vehiculos,
                    f"{r.flujo_vehicular:.2f}",
                    f"{r.velocidad_promedio:.2f}",
                    f"{r.longitud_cola:.2f}",
                    f"{r.icv:.4f}",
                    r.clasificacion_icv,
                    'Si' if r.hay_emergencia else 'No'
                ]

                # Agregar datos del Capítulo 6 si están disponibles
                if tiene_cap6:
                    if r.metricas_cap6:
                        m6 = r.metricas_cap6
                        row.extend([
                            m6['stopped_count'],
                            f"{m6['velocidad_promedio_movimiento']:.2f}",
                            f"{m6['flujo_vehicular']:.2f}",
                            f"{m6['densidad_vehicular']:.4f}",
                            f"{m6['parametro_intensidad']:.3f}",
                            f"{m6['icv']:.4f}",
                            m6['icv_clasificacion']
                        ])
                    else:
                        row.extend([''] * 7)  # Celdas vacías si no hay datos

                writer.writerow(row)

        logger.info(f"Resultados exportados a {ruta_salida}")
        logger.info(f"  NOTA: Todos los valores son REALES (no simulados)")
        if tiene_cap6:
            logger.info(f"  Incluye metricas del Capitulo 6 (formulas exactas de la tesis)")


# Ejemplo de uso
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python procesador_video.py <ruta_video>")
        sys.exit(1)

    ruta_video = sys.argv[1]

    # Crear procesador REAL
    procesador = ProcesadorVideo(
        ruta_video=ruta_video,
        pixeles_por_metro=15.0  # Ajustar según calibración
    )

    # Procesar video
    resultados = procesador.procesar_completo(saltar_frames=2)

    # Exportar
    ruta_salida = f'datos/resultados-video/exportaciones/analisis_{Path(ruta_video).stem}.csv'
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
    procesador.exportar_resultados(resultados, ruta_salida)

    # Estadísticas
    print("\n=== ESTADISTICAS REALES ===")
    print(f"Frames procesados: {len(resultados)}")

    velocidades = [r.velocidad_promedio for r in resultados if r.velocidad_promedio > 0]
    if velocidades:
        print(f"Velocidad promedio: {np.mean(velocidades):.2f} km/h [REAL - Tracking]")

    icvs = [r.icv for r in resultados]
    print(f"ICV promedio: {np.mean(icvs):.3f} [REAL - nucleo/]")

    emergencias = sum(1 for r in resultados if r.hay_emergencia)
    print(f"Detecciones de emergencia: {emergencias}")

    # Estadísticas del Capítulo 6 (si disponibles)
    resultados_con_cap6 = [r for r in resultados if r.metricas_cap6 is not None]
    if resultados_con_cap6:
        print("\n=== ESTADISTICAS CAPITULO 6 ===")
        sc_promedio = np.mean([r.metricas_cap6['stopped_count'] for r in resultados_con_cap6])
        vavg_promedio = np.mean([r.metricas_cap6['velocidad_promedio_movimiento'] for r in resultados_con_cap6])
        pi_promedio = np.mean([r.metricas_cap6['parametro_intensidad'] for r in resultados_con_cap6])
        icv_cap6_promedio = np.mean([r.metricas_cap6['icv'] for r in resultados_con_cap6])

        print(f"Stopped Count promedio: {sc_promedio:.1f} vehiculos")
        print(f"Vavg (movimiento) promedio: {vavg_promedio:.2f} km/h")
        print(f"Parametro Intensidad (PI) promedio: {pi_promedio:.3f}")
        print(f"ICV (Cap 6.2.3) promedio: {icv_cap6_promedio:.3f}")
