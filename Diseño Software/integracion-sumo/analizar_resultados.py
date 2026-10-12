# -*- coding: utf-8 -*-
"""
Análisis estadístico de una campaña de campana_paralela.py.

Calcula, a partir del JSON de resultados:
  - media y desviación estándar por estrategia y métrica;
  - contraste pareado (t de Student) de cada controlador difuso frente al plan
    fijo, con intervalo de confianza del 95 %, d de Cohen pareado, número de
    semillas favorables y ajuste de Holm sobre la familia de métricas;
  - prueba de Friedman (tamaño del efecto W de Kendall) entre estrategias;
  - contrastes pareados de Wilcoxon entre cada controlador difuso y cada línea
    base, con ajuste de Holm por familia (métrica x controlador difuso).

Uso:
    python analizar_resultados.py resultados/multibaseline_ALTA30.json \
        --salida resultados/analisis_ALTA30.json
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

METRICAS = ('ICV_red', 'Vavg_red', 'QL_red', 'q_red', 'throughput',
            'demora_media_s', 'tviaje_media_s', 'tviaje_mediana_s')
MENORES_MEJOR = {'ICV_red', 'QL_red', 'demora_media_s', 'tviaje_media_s',
                 'tviaje_mediana_s', 'tiempo_red_por_veh_s'}
# métrica sin sesgo de supervivencia (solo en campañas que la registran)
METRICAS_TODAS = METRICAS + ('tiempo_red_por_veh_s',)


def metricas_presentes(datos):
    reps = [r for rs in datos['por_estrategia'].values() for r in rs]
    return [m for m in METRICAS_TODAS if all(r.get(m) is not None for r in reps)]
DIFUSOS = ('difuso', 'difuso_opt', 'difuso_fase', 'difuso_ia', 'difuso_fase_cal', 'difuso_ia_cal')
# controladores de fase del experimento: se comparan contra todas las demás estrategias
FASE = ('difuso_fase', 'difuso_ia', 'difuso_fase_cal', 'difuso_ia_cal')


def vector(datos, estrategia, metrica):
    reps = sorted(datos['por_estrategia'][estrategia], key=lambda r: r['seed'])
    return np.asarray([r[metrica] for r in reps], dtype=float)


def holm(p_values):
    orden = sorted(p_values, key=p_values.get)
    m, previo, ajustados = len(orden), 0.0, {}
    for i, clave in enumerate(orden):
        previo = max(previo, min(1.0, (m - i) * p_values[clave]))
        ajustados[clave] = previo
    return ajustados


def resumen(datos):
    filas = {}
    for e in datos['por_estrategia']:
        filas[e] = {'n': len(datos['por_estrategia'][e])}
        for m in metricas_presentes(datos):
            v = vector(datos, e, m)
            filas[e][m] = {'media': float(v.mean()),
                           'sd': float(v.std(ddof=1)) if len(v) > 1 else 0.0}
    return filas


def pareado_vs_fijo(datos, controlador, base='fijo'):
    """Contraste pareado de `controlador` frente a `base` (por defecto, el plan fijo)."""
    filas, p_crudos = [], {}
    for m in metricas_presentes(datos):
        fijo, ctrl = vector(datos, base, m), vector(datos, controlador, m)
        dif = ctrl - fijo
        res = stats.ttest_rel(ctrl, fijo)
        margen = float(stats.t.ppf(0.975, len(dif) - 1) * stats.sem(dif))
        mejor = (ctrl < fijo) if m in MENORES_MEJOR else (ctrl > fijo)
        cambio = (fijo.mean() - ctrl.mean()) / fijo.mean() * 100.0
        if m not in MENORES_MEJOR:
            cambio = -cambio
        sd = float(dif.std(ddof=1))
        p_crudos[m] = float(res.pvalue)
        filas.append({
            'metrica': m, 'n': int(len(dif)),
            base: float(fijo.mean()), controlador: float(ctrl.mean()),
            'diferencia_media': float(dif.mean()),
            'ic95': [float(dif.mean() - margen), float(dif.mean() + margen)],
            'cambio_favorable_pct': float(cambio),
            'semillas_favorables': int(mejor.sum()),
            't': float(res.statistic), 'p': float(res.pvalue),
            'cohen_dz': float(dif.mean() / sd) if sd > 0 else math.nan,
        })
    ajustados = holm(p_crudos)
    for f in filas:
        f['p_holm'] = ajustados[f['metrica']]
    return filas


def friedman(datos, metrica, estrategias):
    muestras = [vector(datos, e, metrica) for e in estrategias]
    r = stats.friedmanchisquare(*muestras)
    n, k = len(muestras[0]), len(muestras)
    return {'metrica': metrica, 'estrategias': list(estrategias), 'n_bloques': n,
            'chi2': float(r.statistic), 'p': float(r.pvalue),
            'kendall_w': float(r.statistic / (n * (k - 1)))}


def wilcoxon_vs_lineas_base(datos, controlador, metrica, bases):
    p_crudos, filas = {}, []
    for b in bases:
        x, y = vector(datos, controlador, metrica), vector(datos, b, metrica)
        res = stats.wilcoxon(x, y)
        p_crudos[b] = float(res.pvalue)
        filas.append({'frente_a': b, 'media_controlador': float(x.mean()),
                      'media_base': float(y.mean()),
                      'p': float(res.pvalue)})
    ajustados = holm(p_crudos)
    for f in filas:
        f['p_holm'] = ajustados[f['frente_a']]
    return filas


def analizar(datos):
    estrategias = list(datos['por_estrategia'])
    difusos = [d for d in DIFUSOS if d in estrategias]
    bases = [e for e in estrategias if e not in DIFUSOS]
    out = {'metadatos': {k: v for k, v in datos.items() if k != 'por_estrategia'},
           'resumen': resumen(datos), 'pareado_vs_fijo': {}, 'friedman': {},
           'wilcoxon_vs_lineas_base': {}}
    for d in difusos:
        out['pareado_vs_fijo'][d] = pareado_vs_fijo(datos, d)
        rivales = ([e for e in estrategias if e != d] if d in FASE else bases)
        out['wilcoxon_vs_lineas_base'][d] = {
            m: wilcoxon_vs_lineas_base(datos, d, m, [b for b in rivales if b != 'fijo'] + ['fijo'])
            for m in ('demora_media_s', 'tviaje_media_s')}
    for m in ('demora_media_s', 'tviaje_media_s'):
        out['friedman'][m] = friedman(datos, m, estrategias)
    # ablaciones: (variante, referencia)
    pares = {'ablacion_ia': ('difuso_ia', 'difuso_fase'),
             'ablacion_ia_cal': ('difuso_ia_cal', 'difuso_fase_cal'),
             'efecto_calibracion': ('difuso_fase_cal', 'difuso_fase')}
    for nombre, (a, b) in pares.items():
        if a in estrategias and b in estrategias:
            out[nombre] = pareado_vs_fijo(datos, a, base=b)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('entrada', type=Path)
    ap.add_argument('--salida', type=Path, required=True)
    a = ap.parse_args()
    datos = json.loads(a.entrada.read_text(encoding='utf-8'))
    res = analizar(datos)
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Guardado en', a.salida)
    sys.exit(0)
