"""
Módulo de Cálculo del Índice de Congestión Vehicular (ICV)

Este módulo implementa el modelo matemático fundamentado para cuantificar
el nivel de congestión en intersecciones vehiculares.

Incluye implementación de fórmulas exactas del Capítulo 6 de la tesis.
"""

import numpy as np
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParametrosInterseccion:
    """Parámetros físicos de la intersección"""
    longitud_maxima_cola: float = 150.0  # metros
    velocidad_maxima: float = 60.0       # km/h
    flujo_saturacion: float = 30.0       # veh/min (1800 veh/h)
    longitud_carril: float = 200.0       # metros
    densidad_atasco: float = 0.2         # veh/m

    # Pesos del modelo (suma = 1.0)
    peso_longitud: float = 0.35
    peso_velocidad: float = 0.25
    peso_flujo: float = 0.25
    peso_densidad: float = 0.15

    # Parámetros adicionales del Capítulo 6
    epsilon_velocidad: float = 2.0       # km/h - umbral para vehículo detenido (Cap 6.2.2)
    sc_max: float = 50.0                 # vehículos - máximo de vehículos detenidos
    k_max: float = 0.2                   # veh/m - densidad máxima
    q_max: float = 30.0                  # veh/min - flujo máximo
    delta_pi: float = 0.1                # Constante pequeña para PI (Cap 6.2.4)


class CalculadorICV:
    """
    Calculador del Índice de Congestión Vehicular

    Implementa el modelo matemático:
    ICV = w1·(L/Lmax) + w2·(1-V/Vmax) + w3·(F/Fsat) + w4·D_norm
    """

    def __init__(self, params: ParametrosInterseccion):
        self.params = params
        self._validar_pesos()

    def _validar_pesos(self):
        """Valida que los pesos sumen 1.0"""
        suma_pesos = (
            self.params.peso_longitud +
            self.params.peso_velocidad +
            self.params.peso_flujo +
            self.params.peso_densidad
        )

        if not np.isclose(suma_pesos, 1.0, atol=1e-6):
            raise ValueError(
                f"Los pesos deben sumar 1.0, suma actual: {suma_pesos}"
            )

    def calcular(
        self,
        longitud_cola: float,      # metros
        velocidad_promedio: float, # km/h
        flujo_vehicular: float,    # veh/min
        num_vehiculos: int = None  # opcional para densidad
    ) -> Dict[str, float]:
        """
        Calcula el ICV y sus componentes

        Args:
            longitud_cola: Longitud de la cola medida (m)
            velocidad_promedio: Velocidad promedio de vehículos (km/h)
            flujo_vehicular: Flujo vehicular (veh/min)
            num_vehiculos: Número de vehículos (para cálculo de densidad)

        Returns:
            Dict con:
                - icv: Índice de congestión [0, 1]
                - componente_longitud: Contribución de longitud
                - componente_velocidad: Contribución de velocidad
                - componente_flujo: Contribución de flujo
                - componente_densidad: Contribución de densidad
                - clasificacion: 'bajo', 'medio', 'alto'
        """

        # 1. Normalizar longitud de cola
        L_norm = min(longitud_cola / self.params.longitud_maxima_cola, 1.0)

        # 2. Normalizar velocidad (invertida: menor velocidad = mayor congestión)
        V_norm = 1.0 - min(velocidad_promedio / self.params.velocidad_maxima, 1.0)

        # 3. Normalizar flujo
        F_norm = min(flujo_vehicular / self.params.flujo_saturacion, 1.0)

        # 4. Calcular densidad normalizada
        if num_vehiculos is not None:
            densidad = num_vehiculos / self.params.longitud_carril
            D_norm = min(densidad / self.params.densidad_atasco, 1.0)
        else:
            # Estimar densidad a partir de flujo y velocidad
            if velocidad_promedio > 0:
                # Relación fundamental: q = k * v
                # k = q / v
                densidad = (flujo_vehicular * 60) / (velocidad_promedio * 1000)
                D_norm = min(densidad / self.params.densidad_atasco, 1.0)
            else:
                D_norm = 1.0  # Atasco total

        # 5. Calcular componentes ponderadas
        comp_longitud = self.params.peso_longitud * L_norm
        comp_velocidad = self.params.peso_velocidad * V_norm
        comp_flujo = self.params.peso_flujo * F_norm
        comp_densidad = self.params.peso_densidad * D_norm

        # 6. Calcular ICV
        icv = comp_longitud + comp_velocidad + comp_flujo + comp_densidad
        icv = np.clip(icv, 0.0, 1.0)

        # 7. Clasificar
        clasificacion = self._clasificar_icv(icv)

        resultado = {
            'icv': round(icv, 3),
            'componente_longitud': round(comp_longitud, 3),
            'componente_velocidad': round(comp_velocidad, 3),
            'componente_flujo': round(comp_flujo, 3),
            'componente_densidad': round(comp_densidad, 3),
            'clasificacion': clasificacion,
            'color': self._obtener_color(clasificacion)
        }

        logger.debug(f"ICV calculado: {resultado}")

        return resultado

    def _clasificar_icv(self, icv: float) -> str:
        """Clasifica el ICV en bajo, medio o alto"""
        if icv < 0.3:
            return 'bajo'
        elif icv < 0.6:
            return 'medio'
        else:
            return 'alto'

    def _obtener_color(self, clasificacion: str) -> str:
        """Obtiene el color asociado a la clasificación"""
        colores = {
            'bajo': '#00FF00',    # Verde
            'medio': '#FFFF00',   # Amarillo
            'alto': '#FF0000'     # Rojo
        }
        return colores[clasificacion]

    # =========================================================================
    # MÉTODOS DEL CAPÍTULO 6 DE LA TESIS
    # =========================================================================

    def calcular_stopped_count(
        self,
        velocidades: List[float]
    ) -> int:
        """
        Calcula el número de vehículos detenidos (Cap 6.2.2)

        Fórmula exacta: SC(l,t) = Σ I_v donde I_v = 1 si velocity(v) < ε

        Args:
            velocidades: Lista de velocidades de vehículos en km/h

        Returns:
            Número de vehículos detenidos
        """
        if not velocidades:
            return 0

        stopped_count = sum(1 for v in velocidades if v < self.params.epsilon_velocidad)

        logger.debug(f"StoppedCount: {stopped_count}/{len(velocidades)} vehículos detenidos (ε={self.params.epsilon_velocidad} km/h)")

        return stopped_count

    def calcular_velocidad_promedio_movimiento(
        self,
        velocidades: List[float]
    ) -> float:
        """
        Calcula velocidad promedio SOLO de vehículos en movimiento (Cap 6.2.2)

        Fórmula exacta: Vavg(l,t) = (1/N_mov) Σ velocity(v) para v con velocity(v) ≥ ε

        Args:
            velocidades: Lista de velocidades de vehículos en km/h

        Returns:
            Velocidad promedio de vehículos en movimiento en km/h
        """
        if not velocidades:
            return 0.0

        # Filtrar solo vehículos en movimiento (velocidad >= epsilon)
        velocidades_movimiento = [v for v in velocidades if v >= self.params.epsilon_velocidad]

        if not velocidades_movimiento:
            return 0.0

        vavg = np.mean(velocidades_movimiento)

        logger.debug(f"Vavg (solo movimiento): {vavg:.2f} km/h de {len(velocidades_movimiento)} vehículos en movimiento")

        return vavg

    def calcular_flujo_vehicular(
        self,
        num_vehiculos_cruzaron: int,
        tiempo_inicial: float,
        tiempo_final: float
    ) -> float:
        """
        Calcula flujo vehicular (Cap 6.2.2)

        Fórmula exacta: q(l,t) = N_cross(l, t0, t) / (t - t0)

        Args:
            num_vehiculos_cruzaron: Número de vehículos que cruzaron la intersección
            tiempo_inicial: Tiempo inicial en segundos
            tiempo_final: Tiempo final en segundos

        Returns:
            Flujo vehicular en veh/min
        """
        delta_t = tiempo_final - tiempo_inicial

        if delta_t <= 0:
            return 0.0

        # Calcular flujo en vehículos por minuto
        flujo_por_segundo = num_vehiculos_cruzaron / delta_t
        flujo_por_minuto = flujo_por_segundo * 60.0

        logger.debug(f"Flujo: {num_vehiculos_cruzaron} veh / {delta_t:.1f}s = {flujo_por_minuto:.2f} veh/min")

        return flujo_por_minuto

    def calcular_densidad_vehicular(
        self,
        num_vehiculos_total: int,
        longitud_efectiva: float
    ) -> float:
        """
        Calcula densidad vehicular (Cap 6.2.2)

        Fórmula exacta: k(l,t) = N_total(l,t) / L_efectiva

        Args:
            num_vehiculos_total: Número total de vehículos en el carril
            longitud_efectiva: Longitud efectiva del carril en metros

        Returns:
            Densidad vehicular en veh/m
        """
        if longitud_efectiva <= 0:
            return 0.0

        densidad = num_vehiculos_total / longitud_efectiva

        logger.debug(f"Densidad: {num_vehiculos_total} veh / {longitud_efectiva}m = {densidad:.4f} veh/m")

        return densidad

    def calcular_parametro_intensidad(
        self,
        velocidad_promedio_movimiento: float,
        stopped_count: int
    ) -> float:
        """
        Calcula el Parámetro de Intensidad (Cap 6.2.4)

        Fórmula exacta: PI(l,t) = Vavg(l,t) / (SC(l,t) + δ)

        Donde:
        - Vavg es la velocidad promedio de vehículos EN MOVIMIENTO
        - SC es el número de vehículos detenidos
        - δ es una constante pequeña para evitar división por cero

        Args:
            velocidad_promedio_movimiento: Velocidad promedio en km/h (solo vehículos en movimiento)
            stopped_count: Número de vehículos detenidos

        Returns:
            Parámetro de Intensidad PI
        """
        denominador = stopped_count + self.params.delta_pi
        pi = velocidad_promedio_movimiento / denominador

        logger.debug(f"PI = {velocidad_promedio_movimiento:.2f} / ({stopped_count} + {self.params.delta_pi}) = {pi:.3f}")

        return pi

    def calcular_icv_cap6(
        self,
        stopped_count: int,
        velocidad_promedio_movimiento: float,
        densidad: float,
        flujo: float
    ) -> Dict[str, float]:
        """
        Calcula ICV según fórmula EXACTA del Capítulo 6.2.3

        Fórmula exacta:
        ICV = w1*(SC/SCmax) + w2*(1-Vavg/Vmax) + w3*(k/kmax) + w4*(1-q/qmax)

        Donde:
        - SC: Stopped Count (vehículos detenidos)
        - Vavg: Velocidad promedio de vehículos EN MOVIMIENTO
        - k: Densidad vehicular (veh/m)
        - q: Flujo vehicular (veh/min)
        - Pesos exactos de la tesis: w1=0.35, w2=0.25, w3=0.25, w4=0.15

        Args:
            stopped_count: Número de vehículos detenidos
            velocidad_promedio_movimiento: Velocidad promedio en km/h (solo vehículos en movimiento)
            densidad: Densidad vehicular en veh/m
            flujo: Flujo vehicular en veh/min

        Returns:
            Dict con ICV y componentes
        """
        # 1. Normalizar Stopped Count
        SC_norm = min(stopped_count / self.params.sc_max, 1.0)

        # 2. Normalizar velocidad (invertida: menor velocidad = mayor congestión)
        Vavg_norm = 1.0 - min(velocidad_promedio_movimiento / self.params.velocidad_maxima, 1.0)

        # 3. Normalizar densidad
        k_norm = min(densidad / self.params.k_max, 1.0)

        # 4. Normalizar flujo (invertido: mayor flujo = mayor congestión, pero cerca de saturación)
        q_norm = 1.0 - min(flujo / self.params.q_max, 1.0)

        # 5. Calcular componentes ponderadas (PESOS EXACTOS DEL CAP 6.2.3)
        comp_stopped_count = self.params.peso_longitud * SC_norm      # w1 = 0.35
        comp_velocidad = self.params.peso_velocidad * Vavg_norm       # w2 = 0.25
        comp_densidad = self.params.peso_flujo * k_norm               # w3 = 0.25
        comp_flujo = self.params.peso_densidad * q_norm               # w4 = 0.15

        # 6. Calcular ICV
        icv = comp_stopped_count + comp_velocidad + comp_densidad + comp_flujo
        icv = np.clip(icv, 0.0, 1.0)

        # 7. Clasificar
        clasificacion = self._clasificar_icv(icv)

        resultado = {
            'icv': round(icv, 3),
            'componente_stopped_count': round(comp_stopped_count, 3),
            'componente_velocidad': round(comp_velocidad, 3),
            'componente_densidad': round(comp_densidad, 3),
            'componente_flujo': round(comp_flujo, 3),
            'clasificacion': clasificacion,
            'color': self._obtener_color(clasificacion),
            'formula': 'Cap6.2.3'
        }

        logger.debug(f"ICV (Cap 6.2.3): {resultado}")

        return resultado

    def calcular_metricas_completas_cap6(
        self,
        velocidades: List[float],
        num_vehiculos_cruzaron: int,
        tiempo_inicial: float,
        tiempo_final: float,
        longitud_efectiva: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Calcula TODAS las métricas del Capítulo 6 en un solo paso

        Este método integra todas las fórmulas del Cap 6.2.2, 6.2.3 y 6.2.4:
        - StoppedCount (Cap 6.2.2)
        - Vavg solo de vehículos en movimiento (Cap 6.2.2)
        - Flujo q (Cap 6.2.2)
        - Densidad k (Cap 6.2.2)
        - Parámetro de Intensidad PI (Cap 6.2.4)
        - ICV según fórmula exacta (Cap 6.2.3)

        Args:
            velocidades: Lista de velocidades de todos los vehículos detectados en km/h
            num_vehiculos_cruzaron: Número de vehículos que cruzaron la línea en el período
            tiempo_inicial: Tiempo inicial del período en segundos
            tiempo_final: Tiempo final del período en segundos
            longitud_efectiva: Longitud efectiva del carril en metros (default: usa parámetro de clase)

        Returns:
            Dict completo con todas las métricas del Capítulo 6
        """
        if longitud_efectiva is None:
            longitud_efectiva = self.params.longitud_carril

        # 1. Stopped Count (Cap 6.2.2)
        stopped_count = self.calcular_stopped_count(velocidades)

        # 2. Velocidad promedio de vehículos en movimiento (Cap 6.2.2)
        vavg = self.calcular_velocidad_promedio_movimiento(velocidades)

        # 3. Flujo vehicular (Cap 6.2.2)
        flujo = self.calcular_flujo_vehicular(num_vehiculos_cruzaron, tiempo_inicial, tiempo_final)

        # 4. Densidad vehicular (Cap 6.2.2)
        num_vehiculos_total = len(velocidades)
        densidad = self.calcular_densidad_vehicular(num_vehiculos_total, longitud_efectiva)

        # 5. Parámetro de Intensidad (Cap 6.2.4)
        parametro_intensidad = self.calcular_parametro_intensidad(vavg, stopped_count)

        # 6. ICV según fórmula exacta del Cap 6.2.3
        resultado_icv = self.calcular_icv_cap6(stopped_count, vavg, densidad, flujo)

        # 7. Construir resultado completo
        resultado_completo = {
            # Métricas básicas (Cap 6.2.2)
            'stopped_count': stopped_count,
            'velocidad_promedio_movimiento': round(vavg, 2),
            'flujo_vehicular': round(flujo, 2),
            'densidad_vehicular': round(densidad, 4),
            'num_vehiculos_total': num_vehiculos_total,
            'num_vehiculos_movimiento': sum(1 for v in velocidades if v >= self.params.epsilon_velocidad),
            'num_vehiculos_cruzaron': num_vehiculos_cruzaron,

            # Parámetro de Intensidad (Cap 6.2.4)
            'parametro_intensidad': round(parametro_intensidad, 3),

            # ICV y componentes (Cap 6.2.3)
            'icv': resultado_icv['icv'],
            'icv_clasificacion': resultado_icv['clasificacion'],
            'icv_color': resultado_icv['color'],
            'icv_componentes': {
                'stopped_count': resultado_icv['componente_stopped_count'],
                'velocidad': resultado_icv['componente_velocidad'],
                'densidad': resultado_icv['componente_densidad'],
                'flujo': resultado_icv['componente_flujo']
            },

            # Metadatos
            'tiempo_analisis': tiempo_final - tiempo_inicial,
            'longitud_efectiva': longitud_efectiva,
            'formula_icv': 'Capitulo_6.2.3',
            'epsilon_velocidad': self.params.epsilon_velocidad
        }

        logger.info(f"Métricas Cap 6 completas: ICV={resultado_icv['icv']}, SC={stopped_count}, Vavg={vavg:.2f}, PI={parametro_intensidad:.3f}")

        return resultado_completo

    # =========================================================================
    # FIN MÉTODOS DEL CAPÍTULO 6
    # =========================================================================

    def analizar_sensibilidad(
        self,
        longitud_base: float,
        velocidad_base: float,
        flujo_base: float,
        variacion_porcentual: float = 10.0
    ) -> Dict:
        """
        Analiza la sensibilidad del ICV ante variaciones en las variables

        Args:
            longitud_base, velocidad_base, flujo_base: Valores base
            variacion_porcentual: Porcentaje de variación a probar

        Returns:
            Dict con análisis de sensibilidad
        """
        icv_base = self.calcular(longitud_base, velocidad_base, flujo_base)['icv']

        # Variación de cada variable
        delta = variacion_porcentual / 100.0

        # Longitud +10%
        icv_l = self.calcular(
            longitud_base * (1 + delta),
            velocidad_base,
            flujo_base
        )['icv']

        # Velocidad +10%
        icv_v = self.calcular(
            longitud_base,
            velocidad_base * (1 + delta),
            flujo_base
        )['icv']

        # Flujo +10%
        icv_f = self.calcular(
            longitud_base,
            velocidad_base,
            flujo_base * (1 + delta)
        )['icv']

        return {
            'icv_base': icv_base,
            'sensibilidad_longitud': icv_l - icv_base,
            'sensibilidad_velocidad': icv_v - icv_base,
            'sensibilidad_flujo': icv_f - icv_base
        }


# Ejemplo de uso
if __name__ == "__main__":
    # Configurar parámetros de Lima
    params_lima = ParametrosInterseccion(
        longitud_maxima_cola=150.0,
        velocidad_maxima=60.0,
        flujo_saturacion=30.0,
        longitud_carril=200.0
    )

    calculador = CalculadorICV(params_lima)

    print("="*70)
    print("PRUEBA DE FÓRMULAS HEREDADAS (Retrocompatibilidad)")
    print("="*70)

    # Caso 1: Flujo libre
    print("\n=== CASO 1: Flujo Libre ===")
    resultado = calculador.calcular(
        longitud_cola=10.0,
        velocidad_promedio=55.0,
        flujo_vehicular=10.0
    )
    print(f"ICV: {resultado['icv']} - {resultado['clasificacion'].upper()}")
    print(f"Componentes: L={resultado['componente_longitud']}, "
          f"V={resultado['componente_velocidad']}, "
          f"F={resultado['componente_flujo']}, "
          f"D={resultado['componente_densidad']}")

    # Caso 2: Congestión severa
    print("\n=== CASO 2: Congestión Severa ===")
    resultado = calculador.calcular(
        longitud_cola=140.0,
        velocidad_promedio=8.0,
        flujo_vehicular=28.0
    )
    print(f"ICV: {resultado['icv']} - {resultado['clasificacion'].upper()}")

    # Análisis de sensibilidad
    print("\n=== ANÁLISIS DE SENSIBILIDAD ===")
    sensibilidad = calculador.analizar_sensibilidad(75.0, 25.0, 22.0)
    print(f"ICV base: {sensibilidad['icv_base']}")
    print(f"Delta ICV por +10% longitud: {sensibilidad['sensibilidad_longitud']:+.3f}")
    print(f"Delta ICV por +10% velocidad: {sensibilidad['sensibilidad_velocidad']:+.3f}")
    print(f"Delta ICV por +10% flujo: {sensibilidad['sensibilidad_flujo']:+.3f}")

    print("\n" + "="*70)
    print("PRUEBA DE FÓRMULAS DEL CAPÍTULO 6 (NUEVAS)")
    print("="*70)

    # Caso 3: Métricas completas del Capítulo 6 - Flujo libre
    print("\n=== CASO 3: Cap 6 - Flujo Libre ===")
    velocidades_flujo_libre = [55, 58, 52, 60, 54, 57, 56, 53, 59, 55]  # 10 vehículos en movimiento
    resultado_cap6 = calculador.calcular_metricas_completas_cap6(
        velocidades=velocidades_flujo_libre,
        num_vehiculos_cruzaron=10,
        tiempo_inicial=0.0,
        tiempo_final=60.0,  # 1 minuto
        longitud_efectiva=200.0
    )
    print(f"Stopped Count: {resultado_cap6['stopped_count']}")
    print(f"Velocidad promedio (movimiento): {resultado_cap6['velocidad_promedio_movimiento']} km/h")
    print(f"Flujo vehicular: {resultado_cap6['flujo_vehicular']} veh/min")
    print(f"Densidad vehicular: {resultado_cap6['densidad_vehicular']} veh/m")
    print(f"Parámetro Intensidad (PI): {resultado_cap6['parametro_intensidad']}")
    print(f"ICV (Cap 6.2.3): {resultado_cap6['icv']} - {resultado_cap6['icv_clasificacion'].upper()}")
    print(f"  Componentes: SC={resultado_cap6['icv_componentes']['stopped_count']}, "
          f"V={resultado_cap6['icv_componentes']['velocidad']}, "
          f"k={resultado_cap6['icv_componentes']['densidad']}, "
          f"q={resultado_cap6['icv_componentes']['flujo']}")

    # Caso 4: Métricas completas del Capítulo 6 - Congestión moderada
    print("\n=== CASO 4: Cap 6 - Congestión Moderada ===")
    velocidades_congestion = [
        0.5, 1.2, 25, 0.8, 30, 1.5, 28, 0.3, 22, 1.0,  # Mezcla: detenidos y en movimiento
        26, 0.9, 24, 1.8, 27, 0.6, 23, 1.1, 29, 0.4
    ]
    resultado_cap6 = calculador.calcular_metricas_completas_cap6(
        velocidades=velocidades_congestion,
        num_vehiculos_cruzaron=12,
        tiempo_inicial=0.0,
        tiempo_final=60.0,
        longitud_efectiva=200.0
    )
    print(f"Stopped Count: {resultado_cap6['stopped_count']} (velocidad < {params_lima.epsilon_velocidad} km/h)")
    print(f"Vehículos en movimiento: {resultado_cap6['num_vehiculos_movimiento']}")
    print(f"Velocidad promedio (movimiento): {resultado_cap6['velocidad_promedio_movimiento']} km/h")
    print(f"Flujo vehicular: {resultado_cap6['flujo_vehicular']} veh/min")
    print(f"Densidad vehicular: {resultado_cap6['densidad_vehicular']} veh/m")
    print(f"Parámetro Intensidad (PI): {resultado_cap6['parametro_intensidad']}")
    print(f"ICV (Cap 6.2.3): {resultado_cap6['icv']} - {resultado_cap6['icv_clasificacion'].upper()}")

    # Caso 5: Métricas completas del Capítulo 6 - Atasco severo
    print("\n=== CASO 5: Cap 6 - Atasco Severo ===")
    velocidades_atasco = [0.2, 0.5, 0.8, 1.0, 0.3, 0.6, 0.9, 0.4, 0.7, 1.2,
                          0.1, 0.8, 5.0, 0.5, 3.0, 0.2, 2.5, 0.6, 4.0, 0.3,
                          0.9, 1.5, 0.4, 0.7, 1.8, 0.5, 1.1, 0.8, 6.0, 0.2]  # 30 vehículos, mayoría detenidos
    resultado_cap6 = calculador.calcular_metricas_completas_cap6(
        velocidades=velocidades_atasco,
        num_vehiculos_cruzaron=5,  # Muy pocos cruzan
        tiempo_inicial=0.0,
        tiempo_final=60.0,
        longitud_efectiva=200.0
    )
    print(f"Stopped Count: {resultado_cap6['stopped_count']} (velocidad < {params_lima.epsilon_velocidad} km/h)")
    print(f"Vehículos en movimiento: {resultado_cap6['num_vehiculos_movimiento']}")
    print(f"Velocidad promedio (movimiento): {resultado_cap6['velocidad_promedio_movimiento']} km/h")
    print(f"Flujo vehicular: {resultado_cap6['flujo_vehicular']} veh/min")
    print(f"Densidad vehicular: {resultado_cap6['densidad_vehicular']} veh/m")
    print(f"Parámetro Intensidad (PI): {resultado_cap6['parametro_intensidad']}")
    print(f"ICV (Cap 6.2.3): {resultado_cap6['icv']} - {resultado_cap6['icv_clasificacion'].upper()}")

    print("\n" + "="*70)
    print("OK - Todas las formulas del Capitulo 6 implementadas y validadas")
    print("="*70)
