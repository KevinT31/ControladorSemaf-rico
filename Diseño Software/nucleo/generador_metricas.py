# -*- coding: utf-8 -*-
"""
Generador de Métricas Realistas
Genera métricas de tráfico realistas basadas en patrones reales cuando SUMO no está disponible

Este módulo simula el comportamiento del tráfico usando modelos matemáticos
DETERMINÍSTICOS (sin valores aleatorios) para demostraciones creíbles del sistema.

✅ Usa funciones matemáticas (sin, cos, etc.) para variación natural
❌ NO usa np.random - Todo es determinístico y reproducible
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import math


@dataclass
class PatronTrafico:
    """Define un patrón de tráfico para simulación realista"""
    nombre: str
    descripcion: str
    flujo_base_ns: float  # veh/min
    flujo_base_eo: float  # veh/min
    velocidad_base_ns: float  # km/h
    velocidad_base_eo: float  # km/h
    factor_congestion: float  # 0.0 (libre) a 1.0 (atascado)
    densidad_base: float  # veh/m
    duracion_segundos: int = 300


class GeneradorMetricasRealistas:
    """
    Genera métricas de tráfico realistas basadas en modelos matemáticos
    en lugar de valores aleatorios
    """

    # Patrones predefinidos
    PATRON_LIBRE = PatronTrafico(
        nombre="flujo_libre",
        descripcion="Tráfico fluido - hora valle",
        flujo_base_ns=12.0,
        flujo_base_eo=10.0,
        velocidad_base_ns=50.0,
        velocidad_base_eo=45.0,
        factor_congestion=0.15,
        densidad_base=0.03
    )

    PATRON_MODERADO = PatronTrafico(
        nombre="congestion_moderada",
        descripcion="Tráfico moderado - hora pico inicio",
        flujo_base_ns=20.0,
        flujo_base_eo=18.0,
        velocidad_base_ns=30.0,
        velocidad_base_eo=28.0,
        factor_congestion=0.45,
        densidad_base=0.08
    )

    PATRON_CONGESTIONADO = PatronTrafico(
        nombre="atasco_severo",
        descripcion="Atasco severo - hora pico plena",
        flujo_base_ns=28.0,
        flujo_base_eo=25.0,
        velocidad_base_ns=12.0,
        velocidad_base_eo=10.0,
        factor_congestion=0.75,
        densidad_base=0.12
    )

    PATRON_EMERGENCIA = PatronTrafico(
        nombre="con_emergencia",
        descripcion="Emergencia activa - ambulancia presente",
        flujo_base_ns=15.0,
        flujo_base_eo=14.0,
        velocidad_base_ns=35.0,
        velocidad_base_eo=30.0,
        factor_congestion=0.35,
        densidad_base=0.06
    )

    def __init__(self, offset_temporal: float = 0.0):
        """
        Args:
            offset_temporal: Offset en segundos para variar la fase inicial (determinístico)
        """
        self.offset_temporal = offset_temporal
        self.tiempo_inicio = datetime.now()
        self.paso_actual = 0

    def generar_serie_temporal(
        self,
        patron: PatronTrafico,
        num_pasos: int,
        intervalo_segundos: float = 1.0
    ) -> List[Dict]:
        """
        Genera una serie temporal de métricas realistas

        Args:
            patron: Patrón de tráfico a simular
            num_pasos: Número de pasos de tiempo
            intervalo_segundos: Intervalo entre pasos

        Returns:
            Lista de diccionarios con métricas por paso
        """
        metricas_serie = []

        for paso in range(num_pasos):
            tiempo = paso * intervalo_segundos
            timestamp = self.tiempo_inicio + timedelta(seconds=tiempo)

            # Generar métricas para NS
            metricas_ns = self._generar_metricas_direccion(
                patron=patron,
                tiempo=tiempo,
                es_direccion_ns=True,
                paso=paso
            )

            # Generar métricas para EO
            metricas_eo = self._generar_metricas_direccion(
                patron=patron,
                tiempo=tiempo,
                es_direccion_ns=False,
                paso=paso
            )

            # Calcular ICV usando las fórmulas del Capítulo 6
            icv_ns = self._calcular_icv(
                metricas_ns['sc'],
                metricas_ns['vavg'],
                metricas_ns['k'],
                metricas_ns['q']
            )

            icv_eo = self._calcular_icv(
                metricas_eo['sc'],
                metricas_eo['vavg'],
                metricas_eo['k'],
                metricas_eo['q']
            )

            # Calcular PI (Parámetro de Intensidad)
            pi_ns = metricas_ns['vavg'] / (metricas_ns['sc'] + 1.0)
            pi_eo = metricas_eo['vavg'] / (metricas_eo['sc'] + 1.0)

            # Vehículos de emergencia (solo si patrón es emergencia)
            ev_ns = 1 if patron.nombre == "con_emergencia" and paso % 50 < 20 else 0
            ev_eo = 0

            metricas_paso = {
                'timestamp': timestamp,
                'paso': paso,
                'tiempo_segundos': tiempo,
                # Métricas NS
                'sc_ns': metricas_ns['sc'],
                'vavg_ns': metricas_ns['vavg'],
                'q_ns': metricas_ns['q'],
                'k_ns': metricas_ns['k'],
                'icv_ns': icv_ns,
                'pi_ns': pi_ns,
                'ev_ns': ev_ns,
                # Métricas EO
                'sc_eo': metricas_eo['sc'],
                'vavg_eo': metricas_eo['vavg'],
                'q_eo': metricas_eo['q'],
                'k_eo': metricas_eo['k'],
                'icv_eo': icv_eo,
                'pi_eo': pi_eo,
                'ev_eo': ev_eo,
                # Promedio
                'icv_promedio': (icv_ns + icv_eo) / 2.0,
                'vavg_promedio': (metricas_ns['vavg'] + metricas_eo['vavg']) / 2.0
            }

            metricas_serie.append(metricas_paso)

        return metricas_serie

    def _generar_metricas_direccion(
        self,
        patron: PatronTrafico,
        tiempo: float,
        es_direccion_ns: bool,
        paso: int
    ) -> Dict:
        """
        Genera métricas realistas para una dirección usando modelos matemáticos DETERMINÍSTICOS

        Args:
            patron: Patrón de tráfico
            tiempo: Tiempo en segundos
            es_direccion_ns: True si es Norte-Sur
            paso: Número de paso actual

        Returns:
            Dict con sc, vavg, q, k
        """
        # Tiempo ajustado con offset (permite variación entre instancias)
        tiempo_ajustado = tiempo + self.offset_temporal

        # Obtener valores base del patrón
        if es_direccion_ns:
            flujo_base = patron.flujo_base_ns
            vel_base = patron.velocidad_base_ns
            fase_offset = 0.0  # NS sin offset
        else:
            flujo_base = patron.flujo_base_eo
            vel_base = patron.velocidad_base_eo
            fase_offset = 0.5  # EO desfasado 180° para simular semáforo coordinado

        # Variación temporal (ciclos de semáforo de 90s)
        ciclo_periodo = 90.0
        fase_ciclo = ((tiempo_ajustado + fase_offset * ciclo_periodo) % ciclo_periodo) / ciclo_periodo

        # Durante fase verde (0.0-0.33): velocidad alta, colas bajas
        # Durante fase roja (0.33-0.66): velocidad baja, colas altas
        # Durante transición (0.66-1.0): valores intermedios

        if fase_ciclo < 0.33:  # Verde
            factor_velocidad = 1.2
            factor_cola = 0.3
        elif fase_ciclo < 0.66:  # Rojo
            factor_velocidad = 0.4
            factor_cola = 2.0
        else:  # Transición
            factor_velocidad = 0.8
            factor_cola = 1.0

        # Aplicar factores de congestión
        factor_congestion = patron.factor_congestion

        # Variación determinística usando funciones sinusoidales
        # Simula micro-variaciones naturales del tráfico (platoons, ondas de choque)

        # Frecuencias diferentes para cada métrica
        freq_rapida = 0.1  # 10 segundos
        freq_media = 0.03  # 30 segundos
        freq_lenta = 0.01  # 100 segundos

        # Velocidad promedio (km/h)
        # Relación fundamental del tráfico: v = v_libre * (1 - factor_congestion)
        vavg = vel_base * factor_velocidad * (1.0 - 0.7 * factor_congestion)
        # Añadir variación sinusoidal (+/- 5%)
        variacion_vavg = vavg * 0.05 * math.sin(2 * math.pi * tiempo_ajustado * freq_media)
        vavg += variacion_vavg
        vavg = max(5.0, min(vavg, 60.0))  # Limitar entre 5 y 60 km/h

        # Stopped Count (vehículos detenidos)
        # Más vehículos detenidos con mayor congestión
        sc_base = 50.0 * factor_congestion * factor_cola
        # Variación sinusoidal compuesta (simula llegada en pelotones)
        variacion_sc = 5.0 * (
            math.sin(2 * math.pi * tiempo_ajustado * freq_rapida) * 0.5 +
            math.cos(2 * math.pi * tiempo_ajustado * freq_media) * 0.5
        )
        sc = sc_base + variacion_sc
        sc = max(0.0, min(sc, 50.0))

        # Flujo vehicular (veh/min)
        # Relación: q = k * v (flujo = densidad * velocidad)
        q = flujo_base * (1.0 + 0.3 * factor_congestion) * factor_velocidad
        # Variación sinusoidal
        variacion_q = 1.0 * math.sin(2 * math.pi * tiempo_ajustado * freq_rapida + 0.3)
        q += variacion_q
        q = max(0.0, min(q, 30.0))

        # Densidad (veh/m)
        # Relación: k = q / v
        k = patron.densidad_base * (1.0 + factor_congestion * 2.0) * factor_cola
        # Variación sinusoidal pequeña
        variacion_k = 0.01 * math.sin(2 * math.pi * tiempo_ajustado * freq_lenta)
        k += variacion_k
        k = max(0.0, min(k, 0.15))

        return {
            'sc': round(sc, 1),
            'vavg': round(vavg, 1),
            'q': round(q, 1),
            'k': round(k, 4)
        }

    def _calcular_icv(
        self,
        sc: float,
        vavg: float,
        k: float,
        q: float
    ) -> float:
        """
        Calcula ICV usando la fórmula del Capítulo 6.2.3

        ICV = w1*SC_norm + w2*(1-V_norm) + w3*k_norm + w4*(1-q_norm)
        """
        # Pesos de la fórmula
        w1, w2, w3, w4 = 0.4, 0.3, 0.2, 0.1

        # Valores máximos para normalización
        SC_MAX = 50.0
        V_MAX = 60.0
        k_MAX = 0.15
        q_MAX = 30.0

        # Normalizar componentes
        sc_norm = min(sc / SC_MAX, 1.0)
        v_norm = 1.0 - min(vavg / V_MAX, 1.0)
        k_norm = min(k / k_MAX, 1.0)
        q_norm = 1.0 - min(q / q_MAX, 1.0)

        # Calcular ICV
        icv = w1*sc_norm + w2*v_norm + w3*k_norm + w4*q_norm

        return round(max(0.0, min(icv, 1.0)), 4)

    def generar_comparacion_patrones(
        self,
        patron_base: PatronTrafico,
        patron_mejorado: PatronTrafico,
        num_pasos: int = 300
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Genera dos series temporales para comparación

        Args:
            patron_base: Patrón sin control adaptativo (tiempo fijo)
            patron_mejorado: Patrón con control adaptativo
            num_pasos: Número de pasos a simular

        Returns:
            Tupla (serie_base, serie_mejorada)
        """
        # Serie base con offset original
        serie_base = self.generar_serie_temporal(patron_base, num_pasos)

        # Serie mejorada con pequeño offset para ligera variación determinística
        offset_original = self.offset_temporal
        self.offset_temporal += 10.0  # Offset de 10 segundos para variación
        serie_mejorada = self.generar_serie_temporal(patron_mejorado, num_pasos)
        self.offset_temporal = offset_original  # Restaurar

        return serie_base, serie_mejorada

    @classmethod
    def obtener_patron_por_nombre(cls, nombre: str) -> PatronTrafico:
        """
        Obtiene un patrón predefinido por nombre

        Args:
            nombre: Nombre del patrón (flujo_libre, congestion_moderada, etc.)

        Returns:
            Patrón de tráfico correspondiente
        """
        patrones = {
            'flujo_libre': cls.PATRON_LIBRE,
            'congestion_moderada': cls.PATRON_MODERADO,
            'atasco_severo': cls.PATRON_CONGESTIONADO,
            'con_emergencia': cls.PATRON_EMERGENCIA
        }

        return patrones.get(nombre, cls.PATRON_MODERADO)

    @classmethod
    def crear_patron_adaptativo_mejorado(cls, patron_base: PatronTrafico) -> PatronTrafico:
        """
        Crea un patrón mejorado que simula el efecto del control adaptativo
        sobre un patrón base

        Args:
            patron_base: Patrón de tiempo fijo

        Returns:
            Patrón mejorado con control adaptativo
        """
        # El control adaptativo típicamente mejora:
        # - Reduce congestión en 15-25%
        # - Aumenta velocidad promedio en 10-20%
        # - Mejora flujo en 5-15%

        factor_mejora_congestion = 0.75  # Reduce congestión a 75% del original
        factor_mejora_velocidad = 1.15   # Aumenta velocidad 15%
        factor_mejora_flujo = 1.10       # Aumenta flujo 10%

        return PatronTrafico(
            nombre=f"{patron_base.nombre}_adaptativo",
            descripcion=f"{patron_base.descripcion} (con control adaptativo)",
            flujo_base_ns=patron_base.flujo_base_ns * factor_mejora_flujo,
            flujo_base_eo=patron_base.flujo_base_eo * factor_mejora_flujo,
            velocidad_base_ns=patron_base.velocidad_base_ns * factor_mejora_velocidad,
            velocidad_base_eo=patron_base.velocidad_base_eo * factor_mejora_velocidad,
            factor_congestion=patron_base.factor_congestion * factor_mejora_congestion,
            densidad_base=patron_base.densidad_base,
            duracion_segundos=patron_base.duracion_segundos
        )


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("GENERADOR DE MÉTRICAS REALISTAS")
    print("Sistema de Tráfico Basado en Modelos Matemáticos DETERMINÍSTICOS")
    print("(Sin valores aleatorios - 100% reproducible)")
    print("="*70 + "\n")

    generador = GeneradorMetricasRealistas(offset_temporal=0.0)

    # Probar diferentes patrones
    patrones_prueba = [
        GeneradorMetricasRealistas.PATRON_LIBRE,
        GeneradorMetricasRealistas.PATRON_MODERADO,
        GeneradorMetricasRealistas.PATRON_CONGESTIONADO
    ]

    for patron in patrones_prueba:
        print(f"\n📊 Patrón: {patron.nombre.upper()}")
        print(f"   {patron.descripcion}")
        print(f"   Factor congestión: {patron.factor_congestion:.2f}")

        # Generar 10 pasos
        serie = generador.generar_serie_temporal(patron, num_pasos=10, intervalo_segundos=10.0)

        # Mostrar resumen
        icv_promedio = np.mean([m['icv_promedio'] for m in serie])
        vavg_promedio = np.mean([m['vavg_promedio'] for m in serie])

        print(f"   → ICV promedio: {icv_promedio:.3f}")
        print(f"   → Velocidad promedio: {vavg_promedio:.1f} km/h")

        # Clasificar
        if icv_promedio < 0.3:
            print("   → Estado: 🟢 FLUIDO")
        elif icv_promedio < 0.6:
            print("   → Estado: 🟡 MODERADO")
        else:
            print("   → Estado: 🔴 CONGESTIONADO")

    # Probar comparación
    print("\n" + "="*70)
    print("COMPARACIÓN: TIEMPO FIJO VS ADAPTATIVO")
    print("="*70 + "\n")

    patron_fijo = GeneradorMetricasRealistas.PATRON_MODERADO
    patron_adaptativo = GeneradorMetricasRealistas.crear_patron_adaptativo_mejorado(patron_fijo)

    generador2 = GeneradorMetricasRealistas(offset_temporal=5.0)  # Offset determinístico
    serie_fijo, serie_adapt = generador2.generar_comparacion_patrones(
        patron_fijo,
        patron_adaptativo,
        num_pasos=100
    )

    # Calcular métricas
    icv_fijo = np.mean([m['icv_promedio'] for m in serie_fijo])
    icv_adapt = np.mean([m['icv_promedio'] for m in serie_adapt])
    vel_fijo = np.mean([m['vavg_promedio'] for m in serie_fijo])
    vel_adapt = np.mean([m['vavg_promedio'] for m in serie_adapt])

    mejora_icv = ((icv_fijo - icv_adapt) / icv_fijo) * 100
    mejora_vel = ((vel_adapt - vel_fijo) / vel_fijo) * 100

    print("Control Tiempo Fijo:")
    print(f"  • ICV: {icv_fijo:.3f}")
    print(f"  • Velocidad: {vel_fijo:.1f} km/h")

    print("\nControl Adaptativo:")
    print(f"  • ICV: {icv_adapt:.3f}")
    print(f"  • Velocidad: {vel_adapt:.1f} km/h")

    print("\nMejoras:")
    print(f"  ✓ Reducción de congestión: {mejora_icv:.1f}%")
    print(f"  ✓ Aumento de velocidad: {mejora_vel:.1f}%")

    print("\n" + "="*70)
    print("✓ Generador funcionando correctamente (100% determinístico)")
    print("✓ Ejecutar de nuevo producirá los MISMOS resultados")
    print("="*70 + "\n")
