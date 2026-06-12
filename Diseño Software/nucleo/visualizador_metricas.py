# -*- coding: utf-8 -*-
"""
Visualizador de Métricas
Genera gráficas y visualizaciones de las métricas del sistema

Este módulo crea carpetas de salida y genera visualizaciones similares
a las que genera ejecutar.py para mantener consistencia.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json
import logging

# Importar matplotlib si está disponible
try:
    import matplotlib
    matplotlib.use('Agg')  # Backend sin GUI
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    MATPLOTLIB_DISPONIBLE = True
except ImportError:
    MATPLOTLIB_DISPONIBLE = False

import numpy as np

logger = logging.getLogger(__name__)


class SistemaVisualizacion:
    """
    Sistema de visualización y generación de carpetas de salida
    """

    def __init__(self, directorio_base: Optional[Path] = None):
        """
        Args:
            directorio_base: Directorio base para salidas (default: ./visualizaciones)
        """
        if directorio_base is None:
            directorio_base = Path("./visualizaciones")

        self.directorio_base = Path(directorio_base)
        self._crear_estructura_carpetas()

    def _crear_estructura_carpetas(self):
        """Crea la estructura de carpetas de salida"""
        # Carpetas principales
        self.carpeta_graficas = self.directorio_base / "graficas"
        self.carpeta_datos = self.directorio_base / "datos"
        self.carpeta_reportes = self.directorio_base / "reportes"
        self.carpeta_comparaciones = self.directorio_base / "comparaciones"
        self.carpeta_logs = self.directorio_base / "logs"

        # Crear todas las carpetas
        for carpeta in [
            self.carpeta_graficas,
            self.carpeta_datos,
            self.carpeta_reportes,
            self.carpeta_comparaciones,
            self.carpeta_logs
        ]:
            carpeta.mkdir(parents=True, exist_ok=True)

        logger.info(f"✓ Estructura de carpetas creada en: {self.directorio_base}")

    def generar_grafica_serie_temporal(
        self,
        serie_metricas: List[Dict],
        metrica: str,
        titulo: str,
        archivo_salida: Optional[Path] = None,
        mostrar_umbral: bool = True
    ) -> Optional[Path]:
        """
        Genera una gráfica de serie temporal para una métrica

        Args:
            serie_metricas: Lista de diccionarios con métricas
            metrica: Nombre de la métrica a graficar ('icv_promedio', 'vavg_promedio', etc.)
            titulo: Título de la gráfica
            archivo_salida: Ruta del archivo de salida (opcional)
            mostrar_umbral: Si mostrar líneas de umbral

        Returns:
            Path al archivo generado o None si falló
        """
        if not MATPLOTLIB_DISPONIBLE:
            logger.warning("Matplotlib no disponible. No se pueden generar gráficas.")
            return None

        if not serie_metricas:
            logger.warning("No hay métricas para graficar")
            return None

        try:
            fig, ax = plt.subplots(figsize=(12, 6))

            # Extraer datos
            tiempos = [m['tiempo_segundos'] for m in serie_metricas]
            valores = [m[metrica] for m in serie_metricas]

            # Graficar
            ax.plot(tiempos, valores, linewidth=2, color='#2563eb', label=metrica)

            # Umbrales para ICV
            if mostrar_umbral and 'icv' in metrica.lower():
                ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.5, label='Umbral Fluido/Moderado')
                ax.axhline(y=0.6, color='red', linestyle='--', alpha=0.5, label='Umbral Moderado/Congestionado')
                ax.fill_between(tiempos, 0, 0.3, alpha=0.1, color='green', label='Fluido')
                ax.fill_between(tiempos, 0.3, 0.6, alpha=0.1, color='yellow', label='Moderado')
                ax.fill_between(tiempos, 0.6, 1.0, alpha=0.1, color='red', label='Congestionado')

            ax.set_xlabel('Tiempo (segundos)', fontsize=12)
            ax.set_ylabel(titulo, fontsize=12)
            ax.set_title(titulo, fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')

            # Guardar
            if archivo_salida is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archivo_salida = self.carpeta_graficas / f"{metrica}_{timestamp}.png"

            plt.tight_layout()
            fig.savefig(archivo_salida, dpi=150, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"✓ Gráfica generada: {archivo_salida.name}")
            return archivo_salida

        except Exception as e:
            logger.error(f"Error generando gráfica: {e}")
            return None

    def generar_grafica_comparacion(
        self,
        serie_1: List[Dict],
        serie_2: List[Dict],
        metrica: str,
        label_1: str,
        label_2: str,
        titulo: str,
        archivo_salida: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Genera una gráfica comparando dos series temporales

        Args:
            serie_1: Primera serie de métricas
            serie_2: Segunda serie de métricas
            metrica: Métrica a comparar
            label_1: Etiqueta para serie 1
            label_2: Etiqueta para serie 2
            titulo: Título de la gráfica
            archivo_salida: Archivo de salida (opcional)

        Returns:
            Path al archivo generado o None
        """
        if not MATPLOTLIB_DISPONIBLE:
            return None

        try:
            fig, ax = plt.subplots(figsize=(14, 7))

            # Extraer datos
            tiempos_1 = [m['tiempo_segundos'] for m in serie_1]
            valores_1 = [m[metrica] for m in serie_1]

            tiempos_2 = [m['tiempo_segundos'] for m in serie_2]
            valores_2 = [m[metrica] for m in serie_2]

            # Graficar ambas series
            ax.plot(tiempos_1, valores_1, linewidth=2, color='#ef4444',
                   label=label_1, alpha=0.8)
            ax.plot(tiempos_2, valores_2, linewidth=2, color='#22c55e',
                   label=label_2, alpha=0.8)

            # Umbrales si es ICV
            if 'icv' in metrica.lower():
                ax.axhline(y=0.3, color='gray', linestyle='--', alpha=0.3)
                ax.axhline(y=0.6, color='gray', linestyle='--', alpha=0.3)

            ax.set_xlabel('Tiempo (segundos)', fontsize=12)
            ax.set_ylabel(titulo, fontsize=12)
            ax.set_title(titulo, fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right', fontsize=11)

            # Calcular mejora
            prom_1 = np.mean(valores_1)
            prom_2 = np.mean(valores_2)

            if 'icv' in metrica.lower():
                mejora = ((prom_1 - prom_2) / prom_1) * 100
                texto_mejora = f"Reducción: {mejora:.1f}%"
            else:
                mejora = ((prom_2 - prom_1) / prom_1) * 100
                texto_mejora = f"Aumento: {mejora:.1f}%"

            # Añadir texto de mejora
            ax.text(0.02, 0.98, texto_mejora, transform=ax.transAxes,
                   fontsize=12, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

            # Guardar
            if archivo_salida is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archivo_salida = self.carpeta_comparaciones / f"comparacion_{metrica}_{timestamp}.png"

            plt.tight_layout()
            fig.savefig(archivo_salida, dpi=150, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"✓ Gráfica de comparación generada: {archivo_salida.name}")
            return archivo_salida

        except Exception as e:
            logger.error(f"Error generando gráfica de comparación: {e}")
            return None

    def generar_dashboard_completo(
        self,
        serie_metricas: List[Dict],
        archivo_salida: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Genera un dashboard completo con múltiples métricas

        Args:
            serie_metricas: Serie de métricas completa
            archivo_salida: Archivo de salida (opcional)

        Returns:
            Path al archivo generado
        """
        if not MATPLOTLIB_DISPONIBLE:
            return None

        try:
            fig = plt.figure(figsize=(16, 10))
            gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

            tiempos = [m['tiempo_segundos'] for m in serie_metricas]

            # 1. ICV Promedio
            ax1 = fig.add_subplot(gs[0, :])
            icv_valores = [m['icv_promedio'] for m in serie_metricas]
            ax1.plot(tiempos, icv_valores, linewidth=2, color='#2563eb')
            ax1.axhline(y=0.3, color='green', linestyle='--', alpha=0.5)
            ax1.axhline(y=0.6, color='red', linestyle='--', alpha=0.5)
            ax1.fill_between(tiempos, 0, 0.3, alpha=0.1, color='green')
            ax1.fill_between(tiempos, 0.3, 0.6, alpha=0.1, color='yellow')
            ax1.fill_between(tiempos, 0.6, 1.0, alpha=0.1, color='red')
            ax1.set_ylabel('ICV', fontsize=11)
            ax1.set_title('Índice de Congestión Vehicular (ICV)', fontsize=12, fontweight='bold')
            ax1.grid(True, alpha=0.3)

            # 2. Velocidad Promedio
            ax2 = fig.add_subplot(gs[1, 0])
            vel_valores = [m['vavg_promedio'] for m in serie_metricas]
            ax2.plot(tiempos, vel_valores, linewidth=2, color='#10b981')
            ax2.set_ylabel('Velocidad (km/h)', fontsize=11)
            ax2.set_title('Velocidad Promedio', fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3)

            # 3. Flujo Vehicular
            ax3 = fig.add_subplot(gs[1, 1])
            q_ns = [m['q_ns'] for m in serie_metricas]
            q_eo = [m['q_eo'] for m in serie_metricas]
            ax3.plot(tiempos, q_ns, linewidth=2, label='NS', alpha=0.7)
            ax3.plot(tiempos, q_eo, linewidth=2, label='EO', alpha=0.7)
            ax3.set_ylabel('Flujo (veh/min)', fontsize=11)
            ax3.set_title('Flujo Vehicular por Dirección', fontsize=12, fontweight='bold')
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            # 4. Vehículos Detenidos (SC)
            ax4 = fig.add_subplot(gs[2, 0])
            sc_ns = [m['sc_ns'] for m in serie_metricas]
            sc_eo = [m['sc_eo'] for m in serie_metricas]
            ax4.plot(tiempos, sc_ns, linewidth=2, label='NS', alpha=0.7)
            ax4.plot(tiempos, sc_eo, linewidth=2, label='EO', alpha=0.7)
            ax4.set_ylabel('Vehículos Detenidos', fontsize=11)
            ax4.set_xlabel('Tiempo (segundos)', fontsize=11)
            ax4.set_title('Stopped Count (SC) por Dirección', fontsize=12, fontweight='bold')
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            # 5. Parámetro de Intensidad (PI)
            ax5 = fig.add_subplot(gs[2, 1])
            pi_ns = [m['pi_ns'] for m in serie_metricas]
            pi_eo = [m['pi_eo'] for m in serie_metricas]
            ax5.plot(tiempos, pi_ns, linewidth=2, label='NS', alpha=0.7)
            ax5.plot(tiempos, pi_eo, linewidth=2, label='EO', alpha=0.7)
            ax5.set_ylabel('PI', fontsize=11)
            ax5.set_xlabel('Tiempo (segundos)', fontsize=11)
            ax5.set_title('Parámetro de Intensidad (PI)', fontsize=12, fontweight='bold')
            ax5.legend()
            ax5.grid(True, alpha=0.3)

            # Título general
            fig.suptitle('Dashboard de Métricas del Sistema', fontsize=16, fontweight='bold')

            # Guardar
            if archivo_salida is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archivo_salida = self.carpeta_graficas / f"dashboard_{timestamp}.png"

            plt.savefig(archivo_salida, dpi=150, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"✓ Dashboard generado: {archivo_salida.name}")
            return archivo_salida

        except Exception as e:
            logger.error(f"Error generando dashboard: {e}")
            return None

    def guardar_metricas_json(
        self,
        serie_metricas: List[Dict],
        nombre_archivo: str = "metricas.json"
    ) -> Path:
        """
        Guarda las métricas en formato JSON

        Args:
            serie_metricas: Serie de métricas
            nombre_archivo: Nombre del archivo de salida

        Returns:
            Path al archivo guardado
        """
        archivo_salida = self.carpeta_datos / nombre_archivo

        # Convertir timestamps a strings
        metricas_serializables = []
        for m in serie_metricas:
            m_copy = m.copy()
            if 'timestamp' in m_copy:
                m_copy['timestamp'] = m_copy['timestamp'].isoformat()
            metricas_serializables.append(m_copy)

        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'fecha_generacion': datetime.now().isoformat(),
                    'num_muestras': len(metricas_serializables)
                },
                'metricas': metricas_serializables
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Métricas guardadas en JSON: {archivo_salida.name}")
        return archivo_salida

    def guardar_metricas_csv(
        self,
        serie_metricas: List[Dict],
        nombre_archivo: str = "metricas.csv"
    ) -> Path:
        """
        Guarda las métricas en formato CSV

        Args:
            serie_metricas: Serie de métricas
            nombre_archivo: Nombre del archivo

        Returns:
            Path al archivo guardado
        """
        archivo_salida = self.carpeta_datos / nombre_archivo

        if not serie_metricas:
            logger.warning("No hay métricas para guardar")
            return archivo_salida

        # Obtener columnas
        columnas = list(serie_metricas[0].keys())

        with open(archivo_salida, 'w', encoding='utf-8') as f:
            # Escribir encabezado
            f.write(','.join(str(c) for c in columnas) + '\n')

            # Escribir datos
            for m in serie_metricas:
                valores = []
                for col in columnas:
                    val = m.get(col, '')
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    valores.append(str(val))
                f.write(','.join(valores) + '\n')

        logger.info(f"✓ Métricas guardadas en CSV: {archivo_salida.name}")
        return archivo_salida

    def generar_resumen_estadistico(
        self,
        serie_metricas: List[Dict],
        nombre_archivo: str = "resumen_estadistico.txt"
    ) -> Path:
        """
        Genera un resumen estadístico en texto

        Args:
            serie_metricas: Serie de métricas
            nombre_archivo: Nombre del archivo

        Returns:
            Path al archivo generado
        """
        archivo_salida = self.carpeta_reportes / nombre_archivo

        # Calcular estadísticas
        icv_valores = [m['icv_promedio'] for m in serie_metricas]
        vel_valores = [m['vavg_promedio'] for m in serie_metricas]

        # Clasificar estados
        num_fluido = sum(1 for icv in icv_valores if icv < 0.3)
        num_moderado = sum(1 for icv in icv_valores if 0.3 <= icv < 0.6)
        num_congestionado = sum(1 for icv in icv_valores if icv >= 0.6)
        total = len(icv_valores)

        with open(archivo_salida, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("RESUMEN ESTADÍSTICO - MÉTRICAS DEL SISTEMA\n")
            f.write("="*70 + "\n\n")

            f.write(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Número de muestras: {total}\n")
            f.write(f"Duración total: {serie_metricas[-1]['tiempo_segundos']:.1f} segundos\n\n")

            f.write("Índice de Congestión Vehicular (ICV):\n")
            f.write(f"  • Promedio: {np.mean(icv_valores):.4f}\n")
            f.write(f"  • Desviación estándar: {np.std(icv_valores):.4f}\n")
            f.write(f"  • Mínimo: {np.min(icv_valores):.4f}\n")
            f.write(f"  • Máximo: {np.max(icv_valores):.4f}\n\n")

            f.write("Velocidad Promedio:\n")
            f.write(f"  • Promedio: {np.mean(vel_valores):.2f} km/h\n")
            f.write(f"  • Desviación estándar: {np.std(vel_valores):.2f} km/h\n")
            f.write(f"  • Mínimo: {np.min(vel_valores):.2f} km/h\n")
            f.write(f"  • Máximo: {np.max(vel_valores):.2f} km/h\n\n")

            f.write("Distribución de Estados:\n")
            f.write(f"  • Fluido (ICV < 0.3): {num_fluido} ({num_fluido/total*100:.1f}%)\n")
            f.write(f"  • Moderado (0.3 ≤ ICV < 0.6): {num_moderado} ({num_moderado/total*100:.1f}%)\n")
            f.write(f"  • Congestionado (ICV ≥ 0.6): {num_congestionado} ({num_congestionado/total*100:.1f}%)\n\n")

            f.write("="*70 + "\n")

        logger.info(f"✓ Resumen estadístico generado: {archivo_salida.name}")
        return archivo_salida

    def obtener_info_carpetas(self) -> Dict[str, Path]:
        """
        Obtiene información de las carpetas creadas

        Returns:
            Dict con las rutas de las carpetas
        """
        return {
            'base': self.directorio_base,
            'graficas': self.carpeta_graficas,
            'datos': self.carpeta_datos,
            'reportes': self.carpeta_reportes,
            'comparaciones': self.carpeta_comparaciones,
            'logs': self.carpeta_logs
        }


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SISTEMA DE VISUALIZACIÓN DE MÉTRICAS")
    print("="*70 + "\n")

    # Crear sistema de visualización
    visualizador = SistemaVisualizacion(directorio_base="./demo_visualizaciones")

    print("✓ Sistema de visualización inicializado")
    print(f"  Carpetas creadas en: {visualizador.directorio_base}\n")

    # Mostrar carpetas
    carpetas = visualizador.obtener_info_carpetas()
    print("Estructura de carpetas:")
    for nombre, ruta in carpetas.items():
        print(f"  • {nombre}: {ruta}")

    print("\n" + "="*70)
    print("✓ Sistema listo para generar visualizaciones")
    print("="*70 + "\n")
