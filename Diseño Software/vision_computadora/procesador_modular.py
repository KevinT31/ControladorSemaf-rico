"""
Procesador de Video Modular - Sistema de Evaluación por Componentes

Este módulo permite procesar videos en 3 modos diferentes para evaluar
cada funcionalidad del sistema de forma independiente:

1. DETECCIÓN BÁSICA: Solo detección de vehículos con YOLO
2. ANÁLISIS DE PARÁMETROS: Tracking + cálculo de métricas de tráfico
3. DETECCIÓN DE EMERGENCIA: Modelo custom para vehículos de emergencia

Ideal para:
- Demos en presentaciones
- Debugging de componentes específicos
- Validación de precisión por módulo
- Documentación visual para tesis

Uso:
    python vision_computadora/procesador_modular.py \
        --modo [deteccion|parametros|emergencia] \
        --video datos/videos-prueba/[carpeta]/[video].mp4 \
        --visualizar \
        --exportar
"""

import cv2
import numpy as np
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging
import sys
import json

# Importar módulos del proyecto
sys.path.append(str(Path(__file__).parent.parent))

from vision_computadora.procesador_video import ProcesadorVideo
from vision_computadora.tracking_vehicular import TrackerVehicular
from vision_computadora.detector_emergencia import DetectorEmergencia

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProcesadorModular:
    """
    Procesador modular con 3 modos de operación
    """

    MODOS_DISPONIBLES = ['deteccion', 'parametros', 'emergencia']

    def __init__(
        self,
        ruta_video: str,
        modo: str,
        pixeles_por_metro: float = 15.0
    ):
        """
        Args:
            ruta_video: Ruta al video a procesar
            modo: Modo de procesamiento ('deteccion', 'parametros', 'emergencia')
            pixeles_por_metro: Calibración espacial
        """
        if modo not in self.MODOS_DISPONIBLES:
            raise ValueError(f"Modo debe ser uno de: {self.MODOS_DISPONIBLES}")

        self.modo = modo
        self.ruta_video = Path(ruta_video)

        if not self.ruta_video.exists():
            raise FileNotFoundError(f"Video no encontrado: {ruta_video}")

        logger.info("=" * 70)
        logger.info(f"PROCESADOR MODULAR - MODO: {modo.upper()}")
        logger.info("=" * 70)

        # Crear procesador completo (todos los módulos activos)
        self.procesador = ProcesadorVideo(
            ruta_video=str(self.ruta_video),
            pixeles_por_metro=pixeles_por_metro
        )

        logger.info(f"✓ Procesador listo en modo: {modo.upper()}")

    def procesar(
        self,
        visualizar: bool = True,
        guardar_video: bool = True,
        exportar_datos: bool = True,
        directorio_salida: Optional[str] = None
    ) -> Dict:
        """
        Procesa el video según el modo seleccionado

        Args:
            visualizar: Si mostrar ventana con visualización en tiempo real
            guardar_video: Si guardar video procesado
            exportar_datos: Si exportar datos a CSV/JSON
            directorio_salida: Directorio donde guardar outputs

        Returns:
            Diccionario con estadísticas del procesamiento
        """
        if directorio_salida is None:
            directorio_salida = f"datos/resultados-video/exportaciones/{self.modo}/"

        Path(directorio_salida).mkdir(parents=True, exist_ok=True)

        logger.info(f"Procesando video: {self.ruta_video.name}")
        logger.info(f"Modo: {self.modo.upper()}")
        logger.info(f"Directorio salida: {directorio_salida}")

        # Procesar según modo
        if self.modo == 'deteccion':
            return self._procesar_modo_deteccion(
                visualizar, guardar_video, exportar_datos, directorio_salida
            )
        elif self.modo == 'parametros':
            return self._procesar_modo_parametros(
                visualizar, guardar_video, exportar_datos, directorio_salida
            )
        elif self.modo == 'emergencia':
            return self._procesar_modo_emergencia(
                visualizar, guardar_video, exportar_datos, directorio_salida
            )

    def _procesar_modo_deteccion(
        self,
        visualizar: bool,
        guardar_video: bool,
        exportar_datos: bool,
        directorio_salida: str
    ) -> Dict:
        """
        MODO 1: Detección Básica

        Solo muestra:
        - Vehículos detectados con bounding boxes
        - Clase y confianza
        - FPS de procesamiento

        NO muestra:
        - Velocidad, flujo, ICV (eso es modo 2)
        - Emergencias (eso es modo 3)
        """
        logger.info("")
        logger.info("📹 MODO DETECCIÓN BÁSICA")
        logger.info("  → Detectando vehículos con YOLOv8")
        logger.info("  → Mostrando bounding boxes y confianza")
        logger.info("")

        resultados = []
        frame_num = 0

        # Preparar video writer si se quiere guardar
        writer = None
        if guardar_video:
            nombre_salida = f"{self.ruta_video.stem}_deteccion.mp4"
            ruta_salida = Path(directorio_salida) / nombre_salida
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(
                str(ruta_salida),
                fourcc,
                self.procesador.fps,
                (self.procesador.ancho, self.procesador.alto)
            )

        tiempo_inicio = datetime.now()

        while True:
            ret, frame = self.procesador.video.read()
            if not ret:
                break

            # Detectar vehículos (solo YOLO, no tracking)
            resultados_yolo = self.procesador.modelo_yolo(frame, verbose=False)
            vehiculos = self.procesador._extraer_vehiculos_yolo(resultados_yolo[0])

            # Dibujar solo bounding boxes (simple)
            frame_anotado = self._dibujar_detecciones_simples(frame, vehiculos, frame_num)

            # Guardar resultado
            resultados.append({
                'frame': frame_num,
                'num_vehiculos': len(vehiculos),
                'vehiculos': vehiculos
            })

            # Guardar en video
            if writer:
                writer.write(frame_anotado)

            # Visualizar
            if visualizar:
                cv2.imshow('MODO: Detección Básica', frame_anotado)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            frame_num += 1

            if frame_num % 30 == 0:
                print(f"\rFrames procesados: {frame_num} - Vehículos detectados: {len(vehiculos)}", end='')

        tiempo_fin = datetime.now()
        duracion = (tiempo_fin - tiempo_inicio).total_seconds()

        # Limpiar
        self.procesador.video.release()
        if writer:
            writer.release()
        if visualizar:
            cv2.destroyAllWindows()

        # Estadísticas
        total_vehiculos = sum(r['num_vehiculos'] for r in resultados)
        promedio_vehiculos = total_vehiculos / len(resultados) if resultados else 0

        estadisticas = {
            'modo': 'deteccion',
            'frames_procesados': frame_num,
            'duracion_segundos': duracion,
            'fps_procesamiento': frame_num / duracion if duracion > 0 else 0,
            'total_vehiculos_detectados': total_vehiculos,
            'promedio_vehiculos_por_frame': promedio_vehiculos
        }

        # Exportar
        if exportar_datos:
            self._exportar_detecciones(resultados, directorio_salida)
            self._exportar_estadisticas(estadisticas, directorio_salida)

        logger.info("")
        logger.info("✓ Procesamiento completado")
        logger.info(f"  Frames: {frame_num}")
        logger.info(f"  Vehículos totales: {total_vehiculos}")
        logger.info(f"  Promedio por frame: {promedio_vehiculos:.1f}")

        return estadisticas

    def _procesar_modo_parametros(
        self,
        visualizar: bool,
        guardar_video: bool,
        exportar_datos: bool,
        directorio_salida: str
    ) -> Dict:
        """
        MODO 2: Análisis de Parámetros

        Muestra:
        - Detección de vehículos
        - Tracking entre frames
        - Velocidad REAL (tracking)
        - Flujo vehicular
        - Longitud de cola
        - ICV REAL (nucleo/)
        """
        logger.info("")
        logger.info("📊 MODO ANÁLISIS DE PARÁMETROS")
        logger.info("  → Detectando vehículos con YOLOv8")
        logger.info("  → Tracking para velocidad REAL")
        logger.info("  → Calculando ICV con nucleo/")
        logger.info("")

        # Procesar video completo
        resultados = self.procesador.procesar_completo(saltar_frames=1, mostrar_progreso=True)

        # Preparar video writer
        if guardar_video:
            nombre_salida = f"{self.ruta_video.stem}_parametros.mp4"
            ruta_salida = Path(directorio_salida) / nombre_salida

            # Re-abrir video para dibujar
            video_temp = cv2.VideoCapture(str(self.ruta_video))
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(
                str(ruta_salida),
                fourcc,
                self.procesador.fps,
                (self.procesador.ancho, self.procesador.alto)
            )

            for i, resultado in enumerate(resultados):
                ret, frame = video_temp.read()
                if not ret:
                    break

                frame_anotado = self.procesador.dibujar_detecciones(frame, resultado, mostrar_info=True)
                writer.write(frame_anotado)

                if visualizar and i % 2 == 0:  # Mostrar cada 2 frames
                    cv2.imshow('MODO: Análisis de Parámetros', frame_anotado)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

            video_temp.release()
            writer.release()
            if visualizar:
                cv2.destroyAllWindows()

        # Estadísticas
        velocidades = [r.velocidad_promedio for r in resultados if r.velocidad_promedio > 0]
        icvs = [r.icv for r in resultados]

        estadisticas = {
            'modo': 'parametros',
            'frames_procesados': len(resultados),
            'velocidad_promedio': np.mean(velocidades) if velocidades else 0,
            'velocidad_maxima': np.max(velocidades) if velocidades else 0,
            'icv_promedio': np.mean(icvs),
            'icv_maximo': np.max(icvs),
            'frames_congestionados': sum(1 for r in resultados if r.icv > 0.6),
            'frames_fluidos': sum(1 for r in resultados if r.icv < 0.3)
        }

        # Exportar
        if exportar_datos:
            ruta_csv = Path(directorio_salida) / f"{self.ruta_video.stem}_metricas.csv"
            self.procesador.exportar_resultados(resultados, str(ruta_csv))
            self._exportar_estadisticas(estadisticas, directorio_salida)
            self._generar_grafico_icv(resultados, directorio_salida)

        logger.info("")
        logger.info("✓ Análisis completado")
        logger.info(f"  Velocidad promedio: {estadisticas['velocidad_promedio']:.1f} km/h [REAL]")
        logger.info(f"  ICV promedio: {estadisticas['icv_promedio']:.3f} [REAL - nucleo/]")

        return estadisticas

    def _procesar_modo_emergencia(
        self,
        visualizar: bool,
        guardar_video: bool,
        exportar_datos: bool,
        directorio_salida: str
    ) -> Dict:
        """
        MODO 3: Detección de Emergencia

        Muestra:
        - Detección de vehículos normales
        - Detección de vehículos de emergencia (modelo custom)
        - Alertas visuales cuando detecta emergencia
        - Timestamps de detección
        """
        logger.info("")
        logger.info("🚨 MODO DETECCIÓN DE EMERGENCIA")
        logger.info("  → Detectando vehículos estándar")
        logger.info("  → Detectando vehículos de emergencia (modelo custom)")
        logger.info("")

        if not self.procesador.detector_emergencia.modelo_disponible:
            logger.error("❌ Modelo de emergencias NO disponible")
            logger.error("Ver: datos/entrenamiento-emergencia/README.md")
            return {'error': 'modelo_no_disponible'}

        resultados_completos = self.procesador.procesar_completo(saltar_frames=1, mostrar_progreso=True)

        # Filtrar solo frames con emergencias para análisis
        detecciones_emergencia = []
        for resultado in resultados_completos:
            if resultado.hay_emergencia:
                detecciones_emergencia.extend(resultado.detecciones_emergencia)

        # Guardar video si se solicita
        if guardar_video:
            nombre_salida = f"{self.ruta_video.stem}_emergencia.mp4"
            ruta_salida = Path(directorio_salida) / nombre_salida

            video_temp = cv2.VideoCapture(str(self.ruta_video))
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(
                str(ruta_salida),
                fourcc,
                self.procesador.fps,
                (self.procesador.ancho, self.procesador.alto)
            )

            for i, resultado in enumerate(resultados_completos):
                ret, frame = video_temp.read()
                if not ret:
                    break

                frame_anotado = self.procesador.dibujar_detecciones(frame, resultado)
                writer.write(frame_anotado)

                if visualizar and i % 2 == 0:
                    cv2.imshow('MODO: Detección de Emergencia', frame_anotado)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

            video_temp.release()
            writer.release()
            if visualizar:
                cv2.destroyAllWindows()

        # Estadísticas
        frames_con_emergencia = sum(1 for r in resultados_completos if r.hay_emergencia)
        tipos_detectados = {}
        for det in detecciones_emergencia:
            tipos_detectados[det.tipo] = tipos_detectados.get(det.tipo, 0) + 1

        estadisticas = {
            'modo': 'emergencia',
            'frames_procesados': len(resultados_completos),
            'frames_con_emergencia': frames_con_emergencia,
            'total_detecciones': len(detecciones_emergencia),
            'tipos_detectados': tipos_detectados
        }

        # Exportar
        if exportar_datos:
            if detecciones_emergencia:
                ruta_csv = Path(directorio_salida) / f"{self.ruta_video.stem}_emergencias.csv"
                self.procesador.detector_emergencia.exportar_detecciones(
                    detecciones_emergencia,
                    str(ruta_csv)
                )
            self._exportar_estadisticas(estadisticas, directorio_salida)

        logger.info("")
        logger.info("✓ Detección de emergencias completada")
        logger.info(f"  Frames con emergencia: {frames_con_emergencia}/{len(resultados_completos)}")
        logger.info(f"  Total detecciones: {len(detecciones_emergencia)}")
        logger.info(f"  Tipos detectados: {tipos_detectados}")

        return estadisticas

    def _dibujar_detecciones_simples(
        self,
        frame: np.ndarray,
        vehiculos: List[Dict],
        frame_num: int
    ) -> np.ndarray:
        """Dibuja detecciones simples (solo para modo detección)"""
        frame_anotado = frame.copy()

        # Dibujar cada vehículo
        for veh in vehiculos:
            x1, y1, x2, y2 = [int(v) for v in veh['bbox']]
            color = (0, 255, 0)

            cv2.rectangle(frame_anotado, (x1, y1), (x2, y2), color, 2)

            label = f"{veh['confianza']:.2f}"
            cv2.putText(frame_anotado, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Panel de info simple
        info_text = f"Frame: {frame_num} | Vehiculos: {len(vehiculos)}"
        cv2.rectangle(frame_anotado, (0, 0), (400, 40), (0, 0, 0), -1)
        cv2.putText(frame_anotado, info_text, (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame_anotado

    def _exportar_detecciones(self, resultados: List, directorio: str):
        """Exporta detecciones a CSV (modo detección)"""
        import csv

        ruta = Path(directorio) / f"{self.ruta_video.stem}_detecciones.csv"

        with open(ruta, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Frame', 'NumVehiculos', 'X1', 'Y1', 'X2', 'Y2', 'Confianza'])

            for r in resultados:
                for veh in r['vehiculos']:
                    writer.writerow([
                        r['frame'],
                        r['num_vehiculos'],
                        *[f"{v:.2f}" for v in veh['bbox']],
                        f"{veh['confianza']:.4f}"
                    ])

        logger.info(f"✓ Detecciones exportadas: {ruta}")

    def _exportar_estadisticas(self, estadisticas: Dict, directorio: str):
        """Exporta estadísticas a JSON"""
        ruta = Path(directorio) / f"{self.ruta_video.stem}_stats.json"

        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(estadisticas, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Estadísticas exportadas: {ruta}")

    def _generar_grafico_icv(self, resultados: List, directorio: str):
        """Genera gráfico de ICV vs tiempo"""
        try:
            import matplotlib.pyplot as plt

            timestamps = [r.timestamp for r in resultados]
            icvs = [r.icv for r in resultados]

            plt.figure(figsize=(12, 6))
            plt.plot(timestamps, icvs, linewidth=2)
            plt.axhline(y=0.3, color='g', linestyle='--', label='Umbral Fluido')
            plt.axhline(y=0.6, color='r', linestyle='--', label='Umbral Congestionado')
            plt.xlabel('Tiempo (s)')
            plt.ylabel('ICV')
            plt.title(f'Índice de Congestión Vehicular - {self.ruta_video.stem}')
            plt.legend()
            plt.grid(True, alpha=0.3)

            ruta = Path(directorio) / f"{self.ruta_video.stem}_icv_graph.png"
            plt.savefig(ruta, dpi=300, bbox_inches='tight')
            plt.close()

            logger.info(f"✓ Gráfico ICV generado: {ruta}")

        except ImportError:
            logger.warning("matplotlib no disponible, no se generó gráfico")


def main():
    parser = argparse.ArgumentParser(
        description='Procesador de Video Modular - Evaluación por Componentes'
    )

    parser.add_argument(
        '--modo',
        type=str,
        required=True,
        choices=['deteccion', 'parametros', 'emergencia'],
        help='Modo de procesamiento'
    )

    parser.add_argument(
        '--video',
        type=str,
        required=True,
        help='Ruta al video a procesar'
    )

    parser.add_argument(
        '--visualizar',
        action='store_true',
        help='Mostrar visualización en tiempo real'
    )

    parser.add_argument(
        '--exportar',
        action='store_true',
        help='Exportar resultados a archivos'
    )

    parser.add_argument(
        '--salida',
        type=str,
        default=None,
        help='Directorio de salida (default: datos/resultados-video/exportaciones/[modo]/)'
    )

    args = parser.parse_args()

    # Crear procesador
    procesador = ProcesadorModular(
        ruta_video=args.video,
        modo=args.modo
    )

    # Procesar
    estadisticas = procesador.procesar(
        visualizar=args.visualizar,
        guardar_video=True,
        exportar_datos=args.exportar,
        directorio_salida=args.salida
    )

    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    for key, value in estadisticas.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
