"""
Exportador de Análisis para Tesis

Este módulo exporta datos del sistema a formatos compatibles con MATLAB (.mat)
para análisis estadístico y generación de gráficos de calidad publicación.

Soporta:
- Exportación a formato MATLAB (.mat)
- Exportación a CSV
- Generación de gráficos de alta calidad (300 DPI)
- Informes completos para documentación de tesis
"""

import numpy as np
from scipy.io import savemat, loadmat
import csv
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

# Matplotlib para gráficos (opcional)
try:
    import matplotlib
    matplotlib.use('Agg')  # Backend sin GUI
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    MATPLOTLIB_DISPONIBLE = True
except ImportError:
    MATPLOTLIB_DISPONIBLE = False
    logging.warning("Matplotlib no disponible. Instalar con: pip install matplotlib")

logger = logging.getLogger(__name__)


class ExportadorAnalisis:
    """
    Exportador de datos para análisis de tesis

    Genera archivos compatibles con MATLAB y gráficos de calidad publicación
    """

    def __init__(self, carpeta_salida: Optional[Path] = None):
        """
        Args:
            carpeta_salida: Carpeta donde guardar exportaciones (default: Calculo-Matlab/)
        """
        if carpeta_salida is None:
            carpeta_salida = Path(__file__).parent.parent / 'Calculo-Matlab'

        self.carpeta_salida = Path(carpeta_salida)
        self.carpeta_salida.mkdir(parents=True, exist_ok=True)

        # Subcarpetas
        self.carpeta_mat = self.carpeta_salida / 'datos-mat'
        self.carpeta_csv = self.carpeta_salida / 'datos-csv'
        self.carpeta_figuras = self.carpeta_salida / 'figuras'

        for carpeta in [self.carpeta_mat, self.carpeta_csv, self.carpeta_figuras]:
            carpeta.mkdir(parents=True, exist_ok=True)

        logger.info(f"Exportador inicializado. Carpeta salida: {self.carpeta_salida}")

    def exportar_serie_temporal_icv(
        self,
        timestamps: List[float],
        valores_icv: List[float],
        nombre_archivo: str = 'serie_temporal_icv',
        metadatos: Optional[Dict] = None
    ):
        """
        Exporta serie temporal de ICV a MATLAB y CSV

        Args:
            timestamps: Timestamps en segundos
            valores_icv: Valores de ICV [0,1]
            nombre_archivo: Nombre base del archivo
            metadatos: Información adicional (intersección, fecha, etc.)
        """
        # Convertir a numpy arrays
        timestamps = np.array(timestamps)
        valores_icv = np.array(valores_icv)

        # Exportar a MATLAB
        datos_mat = {
            'timestamps': timestamps,
            'icv': valores_icv,
            'num_puntos': len(valores_icv),
            'duracion_segundos': timestamps[-1] if len(timestamps) > 0 else 0,
            'icv_promedio': np.mean(valores_icv) if len(valores_icv) > 0 else 0,
            'icv_std': np.std(valores_icv) if len(valores_icv) > 0 else 0,
            'icv_min': np.min(valores_icv) if len(valores_icv) > 0 else 0,
            'icv_max': np.max(valores_icv) if len(valores_icv) > 0 else 0,
            'fecha_exportacion': datetime.now().isoformat()
        }

        if metadatos:
            datos_mat['metadatos'] = metadatos

        ruta_mat = self.carpeta_mat / f'{nombre_archivo}.mat'
        savemat(ruta_mat, datos_mat)
        logger.info(f"Serie temporal ICV exportada a MATLAB: {ruta_mat}")

        # Exportar a CSV
        ruta_csv = self.carpeta_csv / f'{nombre_archivo}.csv'
        with open(ruta_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp_s', 'ICV', 'Clasificacion'])
            for t, icv in zip(timestamps, valores_icv):
                clasificacion = self._clasificar_icv(icv)
                writer.writerow([f"{t:.2f}", f"{icv:.4f}", clasificacion])

        logger.info(f"Serie temporal ICV exportada a CSV: {ruta_csv}")

        # Generar gráfico si matplotlib está disponible
        if MATPLOTLIB_DISPONIBLE:
            self._graficar_serie_temporal_icv(timestamps, valores_icv, nombre_archivo)

        return {
            'archivo_mat': str(ruta_mat),
            'archivo_csv': str(ruta_csv),
            'num_puntos': len(valores_icv),
            'estadisticas': {
                'promedio': np.mean(valores_icv) if len(valores_icv) > 0 else 0,
                'desviacion_std': np.std(valores_icv) if len(valores_icv) > 0 else 0,
                'minimo': np.min(valores_icv) if len(valores_icv) > 0 else 0,
                'maximo': np.max(valores_icv) if len(valores_icv) > 0 else 0
            }
        }

    def exportar_superficie_control_difuso(
        self,
        controlador_difuso,
        nombre_archivo: str = 'superficie_fuzzy',
        resolucion: int = 50
    ):
        """
        Exporta superficie de control difuso 3D a MATLAB

        Args:
            controlador_difuso: Instancia de ControladorDifuso
            nombre_archivo: Nombre base del archivo
            resolucion: Número de puntos en cada dimensión
        """
        # Generar malla de valores
        icv_valores = np.linspace(0, 1, resolucion)
        espera_valores = np.linspace(0, 120, resolucion)

        ICV, ESPERA = np.meshgrid(icv_valores, espera_valores)
        VERDE = np.zeros_like(ICV)

        # Calcular tiempo verde para cada combinación
        for i in range(resolucion):
            for j in range(resolucion):
                resultado = controlador_difuso.calcular(
                    ICV[i, j],
                    ESPERA[i, j]
                )
                VERDE[i, j] = resultado['tiempo_verde']

        # Exportar a MATLAB
        datos_mat = {
            'ICV': ICV,
            'Espera': ESPERA,
            'TiempoVerde': VERDE,
            'resolucion': resolucion,
            'icv_min': 0,
            'icv_max': 1,
            'espera_min': 0,
            'espera_max': 120,
            'verde_min': np.min(VERDE),
            'verde_max': np.max(VERDE),
            'descripcion': 'Superficie de control difuso Mamdani',
            'fecha_exportacion': datetime.now().isoformat()
        }

        ruta_mat = self.carpeta_mat / f'{nombre_archivo}.mat'
        savemat(ruta_mat, datos_mat)
        logger.info(f"Superficie difusa exportada a MATLAB: {ruta_mat}")

        # Generar gráfico 3D si matplotlib está disponible
        if MATPLOTLIB_DISPONIBLE:
            self._graficar_superficie_3d(ICV, ESPERA, VERDE, nombre_archivo)

        return {'archivo_mat': str(ruta_mat)}

    def exportar_analisis_componentes_icv(
        self,
        timestamps: List[float],
        componentes: Dict[str, List[float]],
        nombre_archivo: str = 'componentes_icv'
    ):
        """
        Exporta análisis de componentes del ICV

        Args:
            timestamps: Timestamps en segundos
            componentes: Dict con listas de valores para cada componente
                Ejemplo: {'longitud': [...], 'velocidad': [...], 'flujo': [...], 'densidad': [...]}
            nombre_archivo: Nombre base del archivo
        """
        # Convertir a numpy
        timestamps = np.array(timestamps)
        componentes_np = {k: np.array(v) for k, v in componentes.items()}

        # Exportar a MATLAB
        datos_mat = {
            'timestamps': timestamps,
            **componentes_np,
            'num_puntos': len(timestamps),
            'componentes': list(componentes.keys()),
            'fecha_exportacion': datetime.now().isoformat()
        }

        # Agregar estadísticas
        for nombre, valores in componentes_np.items():
            datos_mat[f'{nombre}_promedio'] = np.mean(valores) if len(valores) > 0 else 0
            datos_mat[f'{nombre}_std'] = np.std(valores) if len(valores) > 0 else 0

        ruta_mat = self.carpeta_mat / f'{nombre_archivo}.mat'
        savemat(ruta_mat, datos_mat)
        logger.info(f"Componentes ICV exportadas a MATLAB: {ruta_mat}")

        # Exportar a CSV
        ruta_csv = self.carpeta_csv / f'{nombre_archivo}.csv'
        with open(ruta_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['Timestamp_s'] + list(componentes.keys())
            writer.writerow(header)

            for i, t in enumerate(timestamps):
                row = [f"{t:.2f}"] + [f"{componentes[k][i]:.4f}" for k in componentes.keys()]
                writer.writerow(row)

        logger.info(f"Componentes ICV exportadas a CSV: {ruta_csv}")

        # Generar gráfico comparativo si matplotlib está disponible
        if MATPLOTLIB_DISPONIBLE:
            self._graficar_componentes(timestamps, componentes, nombre_archivo)

        return {
            'archivo_mat': str(ruta_mat),
            'archivo_csv': str(ruta_csv)
        }

    def exportar_metricas_red(
        self,
        timestamps: List[float],
        metricas: Dict[str, List[float]],
        nombre_archivo: str = 'metricas_red_cap6'
    ):
        """
        Exporta métricas de red del Capítulo 6.3.4

        Args:
            timestamps: Timestamps en segundos
            metricas: Dict con métricas de red (QL_red, Vavg_red, q_red, k_red, ICV_red, PI_red)
            nombre_archivo: Nombre base del archivo
        """
        return self.exportar_analisis_componentes_icv(timestamps, metricas, nombre_archivo)

    def generar_informe_completo(
        self,
        datos_icv: Dict,
        datos_fuzzy: Dict,
        datos_red: Optional[Dict] = None,
        nombre_informe: str = 'informe_tesis'
    ):
        """
        Genera informe completo con todos los análisis

        Args:
            datos_icv: Datos de ICV (timestamps, valores, componentes)
            datos_fuzzy: Datos del controlador difuso
            datos_red: Datos de métricas de red (opcional)
            nombre_informe: Nombre base del informe
        """
        informe = {
            'fecha_generacion': datetime.now().isoformat(),
            'descripcion': 'Informe completo para tesis - Sistema de Control Semafórico Adaptativo',
            'capitulo': 'Capitulo 6 - Implementacion y Resultados',
            'archivos_generados': []
        }

        # Exportar ICV
        if 'timestamps' in datos_icv and 'valores' in datos_icv:
            resultado_icv = self.exportar_serie_temporal_icv(
                datos_icv['timestamps'],
                datos_icv['valores'],
                f'{nombre_informe}_icv'
            )
            informe['archivos_generados'].append(resultado_icv)

        # Exportar componentes ICV
        if 'componentes' in datos_icv:
            resultado_comp = self.exportar_analisis_componentes_icv(
                datos_icv['timestamps'],
                datos_icv['componentes'],
                f'{nombre_informe}_componentes'
            )
            informe['archivos_generados'].append(resultado_comp)

        # Exportar métricas de red
        if datos_red and 'timestamps' in datos_red and 'metricas' in datos_red:
            resultado_red = self.exportar_metricas_red(
                datos_red['timestamps'],
                datos_red['metricas'],
                f'{nombre_informe}_red'
            )
            informe['archivos_generados'].append(resultado_red)

        # Guardar informe
        ruta_informe = self.carpeta_salida / f'{nombre_informe}_resumen.txt'
        with open(ruta_informe, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("INFORME DE ANALISIS - SISTEMA DE CONTROL SEMÁFORICO\n")
            f.write("="*70 + "\n\n")
            f.write(f"Fecha: {informe['fecha_generacion']}\n")
            f.write(f"Descripción: {informe['descripcion']}\n\n")
            f.write(f"Archivos generados: {len(informe['archivos_generados'])}\n\n")

            for i, archivo in enumerate(informe['archivos_generados'], 1):
                f.write(f"{i}. {archivo.get('archivo_mat', 'N/A')}\n")

        logger.info(f"Informe completo generado: {ruta_informe}")
        return informe

    # Métodos auxiliares

    @staticmethod
    def _clasificar_icv(icv: float) -> str:
        """Clasifica ICV"""
        if icv < 0.3:
            return 'bajo'
        elif icv < 0.6:
            return 'medio'
        else:
            return 'alto'

    def _graficar_serie_temporal_icv(
        self,
        timestamps: np.ndarray,
        valores_icv: np.ndarray,
        nombre_archivo: str
    ):
        """Genera gráfico de serie temporal de ICV"""
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(timestamps, valores_icv, linewidth=2, color='#2E86DE')
        ax.fill_between(timestamps, 0, valores_icv, alpha=0.3, color='#2E86DE')

        # Líneas de referencia
        ax.axhline(y=0.3, color='green', linestyle='--', alpha=0.5, label='Umbral Bajo-Medio')
        ax.axhline(y=0.6, color='orange', linestyle='--', alpha=0.5, label='Umbral Medio-Alto')

        ax.set_xlabel('Tiempo (s)', fontsize=12)
        ax.set_ylabel('ICV', fontsize=12)
        ax.set_title('Serie Temporal del Índice de Congestión Vehicular (ICV)', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_ylim([0, 1])

        ruta_fig = self.carpeta_figuras / f'{nombre_archivo}.png'
        plt.savefig(ruta_fig, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Gráfico ICV generado: {ruta_fig}")

    def _graficar_superficie_3d(
        self,
        ICV: np.ndarray,
        ESPERA: np.ndarray,
        VERDE: np.ndarray,
        nombre_archivo: str
    ):
        """Genera gráfico 3D de superficie de control difuso"""
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        surf = ax.plot_surface(ICV, ESPERA, VERDE, cmap='viridis', alpha=0.9)

        ax.set_xlabel('ICV', fontsize=12)
        ax.set_ylabel('Tiempo de Espera (s)', fontsize=12)
        ax.set_zlabel('Tiempo Verde (s)', fontsize=12)
        ax.set_title('Superficie de Control Difuso Mamdani', fontsize=14, fontweight='bold')

        fig.colorbar(surf, shrink=0.5, aspect=5, label='Tiempo Verde (s)')

        ruta_fig = self.carpeta_figuras / f'{nombre_archivo}.png'
        plt.savefig(ruta_fig, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Gráfico superficie 3D generado: {ruta_fig}")

    def _graficar_componentes(
        self,
        timestamps: np.ndarray,
        componentes: Dict[str, np.ndarray],
        nombre_archivo: str
    ):
        """Genera gráfico comparativo de componentes"""
        fig, axes = plt.subplots(len(componentes), 1, figsize=(12, 3*len(componentes)), sharex=True)

        if len(componentes) == 1:
            axes = [axes]

        for ax, (nombre, valores) in zip(axes, componentes.items()):
            ax.plot(timestamps, valores, linewidth=2)
            ax.set_ylabel(nombre.capitalize(), fontsize=11)
            ax.grid(True, alpha=0.3)
            ax.fill_between(timestamps, 0, valores, alpha=0.2)

        axes[-1].set_xlabel('Tiempo (s)', fontsize=12)
        fig.suptitle('Análisis de Componentes del ICV', fontsize=14, fontweight='bold')

        ruta_fig = self.carpeta_figuras / f'{nombre_archivo}.png'
        plt.tight_layout()
        plt.savefig(ruta_fig, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Gráfico componentes generado: {ruta_fig}")


# Ejemplo de uso
if __name__ == "__main__":
    # Crear exportador
    exportador = ExportadorAnalisis()

    # Simular datos de prueba
    timestamps = np.linspace(0, 300, 100)  # 5 minutos
    icv_valores = 0.3 + 0.3 * np.sin(timestamps / 30) + 0.1 * np.random.randn(100)
    icv_valores = np.clip(icv_valores, 0, 1)

    # Exportar serie temporal
    resultado = exportador.exportar_serie_temporal_icv(
        timestamps.tolist(),
        icv_valores.tolist(),
        'ejemplo_icv_test'
    )

    print("\n=== EXPORTACION COMPLETADA ===")
    print(f"Archivo MATLAB: {resultado['archivo_mat']}")
    print(f"Archivo CSV: {resultado['archivo_csv']}")
    print(f"Puntos exportados: {resultado['num_puntos']}")
    print(f"\nEstadísticas:")
    for clave, valor in resultado['estadisticas'].items():
        print(f"  {clave}: {valor:.4f}")
