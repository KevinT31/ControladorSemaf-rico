"""
Runner experimental: ejecuta UNA corrida de control semafórico sobre SUMO con
trazabilidad completa por intervalo de control.

Lazo:  SUMO -> sensado por eje (NS/EO) -> ICV+PI reales -> controlador
       -> envoltura de seguridad -> actuación (setProgramLogic) -> registro.

Artefactos por corrida (results/runs/<run_id>/):
  intervals.csv   una fila por intervalo (esquema del dataset de IA)
  decisions.csv   decisión trazada (ICV actual/predicho, beta, reglas, clipping)
  safety_events.csv
  resumen.json    métricas agregadas de la corrida
Además se registra en SQLite (base-datos/experimentos.db).

CLI:
  python -m experimentos.runner --controlador fuzzy --demanda punta --semilla 7
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .entorno import (traci, USANDO_LIBSUMO, sumolib, ruta_escenario,
                      DIR_RESULTS_RUNS, asegurar_directorios)
from .base import ControladorTrafico, EstadoInterseccion
from .interseccion_sumo import InterseccionSUMO, construir_estado_eje
from .seguridad import EnvolturaSeguridad
from .controladores import crear_controlador
from .almacen import AlmacenExperimentos, escribir_csv

from nucleo.indice_congestion import CalculadorICV, ParametrosInterseccion

logger = logging.getLogger(__name__)

#: Esquema del dataset (una fila por intervalo de control)
COLUMNAS_INTERVALOS = [
    'run_id', 'seed', 'scenario_id', 'demand_level', 'controller_type',
    'source_type', 'time_step', 'control_interval', 'tls_id', 'phase_id',
    'green_ns', 'green_ew',
    'queue_ns', 'queue_ew', 'queue_max_ns', 'queue_max_ew',
    'waiting_ns', 'waiting_ew', 'speed_ns', 'speed_ew',
    'flow_ns', 'flow_ew', 'density_ns', 'density_ew',
    'occupancy_ns', 'occupancy_ew', 'icv_ns', 'icv_ew', 'pi_ns', 'pi_ew',
    'throughput_interval', 'mean_delay_interval',
    'safety_event', 'fallback_active',
]

COLUMNAS_DECISIONES = [
    'run_id', 'time_step', 'controller_type',
    'icv_actual_ns', 'icv_actual_eo', 'icv_pred_ns', 'icv_pred_eo',
    'beta', 'icv_control_ns', 'icv_control_eo',
    'fallback', 'motivo_fallback',
    'delta_pct_ns', 'delta_pct_eo',
    'verde_solicitado_ns', 'verde_solicitado_eo',
    'verde_aplicado_ns', 'verde_aplicado_eo',
    'modo_seguro', 'n_correcciones_seguridad',
    'reglas_ns', 'reglas_eo',
]


@dataclass
class ConfigExperimento:
    controlador: str = 'fuzzy'          # fixed | fuzzy | fuzzy_predictive_ai
    escenario: str = 'cruce-simple'
    demanda: str = 'media'              # baja | media | alta | punta
    semilla: int = 42
    pasos: int = 3600                   # 1 paso = 1 s de simulación
    intervalo_control: int = 25
    tls_id: str = 'C'
    beta: float = 0.40                  # peso de la predicción (solo IA)
    alpha: float = 0.35                 # suavizado EMA de verdes (fuzzy/IA)
    ventana: int = 8                    # W del buffer predictivo
    guardar: bool = True
    persistir_sqlite: bool = True
    dir_salida: Optional[str] = None
    sumocfg: Optional[str] = None       # usar un .sumocfg arbitrario (avanzado)

    @property
    def run_id(self) -> str:
        return (f'{self.escenario}_{self.demanda}_{self.controlador}'
                f'_s{self.semilla}')


def _comando_sumo(cfg: ConfigExperimento) -> List[str]:
    binario = sumolib.checkBinary('sumo')
    cmd = [binario]
    if cfg.sumocfg:
        cmd += ['-c', str(cfg.sumocfg)]
    else:
        carpeta = ruta_escenario(cfg.escenario)
        red = carpeta / 'cruce.net.xml'
        rutas = carpeta / f'demanda_{cfg.demanda}.rou.xml'
        if not red.exists():
            raise FileNotFoundError(
                f'Red no encontrada: {red}\n  -> reconstruir con: '
                f'python "{carpeta / "generar_red.py"}"')
        if not rutas.exists():
            raise FileNotFoundError(f'Demanda no encontrada: {rutas}')
        cmd += ['-n', str(red), '-r', str(rutas)]
    cmd += ['--seed', str(cfg.semilla), '--start', '--quit-on-end',
            '--no-warnings', 'true', '--no-step-log', 'true',
            '--duration-log.disable', 'true', '--time-to-teleport', '300']
    return cmd


def _acumulador_vacio() -> Dict[str, float]:
    return {'n_veh': 0.0, 'cola_veh': 0.0, 'espera_s': 0.0,
            'vel_ms': 0.0, 'ocupacion': 0.0}


def ejecutar_experimento(cfg: ConfigExperimento,
                         controlador: Optional[ControladorTrafico] = None
                         ) -> Dict:
    """Ejecuta una corrida y devuelve el resumen (dict).

    Si `controlador` es None se crea a partir de cfg.controlador.
    """
    asegurar_directorios()
    if controlador is None:
        kwargs = {}
        if cfg.controlador in ('fuzzy', 'fuzzy_predictive_ai'):
            kwargs['alpha_suavizado'] = cfg.alpha
        if cfg.controlador == 'fuzzy_predictive_ai':
            kwargs['beta'] = cfg.beta
            kwargs['ventana'] = cfg.ventana
        controlador = crear_controlador(cfg.controlador, **kwargs)

    run_id = cfg.run_id
    seguridad = EnvolturaSeguridad()
    calc_icv = CalculadorICV(ParametrosInterseccion())

    t0 = time.time()
    traci.start(_comando_sumo(cfg))
    filas_intervalos: List[Dict] = []
    filas_decisiones: List[Dict] = []
    try:
        inter = InterseccionSUMO(cfg.tls_id).preparar()
        controlador.reset({'run_id': run_id, 'tls_id': cfg.tls_id})

        acum = {'ns': _acumulador_vacio(), 'eo': _acumulador_vacio()}
        cola_max = {'ns': 0.0, 'eo': 0.0}
        vistos_eje = {'ns': set(), 'eo': set()}
        nuevos_eje = {'ns': 0, 'eo': 0}
        muestras = 0
        llegadas_intervalo = 0
        demora_intervalo = 0.0
        llegadas_total = 0
        demora_total = 0.0
        intervalo_idx = 0
        verdes_aplicados = inter.verdes_actuales()

        for paso in range(1, cfg.pasos + 1):
            traci.simulationStep()
            # --- sensado instantáneo por eje ---
            for eje in ('ns', 'eo'):
                med = inter.medir_eje_instante(eje)
                a = acum[eje]
                a['n_veh'] += med['n_veh']
                a['cola_veh'] += med['cola_veh']
                a['espera_s'] += med['espera_s']
                a['vel_ms'] += med['vel_ms'] * med['n_veh']  # ponderada por veh
                a['ocupacion'] += med['ocupacion']
                cola_max[eje] = max(cola_max[eje], med['cola_veh'])
                demora_intervalo += med['cola_veh']  # veh detenidos * 1 s
                # flujo: vehículos DISTINTOS que entraron al eje
                for vid in inter.ids_vehiculos_eje(eje):
                    if vid not in vistos_eje[eje]:
                        vistos_eje[eje].add(vid)
                        nuevos_eje[eje] += 1
            llegadas_intervalo += int(traci.simulation.getArrivedNumber())
            muestras += 1

            if paso % cfg.intervalo_control != 0:
                continue

            # ---------- cierre de intervalo: observar / decidir / actuar ----------
            intervalo_idx += 1
            t_sim = float(traci.simulation.getTime())
            estados_eje = {}
            for eje, largo in (('ns', inter.largo_ns_km), ('eo', inter.largo_eo_km)):
                # velocidad ponderada: dividir por sumatoria de vehículos
                a = dict(acum[eje])
                total_veh = a['n_veh']
                a['vel_ms'] = (a['vel_ms'] / total_veh) if total_veh > 0 else 0.0
                a['vel_ms'] *= muestras  # construir_estado_eje divide por muestras
                flujo = nuevos_eje[eje] / cfg.intervalo_control * 60.0
                estados_eje[eje] = construir_estado_eje(
                    a, muestras, flujo, largo, calc_icv, cola_max[eje])

            estado = EstadoInterseccion(
                t_sim=t_sim, intervalo_idx=intervalo_idx,
                ns=estados_eje['ns'], eo=estados_eje['eo'],
                fase_actual=inter.fase_actual(),
                verde_actual_ns=verdes_aplicados[0],
                verde_actual_eo=verdes_aplicados[1],
                llegadas_intervalo=llegadas_intervalo,
                demora_intervalo_veh_s=demora_intervalo,
            )

            controlador.observe(estado)
            accion = controlador.decide(estado)
            accion_segura, res_seg = seguridad.filtrar(accion, estado, t_sim)
            if accion_segura.aplicar:
                inter.aplicar_verdes(accion_segura.verde_ns, accion_segura.verde_eo)
                verdes_aplicados = (accion_segura.verde_ns, accion_segura.verde_eo)

            det = accion_segura.detalle
            hubo_evento_seg = bool(res_seg['modo_seguro'] or res_seg['correcciones'])
            fallback = bool(det.get('fallback', False))

            filas_intervalos.append({
                'run_id': run_id, 'seed': cfg.semilla,
                'scenario_id': cfg.escenario, 'demand_level': cfg.demanda,
                'controller_type': controlador.tipo, 'source_type': 'sumo',
                'time_step': t_sim, 'control_interval': cfg.intervalo_control,
                'tls_id': cfg.tls_id, 'phase_id': estado.fase_actual,
                'green_ns': round(estado.verde_actual_ns, 2),
                'green_ew': round(estado.verde_actual_eo, 2),
                'queue_ns': estado.ns.cola_veh, 'queue_ew': estado.eo.cola_veh,
                'queue_max_ns': estado.ns.cola_max_veh,
                'queue_max_ew': estado.eo.cola_max_veh,
                'waiting_ns': estado.ns.espera_s, 'waiting_ew': estado.eo.espera_s,
                'speed_ns': estado.ns.vel_kmh, 'speed_ew': estado.eo.vel_kmh,
                'flow_ns': estado.ns.flujo_veh_min, 'flow_ew': estado.eo.flujo_veh_min,
                'density_ns': estado.ns.densidad_veh_km,
                'density_ew': estado.eo.densidad_veh_km,
                'occupancy_ns': estado.ns.ocupacion, 'occupancy_ew': estado.eo.ocupacion,
                'icv_ns': estado.ns.icv, 'icv_ew': estado.eo.icv,
                'pi_ns': estado.ns.pi, 'pi_ew': estado.eo.pi,
                'throughput_interval': llegadas_intervalo,
                'mean_delay_interval': round(
                    demora_intervalo / max(1, llegadas_intervalo), 2),
                'safety_event': int(hubo_evento_seg),
                'fallback_active': int(fallback),
            })
            filas_decisiones.append({
                'run_id': run_id, 'time_step': t_sim,
                'controller_type': controlador.tipo,
                'icv_actual_ns': det.get('icv_actual_ns', estado.ns.icv),
                'icv_actual_eo': det.get('icv_actual_eo', estado.eo.icv),
                'icv_pred_ns': det.get('icv_pred_ns'),
                'icv_pred_eo': det.get('icv_pred_eo'),
                'beta': det.get('beta', 0.0),
                'icv_control_ns': det.get('icv_control_ns'),
                'icv_control_eo': det.get('icv_control_eo'),
                'fallback': int(fallback),
                'motivo_fallback': det.get('motivo_fallback'),
                'delta_pct_ns': det.get('delta_pct_ns'),
                'delta_pct_eo': det.get('delta_pct_eo'),
                'verde_solicitado_ns': round(accion.verde_ns, 2),
                'verde_solicitado_eo': round(accion.verde_eo, 2),
                'verde_aplicado_ns': round(accion_segura.verde_ns, 2),
                'verde_aplicado_eo': round(accion_segura.verde_eo, 2),
                'modo_seguro': int(res_seg['modo_seguro']),
                'n_correcciones_seguridad': len(res_seg['correcciones']),
                'reglas_ns': ' | '.join(det.get('reglas_ns', [])),
                'reglas_eo': ' | '.join(det.get('reglas_eo', [])),
            })

            # reiniciar acumuladores del intervalo
            llegadas_total += llegadas_intervalo
            demora_total += demora_intervalo
            acum = {'ns': _acumulador_vacio(), 'eo': _acumulador_vacio()}
            cola_max = {'ns': 0.0, 'eo': 0.0}
            nuevos_eje = {'ns': 0, 'eo': 0}
            muestras = 0
            llegadas_intervalo = 0
            demora_intervalo = 0.0
    finally:
        try:
            traci.close()
        except Exception:
            pass

    duracion = time.time() - t0
    n = max(1, len(filas_intervalos))
    resumen = {
        'run_id': run_id,
        'scenario_id': cfg.escenario, 'demand_level': cfg.demanda,
        'controller_type': controlador.tipo, 'seed': cfg.semilla,
        'steps': cfg.pasos, 'control_interval': cfg.intervalo_control,
        'source_type': 'sumo', 'motor': 'libsumo' if USANDO_LIBSUMO else 'traci',
        'n_intervalos': len(filas_intervalos),
        'throughput_total': llegadas_total,
        'demora_total_veh_s': demora_total,
        'demora_media_s': round(demora_total / max(1, llegadas_total), 2),
        'icv_medio_ns': round(sum(f['icv_ns'] for f in filas_intervalos) / n, 4),
        'icv_medio_ew': round(sum(f['icv_ew'] for f in filas_intervalos) / n, 4),
        'cola_media_ns': round(sum(f['queue_ns'] for f in filas_intervalos) / n, 2),
        'cola_media_ew': round(sum(f['queue_ew'] for f in filas_intervalos) / n, 2),
        'espera_media_ns': round(sum(f['waiting_ns'] for f in filas_intervalos) / n, 2),
        'espera_media_ew': round(sum(f['waiting_ew'] for f in filas_intervalos) / n, 2),
        'vel_media_ns': round(sum(f['speed_ns'] for f in filas_intervalos) / n, 2),
        'vel_media_ew': round(sum(f['speed_ew'] for f in filas_intervalos) / n, 2),
        'eventos_seguridad': sum(f['safety_event'] for f in filas_intervalos),
        'fallbacks': sum(f['fallback_active'] for f in filas_intervalos),
        'duracion_real_s': round(duracion, 1),
        'ejecutado_en': datetime.now().isoformat(timespec='seconds'),
    }
    if hasattr(controlador, 'modelo_disponible'):
        resumen['modelo_ia_disponible'] = bool(controlador.modelo_disponible)

    if cfg.guardar:
        destino = (DIR_RESULTS_RUNS / run_id if cfg.dir_salida is None
                   else Path(cfg.dir_salida))
        destino.mkdir(parents=True, exist_ok=True)
        escribir_csv(destino / 'intervals.csv', filas_intervalos, COLUMNAS_INTERVALOS)
        escribir_csv(destino / 'decisions.csv', filas_decisiones, COLUMNAS_DECISIONES)
        escribir_csv(destino / 'safety_events.csv', seguridad.eventos)
        (destino / 'resumen.json').write_text(
            json.dumps(resumen, indent=2, ensure_ascii=False), encoding='utf-8')
        resumen['dir_salida'] = str(destino)

    if cfg.persistir_sqlite:
        alm = AlmacenExperimentos()
        alm.iniciar_run(run_id, {
            'scenario_id': cfg.escenario, 'demand_level': cfg.demanda,
            'controller_type': controlador.tipo, 'seed': cfg.semilla,
            'steps': cfg.pasos, 'control_interval': cfg.intervalo_control})
        alm.guardar_intervalos(run_id, filas_intervalos)
        alm.guardar_decisiones(run_id, filas_decisiones)
        alm.guardar_eventos_seguridad(run_id, seguridad.eventos)
        alm.cerrar_run(run_id, resumen)
        alm.cerrar()

    return resumen


def main(argv: Optional[List[str]] = None) -> Dict:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    p = argparse.ArgumentParser(description='Corrida experimental de control semafórico sobre SUMO')
    p.add_argument('--controlador', default='fuzzy',
                   choices=['fixed', 'fuzzy', 'fuzzy_predictive_ai'])
    p.add_argument('--escenario', default='cruce-simple')
    p.add_argument('--demanda', default='media',
                   choices=['baja', 'media', 'alta', 'punta'])
    p.add_argument('--semilla', type=int, default=42)
    p.add_argument('--pasos', type=int, default=3600)
    p.add_argument('--intervalo', type=int, default=25)
    p.add_argument('--beta', type=float, default=0.40)
    p.add_argument('--alpha', type=float, default=0.35)
    p.add_argument('--sumocfg', default=None)
    p.add_argument('--sin-guardar', action='store_true')
    a = p.parse_args(argv)

    cfg = ConfigExperimento(
        controlador=a.controlador, escenario=a.escenario, demanda=a.demanda,
        semilla=a.semilla, pasos=a.pasos, intervalo_control=a.intervalo,
        beta=a.beta, alpha=a.alpha, sumocfg=a.sumocfg,
        guardar=not a.sin_guardar, persistir_sqlite=not a.sin_guardar)
    resumen = ejecutar_experimento(cfg)
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    return resumen


if __name__ == '__main__':
    main()
