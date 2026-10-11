# -*- coding: utf-8 -*-
"""
Sistema de Métricas de Red Global
Capítulo 6 - Sección 6.4: Métricas a Nivel de Red

Implementa el sistema de agregación de métricas de toda la red de intersecciones
sin dependencia de Azure (versión local para demostración de tesis).

Métricas calculadas:
- QL_red: Índice de Saturación de Colas de la Red
- Vavg_red: Velocidad Promedio de la Red
- q_red: Flujo Promedio de la Red
- k_red: Densidad Promedio de la Red
- ICV_red: Índice de Congestión Ponderado de la Red
- PI_red: Parámetro de Intensidad Promedio de la Red
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import deque
import numpy as np
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricasInterseccion:
    """
    Métricas de una intersección individual en un instante de tiempo
    """
    interseccion_id: str
    timestamp: datetime

    # Métricas de cada dirección (NS y EO)
    sc_ns: float = 0.0
    sc_eo: float = 0.0
    vavg_ns: float = 0.0
    vavg_eo: float = 0.0
    q_ns: float = 0.0
    q_eo: float = 0.0
    k_ns: float = 0.0
    k_eo: float = 0.0
    icv_ns: float = 0.0
    icv_eo: float = 0.0
    pi_ns: float = 0.0
    pi_eo: float = 0.0
    ev_ns: int = 0
    ev_eo: int = 0

    # Tiempos de verde actuales
    T_verde_ns: float = 30.0
    T_verde_eo: float = 30.0

    # Estado del semáforo
    fase_actual: str = "NS_VERDE"  # NS_VERDE, EO_VERDE, AMBAR, TODO_ROJO

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización"""
        return {
            'interseccion_id': self.interseccion_id,
            'timestamp': self.timestamp.isoformat(),
            'sc_ns': self.sc_ns,
            'sc_eo': self.sc_eo,
            'vavg_ns': self.vavg_ns,
            'vavg_eo': self.vavg_eo,
            'q_ns': self.q_ns,
            'q_eo': self.q_eo,
            'k_ns': self.k_ns,
            'k_eo': self.k_eo,
            'icv_ns': self.icv_ns,
            'icv_eo': self.icv_eo,
            'pi_ns': self.pi_ns,
            'pi_eo': self.pi_eo,
            'ev_ns': self.ev_ns,
            'ev_eo': self.ev_eo,
            'T_verde_ns': self.T_verde_ns,
            'T_verde_eo': self.T_verde_eo,
            'fase_actual': self.fase_actual
        }


@dataclass
class MetricasRed:
    """
    Métricas agregadas de toda la red en un instante de tiempo
    """
    timestamp: datetime

    # Métricas de red ponderadas
    QL_red: float = 0.0      # Saturación de colas de la red
    Vavg_red: float = 0.0    # Velocidad promedio de la red
    q_red: float = 0.0       # Flujo promedio de la red
    k_red: float = 0.0       # Densidad promedio de la red
    ICV_red: float = 0.0     # Índice de congestión de la red
    PI_red: float = 0.0      # Parámetro de intensidad de la red

    # Estadísticas adicionales
    num_intersecciones: int = 0
    num_emergencias_activas: int = 0

    # Distribución de estados
    intersecciones_libres: int = 0      # ICV < 0.3
    intersecciones_moderadas: int = 0   # 0.3 ≤ ICV < 0.6
    intersecciones_congestionadas: int = 0  # ICV ≥ 0.6

    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'QL_red': round(self.QL_red, 4),
            'Vavg_red': round(self.Vavg_red, 2),
            'q_red': round(self.q_red, 2),
            'k_red': round(self.k_red, 4),
            'ICV_red': round(self.ICV_red, 4),
            'PI_red': round(self.PI_red, 4),
            'num_intersecciones': self.num_intersecciones,
            'num_emergencias_activas': self.num_emergencias_activas,
            'intersecciones_libres': self.intersecciones_libres,
            'intersecciones_moderadas': self.intersecciones_moderadas,
            'intersecciones_congestionadas': self.intersecciones_congestionadas
        }


@dataclass
class ConfiguracionInterseccion:
    """
    Configuración de una intersección para el cálculo de métricas de red
    """
    id: str
    nombre: str
    peso: float = 1.0  # Peso ωi para métricas ponderadas
    ubicacion: Tuple[float, float] = (0.0, 0.0)  # (latitud, longitud)
    num_carriles_ns: int = 2
    num_carriles_eo: int = 2
    es_critica: bool = False  # Intersección de alta prioridad

    # Parámetros para normalización
    SC_MAX: float = 50.0
    V_MAX: float = 60.0
    q_MAX: float = 30.0
    k_MAX: float = 0.15


class AgregadorMetricasRed:
    """
    Agrega y procesa métricas de múltiples intersecciones para obtener
    métricas a nivel de red.

    Implementa las fórmulas de agregación ponderada del Capítulo 6:
    - QL_red(t) = Σ(ωi · QLi(t))
    - Vavg_red(t) = Σ(ωi · Vavg_i(t))
    - q_red(t) = Σ(ωi · qi(t))
    - k_red(t) = Σ(ωi · ki(t))
    - ICV_red(t) = Σ(ωi · ICVi(t))
    - PI_red(t) = Σ(ωi · PIi(t))
    """

    def __init__(
        self,
        configuraciones: List[ConfiguracionInterseccion],
        ventana_historico: int = 300,  # Segundos de histórico a mantener
        directorio_datos: Optional[Path] = None
    ):
        """
        Args:
            configuraciones: Lista de configuraciones de intersecciones
            ventana_historico: Ventana de tiempo para mantener histórico (segundos)
            directorio_datos: Directorio donde guardar métricas (opcional)
        """
        self.configuraciones = {c.id: c for c in configuraciones}
        self.ventana_historico = ventana_historico
        self.directorio_datos = directorio_datos

        # Normalizar pesos (para que sumen 1)
        suma_pesos = sum(c.peso for c in self.configuraciones.values())
        if suma_pesos > 0:
            for config in self.configuraciones.values():
                config.peso = config.peso / suma_pesos

        # Histórico de métricas por intersección
        self.historico_intersecciones: Dict[str, deque] = {
            id_inter: deque(maxlen=ventana_historico)
            for id_inter in self.configuraciones.keys()
        }

        # Histórico de métricas de red
        self.historico_red: deque = deque(maxlen=ventana_historico)

        # Métricas actuales
        self.metricas_actuales: Dict[str, MetricasInterseccion] = {}
        self.metricas_red_actual: Optional[MetricasRed] = None

        # Comparación adaptativo vs no adaptativo
        self.modo_comparacion = False
        self.historico_no_adaptativo: deque = deque(maxlen=ventana_historico)

        logger.info(f"AgregadorMetricasRed inicializado con {len(self.configuraciones)} intersecciones")
        for id_inter, config in self.configuraciones.items():
            logger.info(f"  - {config.nombre} (peso={config.peso:.3f})")

    def actualizar_metricas_interseccion(self, metricas: MetricasInterseccion):
        """
        Actualiza las métricas de una intersección individual

        Args:
            metricas: Métricas actuales de la intersección
        """
        if metricas.interseccion_id not in self.configuraciones:
            logger.warning(f"Intersección {metricas.interseccion_id} no registrada")
            return

        # Guardar métricas actuales
        self.metricas_actuales[metricas.interseccion_id] = metricas

        # Agregar al histórico
        self.historico_intersecciones[metricas.interseccion_id].append(metricas)

        # Recalcular métricas de red
        self._calcular_metricas_red()

    def _calcular_metricas_red(self):
        """
        Calcula las métricas agregadas de toda la red usando ponderación
        """
        if not self.metricas_actuales:
            return

        timestamp = datetime.now()

        # Inicializar acumuladores
        QL_red = 0.0
        Vavg_red = 0.0
        q_red = 0.0
        k_red = 0.0
        ICV_red = 0.0
        PI_red = 0.0

        num_emergencias = 0
        num_libres = 0
        num_moderadas = 0
        num_congestionadas = 0

        # Agregar métricas ponderadas de cada intersección
        for id_inter, metricas in self.metricas_actuales.items():
            config = self.configuraciones[id_inter]
            peso = config.peso

            # Calcular promedios de ambas direcciones para cada métrica
            # QL (Queue Length) - Saturación de cola normalizada
            sc_promedio = (metricas.sc_ns + metricas.sc_eo) / 2.0
            QL_i = min(sc_promedio / config.SC_MAX, 1.0)

            # Velocidad promedio
            Vavg_i = (metricas.vavg_ns + metricas.vavg_eo) / 2.0

            # Flujo promedio
            q_i = (metricas.q_ns + metricas.q_eo) / 2.0

            # Densidad promedio
            k_i = (metricas.k_ns + metricas.k_eo) / 2.0

            # ICV promedio
            icv_i = (metricas.icv_ns + metricas.icv_eo) / 2.0

            # PI promedio
            pi_i = (metricas.pi_ns + metricas.pi_eo) / 2.0

            # Acumular con peso
            QL_red += peso * QL_i
            Vavg_red += peso * Vavg_i
            q_red += peso * q_i
            k_red += peso * k_i
            ICV_red += peso * icv_i
            PI_red += peso * pi_i

            # Contar emergencias
            num_emergencias += metricas.ev_ns + metricas.ev_eo

            # Clasificar estado de la intersección
            if icv_i < 0.3:
                num_libres += 1
            elif icv_i < 0.6:
                num_moderadas += 1
            else:
                num_congestionadas += 1

        # Crear objeto de métricas de red
        metricas_red = MetricasRed(
            timestamp=timestamp,
            QL_red=QL_red,
            Vavg_red=Vavg_red,
            q_red=q_red,
            k_red=k_red,
            ICV_red=ICV_red,
            PI_red=PI_red,
            num_intersecciones=len(self.metricas_actuales),
            num_emergencias_activas=num_emergencias,
            intersecciones_libres=num_libres,
            intersecciones_moderadas=num_moderadas,
            intersecciones_congestionadas=num_congestionadas
        )

        # Actualizar histórico
        self.metricas_red_actual = metricas_red
        self.historico_red.append(metricas_red)

        # Guardar en disco si está configurado
        if self.directorio_datos:
            self._guardar_metricas(metricas_red)

    def obtener_metricas_red_actual(self) -> Optional[MetricasRed]:
        """
        Obtiene las métricas de red más recientes

        Returns:
            Métricas de red actuales o None si no hay datos
        """
        return self.metricas_red_actual

    def obtener_tendencia(
        self,
        metrica: str,
        ventana_segundos: int = 60
    ) -> Dict[str, float]:
        """
        Calcula la tendencia de una métrica de red

        Args:
            metrica: Nombre de la métrica ('ICV_red', 'Vavg_red', etc.)
            ventana_segundos: Ventana de tiempo a analizar

        Returns:
            Dict con 'valor_actual', 'promedio', 'tendencia' (positiva/negativa)
        """
        if not self.historico_red:
            return {'valor_actual': 0.0, 'promedio': 0.0, 'tendencia': 0.0}

        # Filtrar datos recientes
        ahora = datetime.now()
        datos_recientes = [
            m for m in self.historico_red
            if (ahora - m.timestamp).total_seconds() <= ventana_segundos
        ]

        if not datos_recientes:
            return {'valor_actual': 0.0, 'promedio': 0.0, 'tendencia': 0.0}

        # Extraer valores de la métrica
        valores = [getattr(m, metrica) for m in datos_recientes]

        valor_actual = valores[-1]
        promedio = np.mean(valores)

        # Calcular tendencia (regresión lineal simple)
        if len(valores) >= 2:
            x = np.arange(len(valores))
            y = np.array(valores)
            tendencia = np.polyfit(x, y, 1)[0]  # Pendiente
        else:
            tendencia = 0.0

        return {
            'valor_actual': float(valor_actual),
            'promedio': float(promedio),
            'tendencia': float(tendencia),
            'desviacion': float(np.std(valores)) if len(valores) > 1 else 0.0
        }

    def obtener_estadisticas_interseccion(
        self,
        interseccion_id: str,
        ventana_segundos: int = 60
    ) -> Dict:
        """
        Obtiene estadísticas de una intersección específica

        Args:
            interseccion_id: ID de la intersección
            ventana_segundos: Ventana de tiempo

        Returns:
            Dict con estadísticas
        """
        if interseccion_id not in self.historico_intersecciones:
            return {}

        historico = self.historico_intersecciones[interseccion_id]
        if not historico:
            return {}

        # Filtrar datos recientes
        ahora = datetime.now()
        datos_recientes = [
            m for m in historico
            if (ahora - m.timestamp).total_seconds() <= ventana_segundos
        ]

        if not datos_recientes:
            return {}

        # Calcular estadísticas
        icv_promedio = np.mean([(m.icv_ns + m.icv_eo)/2 for m in datos_recientes])
        vavg_promedio = np.mean([(m.vavg_ns + m.vavg_eo)/2 for m in datos_recientes])
        q_promedio = np.mean([(m.q_ns + m.q_eo)/2 for m in datos_recientes])

        return {
            'interseccion_id': interseccion_id,
            'nombre': self.configuraciones[interseccion_id].nombre,
            'num_muestras': len(datos_recientes),
            'icv_promedio': float(icv_promedio),
            'vavg_promedio': float(vavg_promedio),
            'q_promedio': float(q_promedio),
            'metricas_recientes': datos_recientes[-1].to_dict()
        }

    def calcular_metricas_comparacion(
        self,
        metricas_adaptativo: List[MetricasRed],
        metricas_no_adaptativo: List[MetricasRed]
    ) -> Dict:
        """
        Compara el rendimiento del sistema adaptativo vs no adaptativo

        Args:
            metricas_adaptativo: Lista de métricas con control adaptativo
            metricas_no_adaptativo: Lista de métricas sin control adaptativo

        Returns:
            Dict con métricas de comparación y mejoras porcentuales
        """
        if not metricas_adaptativo or not metricas_no_adaptativo:
            return {}

        # Calcular promedios para cada modo
        def calcular_promedios(metricas_lista):
            return {
                'ICV_red': np.mean([m.ICV_red for m in metricas_lista]),
                'Vavg_red': np.mean([m.Vavg_red for m in metricas_lista]),
                'q_red': np.mean([m.q_red for m in metricas_lista]),
                'QL_red': np.mean([m.QL_red for m in metricas_lista])
            }

        prom_adaptativo = calcular_promedios(metricas_adaptativo)
        prom_no_adaptativo = calcular_promedios(metricas_no_adaptativo)

        # Calcular mejoras porcentuales
        # Para ICV y QL: reducción es mejora
        # Para Vavg y q: aumento es mejora
        def calcular_mejora(valor_adapt, valor_no_adapt, inverso=False):
            if valor_no_adapt == 0:
                return 0.0
            cambio = ((valor_adapt - valor_no_adapt) / valor_no_adapt) * 100
            return -cambio if inverso else cambio

        mejoras = {
            'ICV_red': calcular_mejora(
                prom_adaptativo['ICV_red'],
                prom_no_adaptativo['ICV_red'],
                inverso=True  # Menor es mejor
            ),
            'Vavg_red': calcular_mejora(
                prom_adaptativo['Vavg_red'],
                prom_no_adaptativo['Vavg_red']
            ),
            'q_red': calcular_mejora(
                prom_adaptativo['q_red'],
                prom_no_adaptativo['q_red']
            ),
            'QL_red': calcular_mejora(
                prom_adaptativo['QL_red'],
                prom_no_adaptativo['QL_red'],
                inverso=True  # Menor es mejor
            )
        }

        return {
            'adaptativo': prom_adaptativo,
            'no_adaptativo': prom_no_adaptativo,
            'mejoras_porcentuales': mejoras,
            'num_muestras_adaptativo': len(metricas_adaptativo),
            'num_muestras_no_adaptativo': len(metricas_no_adaptativo)
        }

    def _guardar_metricas(self, metricas: MetricasRed):
        """
        Guarda las métricas de red en un archivo JSON

        Args:
            metricas: Métricas a guardar
        """
        if not self.directorio_datos:
            return

        try:
            # Crear directorio si no existe
            self.directorio_datos.mkdir(parents=True, exist_ok=True)

            # Nombre de archivo con timestamp
            fecha = metricas.timestamp.strftime("%Y%m%d")
            archivo = self.directorio_datos / f"metricas_red_{fecha}.jsonl"

            # Append a archivo JSONL (JSON Lines)
            with open(archivo, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metricas.to_dict()) + '\n')

        except Exception as e:
            logger.error(f"Error guardando métricas: {e}")

    def exportar_historico(self, archivo_salida: Path) -> bool:
        """
        Exporta todo el histórico de métricas a un archivo JSON

        Args:
            archivo_salida: Ruta del archivo de salida

        Returns:
            True si se exportó correctamente
        """
        try:
            archivo_salida = Path(archivo_salida)
            archivo_salida.parent.mkdir(parents=True, exist_ok=True)
            datos_exportacion = {
                'metadata': {
                    'fecha_exportacion': datetime.now().isoformat(),
                    'num_intersecciones': len(self.configuraciones),
                    'ventana_historico': self.ventana_historico
                },
                'configuraciones': [
                    {
                        'id': c.id,
                        'nombre': c.nombre,
                        'peso': c.peso,
                        'ubicacion': c.ubicacion,
                        'es_critica': c.es_critica
                    }
                    for c in self.configuraciones.values()
                ],
                'metricas_red': [m.to_dict() for m in self.historico_red]
            }

            with open(archivo_salida, 'w', encoding='utf-8') as f:
                json.dump(datos_exportacion, f, indent=2, ensure_ascii=False)

            logger.info(f"Histórico exportado a {archivo_salida}")
            return True

        except Exception as e:
            logger.error(f"Error exportando histórico: {e}")
            return False

    def obtener_resumen_red(self) -> Dict:
        """
        Obtiene un resumen completo del estado actual de la red

        Returns:
            Dict con todas las métricas y estadísticas relevantes
        """
        if not self.metricas_red_actual:
            return {}

        # Tendencias de métricas principales
        tendencia_icv = self.obtener_tendencia('ICV_red', ventana_segundos=60)
        tendencia_vavg = self.obtener_tendencia('Vavg_red', ventana_segundos=60)

        # Estado general de la red
        estado_general = "FLUIDO"
        if self.metricas_red_actual.ICV_red >= 0.6:
            estado_general = "CONGESTIONADO"
        elif self.metricas_red_actual.ICV_red >= 0.3:
            estado_general = "MODERADO"

        return {
            'timestamp': self.metricas_red_actual.timestamp.isoformat(),
            'estado_general': estado_general,
            'metricas_actuales': self.metricas_red_actual.to_dict(),
            'tendencias': {
                'ICV_red': tendencia_icv,
                'Vavg_red': tendencia_vavg
            },
            'distribucion_estados': {
                'libres': self.metricas_red_actual.intersecciones_libres,
                'moderadas': self.metricas_red_actual.intersecciones_moderadas,
                'congestionadas': self.metricas_red_actual.intersecciones_congestionadas
            }
        }


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    import random

    print("\n" + "="*70)
    print("SISTEMA DE MÉTRICAS DE RED GLOBAL")
    print("Capítulo 6 - Agregación de Métricas sin Azure")
    print("="*70 + "\n")

    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Crear configuraciones de intersecciones de ejemplo
    configuraciones = [
        ConfiguracionInterseccion(
            id="I001",
            nombre="Av. Arequipa - Av. Javier Prado",
            peso=1.5,  # Intersección crítica
            ubicacion=(-12.0893, -77.0315),
            es_critica=True
        ),
        ConfiguracionInterseccion(
            id="I002",
            nombre="Av. Brasil - Av. Venezuela",
            peso=1.2,
            ubicacion=(-12.0715, -77.0531)
        ),
        ConfiguracionInterseccion(
            id="I003",
            nombre="Av. Universitaria - Av. La Marina",
            peso=1.0,
            ubicacion=(-12.0893, -77.0842)
        ),
        ConfiguracionInterseccion(
            id="I004",
            nombre="Av. Abancay - Jr. Lampa",
            peso=0.8,
            ubicacion=(-12.0464, -77.0282)
        )
    ]

    # Crear agregador
    agregador = AgregadorMetricasRed(
        configuraciones=configuraciones,
        directorio_datos=Path("./datos/metricas_red")
    )

    print("\n📊 Simulando métricas de red...\n")

    # Simular 30 actualizaciones de métricas
    for paso in range(30):
        timestamp = datetime.now()

        # Simular métricas para cada intersección
        for config in configuraciones:
            # Simular valores aleatorios (en aplicación real vienen de EstadoLocalInterseccion)
            metricas = MetricasInterseccion(
                interseccion_id=config.id,
                timestamp=timestamp,
                sc_ns=random.uniform(0, 40),
                sc_eo=random.uniform(0, 40),
                vavg_ns=random.uniform(10, 50),
                vavg_eo=random.uniform(10, 50),
                q_ns=random.uniform(5, 25),
                q_eo=random.uniform(5, 25),
                k_ns=random.uniform(0.01, 0.12),
                k_eo=random.uniform(0.01, 0.12),
                icv_ns=random.uniform(0.1, 0.8),
                icv_eo=random.uniform(0.1, 0.8),
                pi_ns=random.uniform(0.2, 0.9),
                pi_eo=random.uniform(0.2, 0.9)
            )

            agregador.actualizar_metricas_interseccion(metricas)

        # Mostrar resumen cada 10 pasos
        if (paso + 1) % 10 == 0:
            resumen = agregador.obtener_resumen_red()
            if resumen:
                print(f"\n⏱️  Paso {paso + 1}/30")
                print(f"Estado General: {resumen['estado_general']}")
                print(f"ICV_red: {resumen['metricas_actuales']['ICV_red']:.3f}")
                print(f"Vavg_red: {resumen['metricas_actuales']['Vavg_red']:.1f} km/h")
                print(f"q_red: {resumen['metricas_actuales']['q_red']:.1f} veh/min")
                print(f"Distribución: {resumen['distribucion_estados']['libres']} libres, "
                      f"{resumen['distribucion_estados']['moderadas']} moderadas, "
                      f"{resumen['distribucion_estados']['congestionadas']} congestionadas")

    # Mostrar estadísticas finales
    print("\n" + "="*70)
    print("ESTADÍSTICAS FINALES DE LA RED")
    print("="*70 + "\n")

    resumen_final = agregador.obtener_resumen_red()
    if resumen_final:
        print(f"📍 Intersecciones monitoreadas: {len(configuraciones)}")
        print(f"📊 Estado de la red: {resumen_final['estado_general']}")
        print("\nMétricas actuales:")
        print(f"  • ICV_red (Congestión): {resumen_final['metricas_actuales']['ICV_red']:.3f}")
        print(f"  • Vavg_red (Velocidad): {resumen_final['metricas_actuales']['Vavg_red']:.1f} km/h")
        print(f"  • q_red (Flujo): {resumen_final['metricas_actuales']['q_red']:.1f} veh/min")
        print(f"  • QL_red (Saturación): {resumen_final['metricas_actuales']['QL_red']:.3f}")

        print("\nTendencias (último minuto):")
        print(f"  • ICV: {resumen_final['tendencias']['ICV_red']['tendencia']:.4f}/s")
        print(f"  • Velocidad: {resumen_final['tendencias']['Vavg_red']['tendencia']:.4f} km/h/s")

    # Exportar histórico
    archivo_export = Path("./ejemplo_metricas_red.json")
    if agregador.exportar_historico(archivo_export):
        print(f"\n✅ Histórico exportado a: {archivo_export}")

    print("\n" + "="*70)
    print("✓ Simulación completada")
    print("="*70 + "\n")
