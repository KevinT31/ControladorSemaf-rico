"""
Contratos de la plataforma experimental: estado observado, acción de control
e interfaz común de controladores (TrafficController).

Toda estrategia (tiempo fijo, difusa, difusa+IA, futuras) implementa la misma
interfaz, de modo que el runner y las campañas comparativas las tratan igual.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class EstadoEje:
    """Métricas agregadas de UN eje (NS o EO) durante un intervalo de control.

    Todas provienen de SUMO (promedios sobre el intervalo, no instantáneas).
    """
    n_veh: float = 0.0            # vehículos presentes (promedio)
    cola_veh: float = 0.0         # vehículos detenidos (promedio)
    cola_max_veh: float = 0.0     # pico de cola en el intervalo
    espera_s: float = 0.0         # suma de tiempos de espera en carriles (promedio, veh·s)
    vel_kmh: float = 0.0          # velocidad media ponderada por vehículo
    flujo_veh_min: float = 0.0    # vehículos distintos que entraron al eje / min
    densidad_veh_km: float = 0.0  # vehículos por km de carril
    ocupacion: float = 0.0        # fracción de ocupación de carril [0,1]
    icv: float = 0.0              # Índice de Congestión Vehicular [0,1] (nucleo)
    pi: float = 0.0               # Parámetro de eficiencia [0,1] (Cap.6)


@dataclass
class EstadoInterseccion:
    """Estado observado de la intersección al cierre de un intervalo de control."""
    t_sim: float                  # segundos de simulación al cierre del intervalo
    intervalo_idx: int
    ns: EstadoEje
    eo: EstadoEje
    fase_actual: int = 0
    verde_actual_ns: float = 30.0
    verde_actual_eo: float = 30.0
    llegadas_intervalo: int = 0       # vehículos que completaron viaje en el intervalo
    demora_intervalo_veh_s: float = 0.0  # veh·s detenidos acumulados en el intervalo

    def como_dict_plano(self) -> Dict:
        d = {'t_sim': self.t_sim, 'intervalo_idx': self.intervalo_idx,
             'fase_actual': self.fase_actual,
             'verde_actual_ns': self.verde_actual_ns,
             'verde_actual_eo': self.verde_actual_eo,
             'llegadas_intervalo': self.llegadas_intervalo,
             'demora_intervalo_veh_s': self.demora_intervalo_veh_s}
        for eje, nombre in ((self.ns, 'ns'), (self.eo, 'eo')):
            for k, v in asdict(eje).items():
                d[f'{k}_{nombre}'] = v
        return d


@dataclass
class AccionControl:
    """Acción propuesta por un controlador: tiempos de verde por eje.

    `aplicar=False` significa 'no tocar el programa del semáforo' (p.ej. el
    controlador de tiempo fijo deja el programa estático tal cual).
    """
    verde_ns: float
    verde_eo: float
    origen: str = 'desconocido'      # fixed | fuzzy | fuzzy_predictive_ai | ...
    aplicar: bool = True
    detalle: Dict = field(default_factory=dict)  # trazabilidad (reglas, predicción, beta...)


class ControladorTrafico(ABC):
    """Interfaz común de controladores semafóricos experimentales."""

    #: identificador estable usado en CSVs y nombres de archivo
    tipo: str = 'abstracto'

    def __init__(self):
        self._traza: List[Dict] = []

    def reset(self, contexto: Optional[Dict] = None):
        """Reinicia estado interno al comenzar una corrida (buffers, EMA...)."""
        self._traza = []

    def observe(self, estado: EstadoInterseccion):
        """Alimenta el estado observado (buffers de historia, etc.). Opcional."""

    @abstractmethod
    def decide(self, estado: EstadoInterseccion) -> AccionControl:
        """Propone la acción de control para el próximo intervalo."""

    def registrar(self, evento: Dict):
        self._traza.append(evento)

    def get_trace(self) -> List[Dict]:
        return list(self._traza)
