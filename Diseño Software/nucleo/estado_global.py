"""
Estado Global de la Red de Intersecciones

Agrega estados locales por intersección y expone agregados:
- ICV por dirección (ya normalizado [0,1] en estado local)
- ICV por intersección (promedio ponderado de direcciones)
- PI por dirección e intersección
- Agregados globales (ICV_global, PI_global, flujo_total, emergencias)

Incluye utilidad de normalización componente a componente para X_local (28 vars)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np


@dataclass
class InterseccionGlobal:
    id: str
    estado_local: Dict[str, List[float]]  # matrices: SC,Vavg,q,k,ICV,PI,EV como listas por dir

    def icv_por_interseccion(self, pesos: Optional[List[float]] = None) -> float:
        """Promedio ponderado de ICV por dirección (N,S,E,O)"""
        icv_dirs = self.estado_local.get('ICV', [0, 0, 0, 0])
        if not icv_dirs:
            return 0.0
        if pesos is None:
            pesos = [1.0, 1.0, 1.0, 1.0]
        pesos = np.array(pesos, dtype=float)
        icv_dirs = np.array(icv_dirs, dtype=float)
        denom = np.sum(pesos)
        if denom <= 0:
            return float(np.mean(icv_dirs))
        return float(np.sum(icv_dirs * pesos) / denom)

    def pi_por_interseccion(self) -> float:
        """Promedio simple de PI por dirección"""
        pi_dirs = self.estado_local.get('PI', [0, 0, 0, 0])
        if not pi_dirs:
            return 0.0
        return float(np.mean(np.array(pi_dirs, dtype=float)))


class EstadoGlobalRed:
    def __init__(self):
        self.intersecciones: Dict[str, InterseccionGlobal] = {}

    def actualizar_interseccion(self, paquete_estado_local: Dict):
        """
        Registra/actualiza una intersección a partir del paquete de telemetría local
        Formato esperado (producido por EstadoLocalInterseccion.obtener_paquete_telemetria):
          state_matrix: { 'SC': [N,S,E,O], 'Vavg': [...], 'q': [...], 'k': [...], 'ICV': [...], 'PI': [...], 'EV': [...] }
        """
        inter_id = paquete_estado_local.get('intersection_id', 'UNKNOWN')
        sm = paquete_estado_local.get('state_matrix', {})
        estado_local = {
            'SC': sm.get('SC', [0, 0, 0, 0]),
            'Vavg': sm.get('Vavg', [0, 0, 0, 0]),
            'q': sm.get('q', [0, 0, 0, 0]),
            'k': sm.get('k', [0, 0, 0, 0]),
            'ICV': sm.get('ICV', [0, 0, 0, 0]),
            'PI': sm.get('PI', [0, 0, 0, 0]),
            'EV': sm.get('EV', [0, 0, 0, 0]),
        }

        self.intersecciones[inter_id] = InterseccionGlobal(id=inter_id, estado_local=estado_local)

    def obtener_estado_global(self) -> Dict:
        """Construye el paquete global agregando todas las intersecciones"""
        inter_list = []
        icv_inter_vals = []
        pi_inter_vals = []
        total_ev = 0
        total_q = 0.0

        for inter in self.intersecciones.values():
            icv_inter = inter.icv_por_interseccion()
            pi_inter = inter.pi_por_interseccion()
            inter_list.append({
                'id': inter.id,
                'SC': inter.estado_local['SC'],
                'Vavg': inter.estado_local['Vavg'],
                'q': inter.estado_local['q'],
                'k': inter.estado_local['k'],
                'ICV_direcciones': inter.estado_local['ICV'],
                'PI_direcciones': inter.estado_local['PI'],
                'ICV_interseccion': icv_inter,
                'PI_interseccion': pi_inter,
                'EV': inter.estado_local['EV']
            })
            icv_inter_vals.append(icv_inter)
            pi_inter_vals.append(pi_inter)
            total_ev += int(np.sum(np.array(inter.estado_local['EV'])))
            total_q += float(np.sum(np.array(inter.estado_local['q'], dtype=float)))

        icv_global = float(np.mean(icv_inter_vals)) if icv_inter_vals else 0.0
        pi_global = float(np.mean(pi_inter_vals)) if pi_inter_vals else 0.0

        return {
            'intersections': inter_list,
            'global': {
                'ICV_global': icv_global,
                'PI_global': pi_global,
                'flujo_total': total_q,
                'emergencias_activas': total_ev
            }
        }


def normalizar_estado_vector(X_local: List[float], XMIN: List[float], XMAX: List[float]) -> List[float]:
    """Normaliza componente por componente (NO normalizar globalmente)
    X_local_norm[i] = (X_local[i] - XMIN[i]) / (XMAX[i] - XMIN[i])
    """
    X_local = np.array(X_local, dtype=float)
    XMIN = np.array(XMIN, dtype=float)
    XMAX = np.array(XMAX, dtype=float)
    denom = XMAX - XMIN
    denom[denom == 0] = 1.0
    X_norm = (X_local - XMIN) / denom
    return X_norm.tolist()
