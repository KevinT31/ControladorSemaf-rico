# -*- coding: utf-8 -*-
"""
Calibración del controlador de fase (`difuso_fase`) y de sus variantes con
predictor (`difuso_ia`), según la fase 2 de PROTOCOLO_DIFUSO_IA.md.

Solo usa semillas de entrenamiento (101-104 alta, 101-103 media) y de
validación (201-204 / 201-203). El plan fijo de referencia se toma de los
archivos de desarrollo ya generados con las mismas semillas.

Uso:
    python calibrar_fase.py sin-ia --workers 10 --salida resultados/calibracion_fase.json
    python calibrar_fase.py ia --base resultados/calibracion_fase.json \
        --salida resultados/calibracion_fase_ia.json
"""
import argparse
import json
import multiprocessing as mp
import random
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

CFG = {'alta': str(AQUI / 'escenarios/lima-centro/comparacion.sumocfg'),
       'media': str(AQUI / 'escenarios/lima-centro/comparacion_media.sumocfg')}
DEV = {'alta': AQUI / 'resultados/difuso_fase_ALTA_desarrollo.json',
       'media': AQUI / 'resultados/difuso_fase_MEDIA_desarrollo.json'}
ENTRENAMIENTO = {'alta': [101, 102, 103, 104], 'media': [101, 102, 103]}
VALIDACION = {'alta': [201, 202, 203, 204], 'media': [201, 202, 203]}
N_ALEATORIOS, N_LOCALES, TOP_K = 40, 20, 3
SEMILLA_BUSQUEDA = 20261011
DEFECTO = {'seleccion': 'rotacion', 'w_out': 0.0, 't_base': 25.0, 't_verde_max': 45.0,
           'gap_umbral_s': 2.0, 'gap_considera_mov': False, 't_starve': 45.0,
           'umbral_skip': 1.0, 'w_mov': 0.4, 'k_ext_cola': 1.0}
IA_ABIERTA = {'ia_gate_sat': 1e9, 'ia_gate_dens': 1e9}
MARGEN_IA = 0.01


def referencia_fijo():
    ref = {}
    for esc, ruta in DEV.items():
        d = json.loads(ruta.read_text(encoding='utf-8'))
        for r in d['por_estrategia']['fijo']:
            ref[(esc, r['seed'])] = {'tviaje': r['tviaje_media_s'], 'dstop': r['demora_media_s']}
    return ref


def _trabajo(args):
    esc, semilla, estrategia, params = args
    import comparacion_multibaseline as M
    try:
        r = M.ejecutar_estrategia(CFG[esc], semilla, 700, estrategia, 25, control_params=dict(params))
        dg = r.get('diagnostico_control', {})
        return args, {'tviaje': r['tviaje_media_s'], 'dstop': r['demora_media_s'],
                      'verde_max': dg.get('verde_continuo_max_s'), 'errores': dg.get('errores_paso', 0)}
    except Exception as e:
        return args, {'error': repr(e)}


def evaluar(pool, candidatos, conjunto, ref, estrategia):
    pares = [(e, s) for e, ss in conjunto.items() for s in ss]
    trabajos = [(e, s, estrategia, c) for c in candidatos for (e, s) in pares]
    res = {}
    for args, r in pool.imap_unordered(_trabajo, trabajos, chunksize=1):
        res[(json.dumps(args[3], sort_keys=True), args[0], args[1])] = r
    salida = []
    for c in candidatos:
        clave = json.dumps(c, sort_keys=True)
        terms, ok, vmax = [], True, 0.0
        for (e, s) in pares:
            r = res[(clave, e, s)]
            if 'error' in r or r['errores']:
                ok = False
                break
            f = ref[(e, s)]
            vmax = max(vmax, r['verde_max'] or 0.0)
            terms.append(0.5 * r['tviaje'] / f['tviaje'] + 0.5 * r['dstop'] / f['dstop'])
        salida.append({'params': c, 'J': st.mean(terms) if ok else float('inf'), 'verde_max': vmax})
    return salida


def muestrear(rng):
    sel = rng.choice(['rotacion', 'presion'])
    return {'seleccion': sel,
            'w_out': round(rng.uniform(0.0, 1.0), 3) if sel == 'presion' else 0.0,
            't_base': round(rng.uniform(15, 35), 1),
            't_verde_max': round(rng.uniform(30, 60), 1),
            'gap_umbral_s': round(rng.uniform(1.0, 4.0), 1),
            'gap_considera_mov': rng.random() < 0.5,
            't_starve': round(rng.uniform(30, 90), 1),
            'umbral_skip': round(rng.uniform(0.5, 3.0), 2),
            'w_mov': round(rng.uniform(0.0, 1.0), 2),
            'k_ext_cola': round(rng.uniform(0.0, 2.0), 2)}


def perturbar(p, rng):
    def m(v, lo, hi, e, d=2):
        return round(min(hi, max(lo, v + rng.gauss(0, e))), d)
    q = dict(p)
    q['t_base'] = m(p['t_base'], 15, 35, 3, 1)
    q['t_verde_max'] = m(p['t_verde_max'], 30, 60, 4, 1)
    q['gap_umbral_s'] = m(p['gap_umbral_s'], 1.0, 4.0, 0.4, 1)
    q['t_starve'] = m(p['t_starve'], 30, 90, 8, 1)
    q['umbral_skip'] = m(p['umbral_skip'], 0.5, 3.0, 0.3)
    q['w_mov'] = m(p['w_mov'], 0.0, 1.0, 0.1)
    q['k_ext_cola'] = m(p['k_ext_cola'], 0.0, 2.0, 0.2)
    if p['seleccion'] == 'presion':
        q['w_out'] = m(p['w_out'], 0.0, 1.0, 0.1, 3)
    if rng.random() < 0.15:
        q['gap_considera_mov'] = not p['gap_considera_mov']
    return q


def sin_ia(workers, salida):
    rng = random.Random(SEMILLA_BUSQUEDA)
    ref = referencia_fijo()
    reg = {}
    with mp.get_context('spawn').Pool(workers) as pool:
        cands = [dict(DEFECTO)] + [muestrear(rng) for _ in range(N_ALEATORIOS)]
        ent = evaluar(pool, cands, ENTRENAMIENTO, ref, 'difuso_fase')
        mejor = min(ent, key=lambda r: r['J'])
        print(f"Aleatoria: defecto J={ent[0]['J']:.4f}, mejor J={mejor['J']:.4f}", flush=True)
        loc = evaluar(pool, [perturbar(mejor['params'], rng) for _ in range(N_LOCALES)],
                      ENTRENAMIENTO, ref, 'difuso_fase')
        ent += loc
        print(f"Local: mejor J={min(r['J'] for r in loc):.4f}", flush=True)
        top = sorted(ent, key=lambda r: r['J'])[:TOP_K]
        if not any(r['params'] == DEFECTO for r in top):
            top.append(ent[0])  # el defecto siempre se valida como referencia
        val = evaluar(pool, [r['params'] for r in top], VALIDACION, ref, 'difuso_fase')
        for t, v in zip(top, val):
            t['J_valid'] = v['J']
            t['verde_max_valid'] = v['verde_max']
            print(f"  top J_ent={t['J']:.4f} J_val={v['J']:.4f} {t['params']}", flush=True)
        candidatos_val = [t for t in top if t['params'] != DEFECTO] or top
        elegido = min(candidatos_val, key=lambda r: r['J_valid'])
        defecto_val = next(t['J_valid'] for t in top if t['params'] == DEFECTO)
    out = {'generado': datetime.now().isoformat(timespec='seconds'),
           'protocolo': {'entrenamiento': ENTRENAMIENTO, 'validacion': VALIDACION,
                         'n_aleatorios': N_ALEATORIOS, 'n_locales': N_LOCALES, 'top_k': TOP_K,
                         'semilla_busqueda': SEMILLA_BUSQUEDA},
           'defecto': {'params': DEFECTO, 'J_entrenamiento': ent[0]['J'], 'J_validacion': defecto_val},
           'parametros': elegido['params'], 'J_entrenamiento': elegido['J'],
           'J_validacion': elegido['J_valid'], 'registro': ent, 'top': top}
    Path(salida).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Guardado en', salida)


def con_ia(workers, base, salida):
    ref = referencia_fijo()
    b = json.loads(Path(base).read_text(encoding='utf-8'))
    mejor = b['parametros']
    variantes = {
        'guardia_ext': {**mejor, **IA_ABIERTA, 'modo_ia': 'guardia', 'ia_ext': True},
        'guardia_margen1': {**mejor, **IA_ABIERTA, 'modo_ia': 'guardia', 'ia_margen_veto': 1.0},
        'mezcla_b03': {**mejor, **IA_ABIERTA, 'modo_ia': 'mezcla', 'beta': 0.3},
        'mezcla_b05': {**mejor, **IA_ABIERTA, 'modo_ia': 'mezcla', 'beta': 0.5},
    }
    with mp.get_context('spawn').Pool(workers) as pool:
        val = evaluar(pool, list(variantes.values()), VALIDACION, ref, 'difuso_ia')
    filas = []
    for (nombre, p), v in zip(variantes.items(), val):
        filas.append({'variante': nombre, 'params': p, 'J_validacion': v['J']})
        print(f"  {nombre}: J_val={v['J']:.4f}", flush=True)
    j_sin = b['J_validacion']
    mejor_ia = min(filas, key=lambda r: r['J_validacion'])
    adopta = mejor_ia['J_validacion'] < j_sin - MARGEN_IA
    out = {'generado': datetime.now().isoformat(timespec='seconds'), 'J_validacion_sin_ia': j_sin,
           'margen_requerido': MARGEN_IA, 'variantes': filas, 'mejor_variante': mejor_ia,
           'se_adopta_ia': adopta}
    Path(salida).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Sin IA J_val=%.4f; mejor IA %s J_val=%.4f; se adopta IA: %s'
          % (j_sin, mejor_ia['variante'], mejor_ia['J_validacion'], adopta))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('fase', choices=['sin-ia', 'ia'])
    ap.add_argument('--workers', type=int, default=max(1, (mp.cpu_count() or 2) - 2))
    ap.add_argument('--base', default='')
    ap.add_argument('--salida', required=True)
    a = ap.parse_args()
    if a.fase == 'sin-ia':
        sin_ia(a.workers, a.salida)
    else:
        con_ia(a.workers, a.base, a.salida)
