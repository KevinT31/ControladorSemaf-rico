# -*- coding: utf-8 -*-
"""
Calibración reproducible de los parámetros del controlador difuso en SUMO.

Parámetros ajustados (la base de 12 reglas y los consecuentes no se tocan):
  - puntos_icv = (a, b, c): vértices de las funciones de pertenencia de ICV.
  - puntos_pi  = (a, b, c): ídem para PI.
  - alpha: suavizado exponencial del verde deseado entre decisiones.
  - gamma: exponente de reparto del presupuesto de verde entre fases.

Protocolo (semillas disjuntas para evitar sobreajuste):
  1. Entrenamiento: semillas 101-104 (demanda alta) y 101-103 (demanda media).
     Se evalúan N_ALEATORIOS candidatos por búsqueda aleatoria uniforme y luego
     N_LOCALES perturbaciones del mejor.
  2. Validación: semillas 201-204 / 201-203. Entre los TOP_K mejores del
     entrenamiento se elige el de menor función objetivo en validación.
  3. Prueba: la evalúa campana_paralela.py con la estrategia 'difuso_opt' sobre
     las semillas 1-30 (alta) y 1-10 (media), que no se usaron en 1 ni en 2.

Función objetivo (menor es mejor), promedio sobre pares escenario-semilla:
    J = 0.5 * T_viaje / T_viaje_fijo + 0.5 * D_stop / D_stop_fijo
con el plan fijo evaluado en la misma semilla. Equilibra el tiempo de viaje
medio (MOE principal) y la carga de detención (D_stop), cuyos resultados
iniciales se contraponían.

Uso:
    python calibrar_difuso.py --workers 10 \
        --salida resultados/parametros_difuso_calibrados.json
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

CFG_ALTA = AQUI / 'escenarios/lima-centro/comparacion.sumocfg'
CFG_MEDIA = AQUI / 'escenarios/lima-centro/comparacion_media.sumocfg'
ENTRENAMIENTO = {'alta': list(range(101, 105)), 'media': list(range(101, 104))}
VALIDACION = {'alta': list(range(201, 205)), 'media': list(range(201, 204))}
N_ALEATORIOS, N_LOCALES, TOP_K = 40, 20, 3
SEMILLA_BUSQUEDA = 20260711
BASE = {'alpha': 0.35, 'gamma': 5.0,
        'puntos_icv': (0.2, 0.4, 0.7), 'puntos_pi': (0.3, 0.5, 0.8)}


def _cfg(nombre):
    return str(CFG_ALTA if nombre == 'alta' else CFG_MEDIA)


def _trabajo(args):
    nombre, semilla, estrategia, params = args
    import comparacion_multibaseline as M
    try:
        r = M.ejecutar_estrategia(_cfg(nombre), semilla, 700, estrategia,
                                  25, difuso_params=params)
        return args, {'tviaje': r['tviaje_media_s'], 'dstop': r['demora_media_s']}
    except Exception as e:
        return args, {'error': repr(e)}


def muestrear(rng):
    def tres(lo, hi, sep=0.08):
        while True:
            v = sorted(rng.uniform(lo, hi) for _ in range(3))
            if v[1] - v[0] >= sep and v[2] - v[1] >= sep:
                return tuple(round(x, 3) for x in v)
    return {'alpha': round(rng.uniform(0.1, 1.0), 3),
            'gamma': round(rng.uniform(1.0, 8.0), 3),
            'puntos_icv': tres(0.1, 0.9), 'puntos_pi': tres(0.1, 0.9)}


def perturbar(params, rng, escala=0.08):
    def mover(v, lo, hi, e):
        return min(hi, max(lo, v + rng.gauss(0, e)))
    for _ in range(100):
        icv = sorted(mover(v, 0.05, 0.95, escala) for v in params['puntos_icv'])
        pi = sorted(mover(v, 0.05, 0.95, escala) for v in params['puntos_pi'])
        if all(b - a >= 0.05 for a, b in zip(icv, icv[1:])) and \
           all(b - a >= 0.05 for a, b in zip(pi, pi[1:])):
            return {'alpha': round(mover(params['alpha'], 0.05, 1.0, 0.1), 3),
                    'gamma': round(mover(params['gamma'], 1.0, 10.0, 0.8), 3),
                    'puntos_icv': tuple(round(x, 3) for x in icv),
                    'puntos_pi': tuple(round(x, 3) for x in pi)}
    return params


def evaluar(pool, candidatos, conjunto, ref_fijo):
    """J de cada candidato sobre `conjunto` (dict escenario -> semillas)."""
    pares = [(n, s) for n, ss in conjunto.items() for s in ss]
    trabajos = [(n, s, 'difuso', c) for c in candidatos for (n, s) in pares]
    resultados = {}
    for args, r in pool.imap_unordered(_trabajo, trabajos, chunksize=1):
        resultados[(json.dumps(args[3], sort_keys=True), args[0], args[1])] = r
    out = []
    for c in candidatos:
        clave = json.dumps(c, sort_keys=True)
        terminos, ok = [], True
        for (n, s) in pares:
            r = resultados[(clave, n, s)]
            if 'error' in r:
                ok = False
                break
            f = ref_fijo[(n, s)]
            terminos.append(0.5 * r['tviaje'] / f['tviaje'] + 0.5 * r['dstop'] / f['dstop'])
        out.append(st.mean(terminos) if ok else float('inf'))
    return out


def referencia_fijo(pool, conjuntos):
    pares = sorted({(n, s) for c in conjuntos for n, ss in c.items() for s in ss})
    trabajos = [(n, s, 'fijo', None) for (n, s) in pares]
    ref = {}
    for args, r in pool.imap_unordered(_trabajo, trabajos, chunksize=1):
        ref[(args[0], args[1])] = r
    return ref


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('--workers', type=int, default=max(1, (mp.cpu_count() or 2) - 2))
    ap.add_argument('--salida', required=True)
    a = ap.parse_args()
    rng = random.Random(SEMILLA_BUSQUEDA)
    registro = {'entrenamiento': [], 'validacion': []}

    with mp.get_context('spawn').Pool(a.workers) as pool:
        ref = referencia_fijo(pool, [ENTRENAMIENTO, VALIDACION])
        base_tr = evaluar(pool, [BASE], ENTRENAMIENTO, ref)[0]
        base_va = evaluar(pool, [BASE], VALIDACION, ref)[0]
        print(f'Base (Cap. 6): J_entren={base_tr:.4f} J_valid={base_va:.4f}', flush=True)

        candidatos = [muestrear(rng) for _ in range(N_ALEATORIOS)]
        js = evaluar(pool, candidatos, ENTRENAMIENTO, ref)
        registro['entrenamiento'] += [{'params': c, 'J': j} for c, j in zip(candidatos, js)]
        mejor, j_mejor = min(zip(candidatos, js), key=lambda t: t[1])
        print(f'Búsqueda aleatoria: mejor J={j_mejor:.4f}', flush=True)

        locales = [perturbar(mejor, rng) for _ in range(N_LOCALES)]
        js2 = evaluar(pool, locales, ENTRENAMIENTO, ref)
        registro['entrenamiento'] += [{'params': c, 'J': j} for c, j in zip(locales, js2)]
        print(f'Refinamiento local: mejor J={min(js2):.4f}', flush=True)

        todos = sorted(registro['entrenamiento'], key=lambda r: r['J'])[:TOP_K]
        va = evaluar(pool, [t['params'] for t in todos], VALIDACION, ref)
        for t, j in zip(todos, va):
            registro['validacion'].append({'params': t['params'], 'J_entren': t['J'], 'J_valid': j})
            print(f"  top: J_entren={t['J']:.4f} J_valid={j:.4f} {t['params']}", flush=True)
        elegido = min(registro['validacion'], key=lambda r: r['J_valid'])

    salida = {
        'generado': datetime.now().isoformat(timespec='seconds'),
        'protocolo': {'entrenamiento': ENTRENAMIENTO, 'validacion': VALIDACION,
                      'n_aleatorios': N_ALEATORIOS, 'n_locales': N_LOCALES,
                      'top_k': TOP_K, 'semilla_busqueda': SEMILLA_BUSQUEDA,
                      'objetivo': '0.5*Tviaje/Tviaje_fijo + 0.5*Dstop/Dstop_fijo'},
        'base': {'parametros': BASE, 'J_entrenamiento': base_tr, 'J_validacion': base_va},
        'parametros': elegido['params'],
        'J_entrenamiento': elegido['J_entren'], 'J_validacion': elegido['J_valid'],
        'registro': registro,
    }
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.salida).write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Guardado en', a.salida)


if __name__ == '__main__':
    main()
