"""
Generación del dataset temporal para la IA (una fila por intervalo de control).

Consolida los intervals.csv de todas las corridas reales (results/runs/*/) en
  data/processed/intervalos.csv
y produce particiones SIN FUGA (el split es POR CORRIDA, nunca por fila: una
secuencia jamás mezcla train y test) en
  data/splits/{train,val,test}.csv

El esquema de columnas es COLUMNAS_INTERVALOS del runner; las características
que consume la CNN-LSTM (ia.secuencias.CARACTERISTICAS) son un subconjunto.

CLI:
  python -m experimentos.dataset            # consolidar + particionar
  python -m experimentos.dataset --resumen  # solo inspeccionar lo existente
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .entorno import (DIR_DATA_PROCESSED, DIR_DATA_SPLITS, DIR_RESULTS_RUNS,
                      asegurar_directorios)
from .almacen import escribir_csv

RUTA_CONSOLIDADO = DIR_DATA_PROCESSED / 'intervalos.csv'
RUTA_MANIFIESTO = DIR_DATA_PROCESSED / 'manifiesto.json'

FRACCIONES_DEFECTO = (0.70, 0.15, 0.15)   # train / val / test
SEMILLA_SPLIT = 20260701                  # split reproducible


def leer_csv(ruta: Path) -> List[Dict]:
    with open(ruta, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def recolectar_corridas(dir_runs: Optional[Path] = None) -> List[Dict]:
    """Apila los intervals.csv de todas las corridas persistidas."""
    dir_runs = dir_runs or DIR_RESULTS_RUNS
    filas: List[Dict] = []
    if not dir_runs.exists():
        return filas
    for carpeta in sorted(dir_runs.iterdir()):
        archivo = carpeta / 'intervals.csv'
        if not (carpeta.is_dir() and archivo.exists() and archivo.stat().st_size):
            continue
        filas.extend(leer_csv(archivo))
    return filas


def particionar_por_corrida(filas: List[Dict],
                            fracciones: Tuple[float, float, float] = FRACCIONES_DEFECTO,
                            semilla: int = SEMILLA_SPLIT
                            ) -> Dict[str, List[Dict]]:
    """Split POR run_id (sin fuga entre particiones), reproducible.

    Estratifica por (demand_level, controller_type) para que cada partición
    vea todos los niveles de demanda y estilos de control.
    """
    por_run: Dict[str, List[Dict]] = {}
    estrato_de: Dict[str, Tuple[str, str]] = {}
    for f in filas:
        por_run.setdefault(f['run_id'], []).append(f)
        estrato_de[f['run_id']] = (f['demand_level'], f['controller_type'])

    estratos: Dict[Tuple[str, str], List[str]] = {}
    for run_id, estrato in estrato_de.items():
        estratos.setdefault(estrato, []).append(run_id)

    rng = random.Random(semilla)
    particiones: Dict[str, List[Dict]] = {'train': [], 'val': [], 'test': []}
    asignacion: Dict[str, str] = {}
    for estrato, runs in sorted(estratos.items()):
        runs = sorted(runs)
        rng.shuffle(runs)
        n = len(runs)
        n_train = max(1, round(n * fracciones[0])) if n >= 3 else n
        n_val = max(1, round(n * fracciones[1])) if n >= 3 else 0
        for i, run_id in enumerate(runs):
            if i < n_train:
                destino = 'train'
            elif i < n_train + n_val:
                destino = 'val'
            else:
                destino = 'test'
            asignacion[run_id] = destino
            particiones[destino].extend(por_run[run_id])
    particiones['_asignacion'] = asignacion  # type: ignore[assignment]
    return particiones


def generar(dir_runs: Optional[Path] = None,
            fracciones: Tuple[float, float, float] = FRACCIONES_DEFECTO) -> Dict:
    """Consolida corridas y escribe dataset + splits + manifiesto."""
    asegurar_directorios()
    filas = recolectar_corridas(dir_runs)
    if not filas:
        raise FileNotFoundError(
            f'No hay corridas con intervals.csv en {dir_runs or DIR_RESULTS_RUNS}. '
            f'Ejecutar primero corridas/campañas (experimentos.runner / .campania).')

    columnas = list(filas[0].keys())
    escribir_csv(RUTA_CONSOLIDADO, filas, columnas)

    particiones = particionar_por_corrida(filas, fracciones)
    asignacion: Dict[str, str] = particiones.pop('_asignacion')  # type: ignore[arg-type]
    for nombre in ('train', 'val', 'test'):
        escribir_csv(DIR_DATA_SPLITS / f'{nombre}.csv',
                     particiones[nombre], columnas)

    manifiesto = {
        'generado_en': datetime.now().isoformat(timespec='seconds'),
        'n_filas': len(filas),
        'n_corridas': len(asignacion),
        'fracciones': list(fracciones),
        'semilla_split': SEMILLA_SPLIT,
        'filas_por_particion': {k: len(v) for k, v in particiones.items()},
        'corridas_por_particion': {
            k: sorted(r for r, d in asignacion.items() if d == k)
            for k in ('train', 'val', 'test')},
        'columnas': columnas,
    }
    RUTA_MANIFIESTO.write_text(
        json.dumps(manifiesto, indent=2, ensure_ascii=False), encoding='utf-8')
    return manifiesto


def cargar_particion(nombre: str) -> List[Dict]:
    """Lee data/splits/<nombre>.csv (train | val | test)."""
    ruta = DIR_DATA_SPLITS / f'{nombre}.csv'
    if not ruta.exists():
        raise FileNotFoundError(
            f'{ruta} no existe; generar primero: python -m experimentos.dataset')
    return leer_csv(ruta)


def main(argv: Optional[List[str]] = None):
    p = argparse.ArgumentParser(description='Dataset temporal para la IA')
    p.add_argument('--resumen', action='store_true',
                   help='mostrar el manifiesto existente sin regenerar')
    a = p.parse_args(argv)

    if a.resumen and RUTA_MANIFIESTO.exists():
        manifiesto = json.loads(RUTA_MANIFIESTO.read_text(encoding='utf-8'))
    else:
        manifiesto = generar()
    print(json.dumps(manifiesto, indent=2, ensure_ascii=False))
    return manifiesto


if __name__ == '__main__':
    main()
