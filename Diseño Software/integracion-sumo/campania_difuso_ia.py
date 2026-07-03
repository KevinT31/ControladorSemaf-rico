# -*- coding: utf-8 -*-
"""
Campaña final de difuso_ia sobre los benchmarks multibaseline de la tesis.

Corre el controlador propuesto en sus variantes:
  - difuso_ia        : modo 'guardia' (CNN-LSTM veta saltos, con gating)
  - difuso_ia_off    : modo 'off' (MISMO controlador, IA apagada) -> el
                       contraste pareado difuso_ia vs difuso_ia_off es el
                       APORTE NETO de la CNN-LSTM, reproducible desde código
  - difuso_ia_sombra : (opcional, --sombra) predice y registra sin actuar,
                       para medir MAE online y vetos hipotéticos por régimen

con las MISMAS semillas/cfg de las campañas guardadas y lo fusiona con los
resultados existentes (fijo/actuated/webster/webster_mod/maxpressure/difuso)
en archivos con sufijo nuevo (defecto _v3), sin tocar los originales. Añade
contrastes pareados (t + Wilcoxon) de difuso_ia contra cada línea base y
contra difuso_ia_off.

Cada corrida difuso_ia escribe su traza por inferencia/decisión en
resultados/logs_ia/<base>/<variante>_seed<k>.csv (cola actual vs predicha,
veto, gate, régimen, fallback, latencia) para auditoría post-hoc.

Uso:
  python campania_difuso_ia.py --alta 30 --media 10 [--sombra] [--sufijo v3]
"""
import argparse
import csv
import json
import statistics as st
from pathlib import Path

import comparacion_multibaseline as M

_INTEG = Path(__file__).parent
_RES = _INTEG / 'resultados'

#: variantes del controlador propuesto: nombre -> params_ia
VARIANTES = {
    'difuso_ia': {'modo_ia': 'guardia'},
    'difuso_ia_off': {'modo_ia': 'off'},
}
VARIANTE_SOMBRA = {'difuso_ia_sombra': {'modo_ia': 'sombra'}}


def correr_variante(nombre: str, params_ia: dict, cfg: str, semillas,
                    pasos: int = 700, checkpoint: Path = None,
                    dir_logs: Path = None, estrategia: str = 'difuso_ia'):
    """Corre las semillas de una variante/estrategia con CHECKPOINT (reanudable)."""
    hechos = {}
    if checkpoint and checkpoint.exists():
        hechos = {r['seed']: r for r in
                  json.loads(checkpoint.read_text(encoding='utf-8'))}
        print(f'  ({nombre}: checkpoint con {len(hechos)} semillas)',
              flush=True)
    reps = []
    for s in semillas:
        if s in hechos:
            reps.append(hechos[s])
            continue
        p_ia = None
        if estrategia == 'difuso_ia':
            p_ia = dict(params_ia or {})
            if dir_logs is not None:
                p_ia['log_ia'] = str(dir_logs / f'{nombre}_seed{s}.csv')
        r = M.ejecutar_estrategia(cfg, s, pasos, estrategia, params_ia=p_ia)
        r['seed'] = s
        reps.append(r)
        ia = r.get('ia', {})
        print(f"[{nombre:16s} seed {s:>3}] demora={r['demora_media_s']:.1f} "
              f"tviaje={r['tviaje_media_s']:.1f} thr={r['throughput']} "
              f"tele={r['teleports']} vetos={ia.get('vetos_skip', 0)} "
              f"sombra={ia.get('vetos_sombra', 0)} "
              f"fallb={ia.get('fallbacks_ia', 0)}", flush=True)
        if checkpoint:
            checkpoint.write_text(json.dumps(reps, ensure_ascii=False),
                                  encoding='utf-8')
    return reps


def contrastes(reps_ia, por_estrategia, semillas):
    """t pareada + Wilcoxon de difuso_ia vs cada estrategia guardada."""
    from scipy import stats
    out = {}
    ia_por_seed = {r['seed']: r for r in reps_ia}
    metricas = ['demora_media_s', 'demora_media_veh_s', 'tviaje_media_s',
                'throughput', 'ICV_red', 'teleports']
    for est, reps in por_estrategia.items():
        base_por_seed = {r['seed']: r for r in reps}
        comunes = [s for s in semillas
                   if s in ia_por_seed and s in base_por_seed]
        if len(comunes) < 3:
            continue
        por_met = {}
        for met in metricas:
            if not all(met in ia_por_seed[s] and met in base_por_seed[s]
                       for s in comunes):
                continue   # métrica ausente en corridas antiguas
            a = [ia_por_seed[s][met] for s in comunes]
            b = [base_por_seed[s][met] for s in comunes]
            difs = [x - y for x, y in zip(a, b)]
            res = {
                'n': len(comunes),
                'media_difuso_ia': round(st.mean(a), 3),
                'media_base': round(st.mean(b), 3),
                'mejora_pct': round((st.mean(a) - st.mean(b))
                                    / st.mean(b) * 100.0, 2)
                if st.mean(b) else 0.0,
            }
            if any(d != 0 for d in difs):
                t = stats.ttest_rel(a, b)
                res['p_t_pareada'] = float(t.pvalue)
                try:
                    w = stats.wilcoxon(a, b)
                    res['p_wilcoxon'] = float(w.pvalue)
                except ValueError:
                    pass
            por_met[met] = res
        out[est] = por_met
    return out


BASES = ['fijo', 'actuated', 'webster', 'webster_mod', 'maxpressure', 'difuso']


def fusionar(nombre_base: str, cfg: str, n_seeds: int, pasos: int = 700,
             sufijo: str = 'v3', con_sombra: bool = False,
             rerun_bases: bool = False):
    ruta_json = _RES / f'{nombre_base}.json'
    datos = json.loads(ruta_json.read_text(encoding='utf-8'))
    semillas = datos['semillas'][:n_seeds]
    dir_logs = _RES / 'logs_ia' / nombre_base
    dir_logs.mkdir(parents=True, exist_ok=True)

    variantes = dict(VARIANTES)
    if con_sombra:
        variantes.update(VARIANTE_SOMBRA)

    datos['git_hash'] = M._git_hash()
    datos['difuso_ia_variantes'] = {}

    if rerun_bases:
        # Las líneas base se RE-EJECUTAN con el código corregido (flujo por
        # cruces, transición segura de maxpressure, teleports/backlog):
        # comparar contra corridas antiguas mediría dos aparatos distintos.
        datos['bases_reejecutadas'] = True
        for est in BASES:
            print(f'== {nombre_base}: {est} x {len(semillas)} semillas ==',
                  flush=True)
            datos['por_estrategia'][est] = correr_variante(
                est, None, cfg, semillas, pasos,
                checkpoint=_RES / f'{est}_checkpoint_{nombre_base}_{sufijo}.json',
                estrategia=est)
    reps_por_variante = {}
    for nombre, p_ia in variantes.items():
        print(f'== {nombre_base}: {nombre} x {len(semillas)} semillas ==',
              flush=True)
        reps = correr_variante(
            nombre, p_ia, cfg, semillas, pasos,
            checkpoint=_RES / f'{nombre}_checkpoint_{nombre_base}_{sufijo}.json',
            dir_logs=dir_logs)
        reps_por_variante[nombre] = reps
        datos['por_estrategia'][nombre] = reps
        datos['difuso_ia_variantes'][nombre] = \
            M._params_difuso_ia_efectivos(p_ia)
        if reps and not datos.get('sumo_version'):
            datos['sumo_version'] = reps[0].get('sumo_version', '')

    bases = {k: v for k, v in datos['por_estrategia'].items()
             if k != 'difuso_ia'}
    datos['contrastes_difuso_ia'] = contrastes(
        reps_por_variante['difuso_ia'], bases, semillas)

    (_RES / f'{nombre_base}_{sufijo}.json').write_text(
        json.dumps(datos, indent=2, ensure_ascii=False), encoding='utf-8')

    # CSV agregado
    filas = []
    for est, reps in datos['por_estrategia'].items():
        ag = M._agregar(reps)
        ag['estrategia'] = est
        ag['n_semillas'] = len(reps)
        filas.append(ag)
    cols = ['estrategia', 'n_semillas'] + [
        c for c in filas[0] if c not in ('estrategia', 'n_semillas')]
    with open(_RES / f'{nombre_base}_{sufijo}.csv', 'w', newline='',
              encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for fila in filas:
            w.writerow(fila)
    print(f'Guardado {nombre_base}_{sufijo}.json/csv', flush=True)
    return datos


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--alta', type=int, default=30)
    ap.add_argument('--media', type=int, default=10)
    ap.add_argument('--pasos', type=int, default=700)
    ap.add_argument('--sufijo', type=str, default='v3',
                    help='sufijo de los archivos de salida (no pisa v2)')
    ap.add_argument('--sombra', action='store_true',
                    help='añade la variante difuso_ia_sombra (predice sin actuar)')
    ap.add_argument('--rerun-bases', action='store_true',
                    help='re-ejecuta también las líneas base con el código '
                         'corregido (comparación con un solo aparato de medición)')
    a = ap.parse_args()
    esc = _INTEG / 'escenarios' / 'lima-centro'
    if a.alta:
        fusionar('multibaseline_ALTA30', str(esc / 'comparacion.sumocfg'),
                 a.alta, pasos=a.pasos, sufijo=a.sufijo, con_sombra=a.sombra,
                 rerun_bases=a.rerun_bases)
    if a.media:
        fusionar('multibaseline_MEDIA10',
                 str(esc / 'comparacion_media.sumocfg'), a.media,
                 pasos=a.pasos, sufijo=a.sufijo, con_sombra=a.sombra,
                 rerun_bases=a.rerun_bases)
    print('CAMPANIA FINAL LISTA', flush=True)
