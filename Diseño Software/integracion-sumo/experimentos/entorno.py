"""
Preparación de entorno común para los experimentos.

Centraliza los ajustes de sys.path (el proyecto usa carpetas con guion, no
instalables como paquete) y la importación de traci/libsumo, reutilizando la
selección ya validada de conector_sumo (libsumo embebido si está disponible;
evita el bloqueo del firewall de Windows al socket TraCI).
"""
import sys
from pathlib import Path

DIR_EXPERIMENTOS = Path(__file__).resolve().parent
DIR_INTEGRACION = DIR_EXPERIMENTOS.parent          # integracion-sumo/
RAIZ_SOFTWARE = DIR_INTEGRACION.parent             # Diseño Software/

for _p in (str(RAIZ_SOFTWARE), str(DIR_INTEGRACION)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Reutiliza la lógica probada de selección de motor (libsumo > traci)
from conector_sumo import traci, USANDO_LIBSUMO, TRACI_DISPONIBLE  # noqa: E402,F401

import sumolib  # noqa: E402,F401

# Directorios de artefactos (spec de la plataforma)
DIR_DATA = RAIZ_SOFTWARE / 'data'
DIR_DATA_PROCESSED = DIR_DATA / 'processed'
DIR_DATA_SPLITS = DIR_DATA / 'splits'
DIR_RESULTS = RAIZ_SOFTWARE / 'results'
DIR_RESULTS_RUNS = DIR_RESULTS / 'runs'
DIR_RESULTS_COMPARACION = DIR_RESULTS / 'control_comparison'
DIR_RESULTS_PREDICCION = DIR_RESULTS / 'prediction'
DIR_RESULTS_LOGS = DIR_RESULTS / 'logs'
DIR_IA_ARTIFACTS = RAIZ_SOFTWARE / 'ia' / 'artifacts'


def asegurar_directorios():
    for d in (DIR_DATA_PROCESSED, DIR_DATA_SPLITS, DIR_RESULTS_RUNS,
              DIR_RESULTS_COMPARACION, DIR_RESULTS_PREDICCION,
              DIR_RESULTS_LOGS, DIR_IA_ARTIFACTS):
        d.mkdir(parents=True, exist_ok=True)


def ruta_escenario(escenario: str) -> Path:
    """Carpeta del escenario SUMO (p.ej. 'cruce-simple')."""
    return DIR_INTEGRACION / 'escenarios' / escenario
