# -*- coding: utf-8 -*-
"""
Sistema de Overlay Mejorado para Visualizaciones del Capítulo 6
Dibuja métricas realistas sobre video con estética profesional

Este módulo mejora las visualizaciones de video para que se vean más profesionales
y muestren todas las métricas del Capítulo 6 de forma clara y elegante.
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ConfiguracionOverlay:
    """Configuración visual del overlay"""
    fuente: int = cv2.FONT_HERSHEY_DUPLEX
    grosor_texto: int = 2
    grosor_bbox: int = 2

    # Colores (BGR)
    color_fondo_panel: Tuple[int, int, int] = (40, 40, 40)
    color_texto_principal: Tuple[int, int, int] = (255, 255, 255)
    color_icv_fluido: Tuple[int, int, int] = (0, 255, 0)
    color_icv_moderado: Tuple[int, int, int] = (0, 255, 255)
    color_icv_congestionado: Tuple[int, int, int] = (0, 0, 255)
    color_bbox_normal: Tuple[int, int, int] = (0, 255, 0)
    color_bbox_emergencia: Tuple[int, int, int] = (0, 0, 255)

    # Tamaños
    altura_panel_superior: int = 180
    altura_panel_inferior: int = 120
    margen: int = 10
    espaciado_lineas: int = 35


class OverlayMetricasCap6:
    """
    Sistema de overlay profesional para mostrar métricas del Capítulo 6
    en visualizaciones de video
    """

    def __init__(self, config: Optional[ConfiguracionOverlay] = None):
        """
        Args:
            config: Configuración visual personalizada
        """
        self.config = config or ConfiguracionOverlay()

    def dibujar_panel_superior(
        self,
        frame: np.ndarray,
        metricas: Dict,
        titulo: str = "SISTEMA DE CONTROL SEMAFÓRICO ADAPTATIVO"
    ) -> np.ndarray:
        """
        Dibuja panel superior con información general

        Args:
            frame: Frame del video
            metricas: Diccionario con métricas a mostrar
            titulo: Título del panel

        Returns:
            Frame con panel dibujado
        """
        h, w = frame.shape[:2]
        config = self.config

        # Crear panel semi-transparente
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (0, 0),
            (w, config.altura_panel_superior),
            config.color_fondo_panel,
            -1
        )
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Título
        cv2.putText(
            frame,
            titulo,
            (config.margen, 30),
            config.fuente,
            0.7,
            config.color_texto_principal,
            2
        )

        # Línea separadora
        cv2.line(
            frame,
            (config.margen, 45),
            (w - config.margen, 45),
            (100, 100, 100),
            1
        )

        # Información general en la primera fila
        y_pos = 75

        # Frame y timestamp
        if 'numero_frame' in metricas:
            texto_frame = f"Frame: {metricas['numero_frame']}"
            cv2.putText(
                frame,
                texto_frame,
                (config.margen, y_pos),
                config.fuente,
                0.5,
                (200, 200, 200),
                1
            )

        if 'timestamp' in metricas:
            tiempo_min = int(metricas['timestamp'] // 60)
            tiempo_seg = int(metricas['timestamp'] % 60)
            texto_tiempo = f"Tiempo: {tiempo_min:02d}:{tiempo_seg:02d}"
            cv2.putText(
                frame,
                texto_tiempo,
                (config.margen + 200, y_pos),
                config.fuente,
                0.5,
                (200, 200, 200),
                1
            )

        return frame

    def dibujar_metricas_trafico(
        self,
        frame: np.ndarray,
        metricas: Dict,
        mostrar_cap6: bool = True
    ) -> np.ndarray:
        """
        Dibuja métricas de tráfico en panel lateral o inferior

        Args:
            frame: Frame del video
            metricas: Métricas a mostrar
            mostrar_cap6: Si mostrar métricas específicas del Cap 6

        Returns:
            Frame con métricas dibujadas
        """
        h, w = frame.shape[:2]
        config = self.config

        # Panel derecho para métricas
        x_inicio = w - 350
        y_inicio = config.altura_panel_superior + 20

        # Fondo del panel de métricas
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (x_inicio - 10, y_inicio - 10),
            (w - 10, y_inicio + 400),
            config.color_fondo_panel,
            -1
        )
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Título del panel
        cv2.putText(
            frame,
            "METRICAS EN TIEMPO REAL",
            (x_inicio, y_inicio),
            config.fuente,
            0.6,
            config.color_texto_principal,
            2
        )

        y_pos = y_inicio + 40

        # Número de vehículos
        if 'num_vehiculos' in metricas:
            texto = f"Vehiculos: {metricas['num_vehiculos']}"
            cv2.putText(
                frame,
                texto,
                (x_inicio, y_pos),
                config.fuente,
                0.7,
                (0, 255, 255),
                2
            )
            y_pos += config.espaciado_lineas

        # Velocidad promedio
        if 'velocidad_promedio' in metricas:
            vel = metricas['velocidad_promedio']
            texto = f"Velocidad: {vel:.1f} km/h"
            color = self._obtener_color_velocidad(vel)
            cv2.putText(
                frame,
                texto,
                (x_inicio, y_pos),
                config.fuente,
                0.7,
                color,
                2
            )
            y_pos += config.espaciado_lineas

        # ICV (Índice de Congestión Vehicular)
        if 'icv' in metricas:
            icv = metricas['icv']
            clasificacion = metricas.get('clasificacion_icv', 'N/A')

            # Color según clasificación
            if icv < 0.3:
                color_icv = config.color_icv_fluido
                emoji = "FLUIDO"
            elif icv < 0.6:
                color_icv = config.color_icv_moderado
                emoji = "MODERADO"
            else:
                color_icv = config.color_icv_congestionado
                emoji = "CONGESTIONADO"

            texto_icv = f"ICV: {icv:.3f}"
            cv2.putText(
                frame,
                texto_icv,
                (x_inicio, y_pos),
                config.fuente,
                0.7,
                color_icv,
                2
            )
            y_pos += 30

            # Estado de congestión
            cv2.putText(
                frame,
                emoji,
                (x_inicio, y_pos),
                config.fuente,
                0.6,
                color_icv,
                2
            )
            y_pos += config.espaciado_lineas

        # Métricas del Capítulo 6 (si están disponibles)
        if mostrar_cap6 and 'metricas_cap6' in metricas and metricas['metricas_cap6']:
            cap6 = metricas['metricas_cap6']

            # Separador
            cv2.line(
                frame,
                (x_inicio, y_pos),
                (w - 20, y_pos),
                (100, 100, 100),
                1
            )
            y_pos += 10

            # Título sección Cap 6
            cv2.putText(
                frame,
                "CAP 6 - METRICAS",
                (x_inicio, y_pos),
                config.fuente,
                0.5,
                (150, 150, 255),
                1
            )
            y_pos += 30

            # SC (Stopped Count)
            if 'stopped_count' in cap6:
                texto = f"SC: {cap6['stopped_count']:.0f} veh"
                cv2.putText(
                    frame,
                    texto,
                    (x_inicio, y_pos),
                    config.fuente,
                    0.5,
                    (255, 255, 255),
                    1
                )
                y_pos += 25

            # Vavg (Velocidad promedio en movimiento)
            if 'velocidad_promedio_movimiento' in cap6:
                texto = f"Vavg: {cap6['velocidad_promedio_movimiento']:.1f} km/h"
                cv2.putText(
                    frame,
                    texto,
                    (x_inicio, y_pos),
                    config.fuente,
                    0.5,
                    (255, 255, 255),
                    1
                )
                y_pos += 25

            # q (Flujo vehicular)
            if 'flujo_vehicular' in cap6:
                texto = f"q: {cap6['flujo_vehicular']:.2f} veh/min"
                cv2.putText(
                    frame,
                    texto,
                    (x_inicio, y_pos),
                    config.fuente,
                    0.5,
                    (255, 255, 255),
                    1
                )
                y_pos += 25

            # k (Densidad)
            if 'densidad_vehicular' in cap6:
                texto = f"k: {cap6['densidad_vehicular']:.4f} veh/m"
                cv2.putText(
                    frame,
                    texto,
                    (x_inicio, y_pos),
                    config.fuente,
                    0.5,
                    (255, 255, 255),
                    1
                )
                y_pos += 25

            # PI (Parámetro de Intensidad)
            if 'parametro_intensidad' in cap6:
                texto = f"PI: {cap6['parametro_intensidad']:.3f}"
                cv2.putText(
                    frame,
                    texto,
                    (x_inicio, y_pos),
                    config.fuente,
                    0.5,
                    (255, 255, 255),
                    1
                )

        return frame

    def dibujar_detecciones(
        self,
        frame: np.ndarray,
        detecciones: List[Dict],
        mostrar_velocidad: bool = True,
        mostrar_id: bool = True
    ) -> np.ndarray:
        """
        Dibuja bounding boxes de vehículos detectados

        Args:
            frame: Frame del video
            detecciones: Lista de detecciones de vehículos
            mostrar_velocidad: Si mostrar velocidad individual
            mostrar_id: Si mostrar ID de tracking

        Returns:
            Frame con detecciones dibujadas
        """
        for det in detecciones:
            # Obtener bbox
            x1 = int(det.get('x1', 0))
            y1 = int(det.get('y1', 0))
            x2 = int(det.get('x2', 0))
            y2 = int(det.get('y2', 0))

            # Color según tipo
            es_emergencia = det.get('es_emergencia', False)
            color = self.config.color_bbox_emergencia if es_emergencia else self.config.color_bbox_normal

            # Dibujar bounding box
            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                self.config.grosor_bbox
            )

            # Información encima del bbox
            textos = []

            # ID de tracking
            if mostrar_id and 'id' in det:
                textos.append(f"ID:{det['id']}")

            # Clase
            if 'clase' in det:
                textos.append(det['clase'])

            # Velocidad
            if mostrar_velocidad and 'velocidad' in det:
                vel = det['velocidad']
                if vel > 0:
                    textos.append(f"{vel:.1f}km/h")

            # Dibujar textos
            if textos:
                texto_completo = " | ".join(textos)

                # Fondo para el texto
                (tw, th), _ = cv2.getTextSize(
                    texto_completo,
                    self.config.fuente,
                    0.5,
                    1
                )

                cv2.rectangle(
                    frame,
                    (x1, y1 - th - 10),
                    (x1 + tw + 10, y1),
                    color,
                    -1
                )

                # Texto
                cv2.putText(
                    frame,
                    texto_completo,
                    (x1 + 5, y1 - 5),
                    self.config.fuente,
                    0.5,
                    (0, 0, 0),
                    1
                )

        return frame

    def dibujar_barra_icv(
        self,
        frame: np.ndarray,
        icv: float,
        posicion: str = "inferior"
    ) -> np.ndarray:
        """
        Dibuja una barra de progreso visual para el ICV

        Args:
            frame: Frame del video
            icv: Valor del ICV (0.0 - 1.0)
            posicion: "superior" o "inferior"

        Returns:
            Frame con barra dibujada
        """
        h, w = frame.shape[:2]
        config = self.config

        # Dimensiones de la barra
        barra_ancho = w - 100
        barra_altura = 30
        barra_x = 50

        if posicion == "inferior":
            barra_y = h - 80
        else:
            barra_y = config.altura_panel_superior + 20

        # Fondo de la barra
        cv2.rectangle(
            frame,
            (barra_x, barra_y),
            (barra_x + barra_ancho, barra_y + barra_altura),
            (60, 60, 60),
            -1
        )

        # Borde
        cv2.rectangle(
            frame,
            (barra_x, barra_y),
            (barra_x + barra_ancho, barra_y + barra_altura),
            (255, 255, 255),
            2
        )

        # Marcas de umbral
        umbral_moderado = int(barra_ancho * 0.3)
        umbral_congestionado = int(barra_ancho * 0.6)

        cv2.line(
            frame,
            (barra_x + umbral_moderado, barra_y),
            (barra_x + umbral_moderado, barra_y + barra_altura),
            (200, 200, 200),
            1
        )

        cv2.line(
            frame,
            (barra_x + umbral_congestionado, barra_y),
            (barra_x + umbral_congestionado, barra_y + barra_altura),
            (200, 200, 200),
            1
        )

        # Barra de progreso del ICV
        ancho_icv = int(barra_ancho * min(icv, 1.0))

        # Color según valor
        if icv < 0.3:
            color_barra = config.color_icv_fluido
        elif icv < 0.6:
            color_barra = config.color_icv_moderado
        else:
            color_barra = config.color_icv_congestionado

        cv2.rectangle(
            frame,
            (barra_x + 2, barra_y + 2),
            (barra_x + ancho_icv, barra_y + barra_altura - 2),
            color_barra,
            -1
        )

        # Texto del ICV
        texto_icv = f"ICV: {icv:.3f}"
        cv2.putText(
            frame,
            texto_icv,
            (barra_x + barra_ancho//2 - 50, barra_y - 10),
            config.fuente,
            0.6,
            (255, 255, 255),
            2
        )

        # Etiquetas de umbral
        cv2.putText(
            frame,
            "0.3",
            (barra_x + umbral_moderado - 15, barra_y + barra_altura + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (200, 200, 200),
            1
        )

        cv2.putText(
            frame,
            "0.6",
            (barra_x + umbral_congestionado - 15, barra_y + barra_altura + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (200, 200, 200),
            1
        )

        return frame

    def dibujar_alerta_emergencia(
        self,
        frame: np.ndarray,
        hay_emergencia: bool,
        frame_num: int
    ) -> np.ndarray:
        """
        Dibuja alerta visual de emergencia

        Args:
            frame: Frame del video
            hay_emergencia: Si hay emergencia detectada
            frame_num: Número de frame (para efecto parpadeo)

        Returns:
            Frame con alerta dibujada
        """
        if not hay_emergencia:
            return frame

        h, w = frame.shape[:2]

        # Borde rojo parpadeante
        if frame_num % 10 < 5:
            cv2.rectangle(
                frame,
                (0, 0),
                (w - 1, h - 1),
                (0, 0, 255),
                15
            )

        # Texto de alerta
        texto = "EMERGENCIA DETECTADA"
        escala = 1.5
        grosor = 3

        # Calcular posición centrada
        (tw, th), _ = cv2.getTextSize(
            texto,
            self.config.fuente,
            escala,
            grosor
        )

        x_texto = (w - tw) // 2
        y_texto = 60

        # Fondo semi-transparente
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (x_texto - 20, y_texto - th - 20),
            (x_texto + tw + 20, y_texto + 10),
            (0, 0, 0),
            -1
        )
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Texto
        cv2.putText(
            frame,
            texto,
            (x_texto, y_texto),
            self.config.fuente,
            escala,
            (0, 0, 255),
            grosor
        )

        return frame

    def _obtener_color_velocidad(self, velocidad: float) -> Tuple[int, int, int]:
        """
        Retorna color según velocidad

        Args:
            velocidad: Velocidad en km/h

        Returns:
            Color BGR
        """
        if velocidad < 10:
            return (0, 0, 255)  # Rojo - muy lento
        elif velocidad < 30:
            return (0, 255, 255)  # Amarillo - moderado
        else:
            return (0, 255, 0)  # Verde - fluido

    def crear_overlay_completo(
        self,
        frame: np.ndarray,
        resultado_frame: Dict,
        mostrar_cap6: bool = True,
        mostrar_barra_icv: bool = True
    ) -> np.ndarray:
        """
        Crea overlay completo con todas las métricas

        Args:
            frame: Frame original del video
            resultado_frame: Resultado del procesamiento con todas las métricas
            mostrar_cap6: Si mostrar métricas específicas del Cap 6
            mostrar_barra_icv: Si mostrar barra visual del ICV

        Returns:
            Frame con overlay completo
        """
        # Panel superior
        frame = self.dibujar_panel_superior(frame, resultado_frame)

        # Métricas de tráfico
        frame = self.dibujar_metricas_trafico(frame, resultado_frame, mostrar_cap6)

        # Detecciones de vehículos
        if 'vehiculos_detectados' in resultado_frame:
            frame = self.dibujar_detecciones(
                frame,
                resultado_frame['vehiculos_detectados'],
                mostrar_velocidad=True,
                mostrar_id=True
            )

        # Barra de ICV
        if mostrar_barra_icv and 'icv' in resultado_frame:
            frame = self.dibujar_barra_icv(frame, resultado_frame['icv'], "inferior")

        # Alerta de emergencia
        if resultado_frame.get('hay_emergencia', False):
            frame = self.dibujar_alerta_emergencia(
                frame,
                True,
                resultado_frame.get('numero_frame', 0)
            )

        return frame


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def convertir_resultado_a_dict(resultado_frame) -> Dict:
    """
    Convierte un ResultadoFrame a diccionario para el overlay

    Args:
        resultado_frame: Objeto ResultadoFrame del procesador

    Returns:
        Diccionario con todas las métricas
    """
    if hasattr(resultado_frame, '__dict__'):
        return vars(resultado_frame)
    else:
        return resultado_frame


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SISTEMA DE OVERLAY MEJORADO - CAPÍTULO 6")
    print("="*70 + "\n")

    # Crear overlay
    overlay = OverlayMetricasCap6()

    print("✓ Sistema de overlay creado")
    print("\nCaracterísticas:")
    print("  • Panel superior con información general")
    print("  • Panel lateral con métricas en tiempo real")
    print("  • Bounding boxes con ID y velocidad")
    print("  • Barra visual de ICV")
    print("  • Alertas de emergencia")
    print("  • Métricas completas del Capítulo 6")

    print("\nIntegración con procesador de video:")
    print("  from vision_computadora.overlay_metricas_cap6 import OverlayMetricasCap6")
    print("  overlay = OverlayMetricasCap6()")
    print("  frame_anotado = overlay.crear_overlay_completo(frame, resultado)")

    print("\n" + "="*70)
    print("✓ Sistema listo para usar")
    print("="*70 + "\n")
