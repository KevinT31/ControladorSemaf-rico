"""
Persistencia de experimentos (F6): CSV como formato primario de análisis y
SQLite (stdlib, sin ORM) como registro estructurado consultable.

Tablas: experiment_runs, interval_metrics, controller_decisions,
safety_events, ai_predictions. Todo lo que se guarda proviene de corridas
reales de SUMO (source_type='sumo'); los flujos demo NUNCA pasan por aquí.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .entorno import RAIZ_SOFTWARE

RUTA_BD = RAIZ_SOFTWARE / 'base-datos' / 'experimentos.db'

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS experiment_runs (
    run_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    demand_level TEXT NOT NULL,
    controller_type TEXT NOT NULL,
    seed INTEGER NOT NULL,
    steps INTEGER NOT NULL,
    control_interval INTEGER NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'sumo',
    started_at TEXT,
    finished_at TEXT,
    summary_json TEXT
);
CREATE TABLE IF NOT EXISTS interval_metrics (
    run_id TEXT NOT NULL,
    time_step REAL NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (run_id, time_step)
);
CREATE TABLE IF NOT EXISTS controller_decisions (
    run_id TEXT NOT NULL,
    time_step REAL NOT NULL,
    payload_json TEXT NOT NULL,
    PRIMARY KEY (run_id, time_step)
);
CREATE TABLE IF NOT EXISTS safety_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    time_step REAL NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_predictions (
    run_id TEXT NOT NULL,
    time_step REAL NOT NULL,
    icv_pred_ns REAL, icv_pred_eo REAL,
    icv_actual_ns REAL, icv_actual_eo REAL,
    beta REAL, fallback INTEGER, motivo_fallback TEXT,
    PRIMARY KEY (run_id, time_step)
);
"""


class AlmacenExperimentos:
    """Registro SQLite + volcado CSV de una corrida experimental."""

    def __init__(self, ruta_bd: Optional[Path] = None):
        self.ruta_bd = Path(ruta_bd) if ruta_bd else RUTA_BD
        self.ruta_bd.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(self.ruta_bd))
        self._con.executescript(_ESQUEMA)
        self._con.commit()

    # ------------------------------------------------------------------ #
    def iniciar_run(self, run_id: str, cfg: Dict):
        self._con.execute(
            "INSERT OR REPLACE INTO experiment_runs "
            "(run_id, scenario_id, demand_level, controller_type, seed, steps, "
            " control_interval, source_type, started_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, cfg['scenario_id'], cfg['demand_level'], cfg['controller_type'],
             cfg['seed'], cfg['steps'], cfg['control_interval'], 'sumo',
             datetime.now().isoformat(timespec='seconds')))
        # una corrida repetida reemplaza sus filas anteriores (reproducibilidad)
        for tabla in ('interval_metrics', 'controller_decisions',
                      'safety_events', 'ai_predictions'):
            self._con.execute(f"DELETE FROM {tabla} WHERE run_id=?", (run_id,))
        self._con.commit()

    def cerrar_run(self, run_id: str, resumen: Dict):
        self._con.execute(
            "UPDATE experiment_runs SET finished_at=?, summary_json=? WHERE run_id=?",
            (datetime.now().isoformat(timespec='seconds'),
             json.dumps(resumen, ensure_ascii=False), run_id))
        self._con.commit()

    def guardar_intervalos(self, run_id: str, filas: List[Dict]):
        self._con.executemany(
            "INSERT OR REPLACE INTO interval_metrics VALUES (?,?,?)",
            [(run_id, f['time_step'], json.dumps(f, ensure_ascii=False)) for f in filas])
        self._con.commit()

    def guardar_decisiones(self, run_id: str, filas: List[Dict]):
        self._con.executemany(
            "INSERT OR REPLACE INTO controller_decisions VALUES (?,?,?)",
            [(run_id, f['time_step'], json.dumps(f, ensure_ascii=False)) for f in filas])
        # las decisiones con componente IA también van a ai_predictions
        con_ia = [f for f in filas if f.get('icv_pred_ns') is not None
                  or f.get('fallback')]
        self._con.executemany(
            "INSERT OR REPLACE INTO ai_predictions VALUES (?,?,?,?,?,?,?,?,?)",
            [(run_id, f['time_step'], f.get('icv_pred_ns'), f.get('icv_pred_eo'),
              f.get('icv_actual_ns'), f.get('icv_actual_eo'), f.get('beta'),
              int(bool(f.get('fallback'))), f.get('motivo_fallback'))
             for f in con_ia])
        self._con.commit()

    def guardar_eventos_seguridad(self, run_id: str, eventos: List[Dict]):
        self._con.executemany(
            "INSERT INTO safety_events (run_id, time_step, payload_json) VALUES (?,?,?)",
            [(run_id, e.get('t_sim', 0.0), json.dumps(e, ensure_ascii=False))
             for e in eventos])
        self._con.commit()

    def cerrar(self):
        self._con.close()


# --------------------------------------------------------------------------- #
# CSV helpers (formato primario de análisis)
# --------------------------------------------------------------------------- #
def escribir_csv(ruta: Path, filas: List[Dict], columnas: Optional[List[str]] = None):
    """Escribe filas como CSV (crea directorios). Devuelve la ruta."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not filas:
        ruta.write_text('', encoding='utf-8')
        return ruta
    if columnas is None:
        columnas = list(filas[0].keys())
    with open(ruta, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction='ignore')
        w.writeheader()
        w.writerows(filas)
    return ruta


def anexar_csv(ruta: Path, filas: List[Dict], columnas: List[str]):
    """Anexa filas a un CSV global (crea con cabecera si no existe)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ruta.exists()
    with open(ruta, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction='ignore')
        if nuevo:
            w.writeheader()
        w.writerows(filas)
    return ruta
