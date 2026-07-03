# -*- coding: utf-8 -*-
"""
Configuración común de la suite de tests.

Ejecutar desde 'Diseño Software/':
  python -m pytest tests -q

Los tests que requieren SUMO (marcados con @requiere_sumo) se saltan
automáticamente si sumolib/libsumo o los escenarios no están disponibles.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent          # Diseño Software/
INTEG = RAIZ / 'integracion-sumo'
for _p in (str(RAIZ), str(INTEG)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CRUCE_CFG = INTEG / 'escenarios' / 'cruce-simple' / 'cruce.sumocfg'


def hay_sumo() -> bool:
    try:
        import sumolib  # noqa: F401
        from conector_sumo import traci  # noqa: F401
    except Exception:
        return False
    return CRUCE_CFG.exists()
