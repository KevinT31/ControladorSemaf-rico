"""
Tracking Vehicular REAL - Sin np.random

Este módulo implementa tracking de vehículos entre frames para calcular
velocidad REAL basada en movimiento observado, no simulaciones.

Utiliza (en orden de prioridad):
1. ByteTrack (PREFERIDO - más robusto y rápido)
2. DeepSORT (alternativa robusta)
3. Centroid tracking (fallback simple)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)

# Intentar importar ByteTrack (PREFERIDO - documentación del sistema)
try:
    from boxmot import ByteTrack as BoxMotByteTrack
    BYTETRACK_AVAILABLE = True
    logger.info("ByteTrack disponible (boxmot)")
except ImportError:
    BYTETRACK_AVAILABLE = False
    logger.debug("ByteTrack (boxmot) no disponible. Instalar con: pip install boxmot")

# Intentar importar DeepSORT (alternativa)
try:
    from deep_sort_realtime.deepsort_tracker import DeepSort
    DEEPSORT_AVAILABLE = True
    logger.debug("DeepSORT disponible")
except ImportError:
    DEEPSORT_AVAILABLE = False
    logger.debug("DeepSORT no disponible. Instalar con: pip install deep-sort-realtime")

# Determinar tracker a usar
if not BYTETRACK_AVAILABLE and not DEEPSORT_AVAILABLE:
    logger.warning("Ni ByteTrack ni DeepSORT disponibles. Usando tracking simplificado (menos preciso)")
    logger.warning("Instalar ByteTrack con: pip install boxmot")


@dataclass
class VehiculoTrackeado:
    """Información de un vehículo siendo trackeado"""
    id: int
    clase: int
    bbox: List[float]  # [x1, y1, x2, y2]
    centroide: Tuple[float, float]
    confianza: float

    # Historial de posiciones
    posiciones: deque = field(default_factory=lambda: deque(maxlen=30))  # Últimos 30 frames
    timestamps: deque = field(default_factory=lambda: deque(maxlen=30))

    # Velocidad estimada
    velocidad_instantanea: float = 0.0  # km/h
    velocidad_promedio: float = 0.0  # km/h

    # Frames desde última actualización
    frames_sin_actualizacion: int = 0
    activo: bool = True


class TrackerVehicular:
    """
    Tracker de vehículos con cálculo de velocidad REAL

    NO USA np.random - Todo basado en observaciones reales
    """

    def __init__(
        self,
        max_distance_centroid: float = 50.0,  # Máxima distancia para asociar (píxeles)
        max_frames_perdido: int = 15,  # Frames antes de marcar como perdido
        fps: float = 30.0,  # FPS del video
        pixeles_por_metro: float = 10.0,  # Calibración: píxeles por metro (ajustar)
        usar_deepsort: bool = True,  # Mantener para retrocompatibilidad
        preferir_bytetrack: bool = True  # Preferir ByteTrack sobre DeepSORT (según documentación)
    ):
        """
        Args:
            max_distance_centroid: Distancia máxima para asociar detección con track existente
            max_frames_perdido: Máximo de frames sin actualización antes de eliminar track
            fps: Frames por segundo del video
            pixeles_por_metro: Calibración espacial (depende del ángulo de cámara)
            usar_deepsort: Si usar DeepSORT (mantener para retrocompatibilidad)
            preferir_bytetrack: Si preferir ByteTrack sobre DeepSORT (recomendado en documentación)
        """
        self.max_distance_centroid = max_distance_centroid
        self.max_frames_perdido = max_frames_perdido
        self.fps = fps
        self.pixeles_por_metro = pixeles_por_metro

        # Diccionario de vehículos trackeados
        self.vehiculos: Dict[int, VehiculoTrackeado] = {}
        self.siguiente_id = 0

        # Determinar qué tracker usar (prioridad: ByteTrack > DeepSORT > Centroid)
        self.bytetrack = None
        self.deepsort = None
        self.usar_bytetrack = False
        self.usar_deepsort = False
        self.tipo_tracker = "centroid"

        # Intentar inicializar ByteTrack (PREFERIDO según documentación)
        if preferir_bytetrack and BYTETRACK_AVAILABLE:
            try:
                # ByteTrack de boxmot
                self.bytetrack = BoxMotByteTrack(
                    track_thresh=0.5,
                    track_buffer=max_frames_perdido,
                    match_thresh=0.8,
                    frame_rate=fps
                )
                self.usar_bytetrack = True
                self.tipo_tracker = "ByteTrack"
                logger.info("Usando ByteTrack para tracking (RECOMENDADO - documentacion del sistema)")
            except Exception as e:
                logger.warning(f"Error inicializando ByteTrack: {e}. Fallback a DeepSORT")
                self.bytetrack = None

        # Fallback a DeepSORT si ByteTrack no está disponible
        if not self.usar_bytetrack and usar_deepsort and DEEPSORT_AVAILABLE:
            try:
                self.deepsort = DeepSort(
                    max_age=max_frames_perdido,
                    n_init=3,
                    max_iou_distance=0.7,
                    embedder="mobilenet",
                    half=True
                )
                self.usar_deepsort = True
                self.tipo_tracker = "DeepSORT"
                logger.info("Usando DeepSORT para tracking (fallback)")
            except Exception as e:
                logger.warning(f"Error inicializando DeepSORT: {e}. Usando centroid tracking")
                self.deepsort = None

        # Fallback final: Centroid tracking
        if not self.usar_bytetrack and not self.usar_deepsort:
            self.tipo_tracker = "Centroid"
            logger.info("Usando centroid tracking (simple)")

    def actualizar(
        self,
        detecciones: List[Dict],
        timestamp: float,
        frame: Optional[np.ndarray] = None
    ) -> List[VehiculoTrackeado]:
        """
        Actualiza tracker con nuevas detecciones

        Prioridad: ByteTrack > DeepSORT > Centroid

        Args:
            detecciones: Lista de detecciones YOLO
                Formato: [{'bbox': [x1,y1,x2,y2], 'clase': int, 'confianza': float}, ...]
            timestamp: Timestamp del frame (segundos)
            frame: Frame del video (necesario para ByteTrack/DeepSORT, opcional para Centroid)

        Returns:
            Lista de vehículos trackeados activos con velocidad REAL
        """
        # Prioridad 1: ByteTrack (PREFERIDO según documentación)
        if self.usar_bytetrack and self.bytetrack is not None:
            return self._actualizar_bytetrack(detecciones, timestamp)

        # Prioridad 2: DeepSORT (fallback)
        elif self.usar_deepsort and self.deepsort is not None and frame is not None:
            return self._actualizar_deepsort(detecciones, timestamp, frame)

        # Prioridad 3: Centroid (fallback simple)
        else:
            return self._actualizar_centroid(detecciones, timestamp)

    def _actualizar_bytetrack(
        self,
        detecciones: List[Dict],
        timestamp: float
    ) -> List[VehiculoTrackeado]:
        """
        Actualizar usando ByteTrack (PREFERIDO - más robusto y rápido)

        ByteTrack es el tracker recomendado en la documentación del sistema
        """
        if not detecciones:
            # Sin detecciones, incrementar frames sin actualización
            for vehiculo in self.vehiculos.values():
                vehiculo.frames_sin_actualizacion += 1
            self._limpiar_vehiculos_perdidos()
            return [v for v in self.vehiculos.values() if v.activo]

        # Convertir detecciones a formato ByteTrack
        # ByteTrack espera: numpy array de shape (N, 6) con [x1, y1, x2, y2, confidence, class]
        detecciones_array = []
        for det in detecciones:
            x1, y1, x2, y2 = det['bbox']
            detecciones_array.append([
                x1, y1, x2, y2,
                det['confianza'],
                det['clase']
            ])

        detecciones_np = np.array(detecciones_array, dtype=np.float32)

        # Actualizar ByteTrack
        try:
            tracks = self.bytetrack.update(detecciones_np, None)  # None para frame (no es requerido por ByteTrack)
        except Exception as e:
            logger.error(f"Error en ByteTrack update: {e}. Usando fallback centroid")
            return self._actualizar_centroid(detecciones, timestamp)

        # Marcar todos como no actualizados
        for vehiculo in self.vehiculos.values():
            vehiculo.frames_sin_actualizacion += 1

        # Procesar tracks de ByteTrack
        if tracks is not None and len(tracks) > 0:
            for track in tracks:
                # ByteTrack returns: [x1, y1, x2, y2, track_id, score, class_id, ...]
                if len(track) < 5:
                    continue

                x1, y1, x2, y2 = track[0], track[1], track[2], track[3]
                track_id = int(track[4])
                confianza = track[5] if len(track) > 5 else 0.8
                clase = int(track[6]) if len(track) > 6 else 2

                bbox = [x1, y1, x2, y2]
                centroide = ((x1 + x2) / 2, (y1 + y2) / 2)

                # Actualizar o crear vehículo
                if track_id not in self.vehiculos:
                    # Nuevo vehículo
                    self.vehiculos[track_id] = VehiculoTrackeado(
                        id=track_id,
                        clase=clase,
                        bbox=bbox,
                        centroide=centroide,
                        confianza=confianza
                    )

                vehiculo = self.vehiculos[track_id]

                # Actualizar posición
                vehiculo.bbox = bbox
                vehiculo.centroide = centroide
                vehiculo.confianza = confianza
                vehiculo.posiciones.append(centroide)
                vehiculo.timestamps.append(timestamp)
                vehiculo.frames_sin_actualizacion = 0
                vehiculo.activo = True

                # Calcular velocidad REAL
                velocidad = self._calcular_velocidad_real(vehiculo)
                vehiculo.velocidad_instantanea = velocidad
                vehiculo.velocidad_promedio = self._calcular_velocidad_promedio(vehiculo)

        # Eliminar vehículos perdidos
        self._limpiar_vehiculos_perdidos()

        return [v for v in self.vehiculos.values() if v.activo]

    def _actualizar_deepsort(
        self,
        detecciones: List[Dict],
        timestamp: float,
        frame: np.ndarray
    ) -> List[VehiculoTrackeado]:
        """Actualizar usando DeepSORT (más robusto)"""
        # Convertir detecciones a formato DeepSORT
        detecciones_deepsort = []
        for det in detecciones:
            x1, y1, x2, y2 = det['bbox']
            # DeepSORT espera: ([left, top, width, height], confidence, class)
            detecciones_deepsort.append((
                [x1, y1, x2-x1, y2-y1],
                det['confianza'],
                det['clase']
            ))

        # Actualizar DeepSORT (ahora con frame)
        tracks = self.deepsort.update_tracks(detecciones_deepsort, frame=frame)

        # Marcar todos como no actualizados
        for vehiculo in self.vehiculos.values():
            vehiculo.frames_sin_actualizacion += 1

        # Procesar tracks
        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            bbox = track.to_ltrb()  # [left, top, right, bottom]
            centroide = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

            # Actualizar o crear vehículo
            if track_id not in self.vehiculos:
                # Nuevo vehículo
                self.vehiculos[track_id] = VehiculoTrackeado(
                    id=track_id,
                    clase=int(track.get_det_class()) if hasattr(track, 'get_det_class') else 2,
                    bbox=bbox.tolist(),
                    centroide=centroide,
                    confianza=track.get_det_conf() if hasattr(track, 'get_det_conf') else 0.8
                )

            vehiculo = self.vehiculos[track_id]

            # Actualizar posición
            vehiculo.bbox = bbox.tolist()
            vehiculo.centroide = centroide
            vehiculo.posiciones.append(centroide)
            vehiculo.timestamps.append(timestamp)
            vehiculo.frames_sin_actualizacion = 0
            vehiculo.activo = True

            # Calcular velocidad REAL
            velocidad = self._calcular_velocidad_real(vehiculo)
            vehiculo.velocidad_instantanea = velocidad
            vehiculo.velocidad_promedio = self._calcular_velocidad_promedio(vehiculo)

        # Eliminar vehículos perdidos
        self._limpiar_vehiculos_perdidos()

        return [v for v in self.vehiculos.values() if v.activo]

    def _actualizar_centroid(
        self,
        detecciones: List[Dict],
        timestamp: float
    ) -> List[VehiculoTrackeado]:
        """
        Actualizar usando centroid tracking (simple pero funcional)

        Asocia detecciones con tracks existentes basándose en distancia entre centroides
        """
        # Si no hay detecciones, incrementar frames sin actualización
        if not detecciones:
            for vehiculo in self.vehiculos.values():
                vehiculo.frames_sin_actualizacion += 1
            self._limpiar_vehiculos_perdidos()
            return [v for v in self.vehiculos.values() if v.activo]

        # Calcular centroides de detecciones
        detecciones_con_centroide = []
        for det in detecciones:
            x1, y1, x2, y2 = det['bbox']
            centroide = ((x1 + x2) / 2, (y1 + y2) / 2)
            detecciones_con_centroide.append({
                **det,
                'centroide': centroide
            })

        # Si no hay vehículos trackeados, crear nuevos
        if not self.vehiculos:
            for det in detecciones_con_centroide:
                self._crear_nuevo_vehiculo(det, timestamp)
            return list(self.vehiculos.values())

        # Asociar detecciones con vehículos existentes
        vehiculos_ids = list(self.vehiculos.keys())
        detecciones_asignadas = set()

        for vehiculo_id in vehiculos_ids:
            vehiculo = self.vehiculos[vehiculo_id]

            # Encontrar detección más cercana
            mejor_match = None
            mejor_distancia = self.max_distance_centroid

            for idx, det in enumerate(detecciones_con_centroide):
                if idx in detecciones_asignadas:
                    continue

                distancia = self._distancia_euclidiana(
                    vehiculo.centroide,
                    det['centroide']
                )

                if distancia < mejor_distancia:
                    mejor_distancia = distancia
                    mejor_match = idx

            # Actualizar vehículo si hay match
            if mejor_match is not None:
                det = detecciones_con_centroide[mejor_match]
                detecciones_asignadas.add(mejor_match)

                vehiculo.bbox = det['bbox']
                vehiculo.centroide = det['centroide']
                vehiculo.confianza = det['confianza']
                vehiculo.posiciones.append(det['centroide'])
                vehiculo.timestamps.append(timestamp)
                vehiculo.frames_sin_actualizacion = 0
                vehiculo.activo = True

                # Calcular velocidad REAL
                velocidad = self._calcular_velocidad_real(vehiculo)
                vehiculo.velocidad_instantanea = velocidad
                vehiculo.velocidad_promedio = self._calcular_velocidad_promedio(vehiculo)
            else:
                # No hay match, incrementar frames sin actualización
                vehiculo.frames_sin_actualizacion += 1

        # Crear nuevos vehículos para detecciones no asignadas
        for idx, det in enumerate(detecciones_con_centroide):
            if idx not in detecciones_asignadas:
                self._crear_nuevo_vehiculo(det, timestamp)

        # Limpiar vehículos perdidos
        self._limpiar_vehiculos_perdidos()

        return [v for v in self.vehiculos.values() if v.activo]

    def _crear_nuevo_vehiculo(self, deteccion: Dict, timestamp: float) -> VehiculoTrackeado:
        """Crea un nuevo vehículo trackeado"""
        vehiculo = VehiculoTrackeado(
            id=self.siguiente_id,
            clase=deteccion['clase'],
            bbox=deteccion['bbox'],
            centroide=deteccion['centroide'],
            confianza=deteccion['confianza']
        )
        vehiculo.posiciones.append(deteccion['centroide'])
        vehiculo.timestamps.append(timestamp)

        self.vehiculos[self.siguiente_id] = vehiculo
        self.siguiente_id += 1

        return vehiculo

    def _calcular_velocidad_real(self, vehiculo: VehiculoTrackeado) -> float:
        """
        Calcula velocidad REAL basada en movimiento observado

        NO USA np.random - Solo cálculo basado en tracking

        Returns:
            Velocidad en km/h
        """
        if len(vehiculo.posiciones) < 2:
            return 0.0

        # Usar últimas 2 posiciones para velocidad instantánea
        pos_actual = vehiculo.posiciones[-1]
        pos_anterior = vehiculo.posiciones[-2]

        time_actual = vehiculo.timestamps[-1]
        time_anterior = vehiculo.timestamps[-2]

        # Calcular desplazamiento en píxeles
        dx = pos_actual[0] - pos_anterior[0]
        dy = pos_actual[1] - pos_anterior[1]
        desplazamiento_pixeles = np.sqrt(dx**2 + dy**2)

        # Convertir a metros
        desplazamiento_metros = desplazamiento_pixeles / self.pixeles_por_metro

        # Calcular tiempo transcurrido
        delta_tiempo_segundos = time_actual - time_anterior

        if delta_tiempo_segundos <= 0:
            return 0.0

        # Velocidad en m/s
        velocidad_ms = desplazamiento_metros / delta_tiempo_segundos

        # Convertir a km/h
        velocidad_kmh = velocidad_ms * 3.6

        # Limitar valores absurdos (0-150 km/h es rango razonable en ciudad)
        velocidad_kmh = np.clip(velocidad_kmh, 0, 150)

        return velocidad_kmh

    def _calcular_velocidad_promedio(self, vehiculo: VehiculoTrackeado) -> float:
        """
        Calcula velocidad promedio usando todas las posiciones disponibles

        Returns:
            Velocidad promedio en km/h
        """
        if len(vehiculo.posiciones) < 3:
            return vehiculo.velocidad_instantanea

        # Usar últimos N frames para suavizar
        n_frames = min(10, len(vehiculo.posiciones))

        pos_inicio = vehiculo.posiciones[-n_frames]
        pos_fin = vehiculo.posiciones[-1]

        time_inicio = vehiculo.timestamps[-n_frames]
        time_fin = vehiculo.timestamps[-1]

        # Desplazamiento total
        dx = pos_fin[0] - pos_inicio[0]
        dy = pos_fin[1] - pos_inicio[1]
        desplazamiento_pixeles = np.sqrt(dx**2 + dy**2)
        desplazamiento_metros = desplazamiento_pixeles / self.pixeles_por_metro

        # Tiempo total
        delta_tiempo = time_fin - time_inicio

        if delta_tiempo <= 0:
            return vehiculo.velocidad_instantanea

        # Velocidad promedio
        velocidad_ms = desplazamiento_metros / delta_tiempo
        velocidad_kmh = velocidad_ms * 3.6

        # Limitar
        velocidad_kmh = np.clip(velocidad_kmh, 0, 150)

        return velocidad_kmh

    def _limpiar_vehiculos_perdidos(self):
        """Elimina vehículos que no se han actualizado en mucho tiempo"""
        ids_a_eliminar = []

        for vehiculo_id, vehiculo in self.vehiculos.items():
            if vehiculo.frames_sin_actualizacion > self.max_frames_perdido:
                vehiculo.activo = False
                ids_a_eliminar.append(vehiculo_id)

        for vehiculo_id in ids_a_eliminar:
            del self.vehiculos[vehiculo_id]

    @staticmethod
    def _distancia_euclidiana(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calcula distancia euclidiana entre dos puntos"""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def obtener_velocidad_promedio_general(self) -> float:
        """
        Obtiene velocidad promedio de todos los vehículos activos

        Returns:
            Velocidad promedio en km/h (0 si no hay vehículos)
        """
        vehiculos_activos = [v for v in self.vehiculos.values() if v.activo]

        if not vehiculos_activos:
            return 0.0

        # Promediar velocidades de vehículos con suficiente historial
        velocidades = [
            v.velocidad_promedio
            for v in vehiculos_activos
            if len(v.posiciones) >= 3 and v.velocidad_promedio > 0
        ]

        if not velocidades:
            return 0.0

        return np.mean(velocidades)

    def obtener_estadisticas(self) -> Dict:
        """
        Obtiene estadísticas del tracking

        Returns:
            Diccionario con estadísticas
        """
        vehiculos_activos = [v for v in self.vehiculos.values() if v.activo]

        if not vehiculos_activos:
            return {
                'num_vehiculos': 0,
                'velocidad_promedio': 0.0,
                'velocidad_maxima': 0.0,
                'velocidad_minima': 0.0,
                'vehiculos_en_movimiento': 0
            }

        velocidades = [v.velocidad_promedio for v in vehiculos_activos if v.velocidad_promedio > 0]

        return {
            'num_vehiculos': len(vehiculos_activos),
            'velocidad_promedio': np.mean(velocidades) if velocidades else 0.0,
            'velocidad_maxima': np.max(velocidades) if velocidades else 0.0,
            'velocidad_minima': np.min(velocidades) if velocidades else 0.0,
            'vehiculos_en_movimiento': len([v for v in vehiculos_activos if v.velocidad_promedio > 2.0])
        }


# Ejemplo de uso
if __name__ == "__main__":
    # Ejemplo de tracking
    tracker = TrackerVehicular(
        fps=30.0,
        pixeles_por_metro=15.0,  # Ajustar según calibración
        usar_deepsort=True  # Usar DeepSORT si está disponible
    )

    # Simular detecciones en 3 frames consecutivos
    frame1_detecciones = [
        {'bbox': [100, 200, 150, 250], 'clase': 2, 'confianza': 0.9}
    ]

    frame2_detecciones = [
        {'bbox': [105, 200, 155, 250], 'clase': 2, 'confianza': 0.9}  # Se movió 5 píxeles
    ]

    frame3_detecciones = [
        {'bbox': [110, 200, 160, 250], 'clase': 2, 'confianza': 0.9}  # Se movió otros 5 píxeles
    ]

    # Frames simulados (para DeepSORT necesitaríamos frame real, usamos None para Centroid)
    frame_mock = None

    # Actualizar tracker (sin frame usa Centroid automáticamente)
    vehiculos_t1 = tracker.actualizar(frame1_detecciones, timestamp=0.0, frame=frame_mock)
    vehiculos_t2 = tracker.actualizar(frame2_detecciones, timestamp=1/30.0, frame=frame_mock)
    vehiculos_t3 = tracker.actualizar(frame3_detecciones, timestamp=2/30.0, frame=frame_mock)

    # Mostrar resultados
    for v in vehiculos_t3:
        print(f"Vehículo ID {v.id}:")
        print(f"  Velocidad instantánea: {v.velocidad_instantanea:.2f} km/h")
        print(f"  Velocidad promedio: {v.velocidad_promedio:.2f} km/h")

    stats = tracker.obtener_estadisticas()
    print(f"\nEstadísticas generales:")
    print(f"  Vehículos activos: {stats['num_vehiculos']}")
    print(f"  Velocidad promedio: {stats['velocidad_promedio']:.2f} km/h")
