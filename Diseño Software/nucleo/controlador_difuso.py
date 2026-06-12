"""
Sistema de Control Difuso para Semáforos Adaptativos

Implementa un controlador basado en lógica difusa que determina
el tiempo óptimo de fase verde en función del ICV y tiempo de espera.

Entradas:
- ICV (Índice de Congestión Vehicular): [0, 1]
- Tiempo de Espera: [0, 120] segundos

Salida:
- Tiempo de Verde: [15, 90] segundos
"""

import numpy as np
from typing import Dict, Tuple, List
import logging

logger = logging.getLogger(__name__)


class ConjuntoDifuso:
    """
    Representa un conjunto difuso con función de pertenencia trapezoidal
    """

    def __init__(self, nombre: str, a: float, b: float, c: float, d: float):
        """
        Constructor del conjunto difuso trapezoidal

        Args:
            nombre: Nombre del conjunto (ej: 'bajo', 'medio', 'alto')
            a, b, c, d: Parámetros del trapezoide
                        μ(x) = 0 si x <= a o x >= d
                        μ(x) = 1 si b <= x <= c
                        μ(x) lineal en [a,b] y [c,d]
        """
        self.nombre = nombre
        self.a = a
        self.b = b
        self.c = c
        self.d = d

    def pertenencia(self, x: float) -> float:
        """
        Calcula el grado de pertenencia de x al conjunto difuso

        Args:
            x: Valor a evaluar

        Returns:
            Grado de pertenencia μ(x) ∈ [0, 1]
        """
        if x <= self.a or x >= self.d:
            return 0.0
        elif self.b <= x <= self.c:
            return 1.0
        elif self.a < x < self.b:
            return (x - self.a) / (self.b - self.a)
        else:  # c < x < d
            return (self.d - x) / (self.d - self.c)


class ControladorDifuso:
    """
    Controlador de Lógica Difusa para Semáforos Adaptativos

    Base de Reglas:
    1. Si ICV es BAJO y Espera es CORTA → Verde CORTO
    2. Si ICV es BAJO y Espera es MEDIA → Verde MEDIO
    3. Si ICV es BAJO y Espera es LARGA → Verde LARGO
    4. Si ICV es MEDIO y Espera es CORTA → Verde MEDIO
    5. Si ICV es MEDIO y Espera es MEDIA → Verde MEDIO
    6. Si ICV es MEDIO y Espera es LARGA → Verde LARGO
    7. Si ICV es ALTO y Espera es CORTA → Verde LARGO
    8. Si ICV es ALTO y Espera es MEDIA → Verde LARGO
    9. Si ICV es ALTO y Espera es LARGA → Verde MUY_LARGO
    """

    def __init__(self):
        # Definir conjuntos difusos para ICV [0, 1]
        self.icv_bajo = ConjuntoDifuso('bajo', 0.0, 0.0, 0.2, 0.4)
        self.icv_medio = ConjuntoDifuso('medio', 0.3, 0.4, 0.6, 0.7)
        self.icv_alto = ConjuntoDifuso('alto', 0.6, 0.8, 1.0, 1.0)

        # Definir conjuntos difusos para Tiempo de Espera [0, 120] segundos
        self.espera_corta = ConjuntoDifuso('corta', 0, 0, 20, 40)
        self.espera_media = ConjuntoDifuso('media', 30, 40, 60, 70)
        self.espera_larga = ConjuntoDifuso('larga', 60, 80, 120, 120)

        # Definir conjuntos difusos para Tiempo Verde [15, 90] segundos
        self.verde_corto = ConjuntoDifuso('corto', 15, 15, 25, 35)
        self.verde_medio = ConjuntoDifuso('medio', 30, 40, 50, 60)
        self.verde_largo = ConjuntoDifuso('largo', 55, 65, 75, 85)
        self.verde_muy_largo = ConjuntoDifuso('muy_largo', 80, 85, 90, 90)

        logger.info("Controlador difuso inicializado con 9 reglas")

    def fuzzificar_icv(self, icv: float) -> Dict[str, float]:
        """
        Fuzzifica el valor de ICV

        Args:
            icv: Valor del ICV [0, 1]

        Returns:
            Dict con grados de pertenencia a cada conjunto
        """
        return {
            'bajo': self.icv_bajo.pertenencia(icv),
            'medio': self.icv_medio.pertenencia(icv),
            'alto': self.icv_alto.pertenencia(icv)
        }

    def fuzzificar_espera(self, espera: float) -> Dict[str, float]:
        """
        Fuzzifica el tiempo de espera

        Args:
            espera: Tiempo de espera en segundos [0, 120]

        Returns:
            Dict con grados de pertenencia a cada conjunto
        """
        return {
            'corta': self.espera_corta.pertenencia(espera),
            'media': self.espera_media.pertenencia(espera),
            'larga': self.espera_larga.pertenencia(espera)
        }

    def aplicar_reglas(
        self,
        icv_fuzzy: Dict[str, float],
        espera_fuzzy: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Aplica las reglas difusas usando operador MIN para AND

        Args:
            icv_fuzzy: Valores fuzzificados de ICV
            espera_fuzzy: Valores fuzzificados de Espera

        Returns:
            Dict con activación de cada salida difusa
        """
        # Inicializar activaciones de salida
        activaciones = {
            'corto': 0.0,
            'medio': 0.0,
            'largo': 0.0,
            'muy_largo': 0.0
        }

        # Regla 1: ICV bajo AND Espera corta → Verde CORTO
        activaciones['corto'] = max(
            activaciones['corto'],
            min(icv_fuzzy['bajo'], espera_fuzzy['corta'])
        )

        # Regla 2: ICV bajo AND Espera media → Verde MEDIO
        activaciones['medio'] = max(
            activaciones['medio'],
            min(icv_fuzzy['bajo'], espera_fuzzy['media'])
        )

        # Regla 3: ICV bajo AND Espera larga → Verde LARGO
        activaciones['largo'] = max(
            activaciones['largo'],
            min(icv_fuzzy['bajo'], espera_fuzzy['larga'])
        )

        # Regla 4: ICV medio AND Espera corta → Verde MEDIO
        activaciones['medio'] = max(
            activaciones['medio'],
            min(icv_fuzzy['medio'], espera_fuzzy['corta'])
        )

        # Regla 5: ICV medio AND Espera media → Verde MEDIO
        activaciones['medio'] = max(
            activaciones['medio'],
            min(icv_fuzzy['medio'], espera_fuzzy['media'])
        )

        # Regla 6: ICV medio AND Espera larga → Verde LARGO
        activaciones['largo'] = max(
            activaciones['largo'],
            min(icv_fuzzy['medio'], espera_fuzzy['larga'])
        )

        # Regla 7: ICV alto AND Espera corta → Verde LARGO
        activaciones['largo'] = max(
            activaciones['largo'],
            min(icv_fuzzy['alto'], espera_fuzzy['corta'])
        )

        # Regla 8: ICV alto AND Espera media → Verde LARGO
        activaciones['largo'] = max(
            activaciones['largo'],
            min(icv_fuzzy['alto'], espera_fuzzy['media'])
        )

        # Regla 9: ICV alto AND Espera larga → Verde MUY LARGO
        activaciones['muy_largo'] = max(
            activaciones['muy_largo'],
            min(icv_fuzzy['alto'], espera_fuzzy['larga'])
        )

        return activaciones

    def defuzzificar(self, activaciones: Dict[str, float]) -> float:
        """
        Defuzzifica usando método del centroide

        Args:
            activaciones: Activaciones de cada conjunto de salida

        Returns:
            Valor defuzzificado de tiempo verde en segundos
        """
        # Centroides de cada conjunto de salida
        centroides = {
            'corto': 25.0,        # Centro de [15, 35]
            'medio': 45.0,        # Centro de [30, 60]
            'largo': 70.0,        # Centro de [55, 85]
            'muy_largo': 87.5     # Centro de [80, 90]
        }

        # Calcular centroide ponderado
        numerador = sum(activaciones[k] * centroides[k] for k in activaciones)
        denominador = sum(activaciones.values())

        if denominador == 0:
            # Si no hay activación, usar valor por defecto
            logger.warning("No hay activaciones, usando tiempo por defecto")
            return 45.0

        tiempo_verde = numerador / denominador

        # Asegurar que esté en el rango válido
        tiempo_verde = np.clip(tiempo_verde, 15, 90)

        return round(tiempo_verde, 1)

    def calcular(self, icv: float, tiempo_espera: float) -> Dict:
        """
        Calcula el tiempo verde óptimo usando lógica difusa

        Args:
            icv: Índice de Congestión Vehicular [0, 1]
            tiempo_espera: Tiempo de espera en segundos [0, 120]

        Returns:
            Dict con resultado y detalles del proceso
        """
        # 1. Fuzzificación
        icv_fuzzy = self.fuzzificar_icv(icv)
        espera_fuzzy = self.fuzzificar_espera(tiempo_espera)

        # 2. Aplicar reglas
        activaciones = self.aplicar_reglas(icv_fuzzy, espera_fuzzy)

        # 3. Defuzzificación
        tiempo_verde = self.defuzzificar(activaciones)

        resultado = {
            'tiempo_verde': tiempo_verde,
            'icv_entrada': icv,
            'espera_entrada': tiempo_espera,
            'icv_fuzzy': icv_fuzzy,
            'espera_fuzzy': espera_fuzzy,
            'activaciones': activaciones
        }

        logger.debug(
            f"Control difuso: ICV={icv:.2f}, Espera={tiempo_espera:.0f}s "
            f"→ Verde={tiempo_verde:.0f}s"
        )

        return resultado

    def generar_superficie_control(
        self,
        resolucion: int = 20
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Genera la superficie de control para visualización

        Args:
            resolucion: Número de puntos en cada eje

        Returns:
            Tupla (ICV_grid, Espera_grid, Verde_grid)
        """
        icv_range = np.linspace(0, 1, resolucion)
        espera_range = np.linspace(0, 120, resolucion)

        ICV_grid, Espera_grid = np.meshgrid(icv_range, espera_range)
        Verde_grid = np.zeros_like(ICV_grid)

        for i in range(resolucion):
            for j in range(resolucion):
                resultado = self.calcular(ICV_grid[i, j], Espera_grid[i, j])
                Verde_grid[i, j] = resultado['tiempo_verde']

        return ICV_grid, Espera_grid, Verde_grid


# Ejemplo de uso
if __name__ == "__main__":
    controlador = ControladorDifuso()

    # Casos de prueba
    casos = [
        (0.15, 10, "ICV bajo, espera corta"),
        (0.15, 50, "ICV bajo, espera media"),
        (0.15, 100, "ICV bajo, espera larga"),
        (0.50, 10, "ICV medio, espera corta"),
        (0.50, 50, "ICV medio, espera media"),
        (0.50, 100, "ICV medio, espera larga"),
        (0.85, 10, "ICV alto, espera corta"),
        (0.85, 50, "ICV alto, espera media"),
        (0.85, 100, "ICV alto, espera larga"),
    ]

    print("=== PRUEBAS DE CONTROL DIFUSO ===\n")

    for icv, espera, descripcion in casos:
        resultado = controlador.calcular(icv, espera)
        print(f"{descripcion}:")
        print(f"  Entrada: ICV={icv:.2f}, Espera={espera}s")
        print(f"  Salida: Tiempo Verde = {resultado['tiempo_verde']:.1f}s")
        print(f"  Activaciones: {resultado['activaciones']}")
        print()

    # Generar superficie de control
    print("Generando superficie de control...")
    ICV, Espera, Verde = controlador.generar_superficie_control(resolucion=10)
    print(f"Superficie generada: {Verde.shape}")
    print(f"Rango de tiempo verde: [{Verde.min():.1f}, {Verde.max():.1f}]")
