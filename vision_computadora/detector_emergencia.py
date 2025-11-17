"""
Detector de Vehículos de Emergencia REAL

Este módulo detecta vehículos de emergencia (ambulancia, bomberos, policía)
usando un modelo YOLOv8 custom entrenado.

NO USA np.random - Solo detecciones reales basadas en YOLO
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import cv2
import numpy as np

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    logger.error("ultralytics no instalado. Instalar con: pip install ultralytics")


@dataclass
class DeteccionEmergencia:
    """Detección de vehículo de emergencia"""
    tipo: str  # 'ambulancia', 'bomberos', 'policia'
    bbox: List[float]  # [x1, y1, x2, y2]
    confianza: float
    timestamp: datetime
    frame_numero: int
    centroide: Tuple[float, float]


class DetectorEmergencia:
    """
    Detector de vehículos de emergencia usando YOLOv8 custom

    El modelo debe estar entrenado con el dataset en:
    datos/entrenamiento-emergencia/

    Si el modelo no existe, provee instrucciones de entrenamiento.
    """

    # Clases del modelo custom
    CLASES_EMERGENCIA = {
        0: 'ambulancia',
        1: 'bomberos',
        2: 'policia'
    }

    # Colores para visualización (BGR)
    COLORES_EMERGENCIA = {
        'ambulancia': (0, 255, 255),    # Amarillo
        'bomberos': (0, 0, 255),        # Rojo
        'policia': (255, 0, 0),         # Azul
    }

    def __init__(
        self,
        modelo_path: Optional[str] = None,
        confianza_minima: float = 0.5,
        usar_fallback: bool = True,
        silencioso: bool = True  # Por defecto silencioso
    ):
        """
        Args:
            modelo_path: Ruta al modelo custom entrenado (.pt)
                        Si es None, busca en ubicaciones predeterminadas
            confianza_minima: Confianza mínima para considerar detección válida
            usar_fallback: Si usar detección alternativa cuando no hay modelo custom
            silencioso: Si True, no muestra warnings cuando no hay modelo (por defecto True)
        """
        self.confianza_minima = confianza_minima
        self.usar_fallback = usar_fallback
        self.silencioso = silencioso

        # Buscar modelo custom
        if modelo_path is None:
            modelo_path = self._buscar_modelo_custom()

        # Cargar modelo
        self.modelo = self._cargar_modelo(modelo_path)
        self.modelo_disponible = self.modelo is not None

        # Estadísticas
        self.total_detecciones = 0
        self.detecciones_por_tipo = {
            'ambulancia': 0,
            'bomberos': 0,
            'policia': 0
        }

    def _buscar_modelo_custom(self) -> Optional[str]:
        """
        Busca modelo custom en ubicaciones predeterminadas

        Returns:
            Ruta al modelo o None si no se encuentra
        """
        rutas_posibles = [
            # Modelo entrenado con YOLO
            Path("runs/detect/train/weights/best.pt"),
            Path("runs/detect/train2/weights/best.pt"),

            # Modelo guardado manualmente
            Path("datos/modelos-entrenados/emergencia_best.pt"),
            Path("vision_computadora/modelos/emergencia.pt"),

            # Modelo en directorio del proyecto
            Path("modelos/emergencia_yolov8.pt"),
        ]

        for ruta in rutas_posibles:
            if ruta.exists():
                if not self.silencioso:
                    logger.info(f"✓ Modelo custom encontrado: {ruta}")
                return str(ruta)

        # Solo mostrar warnings si no está en modo silencioso
        if not self.silencioso:
            logger.warning("⚠️ Modelo custom de emergencias NO encontrado")
            logger.warning("Ubicaciones buscadas:")
            for ruta in rutas_posibles:
                logger.warning(f"  - {ruta}")

        return None

    def _cargar_modelo(self, modelo_path: Optional[str]) -> Optional[YOLO]:
        """
        Carga el modelo YOLO custom

        Returns:
            Modelo YOLO o None si no se puede cargar
        """
        if YOLO is None:
            if not self.silencioso:
                logger.error("❌ ultralytics no instalado")
            return None

        if modelo_path is None or not Path(modelo_path).exists():
            if not self.silencioso:
                logger.warning("❌ Modelo custom no disponible")
                self._mostrar_instrucciones_entrenamiento()
            return None

        try:
            modelo = YOLO(modelo_path)
            if not self.silencioso:
                logger.info(f"✓ Modelo custom cargado: {modelo_path}")
            return modelo
        except Exception as e:
            if not self.silencioso:
                logger.error(f"❌ Error cargando modelo: {e}")
            return None

    def _mostrar_instrucciones_entrenamiento(self):
        """Muestra instrucciones para entrenar el modelo"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("MODELO DE EMERGENCIAS NO DISPONIBLE")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Para entrenar el modelo custom:")
        logger.info("")
        logger.info("1. Preparar dataset:")
        logger.info("   - Colocar imágenes en: datos/entrenamiento-emergencia/images/train/")
        logger.info("   - Colocar labels en:   datos/entrenamiento-emergencia/labels/train/")
        logger.info("   - Ver instrucciones en: datos/entrenamiento-emergencia/README.md")
        logger.info("")
        logger.info("2. Entrenar modelo:")
        logger.info("   cd C:\\Users\\kevin\\OneDrive\\Desktop\\ControladorSemaforicoTFC2")
        logger.info("   yolo train data=datos/entrenamiento-emergencia/dataset.yaml model=yolov8n.pt epochs=50")
        logger.info("")
        logger.info("3. El modelo entrenado se guardará en:")
        logger.info("   runs/detect/train/weights/best.pt")
        logger.info("")
        logger.info("=" * 70)
        logger.info("")

    def detectar(
        self,
        frame: np.ndarray,
        frame_numero: int = 0,
        timestamp: Optional[datetime] = None
    ) -> List[DeteccionEmergencia]:
        """
        Detecta vehículos de emergencia en un frame

        Args:
            frame: Frame del video (array numpy)
            frame_numero: Número de frame
            timestamp: Timestamp de captura

        Returns:
            Lista de detecciones de emergencia
        """
        if timestamp is None:
            timestamp = datetime.now()

        if not self.modelo_disponible:
            # Si no hay modelo, retornar lista vacía (NO generar detecciones falsas)
            return []

        # Realizar detección con YOLO
        resultados = self.modelo(frame, verbose=False, conf=self.confianza_minima)

        detecciones = []

        for resultado in resultados:
            for box in resultado.boxes:
                clase_id = int(box.cls[0])
                confianza = float(box.conf[0])

                # Verificar que sea una clase de emergencia
                if clase_id not in self.CLASES_EMERGENCIA:
                    continue

                tipo = self.CLASES_EMERGENCIA[clase_id]

                # Extraer bounding box
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                bbox = [float(x1), float(y1), float(x2), float(y2)]

                # Calcular centroide
                centroide = ((x1 + x2) / 2, (y1 + y2) / 2)

                # Crear detección
                deteccion = DeteccionEmergencia(
                    tipo=tipo,
                    bbox=bbox,
                    confianza=confianza,
                    timestamp=timestamp,
                    frame_numero=frame_numero,
                    centroide=centroide
                )

                detecciones.append(deteccion)

                # Actualizar estadísticas
                self.total_detecciones += 1
                self.detecciones_por_tipo[tipo] += 1

                logger.info(f"🚨 {tipo.upper()} detectado (confianza: {confianza:.2f})")

        return detecciones

    def dibujar_detecciones(
        self,
        frame: np.ndarray,
        detecciones: List[DeteccionEmergencia],
        mostrar_alerta: bool = True
    ) -> np.ndarray:
        """
        Dibuja las detecciones de emergencia en el frame

        Args:
            frame: Frame original
            detecciones: Lista de detecciones
            mostrar_alerta: Si mostrar alerta visual grande

        Returns:
            Frame con detecciones dibujadas
        """
        frame_anotado = frame.copy()

        # Si no hay detecciones, retornar frame original
        if not detecciones:
            return frame_anotado

        # Dibujar cada detección
        for det in detecciones:
            x1, y1, x2, y2 = [int(v) for v in det.bbox]
            color = self.COLORES_EMERGENCIA[det.tipo]

            # Bounding box más grueso para emergencias
            cv2.rectangle(frame_anotado, (x1, y1), (x2, y2), color, 3)

            # Etiqueta con tipo y confianza
            label = f"{det.tipo.upper()} {det.confianza:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)

            # Fondo para etiqueta
            cv2.rectangle(
                frame_anotado,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                color,
                -1
            )

            # Texto
            cv2.putText(
                frame_anotado,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

        # Mostrar alerta general si hay detecciones
        if mostrar_alerta:
            self._dibujar_alerta_emergencia(frame_anotado, detecciones)

        return frame_anotado

    def _dibujar_alerta_emergencia(
        self,
        frame: np.ndarray,
        detecciones: List[DeteccionEmergencia]
    ):
        """Dibuja alerta visual grande para emergencias"""
        h, w = frame.shape[:2]

        # Fondo semi-transparente rojo parpadeante
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 100), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        # Texto de alerta
        texto_alerta = f"🚨 VEHICULO DE EMERGENCIA DETECTADO 🚨"
        font_scale = 1.0
        thickness = 2

        # Centrar texto
        text_size, _ = cv2.getTextSize(texto_alerta, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        text_x = (w - text_size[0]) // 2
        text_y = 50

        # Texto con borde
        cv2.putText(frame, texto_alerta, (text_x, text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness + 2)
        cv2.putText(frame, texto_alerta, (text_x, text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)

        # Detalles de detecciones
        y_pos = 80
        for det in detecciones:
            detalle = f"{det.tipo.upper()}: {det.confianza:.2%}"
            cv2.putText(frame, detalle, (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_pos += 25

    def obtener_estadisticas(self) -> Dict:
        """
        Obtiene estadísticas de detecciones

        Returns:
            Diccionario con estadísticas
        """
        return {
            'total_detecciones': self.total_detecciones,
            'ambulancias': self.detecciones_por_tipo['ambulancia'],
            'bomberos': self.detecciones_por_tipo['bomberos'],
            'policia': self.detecciones_por_tipo['policia'],
            'modelo_disponible': self.modelo_disponible
        }

    def exportar_detecciones(
        self,
        detecciones: List[DeteccionEmergencia],
        ruta_salida: str
    ):
        """
        Exporta detecciones a CSV

        Args:
            detecciones: Lista de detecciones
            ruta_salida: Ruta del archivo CSV de salida
        """
        import csv

        with open(ruta_salida, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Frame', 'Timestamp', 'Tipo', 'Confianza',
                'X1', 'Y1', 'X2', 'Y2', 'Centroide_X', 'Centroide_Y'
            ])

            for det in detecciones:
                writer.writerow([
                    det.frame_numero,
                    det.timestamp.isoformat(),
                    det.tipo,
                    f"{det.confianza:.4f}",
                    *[f"{v:.2f}" for v in det.bbox],
                    f"{det.centroide[0]:.2f}",
                    f"{det.centroide[1]:.2f}"
                ])

        logger.info(f"✓ Detecciones exportadas a {ruta_salida}")


# Función auxiliar para detección de colores (fallback si no hay modelo custom)
def detectar_emergencia_por_color(frame: np.ndarray) -> bool:
    """
    FALLBACK: Detecta posibles emergencias por color

    Busca predominancia de colores típicos:
    - Rojo/Blanco para ambulancias y bomberos
    - Azul/Blanco para policía

    NOTA: Esto es un FALLBACK temporal. NO es confiable.
    Solo usar cuando NO hay modelo custom entrenado.

    Returns:
        True si detecta colores típicos de emergencia
    """
    # Convertir a HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Rangos de colores (HSV)
    # Rojo (ambulancia/bomberos)
    rojo_bajo1 = np.array([0, 100, 100])
    rojo_alto1 = np.array([10, 255, 255])
    rojo_bajo2 = np.array([160, 100, 100])
    rojo_alto2 = np.array([180, 255, 255])

    # Azul (policía)
    azul_bajo = np.array([100, 100, 100])
    azul_alto = np.array([130, 255, 255])

    # Máscaras
    mask_rojo1 = cv2.inRange(hsv, rojo_bajo1, rojo_alto1)
    mask_rojo2 = cv2.inRange(hsv, rojo_bajo2, rojo_alto2)
    mask_rojo = cv2.bitwise_or(mask_rojo1, mask_rojo2)
    mask_azul = cv2.inRange(hsv, azul_bajo, azul_alto)

    # Contar píxeles
    pixeles_rojo = cv2.countNonZero(mask_rojo)
    pixeles_azul = cv2.countNonZero(mask_azul)

    total_pixeles = frame.shape[0] * frame.shape[1]

    # Si más del 10% es rojo o azul, posible emergencia
    porcentaje_rojo = pixeles_rojo / total_pixeles
    porcentaje_azul = pixeles_azul / total_pixeles

    return porcentaje_rojo > 0.1 or porcentaje_azul > 0.1


# Ejemplo de uso
if __name__ == "__main__":
    # Crear detector
    detector = DetectorEmergencia()

    if detector.modelo_disponible:
        print("✓ Detector listo para usar")

        # Probar con imagen
        frame = cv2.imread("test_ambulancia.jpg")
        if frame is not None:
            detecciones = detector.detectar(frame)

            if detecciones:
                print(f"Detectadas {len(detecciones)} emergencias:")
                for det in detecciones:
                    print(f"  - {det.tipo}: {det.confianza:.2f}")

                # Dibujar y guardar
                frame_anotado = detector.dibujar_detecciones(frame, detecciones)
                cv2.imwrite("test_ambulancia_detectado.jpg", frame_anotado)
            else:
                print("No se detectaron vehículos de emergencia")
    else:
        print("❌ Detector no disponible - Entrena el modelo primero")
        print("Ver: datos/entrenamiento-emergencia/README.md")
