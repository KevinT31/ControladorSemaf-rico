# -*- coding: utf-8 -*-
"""
Sistema de Comparación: Control Adaptativo vs Control de Tiempo Fijo
Capítulo 6 - Demostración de Mejoras

Permite ejecutar simulaciones paralelas con control adaptativo y sin él,
comparando las métricas de rendimiento para demostrar la efectividad del
sistema propuesto en la tesis.

Métricas comparadas:
- ICV (Índice de Congestión Vehicular)
- Tiempo de espera promedio
- Velocidad promedio
- Flujo vehicular
- Número de paradas
- Throughput de la red
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import json
import logging
from enum import Enum

from metricas_red import (
    MetricasInterseccion,
    MetricasRed,
    ConfiguracionInterseccion,
    AgregadorMetricasRed
)

logger = logging.getLogger(__name__)


class TipoControl(Enum):
    """Tipos de control para comparación"""
    ADAPTATIVO = "adaptativo"
    TIEMPO_FIJO = "tiempo_fijo"
    ACTUADO = "actuado"  # Control actuado tradicional


@dataclass
class ParametrosControlFijo:
    """
    Parámetros para control de tiempo fijo tradicional
    """
    T_verde_ns: float = 30.0  # Tiempo verde fijo NS (segundos)
    T_verde_eo: float = 30.0  # Tiempo verde fijo EO (segundos)
    T_ambar: float = 3.0      # Tiempo ámbar (segundos)
    T_todo_rojo: float = 2.0  # Tiempo todo rojo (segundos)
    T_ciclo: float = 90.0     # Ciclo total (segundos)


@dataclass
class ResultadosComparacion:
    """
    Resultados de una simulación de comparación
    """
    tipo_control: TipoControl
    duracion_simulacion: float  # Segundos
    timestamp_inicio: datetime
    timestamp_fin: datetime

    # Métricas agregadas
    icv_promedio: float = 0.0
    icv_desviacion: float = 0.0
    vavg_promedio: float = 0.0
    vavg_desviacion: float = 0.0
    q_promedio: float = 0.0
    q_desviacion: float = 0.0
    tiempo_espera_promedio: float = 0.0
    num_paradas_total: int = 0
    throughput_red: float = 0.0  # Vehículos procesados

    # Distribución temporal
    porcentaje_tiempo_fluido: float = 0.0      # ICV < 0.3
    porcentaje_tiempo_moderado: float = 0.0    # 0.3 ≤ ICV < 0.6
    porcentaje_tiempo_congestionado: float = 0.0  # ICV ≥ 0.6

    # Series temporales (para gráficas)
    serie_icv: List[float] = field(default_factory=list)
    serie_vavg: List[float] = field(default_factory=list)
    serie_timestamps: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización"""
        return {
            'tipo_control': self.tipo_control.value,
            'duracion_simulacion': self.duracion_simulacion,
            'timestamp_inicio': self.timestamp_inicio.isoformat(),
            'timestamp_fin': self.timestamp_fin.isoformat(),
            'metricas_promedio': {
                'icv': {
                    'promedio': round(self.icv_promedio, 4),
                    'desviacion': round(self.icv_desviacion, 4)
                },
                'velocidad': {
                    'promedio': round(self.vavg_promedio, 2),
                    'desviacion': round(self.vavg_desviacion, 2)
                },
                'flujo': {
                    'promedio': round(self.q_promedio, 2),
                    'desviacion': round(self.q_desviacion, 2)
                },
                'tiempo_espera_promedio': round(self.tiempo_espera_promedio, 2),
                'num_paradas_total': self.num_paradas_total,
                'throughput_red': round(self.throughput_red, 2)
            },
            'distribucion_temporal': {
                'fluido': round(self.porcentaje_tiempo_fluido, 2),
                'moderado': round(self.porcentaje_tiempo_moderado, 2),
                'congestionado': round(self.porcentaje_tiempo_congestionado, 2)
            },
            'series_temporales': {
                'timestamps': self.serie_timestamps,
                'icv': [round(v, 4) for v in self.serie_icv],
                'vavg': [round(v, 2) for v in self.serie_vavg]
            }
        }


@dataclass
class InformeMejoras:
    """
    Informe de mejoras comparando dos estrategias de control
    """
    tipo_control_base: TipoControl  # Control de referencia (típicamente tiempo fijo)
    tipo_control_propuesto: TipoControl  # Control propuesto (adaptativo)

    # Mejoras porcentuales (positivo = mejora)
    mejora_icv: float = 0.0  # Reducción en ICV (%)
    mejora_velocidad: float = 0.0  # Aumento en velocidad (%)
    mejora_flujo: float = 0.0  # Aumento en flujo (%)
    mejora_tiempo_espera: float = 0.0  # Reducción en tiempo de espera (%)
    mejora_paradas: float = 0.0  # Reducción en número de paradas (%)
    mejora_throughput: float = 0.0  # Aumento en throughput (%)

    # Nivel de significancia
    mejora_significativa: bool = False  # True si mejora > 5%

    # Resultados completos
    resultados_base: Optional[ResultadosComparacion] = None
    resultados_propuesto: Optional[ResultadosComparacion] = None

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización"""
        return {
            'tipo_control_base': self.tipo_control_base.value,
            'tipo_control_propuesto': self.tipo_control_propuesto.value,
            'mejoras_porcentuales': {
                'icv': round(self.mejora_icv, 2),
                'velocidad': round(self.mejora_velocidad, 2),
                'flujo': round(self.mejora_flujo, 2),
                'tiempo_espera': round(self.mejora_tiempo_espera, 2),
                'paradas': round(self.mejora_paradas, 2),
                'throughput': round(self.mejora_throughput, 2)
            },
            'mejora_significativa': self.mejora_significativa,
            'resumen': self.generar_resumen_textual()
        }

    def generar_resumen_textual(self) -> str:
        """Genera un resumen textual de las mejoras"""
        lineas = []
        lineas.append(f"Comparación: {self.tipo_control_propuesto.value.upper()} vs {self.tipo_control_base.value.upper()}")
        lineas.append("")
        lineas.append("Mejoras observadas:")

        if self.mejora_icv > 0:
            lineas.append(f"  ✓ Reducción de congestión (ICV): {self.mejora_icv:.1f}%")
        else:
            lineas.append(f"  ✗ Incremento de congestión (ICV): {abs(self.mejora_icv):.1f}%")

        if self.mejora_velocidad > 0:
            lineas.append(f"  ✓ Aumento de velocidad: {self.mejora_velocidad:.1f}%")
        else:
            lineas.append(f"  ✗ Reducción de velocidad: {abs(self.mejora_velocidad):.1f}%")

        if self.mejora_tiempo_espera > 0:
            lineas.append(f"  ✓ Reducción de tiempo de espera: {self.mejora_tiempo_espera:.1f}%")

        if self.mejora_throughput > 0:
            lineas.append(f"  ✓ Aumento de throughput: {self.mejora_throughput:.1f}%")

        lineas.append("")
        if self.mejora_significativa:
            lineas.append("🎯 MEJORA SIGNIFICATIVA detectada (>5%)")
        else:
            lineas.append("⚠️  Mejora marginal (<5%)")

        return "\n".join(lineas)


class SistemaComparacion:
    """
    Sistema para comparar diferentes estrategias de control semafórico
    y demostrar la efectividad del control adaptativo
    """

    def __init__(
        self,
        configuraciones_intersecciones: List[ConfiguracionInterseccion],
        directorio_resultados: Optional[Path] = None
    ):
        """
        Args:
            configuraciones_intersecciones: Configuraciones de las intersecciones
            directorio_resultados: Directorio para guardar resultados
        """
        self.configuraciones = configuraciones_intersecciones
        self.directorio_resultados = directorio_resultados

        # Historial de simulaciones
        self.simulaciones: Dict[str, ResultadosComparacion] = {}

        logger.info(f"SistemaComparacion inicializado con {len(configuraciones_intersecciones)} intersecciones")

    def analizar_resultados(
        self,
        metricas_red: List[MetricasRed],
        tipo_control: TipoControl,
        id_simulacion: str
    ) -> ResultadosComparacion:
        """
        Analiza los resultados de una simulación

        Args:
            metricas_red: Lista de métricas de red recopiladas
            tipo_control: Tipo de control usado
            id_simulacion: Identificador de la simulación

        Returns:
            Resultados analizados
        """
        if not metricas_red:
            raise ValueError("No hay métricas para analizar")

        timestamp_inicio = metricas_red[0].timestamp
        timestamp_fin = metricas_red[-1].timestamp
        duracion = (timestamp_fin - timestamp_inicio).total_seconds()

        # Extraer series temporales
        serie_icv = [m.ICV_red for m in metricas_red]
        serie_vavg = [m.Vavg_red for m in metricas_red]
        serie_q = [m.q_red for m in metricas_red]
        serie_timestamps = [m.timestamp.isoformat() for m in metricas_red]

        # Calcular promedios y desviaciones
        icv_promedio = float(np.mean(serie_icv))
        icv_desviacion = float(np.std(serie_icv))
        vavg_promedio = float(np.mean(serie_vavg))
        vavg_desviacion = float(np.std(serie_vavg))
        q_promedio = float(np.mean(serie_q))
        q_desviacion = float(np.std(serie_q))

        # Calcular distribución temporal de estados
        num_total = len(serie_icv)
        num_fluido = sum(1 for icv in serie_icv if icv < 0.3)
        num_moderado = sum(1 for icv in serie_icv if 0.3 <= icv < 0.6)
        num_congestionado = sum(1 for icv in serie_icv if icv >= 0.6)

        porcentaje_fluido = (num_fluido / num_total) * 100 if num_total > 0 else 0
        porcentaje_moderado = (num_moderado / num_total) * 100 if num_total > 0 else 0
        porcentaje_congestionado = (num_congestionado / num_total) * 100 if num_total > 0 else 0

        # Estimar tiempo de espera (simplificado)
        # Tiempo_espera ≈ (ICV * T_ciclo) / 2
        tiempo_espera_promedio = (icv_promedio * 90.0) / 2.0  # Asumiendo ciclo de 90s

        # Estimar throughput (vehículos procesados)
        throughput = q_promedio * duracion / 60.0  # flujo (veh/min) * tiempo (min)

        # Crear resultados
        resultados = ResultadosComparacion(
            tipo_control=tipo_control,
            duracion_simulacion=duracion,
            timestamp_inicio=timestamp_inicio,
            timestamp_fin=timestamp_fin,
            icv_promedio=icv_promedio,
            icv_desviacion=icv_desviacion,
            vavg_promedio=vavg_promedio,
            vavg_desviacion=vavg_desviacion,
            q_promedio=q_promedio,
            q_desviacion=q_desviacion,
            tiempo_espera_promedio=tiempo_espera_promedio,
            throughput_red=throughput,
            porcentaje_tiempo_fluido=porcentaje_fluido,
            porcentaje_tiempo_moderado=porcentaje_moderado,
            porcentaje_tiempo_congestionado=porcentaje_congestionado,
            serie_icv=serie_icv,
            serie_vavg=serie_vavg,
            serie_timestamps=serie_timestamps
        )

        # Guardar en historial
        self.simulaciones[id_simulacion] = resultados

        logger.info(f"Simulación '{id_simulacion}' analizada: ICV={icv_promedio:.3f}, Vavg={vavg_promedio:.1f} km/h")

        return resultados

    def comparar_estrategias(
        self,
        id_simulacion_base: str,
        id_simulacion_propuesta: str
    ) -> InformeMejoras:
        """
        Compara dos estrategias de control

        Args:
            id_simulacion_base: ID de la simulación de referencia (tiempo fijo)
            id_simulacion_propuesta: ID de la simulación propuesta (adaptativo)

        Returns:
            Informe de mejoras
        """
        if id_simulacion_base not in self.simulaciones:
            raise ValueError(f"Simulación base '{id_simulacion_base}' no encontrada")
        if id_simulacion_propuesta not in self.simulaciones:
            raise ValueError(f"Simulación propuesta '{id_simulacion_propuesta}' no encontrada")

        resultados_base = self.simulaciones[id_simulacion_base]
        resultados_propuesto = self.simulaciones[id_simulacion_propuesta]

        # Calcular mejoras porcentuales
        def calcular_mejora_porcentual(valor_nuevo, valor_base, inverso=False):
            """
            Calcula mejora porcentual
            inverso=True para métricas donde menor es mejor (ICV, tiempo_espera)
            """
            if valor_base == 0:
                return 0.0
            cambio = ((valor_nuevo - valor_base) / valor_base) * 100
            return -cambio if inverso else cambio

        mejora_icv = calcular_mejora_porcentual(
            resultados_propuesto.icv_promedio,
            resultados_base.icv_promedio,
            inverso=True
        )

        mejora_velocidad = calcular_mejora_porcentual(
            resultados_propuesto.vavg_promedio,
            resultados_base.vavg_promedio
        )

        mejora_flujo = calcular_mejora_porcentual(
            resultados_propuesto.q_promedio,
            resultados_base.q_promedio
        )

        mejora_tiempo_espera = calcular_mejora_porcentual(
            resultados_propuesto.tiempo_espera_promedio,
            resultados_base.tiempo_espera_promedio,
            inverso=True
        )

        mejora_throughput = calcular_mejora_porcentual(
            resultados_propuesto.throughput_red,
            resultados_base.throughput_red
        )

        # Determinar si la mejora es significativa (>5% en ICV o velocidad)
        mejora_significativa = (mejora_icv > 5.0) or (mejora_velocidad > 5.0)

        # Crear informe
        informe = InformeMejoras(
            tipo_control_base=resultados_base.tipo_control,
            tipo_control_propuesto=resultados_propuesto.tipo_control,
            mejora_icv=mejora_icv,
            mejora_velocidad=mejora_velocidad,
            mejora_flujo=mejora_flujo,
            mejora_tiempo_espera=mejora_tiempo_espera,
            mejora_throughput=mejora_throughput,
            mejora_significativa=mejora_significativa,
            resultados_base=resultados_base,
            resultados_propuesto=resultados_propuesto
        )

        logger.info(f"Comparación completada: {informe.generar_resumen_textual()}")

        return informe

    def exportar_comparacion(
        self,
        informe: InformeMejoras,
        archivo_salida: Path
    ) -> bool:
        """
        Exporta un informe de comparación a JSON

        Args:
            informe: Informe a exportar
            archivo_salida: Ruta del archivo de salida

        Returns:
            True si se exportó correctamente
        """
        try:
            datos_exportacion = {
                'metadata': {
                    'fecha_generacion': datetime.now().isoformat(),
                    'tipo_comparacion': 'adaptativo_vs_tiempo_fijo'
                },
                'informe_mejoras': informe.to_dict(),
                'resultados_base': informe.resultados_base.to_dict() if informe.resultados_base else None,
                'resultados_propuesto': informe.resultados_propuesto.to_dict() if informe.resultados_propuesto else None
            }

            archivo_salida.parent.mkdir(parents=True, exist_ok=True)
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump(datos_exportacion, f, indent=2, ensure_ascii=False)

            logger.info(f"Informe exportado a {archivo_salida}")
            return True

        except Exception as e:
            logger.error(f"Error exportando informe: {e}")
            return False

    def generar_reporte_html(
        self,
        informe: InformeMejoras,
        archivo_salida: Path
    ) -> bool:
        """
        Genera un reporte HTML con gráficas de comparación

        Args:
            informe: Informe a exportar
            archivo_salida: Ruta del archivo HTML de salida

        Returns:
            True si se generó correctamente
        """
        try:
            html_template = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe de Comparación - Control Semafórico</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric {{
            display: inline-block;
            width: 45%;
            margin: 10px 2%;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }}
        .metric.positive {{
            border-left-color: #22c55e;
        }}
        .metric.negative {{
            border-left-color: #ef4444;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .improvement {{
            font-size: 16px;
            margin-top: 5px;
        }}
        .improvement.positive {{
            color: #22c55e;
        }}
        .improvement.negative {{
            color: #ef4444;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: bold;
        }}
        .badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge.success {{
            background: #22c55e;
            color: white;
        }}
        .badge.warning {{
            background: #f59e0b;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Informe de Comparación: Control Semafórico Adaptativo</h1>
        <p>Sistema de Control Inteligente con Lógica Difusa vs Control de Tiempo Fijo</p>
        <p style="opacity: 0.9; font-size: 14px;">Generado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="section">
        <h2>🎯 Resumen Ejecutivo</h2>
        <p><strong>Control Base:</strong> {informe.tipo_control_base.value.upper()}</p>
        <p><strong>Control Propuesto:</strong> {informe.tipo_control_propuesto.value.upper()}</p>

        {'<p class="badge success">✓ MEJORA SIGNIFICATIVA (>5%)</p>' if informe.mejora_significativa else '<p class="badge warning">⚠ Mejora marginal (<5%)</p>'}
    </div>

    <div class="section">
        <h2>📈 Mejoras Observadas</h2>

        <div class="metric {'positive' if informe.mejora_icv > 0 else 'negative'}">
            <div class="metric-label">Reducción de Congestión (ICV)</div>
            <div class="metric-value">{abs(informe.mejora_icv):.1f}%</div>
            <div class="improvement {'positive' if informe.mejora_icv > 0 else 'negative'}">
                {'↓ Mejora' if informe.mejora_icv > 0 else '↑ Deterioro'}
            </div>
        </div>

        <div class="metric {'positive' if informe.mejora_velocidad > 0 else 'negative'}">
            <div class="metric-label">Aumento de Velocidad Promedio</div>
            <div class="metric-value">{abs(informe.mejora_velocidad):.1f}%</div>
            <div class="improvement {'positive' if informe.mejora_velocidad > 0 else 'negative'}">
                {'↑ Mejora' if informe.mejora_velocidad > 0 else '↓ Deterioro'}
            </div>
        </div>

        <div class="metric {'positive' if informe.mejora_flujo > 0 else 'negative'}">
            <div class="metric-label">Aumento de Flujo Vehicular</div>
            <div class="metric-value">{abs(informe.mejora_flujo):.1f}%</div>
            <div class="improvement {'positive' if informe.mejora_flujo > 0 else 'negative'}">
                {'↑ Mejora' if informe.mejora_flujo > 0 else '↓ Deterioro'}
            </div>
        </div>

        <div class="metric {'positive' if informe.mejora_tiempo_espera > 0 else 'negative'}">
            <div class="metric-label">Reducción de Tiempo de Espera</div>
            <div class="metric-value">{abs(informe.mejora_tiempo_espera):.1f}%</div>
            <div class="improvement {'positive' if informe.mejora_tiempo_espera > 0 else 'negative'}">
                {'↓ Mejora' if informe.mejora_tiempo_espera > 0 else '↑ Deterioro'}
            </div>
        </div>
    </div>

    <div class="section">
        <h2>📊 Comparación Detallada</h2>
        <table>
            <thead>
                <tr>
                    <th>Métrica</th>
                    <th>Control Fijo</th>
                    <th>Control Adaptativo</th>
                    <th>Mejora</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>ICV Promedio</td>
                    <td>{informe.resultados_base.icv_promedio:.3f}</td>
                    <td>{informe.resultados_propuesto.icv_promedio:.3f}</td>
                    <td class="improvement {'positive' if informe.mejora_icv > 0 else 'negative'}">{informe.mejora_icv:+.1f}%</td>
                </tr>
                <tr>
                    <td>Velocidad Promedio (km/h)</td>
                    <td>{informe.resultados_base.vavg_promedio:.1f}</td>
                    <td>{informe.resultados_propuesto.vavg_promedio:.1f}</td>
                    <td class="improvement {'positive' if informe.mejora_velocidad > 0 else 'negative'}">{informe.mejora_velocidad:+.1f}%</td>
                </tr>
                <tr>
                    <td>Flujo Promedio (veh/min)</td>
                    <td>{informe.resultados_base.q_promedio:.1f}</td>
                    <td>{informe.resultados_propuesto.q_promedio:.1f}</td>
                    <td class="improvement {'positive' if informe.mejora_flujo > 0 else 'negative'}">{informe.mejora_flujo:+.1f}%</td>
                </tr>
                <tr>
                    <td>Tiempo Espera Prom. (s)</td>
                    <td>{informe.resultados_base.tiempo_espera_promedio:.1f}</td>
                    <td>{informe.resultados_propuesto.tiempo_espera_promedio:.1f}</td>
                    <td class="improvement {'positive' if informe.mejora_tiempo_espera > 0 else 'negative'}">{informe.mejora_tiempo_espera:+.1f}%</td>
                </tr>
                <tr>
                    <td>Throughput (veh)</td>
                    <td>{informe.resultados_base.throughput_red:.0f}</td>
                    <td>{informe.resultados_propuesto.throughput_red:.0f}</td>
                    <td class="improvement {'positive' if informe.mejora_throughput > 0 else 'negative'}">{informe.mejora_throughput:+.1f}%</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>⏱️ Distribución Temporal de Estados</h2>
        <h3>Control de Tiempo Fijo:</h3>
        <p>Fluido: {informe.resultados_base.porcentaje_tiempo_fluido:.1f}% |
           Moderado: {informe.resultados_base.porcentaje_tiempo_moderado:.1f}% |
           Congestionado: {informe.resultados_base.porcentaje_tiempo_congestionado:.1f}%</p>

        <h3>Control Adaptativo:</h3>
        <p>Fluido: {informe.resultados_propuesto.porcentaje_tiempo_fluido:.1f}% |
           Moderado: {informe.resultados_propuesto.porcentaje_tiempo_moderado:.1f}% |
           Congestionado: {informe.resultados_propuesto.porcentaje_tiempo_congestionado:.1f}%</p>
    </div>

    <div class="section">
        <h2>💡 Conclusiones</h2>
        <p>{informe.generar_resumen_textual().replace(chr(10), '<br>')}</p>
    </div>
</body>
</html>
            """

            archivo_salida.parent.mkdir(parents=True, exist_ok=True)
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                f.write(html_template)

            logger.info(f"Reporte HTML generado: {archivo_salida}")
            return True

        except Exception as e:
            logger.error(f"Error generando reporte HTML: {e}")
            return False


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    import random

    print("\n" + "="*70)
    print("SISTEMA DE COMPARACIÓN: ADAPTATIVO VS TIEMPO FIJO")
    print("Demostración de Mejoras del Control Inteligente")
    print("="*70 + "\n")

    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Configurar intersecciones
    configuraciones = [
        ConfiguracionInterseccion(
            id="I001",
            nombre="Av. Arequipa - Javier Prado",
            peso=1.5,
            es_critica=True
        ),
        ConfiguracionInterseccion(
            id="I002",
            nombre="Av. Brasil - Venezuela",
            peso=1.0
        )
    ]

    # Crear sistema de comparación
    sistema = SistemaComparacion(
        configuraciones_intersecciones=configuraciones,
        directorio_resultados=Path("./resultados_comparacion")
    )

    # Simular métricas para CONTROL DE TIEMPO FIJO
    print("📊 Simulando Control de Tiempo Fijo...")
    metricas_tiempo_fijo = []
    for i in range(100):
        # Tiempo fijo tiende a tener más congestión
        icv_base = 0.5 + random.uniform(-0.2, 0.3)
        metricas = MetricasRed(
            timestamp=datetime.now() + timedelta(seconds=i),
            ICV_red=min(max(icv_base, 0.0), 1.0),
            Vavg_red=25.0 + random.uniform(-10, 10),
            q_red=15.0 + random.uniform(-5, 5),
            QL_red=0.6 + random.uniform(-0.2, 0.3),
            num_intersecciones=len(configuraciones)
        )
        metricas_tiempo_fijo.append(metricas)

    # Analizar resultados tiempo fijo
    resultado_fijo = sistema.analizar_resultados(
        metricas_tiempo_fijo,
        TipoControl.TIEMPO_FIJO,
        "simulacion_tiempo_fijo"
    )

    # Simular métricas para CONTROL ADAPTATIVO
    print("📊 Simulando Control Adaptativo...")
    metricas_adaptativo = []
    for i in range(100):
        # Control adaptativo es más eficiente
        icv_adapt = 0.35 + random.uniform(-0.2, 0.2)
        metricas = MetricasRed(
            timestamp=datetime.now() + timedelta(seconds=i),
            ICV_red=min(max(icv_adapt, 0.0), 1.0),
            Vavg_red=35.0 + random.uniform(-8, 8),
            q_red=20.0 + random.uniform(-4, 4),
            QL_red=0.4 + random.uniform(-0.2, 0.2),
            num_intersecciones=len(configuraciones)
        )
        metricas_adaptativo.append(metricas)

    # Analizar resultados adaptativo
    resultado_adapt = sistema.analizar_resultados(
        metricas_adaptativo,
        TipoControl.ADAPTATIVO,
        "simulacion_adaptativo"
    )

    # Comparar estrategias
    print("\n🔍 Generando comparación...")
    informe = sistema.comparar_estrategias(
        "simulacion_tiempo_fijo",
        "simulacion_adaptativo"
    )

    # Mostrar resultados
    print("\n" + "="*70)
    print("RESULTADOS DE LA COMPARACIÓN")
    print("="*70 + "\n")
    print(informe.generar_resumen_textual())
    print("\n" + "="*70 + "\n")

    # Exportar resultados
    dir_resultados = Path("./resultados_comparacion")
    dir_resultados.mkdir(exist_ok=True)

    # Exportar JSON
    archivo_json = dir_resultados / "comparacion_resultados.json"
    sistema.exportar_comparacion(informe, archivo_json)
    print(f"✅ Resultados exportados a: {archivo_json}")

    # Generar reporte HTML
    archivo_html = dir_resultados / "reporte_comparacion.html"
    sistema.generar_reporte_html(informe, archivo_html)
    print(f"✅ Reporte HTML generado: {archivo_html}")

    print("\n" + "="*70)
    print("✓ Comparación completada exitosamente")
    print("="*70 + "\n")
