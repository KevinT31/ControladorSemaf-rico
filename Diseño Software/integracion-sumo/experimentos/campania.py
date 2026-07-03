"""
Campañas experimentales multi-semilla con estadística pareada.

Ejecuta una matriz {controlador} x {demanda} x {semilla} de corridas reales de
SUMO (todas comparten semilla/demanda -> comparación PAREADA) y contrasta cada
controlador contra la línea base con:
  - t de Student pareada (scipy.stats.ttest_rel) + IC95% de la diferencia
  - Wilcoxon de rangos con signo (no paramétrica, robusta a no-normalidad)

Artefactos por campaña (results/control_comparison/<campania_id>/):
  resumenes.csv     una fila por corrida (los resumen.json apilados)
  estadistica.json  contrastes por métrica/demanda/controlador
  reporte.md        tabla legible para la tesis

CLI:
  python -m experimentos.campania --controladores fixed fuzzy \
      --demandas media punta --semillas 1 2 3 4 5 6 7 8
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .entorno import DIR_RESULTS_COMPARACION, asegurar_directorios
from .runner import ConfigExperimento, ejecutar_experimento
from .almacen import escribir_csv

logger = logging.getLogger(__name__)

#: métricas del resumen que se contrastan (nombre -> mejor si)
METRICAS_CONTRASTE = {
    'demora_media_s': 'menor',
    'throughput_total': 'mayor',
    'icv_medio': 'menor',        # promedio de icv_medio_ns / icv_medio_ew
    'cola_media': 'menor',       # promedio de cola_media_ns / cola_media_ew
    'espera_media': 'menor',
    'vel_media': 'mayor',
}


@dataclass
class ConfigCampania:
    controladores: List[str] = field(default_factory=lambda: ['fixed', 'fuzzy'])
    demandas: List[str] = field(default_factory=lambda: ['media'])
    semillas: List[int] = field(default_factory=lambda: list(range(1, 11)))
    escenario: str = 'cruce-simple'
    pasos: int = 3600
    intervalo_control: int = 25
    linea_base: str = 'fixed'
    etiqueta: Optional[str] = None    # sufijo del directorio de salida
    guardar_runs: bool = True         # False = solo resúmenes (sin CSVs por corrida)

    @property
    def campania_id(self) -> str:
        et = f'_{self.etiqueta}' if self.etiqueta else ''
        return (f'{self.escenario}_{"-".join(self.demandas)}'
                f'_n{len(self.semillas)}{et}')


def _metricas_derivadas(resumen: Dict) -> Dict[str, float]:
    """Extrae las métricas de contraste de un resumen de corrida."""
    return {
        'demora_media_s': resumen['demora_media_s'],
        'throughput_total': float(resumen['throughput_total']),
        'icv_medio': (resumen['icv_medio_ns'] + resumen['icv_medio_ew']) / 2.0,
        'cola_media': (resumen['cola_media_ns'] + resumen['cola_media_ew']) / 2.0,
        'espera_media': (resumen['espera_media_ns'] + resumen['espera_media_ew']) / 2.0,
        'vel_media': (resumen['vel_media_ns'] + resumen['vel_media_ew']) / 2.0,
    }


def _contraste_pareado(base: List[float], trat: List[float],
                       mejor: str) -> Dict:
    """Estadística pareada tratamiento-vs-base para UNA métrica.

    diferencia = tratamiento - base (por semilla). 'mejora' respeta el sentido
    de la métrica ('menor' => diferencia negativa es mejora).
    """
    from scipy import stats

    n = len(base)
    difs = [t - b for b, t in zip(base, trat)]
    media_dif = statistics.fmean(difs)
    media_base = statistics.fmean(base)
    media_trat = statistics.fmean(trat)

    resultado = {
        'n': n,
        'media_base': round(media_base, 4),
        'media_tratamiento': round(media_trat, 4),
        'diferencia_media': round(media_dif, 4),
        'mejora_pct': round(
            (media_dif / media_base * 100.0) if media_base else 0.0, 2),
        'gana_por_semilla': sum(
            1 for d in difs if (d < 0 if mejor == 'menor' else d > 0)),
    }

    if n >= 2 and any(d != 0 for d in difs):
        sd = statistics.stdev(difs)
        t_res = stats.ttest_rel(trat, base)
        # IC95% de la diferencia media (t de Student, n-1 gl)
        margen = stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)
        resultado.update({
            't_pareada': round(float(t_res.statistic), 4),
            'p_t_pareada': float(t_res.pvalue),
            'ic95_diferencia': [round(media_dif - margen, 4),
                                round(media_dif + margen, 4)],
        })
        try:
            w_res = stats.wilcoxon(trat, base)
            resultado.update({
                'wilcoxon_W': float(w_res.statistic),
                'p_wilcoxon': float(w_res.pvalue),
            })
        except ValueError as e:  # p.ej. muy pocas diferencias no nulas
            resultado['wilcoxon_error'] = str(e)
    else:
        resultado['nota'] = 'sin variacion o n<2: no se calculan contrastes'
    return resultado


def ejecutar_campania(cfg: ConfigCampania) -> Dict:
    """Corre la matriz completa y devuelve el informe (dict) ya persistido."""
    asegurar_directorios()
    destino = DIR_RESULTS_COMPARACION / cfg.campania_id
    destino.mkdir(parents=True, exist_ok=True)

    resumenes: List[Dict] = []
    total = len(cfg.controladores) * len(cfg.demandas) * len(cfg.semillas)
    hecho = 0
    for demanda in cfg.demandas:
        for controlador in cfg.controladores:
            for semilla in cfg.semillas:
                hecho += 1
                logger.info(f'[{hecho}/{total}] {controlador} demanda={demanda} '
                            f'semilla={semilla}')
                resumen = ejecutar_experimento(ConfigExperimento(
                    controlador=controlador, escenario=cfg.escenario,
                    demanda=demanda, semilla=semilla, pasos=cfg.pasos,
                    intervalo_control=cfg.intervalo_control,
                    guardar=cfg.guardar_runs, persistir_sqlite=cfg.guardar_runs))
                resumenes.append(resumen)

    escribir_csv(destino / 'resumenes.csv', resumenes)

    # ---------------- estadística pareada por demanda ----------------
    def _fila(c: str, d: str, s: int) -> Optional[Dict]:
        for r in resumenes:
            if (r['controller_type'] == c and r['demand_level'] == d
                    and r['seed'] == s):
                return r
        return None

    contrastes: Dict[str, Dict] = {}
    for demanda in cfg.demandas:
        por_controlador = {}
        for controlador in cfg.controladores:
            if controlador == cfg.linea_base:
                continue
            por_metrica = {}
            base_v, trat_v = [], []
            for metrica, mejor in METRICAS_CONTRASTE.items():
                base_v = []
                trat_v = []
                for s in cfg.semillas:
                    rb = _fila(cfg.linea_base, demanda, s)
                    rt = _fila(controlador, demanda, s)
                    if rb is None or rt is None:
                        continue
                    base_v.append(_metricas_derivadas(rb)[metrica])
                    trat_v.append(_metricas_derivadas(rt)[metrica])
                if base_v:
                    por_metrica[metrica] = _contraste_pareado(base_v, trat_v, mejor)
            por_controlador[controlador] = por_metrica
        contrastes[demanda] = por_controlador

    informe = {
        'campania_id': cfg.campania_id,
        'escenario': cfg.escenario,
        'linea_base': cfg.linea_base,
        'controladores': cfg.controladores,
        'demandas': cfg.demandas,
        'semillas': cfg.semillas,
        'pasos': cfg.pasos,
        'control_interval': cfg.intervalo_control,
        'n_corridas': len(resumenes),
        'ejecutado_en': datetime.now().isoformat(timespec='seconds'),
        'contrastes': contrastes,
        'dir_salida': str(destino),
    }
    (destino / 'estadistica.json').write_text(
        json.dumps(informe, indent=2, ensure_ascii=False), encoding='utf-8')
    (destino / 'reporte.md').write_text(
        generar_reporte_md(informe), encoding='utf-8')
    return informe


def generar_reporte_md(informe: Dict) -> str:
    """Tabla legible (una por demanda) con los contrastes vs línea base."""
    li = [f'# Campaña {informe["campania_id"]}', '',
          f'- Escenario: `{informe["escenario"]}` | línea base: '
          f'`{informe["linea_base"]}` | semillas: {len(informe["semillas"])} | '
          f'pasos: {informe["pasos"]} (intervalo {informe["control_interval"]} s)',
          f'- Ejecutado: {informe["ejecutado_en"]} | corridas: {informe["n_corridas"]}',
          '']
    for demanda, por_ctrl in informe['contrastes'].items():
        li.append(f'## Demanda: {demanda}')
        for ctrl, por_met in por_ctrl.items():
            li += [f'### {ctrl} vs {informe["linea_base"]}', '',
                   '| Métrica | Base | ' + ctrl + ' | Δ | Δ% | gana | p (t) | p (Wilcoxon) |',
                   '|---|---|---|---|---|---|---|---|']
            for met, c in por_met.items():
                p_t = c.get('p_t_pareada')
                p_w = c.get('p_wilcoxon')
                li.append(
                    f'| {met} | {c["media_base"]:.3f} | '
                    f'{c["media_tratamiento"]:.3f} | {c["diferencia_media"]:+.3f} | '
                    f'{c["mejora_pct"]:+.1f}% | {c["gana_por_semilla"]}/{c["n"]} | '
                    f'{f"{p_t:.4g}" if p_t is not None else "-"} | '
                    f'{f"{p_w:.4g}" if p_w is not None else "-"} |')
            li.append('')
    return '\n'.join(li) + '\n'


def main(argv: Optional[List[str]] = None) -> Dict:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    p = argparse.ArgumentParser(description='Campaña experimental multi-semilla')
    p.add_argument('--controladores', nargs='+',
                   default=['fixed', 'fuzzy'])
    p.add_argument('--demandas', nargs='+', default=['media'],
                   choices=['baja', 'media', 'alta', 'punta'])
    p.add_argument('--semillas', nargs='+', type=int,
                   default=list(range(1, 11)))
    p.add_argument('--escenario', default='cruce-simple')
    p.add_argument('--pasos', type=int, default=3600)
    p.add_argument('--intervalo', type=int, default=25)
    p.add_argument('--linea-base', default='fixed')
    p.add_argument('--etiqueta', default=None)
    p.add_argument('--sin-runs', action='store_true',
                   help='no persistir CSVs por corrida (solo resúmenes)')
    a = p.parse_args(argv)

    cfg = ConfigCampania(
        controladores=a.controladores, demandas=a.demandas,
        semillas=a.semillas, escenario=a.escenario, pasos=a.pasos,
        intervalo_control=a.intervalo, linea_base=a.linea_base,
        etiqueta=a.etiqueta, guardar_runs=not a.sin_runs)
    informe = ejecutar_campania(cfg)
    print(json.dumps({k: v for k, v in informe.items() if k != 'contrastes'},
                     indent=2, ensure_ascii=False))
    print(f"\nReporte: {informe['dir_salida']}\\reporte.md")
    return informe


if __name__ == '__main__':
    main()
