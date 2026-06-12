"""
Sistema de Control Difuso Local - Capítulo 6 (Sección 6.3.6)

Implementa el sistema de lógica difusa con:
- 3 variables de entrada: ICV, PI, EV
- 1 variable de salida: ΔTverde (ajuste porcentual)
- 12 reglas difusas jerárquicas
- Método de Mamdani: Fuzzificación → MIN → MAX → Centroide
"""

import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ConjuntoDifusoTesis:
    """
    Conjunto difuso definido por funciones de pertenencia exactas del Capítulo 6
    """

    def __init__(self, nombre: str, puntos: List[Tuple[float, float]]):
        """
        Args:
            nombre: Nombre del conjunto (ej: 'Bajo', 'Extender_Fuerte')
            puntos: Lista de tuplas (x, μ) que definen la función de pertenencia
        """
        self.nombre = nombre
        self.puntos = sorted(puntos, key=lambda p: p[0])

    def pertenencia(self, x: float) -> float:
        """
        Calcula μ(x) mediante interpolación lineal entre puntos
        """
        if x <= self.puntos[0][0]:
            return self.puntos[0][1]
        if x >= self.puntos[-1][0]:
            return self.puntos[-1][1]

        # Interpolación lineal
        for i in range(len(self.puntos) - 1):
            x1, y1 = self.puntos[i]
            x2, y2 = self.puntos[i + 1]

            if x1 <= x <= x2:
                if x2 == x1:
                    return y1
                return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

        return 0.0


class ControladorDifusoCapitulo6:
    """
    Controlador difuso completo según especificaciones del Capítulo 6

    Implementa:
    - Fuzzificación de ICV, PI, EV
    - 12 reglas difusas con prioridades
    - Defuzzificación por centroide
    - Cálculo de tiempos verdes ajustados
    - Balanceo de fases perpendiculares
    """

    def __init__(self,
                 T_base_NS: float = 30.0,
                 T_base_EO: float = 30.0,
                 T_ambar: float = 3.0,
                 T_todo_rojo: float = 2.0,
                 T_ciclo: float = 90.0):
        """
        Args:
            T_base_NS: Tiempo verde base Norte-Sur (segundos)
            T_base_EO: Tiempo verde base Este-Oeste (segundos)
            T_ambar: Duración de amarillo (segundos)
            T_todo_rojo: Duración de todo rojo (segundos)
            T_ciclo: Duración total del ciclo (segundos)
        """
        self.T_base_NS = T_base_NS
        self.T_base_EO = T_base_EO
        self.T_ambar = T_ambar
        self.T_todo_rojo = T_todo_rojo
        self.T_ciclo = T_ciclo

        # Límites de seguridad
        self.T_verde_min = 10.0  # Mínimo para cruce peatonal seguro
        self.T_verde_max = 120.0  # Máximo para evitar acumulación excesiva

        # Inicializar conjuntos difusos
        self._inicializar_conjuntos_difusos()

        # Definir reglas difusas
        self._definir_reglas_difusas()

        logger.info("Controlador Difuso Capítulo 6 inicializado")
        logger.info(f"  - 12 reglas difusas jerárquicas")
        logger.info(f"  - Método Mamdani con defuzzificación por centroide")
        logger.info(f"  - T_ciclo: {T_ciclo}s, T_base_NS: {T_base_NS}s, T_base_EO: {T_base_EO}s")

    def _inicializar_conjuntos_difusos(self):
        """
        Define los conjuntos difusos según las fórmulas exactas del Capítulo 6
        """
        # ==================== ENTRADAS ====================

        # ICV: Índice de Congestión Vehicular [0, 1]
        # μBajo(ICV) = 1 si ICV ≤ 0.2, lineal hasta 0.4, luego 0
        self.icv_bajo = ConjuntoDifusoTesis('Bajo', [
            (0.0, 1.0),
            (0.2, 1.0),
            (0.4, 0.0),
            (1.0, 0.0)
        ])

        # μMedio(ICV) = trapecio en [0.2, 0.4, 0.7]
        self.icv_medio = ConjuntoDifusoTesis('Medio', [
            (0.0, 0.0),
            (0.2, 0.0),
            (0.4, 1.0),
            (0.7, 0.0),
            (1.0, 0.0)
        ])

        # μAlto(ICV) = 0 si ICV ≤ 0.4, lineal desde 0.4-0.7, luego 1
        self.icv_alto = ConjuntoDifusoTesis('Alto', [
            (0.0, 0.0),
            (0.4, 0.0),
            (0.7, 1.0),
            (1.0, 1.0)
        ])

        # PI: Parámetro de Intensidad [0, 1]
        # μIneficiente(PI) = 1 si PI ≤ 0.3, lineal hasta 0.5, luego 0
        self.pi_ineficiente = ConjuntoDifusoTesis('Ineficiente', [
            (0.0, 1.0),
            (0.3, 1.0),
            (0.5, 0.0),
            (1.0, 0.0)
        ])

        # μModeradamente_Eficiente(PI) = trapecio en [0.3, 0.5, 0.8]
        self.pi_moderado = ConjuntoDifusoTesis('Moderadamente_Eficiente', [
            (0.0, 0.0),
            (0.3, 0.0),
            (0.5, 1.0),
            (0.8, 0.0),
            (1.0, 0.0)
        ])

        # μMuy_Eficiente(PI) = 0 si PI ≤ 0.5, lineal desde 0.5-0.8, luego 1
        self.pi_muy_eficiente = ConjuntoDifusoTesis('Muy_Eficiente', [
            (0.0, 0.0),
            (0.5, 0.0),
            (0.8, 1.0),
            (1.0, 1.0)
        ])

        # EV: Vehículos de Emergencia (crisp)
        # μAusente = 1 si EV = 0, else 0
        # μPresente = 1 si EV > 0, else 0
        # (implementado directamente en fuzzificar_ev)

        # ==================== SALIDAS ====================

        # ΔTverde: Ajuste porcentual [-30%, +30%]

        # μReducir_Fuerte(ΔT) = 1 si ΔT ≤ -30%, lineal hasta -10%, luego 0
        self.reducir_fuerte = ConjuntoDifusoTesis('Reducir_Fuerte', [
            (-30, 1.0),
            (-10, 0.0),
            (30, 0.0)
        ])

        # μReducir_Leve(ΔT) = trapecio en [-30, -10, -5]
        self.reducir_leve = ConjuntoDifusoTesis('Reducir_Leve', [
            (-30, 0.0),
            (-10, 1.0),
            (-5, 0.0),
            (30, 0.0)
        ])

        # μMantener(ΔT) = trapecio en [-10, 0, 10]
        self.mantener = ConjuntoDifusoTesis('Mantener', [
            (-30, 0.0),
            (-10, 0.0),
            (0, 1.0),
            (10, 0.0),
            (30, 0.0)
        ])

        # μExtender_Leve(ΔT) = trapecio en [5, 15, 30]
        self.extender_leve = ConjuntoDifusoTesis('Extender_Leve', [
            (-30, 0.0),
            (5, 0.0),
            (15, 1.0),
            (30, 0.0)
        ])

        # μExtender_Fuerte(ΔT) = 0 si ΔT ≤ 15%, lineal hasta 30%, luego 1
        self.extender_fuerte = ConjuntoDifusoTesis('Extender_Fuerte', [
            (-30, 0.0),
            (15, 0.0),
            (30, 1.0)
        ])

    def _definir_reglas_difusas(self):
        """
        Define las 12 reglas difusas jerárquicas del Capítulo 6

        Estructura: (prioridad, antecedentes, consecuente, descripción)
        """
        self.reglas = [
            # PRIORIDAD 1: Emergencias (máxima prioridad)
            (1, ['EV_Presente', 'ICV_Alto'], 'Extender_Fuerte',
             'R1: Emergencia + Congestión alta'),

            (1, ['EV_Presente', 'ICV_Medio'], 'Extender_Fuerte',
             'R2: Emergencia + Congestión media'),

            (1, ['EV_Presente', 'ICV_Bajo'], 'Extender_Leve',
             'R3: Emergencia + Flujo libre'),

            # PRIORIDAD 2: Congestión severa
            (2, ['EV_Ausente', 'ICV_Alto', 'PI_Ineficiente'], 'Extender_Fuerte',
             'R4: Congestión alta + Ineficiencia'),

            (2, ['EV_Ausente', 'ICV_Alto', 'PI_Moderado'], 'Extender_Leve',
             'R5: Congestión alta + Moderada eficiencia'),

            (2, ['EV_Ausente', 'ICV_Alto', 'PI_MuyEficiente'], 'Mantener',
             'R6: Congestión alta + Alta eficiencia'),

            # PRIORIDAD 3: Congestión moderada
            (3, ['EV_Ausente', 'ICV_Medio', 'PI_Ineficiente'], 'Extender_Leve',
             'R7: Congestión media + Ineficiencia'),

            (3, ['EV_Ausente', 'ICV_Medio', 'PI_Moderado'], 'Mantener',
             'R8: Congestión media + Moderada eficiencia'),

            (3, ['EV_Ausente', 'ICV_Medio', 'PI_MuyEficiente'], 'Reducir_Leve',
             'R9: Congestión media + Alta eficiencia'),

            # PRIORIDAD 4: Flujo libre
            (4, ['EV_Ausente', 'ICV_Bajo', 'PI_Ineficiente'], 'Mantener',
             'R10: Flujo libre + Ineficiencia'),

            (4, ['EV_Ausente', 'ICV_Bajo', 'PI_Moderado'], 'Reducir_Leve',
             'R11: Flujo libre + Moderada eficiencia'),

            (4, ['EV_Ausente', 'ICV_Bajo', 'PI_MuyEficiente'], 'Reducir_Fuerte',
             'R12: Flujo libre + Alta eficiencia'),
        ]

    def fuzzificar_icv(self, icv: float) -> Dict[str, float]:
        """
        Calcula grados de pertenencia para ICV

        Returns:
            Dict con {'Bajo': α, 'Medio': β, 'Alto': γ}
        """
        return {
            'Bajo': self.icv_bajo.pertenencia(icv),
            'Medio': self.icv_medio.pertenencia(icv),
            'Alto': self.icv_alto.pertenencia(icv)
        }

    def fuzzificar_pi(self, pi: float) -> Dict[str, float]:
        """
        Calcula grados de pertenencia para PI

        Returns:
            Dict con {'Ineficiente': α, 'Moderado': β, 'MuyEficiente': γ}
        """
        return {
            'Ineficiente': self.pi_ineficiente.pertenencia(pi),
            'Moderado': self.pi_moderado.pertenencia(pi),
            'MuyEficiente': self.pi_muy_eficiente.pertenencia(pi)
        }

    def fuzzificar_ev(self, ev: float) -> Dict[str, float]:
        """
        Fuzzifica variable crisp de emergencias

        Returns:
            Dict con {'Ausente': α, 'Presente': β}
        """
        return {
            'Ausente': 1.0 if ev == 0 else 0.0,
            'Presente': 1.0 if ev > 0 else 0.0
        }

    def aplicar_regla(self, antecedentes: List[str],
                     grados_icv: Dict, grados_pi: Dict, grados_ev: Dict) -> float:
        """
        Aplica operador MIN a los antecedentes de una regla

        Args:
            antecedentes: Lista de strings como ['EV_Presente', 'ICV_Alto']
            grados_icv, grados_pi, grados_ev: Grados de pertenencia fuzzificados

        Returns:
            Grado de activación de la regla (operador MIN)
        """
        grados = []

        for ant in antecedentes:
            if ant.startswith('EV_'):
                tipo = ant.split('_')[1]
                grados.append(grados_ev[tipo])
            elif ant.startswith('ICV_'):
                tipo = ant.split('_')[1]
                grados.append(grados_icv[tipo])
            elif ant.startswith('PI_'):
                tipo = ant.split('_')[1]
                grados.append(grados_pi[tipo])

        return min(grados) if grados else 0.0

    def defuzzificar_centroide(self, agregado: Dict[str, float]) -> float:
        """
        Defuzzificación por método del centroide

        Args:
            agregado: Dict {nombre_conjunto: grado_activacion}

        Returns:
            Valor crisp de ΔTverde en porcentaje
        """
        # Discretización del universo de discurso [-30, 30]
        delta_t_range = np.linspace(-30, 30, 300)

        # Calcular función de pertenencia agregada μ_agregado(ΔT)
        mu_agregado = np.zeros_like(delta_t_range)

        for nombre, grado_activacion in agregado.items():
            if grado_activacion > 0:
                conjunto = getattr(self, nombre.lower().replace('_', '_'))
                for i, dt in enumerate(delta_t_range):
                    mu_conjunto = conjunto.pertenencia(dt)
                    # Operador MAX
                    mu_agregado[i] = max(mu_agregado[i],
                                        min(grado_activacion, mu_conjunto))

        # Calcular centroide
        numerador = np.sum(delta_t_range * mu_agregado)
        denominador = np.sum(mu_agregado)

        if denominador == 0:
            return 0.0  # Mantener si no hay activación

        return numerador / denominador

    def calcular_ajuste_verde(self, icv: float, pi: float, ev: float) -> Dict:
        """
        Calcula el ajuste de tiempo verde mediante inferencia difusa completa

        Proceso:
        1. Fuzzificación de entradas
        2. Aplicación de reglas (MIN)
        3. Agregación de consecuentes (MAX)
        4. Defuzzificación (Centroide)

        Args:
            icv: Índice de Congestión Vehicular [0, 1]
            pi: Parámetro de Intensidad [0, 1]
            ev: Número de vehículos de emergencia (≥ 0)

        Returns:
            Dict con resultado completo del cálculo
        """
        # Etapa 1: Fuzzificación
        grados_icv = self.fuzzificar_icv(icv)
        grados_pi = self.fuzzificar_pi(pi)
        grados_ev = self.fuzzificar_ev(ev)

        # Etapa 2: Aplicación de reglas
        activaciones = {}
        reglas_disparadas = []

        for prioridad, antecedentes, consecuente, descripcion in self.reglas:
            grado = self.aplicar_regla(antecedentes, grados_icv, grados_pi, grados_ev)

            if grado > 0:
                # Agregar a consecuentes (operador MAX)
                if consecuente not in activaciones:
                    activaciones[consecuente] = grado
                else:
                    activaciones[consecuente] = max(activaciones[consecuente], grado)

                reglas_disparadas.append({
                    'prioridad': prioridad,
                    'descripcion': descripcion,
                    'grado': grado,
                    'consecuente': consecuente
                })

        # Etapa 3 y 4: Agregación y Defuzzificación
        if not activaciones:
            delta_t_verde = 0.0  # Mantener si no hay reglas activas
        else:
            delta_t_verde = self.defuzzificar_centroide(activaciones)

        return {
            'delta_t_porcentaje': delta_t_verde,
            'grados_icv': grados_icv,
            'grados_pi': grados_pi,
            'grados_ev': grados_ev,
            'activaciones': activaciones,
            'reglas_disparadas': sorted(reglas_disparadas,
                                       key=lambda x: x['prioridad']),
            'icv': icv,
            'pi': pi,
            'ev': ev
        }

    def calcular_tiempo_verde_ajustado(self, T_base: float, delta_t_porcentaje: float) -> float:
        """
        Calcula tiempo verde ajustado con restricciones de seguridad

        Fórmula: T_verde = T_base * (1 + ΔT/100)
        Sujeto a: T_verde_min ≤ T_verde ≤ T_verde_max

        Args:
            T_base: Tiempo verde base (segundos)
            delta_t_porcentaje: Ajuste porcentual (%)

        Returns:
            Tiempo verde ajustado en segundos
        """
        T_verde = T_base * (1 + delta_t_porcentaje / 100.0)

        # Aplicar restricciones de seguridad
        T_verde = max(self.T_verde_min, min(T_verde, self.T_verde_max))

        return T_verde

    def balancear_fases(self, T_verde_NS: float, T_verde_EO: float) -> Tuple[float, float]:
        """
        Balancea fases perpendiculares para respetar ciclo total

        Restricción: T_NS + T_EO + 2*T_ambar + 2*T_todo_rojo ≤ T_ciclo

        Si se viola, aplica normalización proporcional:
        T' = T * (disponible / (T_NS + T_EO))

        Args:
            T_verde_NS: Tiempo verde Norte-Sur calculado
            T_verde_EO: Tiempo verde Este-Oeste calculado

        Returns:
            Tupla (T_verde_NS_final, T_verde_EO_final)
        """
        # Tiempo disponible para verdes
        tiempo_fijo = 2 * self.T_ambar + 2 * self.T_todo_rojo
        tiempo_disponible = self.T_ciclo - tiempo_fijo

        suma_verdes = T_verde_NS + T_verde_EO

        if suma_verdes > tiempo_disponible:
            # Normalización proporcional
            factor = tiempo_disponible / suma_verdes
            T_verde_NS_final = T_verde_NS * factor
            T_verde_EO_final = T_verde_EO * factor

            logger.warning(f"Balanceo aplicado: NS {T_verde_NS:.1f}→{T_verde_NS_final:.1f}s, "
                         f"EO {T_verde_EO:.1f}→{T_verde_EO_final:.1f}s")
        else:
            T_verde_NS_final = T_verde_NS
            T_verde_EO_final = T_verde_EO

        return T_verde_NS_final, T_verde_EO_final

    def calcular_control_completo(self,
                                  icv_ns: float, pi_ns: float, ev_ns: float,
                                  icv_eo: float, pi_eo: float, ev_eo: float) -> Dict:
        """
        Calcula control difuso completo para ambas direcciones

        Args:
            icv_ns, pi_ns, ev_ns: Parámetros dirección Norte-Sur
            icv_eo, pi_eo, ev_eo: Parámetros dirección Este-Oeste

        Returns:
            Dict con tiempos verdes finales y detalles del cálculo
        """
        # Calcular ajustes difusos para cada dirección
        resultado_ns = self.calcular_ajuste_verde(icv_ns, pi_ns, ev_ns)
        resultado_eo = self.calcular_ajuste_verde(icv_eo, pi_eo, ev_eo)

        # Calcular tiempos verdes ajustados
        T_verde_NS_bruto = self.calcular_tiempo_verde_ajustado(
            self.T_base_NS, resultado_ns['delta_t_porcentaje']
        )
        T_verde_EO_bruto = self.calcular_tiempo_verde_ajustado(
            self.T_base_EO, resultado_eo['delta_t_porcentaje']
        )

        # Balancear fases
        T_verde_NS_final, T_verde_EO_final = self.balancear_fases(
            T_verde_NS_bruto, T_verde_EO_bruto
        )

        return {
            'NS': {
                'T_verde': T_verde_NS_final,
                'T_verde_bruto': T_verde_NS_bruto,
                'delta_t_porcentaje': resultado_ns['delta_t_porcentaje'],
                'inferencia': resultado_ns
            },
            'EO': {
                'T_verde': T_verde_EO_final,
                'T_verde_bruto': T_verde_EO_bruto,
                'delta_t_porcentaje': resultado_eo['delta_t_porcentaje'],
                'inferencia': resultado_eo
            },
            'ciclo': {
                'T_ciclo': self.T_ciclo,
                'T_ambar': self.T_ambar,
                'T_todo_rojo': self.T_todo_rojo,
                'tiempo_total': T_verde_NS_final + T_verde_EO_final +
                               2*self.T_ambar + 2*self.T_todo_rojo
            }
        }

    def obtener_resumen_legible(self, resultado: Dict) -> str:
        """
        Genera resumen legible del resultado del control
        """
        resumen = "\n" + "="*70 + "\n"
        resumen += "CONTROL DIFUSO - CAPÍTULO 6 (Sección 6.3.6)\n"
        resumen += "="*70 + "\n\n"

        # Norte-Sur
        resumen += "DIRECCIÓN NORTE-SUR:\n"
        ns = resultado['NS']['inferencia']
        resumen += f"  Entradas: ICV={ns['icv']:.3f}, PI={ns['pi']:.3f}, EV={ns['ev']:.0f}\n"
        resumen += f"  Fuzzificación ICV: "
        resumen += ", ".join([f"{k}={v:.3f}" for k, v in ns['grados_icv'].items()]) + "\n"
        resumen += f"  Fuzzificación PI:  "
        resumen += ", ".join([f"{k}={v:.3f}" for k, v in ns['grados_pi'].items()]) + "\n"
        resumen += f"  Fuzzificación EV:  "
        resumen += ", ".join([f"{k}={v:.3f}" for k, v in ns['grados_ev'].items()]) + "\n"
        resumen += f"\n  Reglas disparadas ({len(ns['reglas_disparadas'])}):\n"
        for regla in ns['reglas_disparadas']:
            resumen += f"    - {regla['descripcion']} → {regla['consecuente']} (α={regla['grado']:.3f})\n"
        resumen += f"\n  Resultado: ΔT = {ns['delta_t_porcentaje']:.1f}%\n"
        resumen += f"  Tiempo verde: {resultado['NS']['T_verde']:.1f}s "
        resumen += f"(base: {self.T_base_NS:.1f}s)\n\n"

        # Este-Oeste
        resumen += "DIRECCIÓN ESTE-OESTE:\n"
        eo = resultado['EO']['inferencia']
        resumen += f"  Entradas: ICV={eo['icv']:.3f}, PI={eo['pi']:.3f}, EV={eo['ev']:.0f}\n"
        resumen += f"  Fuzzificación ICV: "
        resumen += ", ".join([f"{k}={v:.3f}" for k, v in eo['grados_icv'].items()]) + "\n"
        resumen += f"  Fuzzificación PI:  "
        resumen += ", ".join([f"{k}={v:.3f}" for k, v in eo['grados_pi'].items()]) + "\n"
        resumen += f"  Fuzzificación EV:  "
        resumen += ", ".join([f"{k}={v:.3f}" for k, v in eo['grados_ev'].items()]) + "\n"
        resumen += f"\n  Reglas disparadas ({len(eo['reglas_disparadas'])}):\n"
        for regla in eo['reglas_disparadas']:
            resumen += f"    - {regla['descripcion']} → {regla['consecuente']} (α={regla['grado']:.3f})\n"
        resumen += f"\n  Resultado: ΔT = {eo['delta_t_porcentaje']:.1f}%\n"
        resumen += f"  Tiempo verde: {resultado['EO']['T_verde']:.1f}s "
        resumen += f"(base: {self.T_base_EO:.1f}s)\n\n"

        # Ciclo
        resumen += "CICLO SEMAFÓRICO:\n"
        ciclo = resultado['ciclo']
        resumen += f"  Tiempo total: {ciclo['tiempo_total']:.1f}s / {ciclo['T_ciclo']:.1f}s\n"
        resumen += f"  Verde NS: {resultado['NS']['T_verde']:.1f}s\n"
        resumen += f"  Verde EO: {resultado['EO']['T_verde']:.1f}s\n"
        resumen += f"  Ambar: {ciclo['T_ambar']:.1f}s × 2\n"
        resumen += f"  Todo rojo: {ciclo['T_todo_rojo']:.1f}s × 2\n"

        resumen += "="*70 + "\n"

        return resumen


# Ejemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Crear controlador
    controlador = ControladorDifusoCapitulo6(
        T_base_NS=30.0,
        T_base_EO=30.0,
        T_ciclo=90.0
    )

    # Caso de prueba 1: Congestión alta en NS, flujo libre en EO
    print("\n" + "="*70)
    print("CASO 1: Congestión alta NS + Flujo libre EO")
    print("="*70)

    resultado1 = controlador.calcular_control_completo(
        icv_ns=0.75,  # ICV alto
        pi_ns=0.25,   # PI ineficiente
        ev_ns=0,      # Sin emergencias
        icv_eo=0.15,  # ICV bajo
        pi_eo=0.85,   # PI muy eficiente
        ev_eo=0       # Sin emergencias
    )

    print(controlador.obtener_resumen_legible(resultado1))

    # Caso de prueba 2: Emergencia en NS
    print("\n" + "="*70)
    print("CASO 2: Emergencia activa en NS")
    print("="*70)

    resultado2 = controlador.calcular_control_completo(
        icv_ns=0.50,  # ICV medio
        pi_ns=0.60,   # PI moderado
        ev_ns=1,      # ¡EMERGENCIA!
        icv_eo=0.30,  # ICV bajo-medio
        pi_eo=0.70,   # PI moderado-eficiente
        ev_eo=0       # Sin emergencias
    )

    print(controlador.obtener_resumen_legible(resultado2))
