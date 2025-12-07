# -*- coding: utf-8 -*-
"""
Sistema de Visualización Mejorado para Análisis de Tráfico
Overlay moderno y profesional con métricas en tiempo real
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class EstiloVisual:
    """Configuración de estilo visual moderna - Morado/Verde/Blanco"""
    # Colores principales (BGR) - MORADO Y VERDE
    color_primario = (246, 92, 139)  # Morado claro #8B5CF6
    color_fondo = (35, 30, 40)  # Gris oscuro con tinte morado
    color_fondo_panel = (50, 40, 55)  # Panel con tinte morado
    color_texto = (255, 255, 255)  # Blanco puro
    color_texto_secundario = (220, 220, 220)  # Blanco ligeramente atenuado

    # Colores de estado ICV - VERDE para fluido, MORADO para congestionado
    color_fluido = (129, 185, 16)  # Verde #10B981
    color_moderado = (0, 200, 255)  # Amarillo
    color_congestionado = (100, 100, 255)  # Rojo suave

    # Colores de velocidad - VERDE
    color_vel_alta = (129, 185, 16)  # Verde
    color_vel_media = (0, 200, 255)  # Amarillo
    color_vel_baja = (100, 100, 255)  # Rojo

    # Fuentes - MÁS PEQUEÑAS Y PROFESIONALES
    fuente_titulo = cv2.FONT_HERSHEY_SIMPLEX
    fuente_texto = cv2.FONT_HERSHEY_SIMPLEX
    fuente_metrica = cv2.FONT_HERSHEY_SIMPLEX

    # Tamaños - REDUCIDOS
    grosor_texto_grande = 1
    grosor_texto_normal = 1
    grosor_bbox = 2
    radio_borde = 8


class OverlayVisualModerno:
    """
    Sistema de overlay moderno y profesional
    Muestra métricas REALES sin inventar datos
    """

    def __init__(self, estilo: Optional[EstiloVisual] = None):
        self.estilo = estilo or EstiloVisual()

    def dibujar_rectangulo_redondeado(
        self,
        img: np.ndarray,
        pt1: Tuple[int, int],
        pt2: Tuple[int, int],
        color: Tuple[int, int, int],
        thickness: int = -1,
        radio: int = 10
    ):
        """Dibuja un rectángulo con bordes redondeados"""
        x1, y1 = pt1
        x2, y2 = pt2

        # Líneas principales
        cv2.line(img, (x1 + radio, y1), (x2 - radio, y1), color, thickness if thickness > 0 else 1)
        cv2.line(img, (x1 + radio, y2), (x2 - radio, y2), color, thickness if thickness > 0 else 1)
        cv2.line(img, (x1, y1 + radio), (x1, y2 - radio), color, thickness if thickness > 0 else 1)
        cv2.line(img, (x2, y1 + radio), (x2, y2 - radio), color, thickness if thickness > 0 else 1)

        # Esquinas redondeadas
        cv2.ellipse(img, (x1 + radio, y1 + radio), (radio, radio), 180, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radio, y1 + radio), (radio, radio), 270, 0, 90, color, thickness)
        cv2.ellipse(img, (x1 + radio, y2 - radio), (radio, radio), 90, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radio, y2 - radio), (radio, radio), 0, 0, 90, color, thickness)

        # Rellenar si thickness == -1
        if thickness == -1:
            cv2.rectangle(img, (x1 + radio, y1), (x2 - radio, y2), color, -1)
            cv2.rectangle(img, (x1, y1 + radio), (x2, y2 - radio), color, -1)
            cv2.circle(img, (x1 + radio, y1 + radio), radio, color, -1)
            cv2.circle(img, (x2 - radio, y1 + radio), radio, color, -1)
            cv2.circle(img, (x1 + radio, y2 - radio), radio, color, -1)
            cv2.circle(img, (x2 - radio, y2 - radio), radio, color, -1)

    def dibujar_panel_superior(
        self,
        frame: np.ndarray,
        resultado: Dict,
        titulo: str = "ANALISIS DE TRAFICO EN TIEMPO REAL"
    ) -> np.ndarray:
        """Dibuja panel superior moderno con título"""
        h, w = frame.shape[:2]
        # Escalado dinámico según altura del frame (referencia 720px)
        s = max(0.6, min(1.5, h / 720.0))

        # Panel semi-transparente - Más compacto
        overlay = frame.copy()
        panel_height = int(55 * s)
        cv2.rectangle(overlay, (0, 0), (w, panel_height), self.estilo.color_fondo, -1)
        frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)

        # Línea de acento superior morada
        cv2.rectangle(frame, (0, 0), (w, 3), self.estilo.color_primario, -1)

        # Título - Más pequeño
        cv2.putText(
            frame,
            titulo,
            (int(20 * s), int(38 * s)),
            self.estilo.fuente_titulo,
            0.6 * s,
            self.estilo.color_texto,
            1
        )

        # Información de tiempo - Más pequeño
        tiempo_min = int(resultado.get('timestamp', 0) // 60)
        tiempo_seg = int(resultado.get('timestamp', 0) % 60)
        texto_tiempo = f"{tiempo_min:02d}:{tiempo_seg:02d}"

        cv2.putText(
            frame,
            texto_tiempo,
            (w - int(120 * s), int(38 * s)),
            self.estilo.fuente_metrica,
            0.7 * s,
            self.estilo.color_primario,
            1
        )

        return frame

    def dibujar_panel_metricas(
        self,
        frame: np.ndarray,
        resultado: Dict,
        forzar_omitir: bool = False
    ) -> np.ndarray:
        """Dibuja panel lateral con métricas principales con mejor espaciado"""
        
        # Si forzar_omitir está activo, NO dibujar nada salvo que haya emergencia
        if forzar_omitir:
            try:
                if not resultado.get('hay_emergencia', False):
                    return frame
            except Exception:
                return frame
        
        h, w = frame.shape[:2]
        # Escala dinámica (referencia 720px)
        s = max(0.6, min(1.5, h / 720.0))

        # Panel MÁS GRANDE para acomodar todas las métricas
        panel_x = w - int(420 * s)
        panel_y = int(90 * s)
        panel_w = int(400 * s)
        panel_h = h - int(200 * s)  # Usar casi toda la altura disponible

        # Fondo del panel con transparencia
        overlay = frame.copy()
        self.dibujar_rectangulo_redondeado(
            overlay,
            (panel_x, panel_y),
            (panel_x + panel_w, panel_y + panel_h),
            self.estilo.color_fondo_panel,
            -1,
            int(15 * s)
        )
        frame = cv2.addWeighted(overlay, 0.90, frame, 0.10, 0)

        # Borde del panel
        self.dibujar_rectangulo_redondeado(
            frame,
            (panel_x, panel_y),
            (panel_x + panel_w, panel_y + panel_h),
            self.estilo.color_primario,
            max(1, int(2 * s)),
            int(15 * s)
        )

        y_pos = panel_y + int(30 * s)  # Margen superior compacto
        x_pos = panel_x + int(15 * s)
        ESPACIADO_GRANDE = int(65 * s)  # Espaciado entre métricas grandes
        ESPACIADO_PEQUENO = int(42 * s)  # Espaciado entre métricas pequeñas

        # 1. Número de vehículos (métrica REAL)
        num_vehiculos = resultado.get('num_vehiculos', 0)
        self._dibujar_metrica_grande(
            frame,
            "VEHICULOS DETECTADOS",
            str(num_vehiculos),
            x_pos,
            y_pos,
            self.estilo.color_primario
        )
        y_pos += ESPACIADO_GRANDE

        # 2. Velocidad promedio (métrica REAL)
        velocidad = resultado.get('velocidad_promedio', 0.0)
        color_vel = self._obtener_color_velocidad(velocidad)
        self._dibujar_metrica_grande(
            frame,
            "VELOCIDAD PROMEDIO",
            f"{velocidad:.1f} km/h",
            x_pos,
            y_pos,
            color_vel
        )
        y_pos += ESPACIADO_GRANDE

        # 3. ICV (métrica REAL) - LA MÁS IMPORTANTE
        icv = resultado.get('icv', 0.0)
        clasificacion = resultado.get('clasificacion_icv', 'fluido')
        color_icv = self._obtener_color_icv(icv)

        self._dibujar_metrica_grande(
            frame,
            "INDICE CONGESTION (ICV)",
            f"{icv:.3f}",
            x_pos,
            y_pos,
            color_icv
        )

        # Estado textual debajo del ICV - Mucho más abajo
        estado_texto = clasificacion.upper()
        cv2.putText(
            frame,
            estado_texto,
            (x_pos, y_pos + int(65 * s)),
            self.estilo.fuente_texto,
            0.6 * s,
            color_icv,
            2
        )
        y_pos += int(115 * s)

        # === SECCIÓN: MÉTRICAS ADICIONALES ===
        # Línea separadora con más margen
        cv2.line(
            frame,
            (x_pos, y_pos - int(5 * s)),
            (panel_x + panel_w - int(20 * s), y_pos - int(5 * s)),
            (100, 100, 100),
            max(1, int(1 * s))
        )
        y_pos += int(15 * s)  # Más espacio después de la línea separadora

        # 4. Flujo vehicular (q)
        flujo = resultado.get('flujo_vehicular', 0.0)
        self._dibujar_metrica_pequena(
            frame,
            "Flujo (q)",
            f"{flujo:.1f} veh/min",
            x_pos,
            y_pos,
            self.estilo.color_texto_secundario
        )
        y_pos += ESPACIADO_PEQUENO

        # 5. Longitud de cola
        cola = resultado.get('longitud_cola', 0.0)
        self._dibujar_metrica_pequena(
            frame,
            "Long. Cola",
            f"{cola:.1f} m",
            x_pos,
            y_pos,
            self.estilo.color_texto_secundario
        )
        y_pos += ESPACIADO_PEQUENO

        # 5b. Cola por vehículos (nuevo requerimiento)
        cola_veh = resultado.get('cola_vehiculos_count', 0)
        self._dibujar_metrica_pequena(
            frame,
            "Cola (veh)",
            f"{int(cola_veh)} veh",
            x_pos,
            y_pos,
            self.estilo.color_texto_secundario
        )
        y_pos += ESPACIADO_PEQUENO

        # 6. PI (Parámetro de Intensidad) - IMPORTANTE
        metricas_cap6 = resultado.get('metricas_cap6')
        if metricas_cap6:
            pi = metricas_cap6.get('parametro_intensidad', 0.0)
            self._dibujar_metrica_pequena(
                frame,
                "Param. Intensidad (PI)",
                f"{pi:.3f}",
                x_pos,
                y_pos,
                self.estilo.color_primario
            )
            y_pos += ESPACIADO_PEQUENO

            # 7. SC (Stopped Count)
            sc = metricas_cap6.get('stopped_count', 0)
            self._dibujar_metrica_pequena(
                frame,
                "Vehiculos Detenidos (SC)",
                f"{sc:.0f}",
                x_pos,
                y_pos,
                self.estilo.color_texto_secundario
            )
            y_pos += ESPACIADO_PEQUENO

            # 8. k (Densidad)
            k = metricas_cap6.get('densidad_vehicular', 0.0)
            self._dibujar_metrica_pequena(
                frame,
                "Densidad (k)",
                f"{k:.4f} veh/m",
                x_pos,
                y_pos,
                self.estilo.color_texto_secundario
            )
            y_pos += ESPACIADO_PEQUENO

            # 9. Vavg (solo vehículos en movimiento)
            vavg = metricas_cap6.get('velocidad_promedio_movimiento', 0.0)
            if vavg > 0:
                self._dibujar_metrica_pequena(
                    frame,
                    "Vel. en Movimiento (Vavg)",
                    f"{vavg:.1f} km/h",
                    x_pos,
                    y_pos,
                    self.estilo.color_texto_secundario
                )

        return frame

    def dibujar_barra_icv(
        self,
        frame: np.ndarray,
        icv: float
    ) -> np.ndarray:
        """Dibuja barra visual VERTICAL en el lado izquierdo"""
        h, w = frame.shape[:2]
        s = max(0.6, min(1.5, h / 720.0))

        # Posición de la barra VERTICAL (lado izquierdo)
        barra_x = int(25 * s)
        barra_y = int(120 * s)
        barra_w = int(35 * s)  # Ancho de la barra vertical
        barra_h = h - int(250 * s)  # Alto de la barra vertical

        # Fondo de la barra
        overlay = frame.copy()
        self.dibujar_rectangulo_redondeado(
            overlay,
            (barra_x, barra_y),
            (barra_x + barra_w, barra_y + barra_h),
            self.estilo.color_fondo_panel,
            -1,
            int(8 * s)
        )
        frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)

        # Borde de la barra
        self.dibujar_rectangulo_redondeado(
            frame,
            (barra_x, barra_y),
            (barra_x + barra_w, barra_y + barra_h),
            self.estilo.color_primario,
            max(1, int(2 * s)),
            int(8 * s)
        )

        # Marcadores de umbral (horizontal en barra vertical)
        umbral_30 = int(barra_h * 0.7)
        umbral_60 = int(barra_h * 0.4)

        # Líneas de umbral
        cv2.line(frame, (barra_x, barra_y + umbral_30), (barra_x + barra_w, barra_y + umbral_30), (120, 120, 120), max(1, int(1 * s)))
        cv2.line(frame, (barra_x, barra_y + umbral_60), (barra_x + barra_w, barra_y + umbral_60), (120, 120, 120), max(1, int(1 * s)))

        # Etiquetas de umbral al lado de la barra
        cv2.putText(frame, "0.3", (barra_x + barra_w + int(5 * s), barra_y + umbral_30 + int(5 * s)),
               cv2.FONT_HERSHEY_SIMPLEX, 0.35 * s, (200, 200, 200), max(1, int(1 * s)))
        cv2.putText(frame, "0.6", (barra_x + barra_w + int(5 * s), barra_y + umbral_60 + int(5 * s)),
               cv2.FONT_HERSHEY_SIMPLEX, 0.35 * s, (200, 200, 200), max(1, int(1 * s)))

        # Título de la barra (rotado)
        cv2.putText(frame, "ICV", (barra_x, barra_y - int(10 * s)),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5 * s, self.estilo.color_texto, max(1, int(1 * s)))

        # Barra de progreso del ICV (de abajo hacia arriba)
        altura_icv = int(barra_h * min(icv, 1.0))
        color_barra = self._obtener_color_icv(icv)

        if altura_icv > 0:
            overlay2 = frame.copy()
            # Dibujar desde abajo hacia arriba
            self.dibujar_rectangulo_redondeado(
                overlay2,
                (barra_x + 3, barra_y + barra_h - altura_icv),
                (barra_x + barra_w - 3, barra_y + barra_h - 3),
                color_barra,
                -1,
                int(6 * s)
            )
            frame = cv2.addWeighted(overlay2, 0.9, frame, 0.1, 0)

        # Valor del ICV debajo de la barra
        cv2.putText(frame, f"{icv:.2f}", (barra_x - int(5 * s), barra_y + barra_h + int(20 * s)),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5 * s, color_barra, max(1, int(2 * s)))

        return frame

    def dibujar_detecciones_vehiculos(
        self,
        frame: np.ndarray,
        vehiculos: List[Dict],
        mostrar_velocidad: bool = True
    ) -> np.ndarray:
        """Dibuja bounding boxes de vehículos con diseño moderno"""
        for vehiculo in vehiculos:
            x1, y1, x2, y2 = map(int, vehiculo.get('bbox', [0, 0, 0, 0]))

            # Color según confianza
            confianza = vehiculo.get('confianza', 0.0)
            if confianza > 0.8:
                color = self.estilo.color_fluido
            elif confianza > 0.6:
                color = self.estilo.color_moderado
            else:
                color = self.estilo.color_congestionado

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Pequeño marcador en esquina
            cv2.circle(frame, (x1 + 5, y1 + 5), 4, color, -1)

            # Etiqueta compacta
            if mostrar_velocidad and 'velocidad' in vehiculo:
                vel = vehiculo['velocidad']
                if vel > 0:
                    label = f"{vel:.0f} km/h"

                    # Fondo de la etiqueta
                    (tw, th), _ = cv2.getTextSize(label, self.estilo.fuente_texto, 0.5, 1)
                    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 8, y1), color, -1)
                    cv2.putText(frame, label, (x1 + 4, y1 - 4),
                               self.estilo.fuente_texto, 0.5, (0, 0, 0), 1)

        return frame

    def crear_visualizacion_completa(
        self,
        frame: np.ndarray,
        resultado: Dict,
        mostrar_barra: bool = True,
        modo_simple: bool = False
    ) -> np.ndarray:
        """
        Crea visualización completa con todos los elementos
        IMPORTANTE: Usa métricas REALES del resultado, no inventa datos
        
        Args:
            frame: Frame a procesar
            resultado: Diccionario con resultados del análisis
            mostrar_barra: Si mostrar barra de ICV
            modo_simple: Si True, solo muestra título y barra (sin panel de métricas)
        """
        # 1. Panel superior
        frame = self.dibujar_panel_superior(frame, resultado)

        # 2. Panel de métricas lateral
        # SIEMPRE llamar pero pasar forzar_omitir=True si está en modo_simple
        frame = self.dibujar_panel_metricas(frame, resultado, forzar_omitir=modo_simple)

        # 3. Detecciones de vehículos
        if 'vehiculos_detectados' in resultado:
            frame = self.dibujar_detecciones_vehiculos(
                frame,
                resultado['vehiculos_detectados'],
                mostrar_velocidad=False  # No mostrar velocidad por vehículo en la interfaz
            )

        # 4. Barra de ICV (siempre si mostrar_barra=True)
        if mostrar_barra and 'icv' in resultado:
            frame = self.dibujar_barra_icv(frame, resultado['icv'])

        # 5. Zonas de activación de CamMask (visualización sutil)
        # Dibuja bandas suaves cerca de extremos para NS y EO basadas en R y R_trigger si están en resultado
        try:
            params = resultado.get('metricas_cap6') or {}
            # Usar parámetros del sistema si están disponibles en resultado
            R = resultado.get('radio_cobertura', None)
            Rtrig = resultado.get('radio_trigger', None)
            cx = resultado.get('centroide_x', None)
            cy = resultado.get('centroide_y', None)
            if R and Rtrig and cx is not None and cy is not None:
                h, w = frame.shape[:2]
                # Convertir metros a píxeles si se proporciona pixeles_por_metro
                ppm = resultado.get('pixeles_por_metro', None)
                if ppm:
                    R_px = int(R * ppm)
                    Rt_px = int(Rtrig * ppm)
                    cx_px = int(cx)
                    cy_px = int(cy)
                    # Dibujar bandas verticales (EO) y horizontales (NS) con baja opacidad
                    overlay = frame.copy()
                    color_zone = (180, 120, 200)
                    alpha = 0.12
                    # EO: bandas verticales
                    x_left1 = max(0, cx_px - R_px)
                    x_left2 = max(0, cx_px - Rt_px)
                    x_right1 = min(w-1, cx_px + Rt_px)
                    x_right2 = min(w-1, cx_px + R_px)
                    cv2.rectangle(overlay, (x_left1, 0), (x_left2, h), color_zone, -1)
                    cv2.rectangle(overlay, (x_right1, 0), (x_right2, h), color_zone, -1)
                    # NS: bandas horizontales
                    y_top1 = max(0, cy_px - R_px)
                    y_top2 = max(0, cy_px - Rt_px)
                    y_bot1 = min(h-1, cy_px + Rt_px)
                    y_bot2 = min(h-1, cy_px + R_px)
                    cv2.rectangle(overlay, (0, y_top1), (w, y_top2), color_zone, -1)
                    cv2.rectangle(overlay, (0, y_bot1), (w, y_bot2), color_zone, -1)
                    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        except Exception:
            pass

        return frame

    def _dibujar_metrica_grande(
        self,
        frame: np.ndarray,
        label: str,
        valor: str,
        x: int,
        y: int,
        color: Tuple[int, int, int]
    ):
        """Dibuja una métrica grande con label y valor - Profesional y compacto"""
        # Escala por altura del frame
        h = frame.shape[0]
        s = max(0.6, min(1.5, h / 720.0))
        # Label pequeño arriba
        cv2.putText(
            frame,
            label,
            (x, y),
            self.estilo.fuente_texto,
            0.45 * s,
            self.estilo.color_texto_secundario,
            1
        )

        # Valor grande abajo - MÁS PEQUEÑO
        cv2.putText(
            frame,
            valor,
            (x, y + int(30 * s)),
            self.estilo.fuente_metrica,
            0.85 * s,
            color,
            max(1, int(2 * s))
        )

    def _dibujar_metrica_pequena(
        self,
        frame: np.ndarray,
        label: str,
        valor: str,
        x: int,
        y: int,
        color: Tuple[int, int, int]
    ):
        """Dibuja una métrica pequeña - Profesional y compacto"""
        h = frame.shape[0]
        s = max(0.6, min(1.5, h / 720.0))
        # Label en línea superior
        cv2.putText(
            frame,
            label,
            (x, y),
            self.estilo.fuente_texto,
            0.4 * s,
            self.estilo.color_texto_secundario,
            max(1, int(1 * s))
        )

        # Valor en línea inferior - MÁS PEQUEÑO
        cv2.putText(
            frame,
            valor,
            (x + int(5 * s), y + int(18 * s)),
            self.estilo.fuente_texto,
            0.55 * s,
            color,
            max(1, int(1 * s))
        )

    def _obtener_color_icv(self, icv: float) -> Tuple[int, int, int]:
        """Retorna color según valor de ICV"""
        if icv < 0.3:
            return self.estilo.color_fluido
        elif icv < 0.6:
            return self.estilo.color_moderado
        else:
            return self.estilo.color_congestionado

    def _obtener_color_velocidad(self, velocidad: float) -> Tuple[int, int, int]:
        """Retorna color según velocidad"""
        if velocidad >= 40:
            return self.estilo.color_vel_alta
        elif velocidad >= 20:
            return self.estilo.color_vel_media
        else:
            return self.estilo.color_vel_baja


def convertir_resultado_a_dict(resultado) -> Dict:
    """Convierte ResultadoFrame a diccionario para el overlay"""
    if hasattr(resultado, '__dict__'):
        data = vars(resultado)
        # Adjuntar parámetros geométricos si existen en calculador o procesador
        # Estos campos permiten dibujar zonas de activación de CamMask de forma sutil
        if 'metricas_cap6' in data and data['metricas_cap6']:
            # Intentar añadir parámetros básicos si están accesibles
            data.setdefault('radio_cobertura', 50.0)
            data.setdefault('radio_trigger', 30.0)
            data.setdefault('centroide_x', 0.0)
            data.setdefault('centroide_y', 0.0)
        return data
    else:
        return resultado
