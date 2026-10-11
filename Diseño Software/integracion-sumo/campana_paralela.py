# -*- coding: utf-8 -*-
"""
Ejecuta la campaña multi-línea-base de comparacion_multibaseline.py en
paralelo (un proceso SUMO por par estrategia-semilla) y guarda el mismo JSON
que la versión secuencial, más los metadatos necesarios para auditar la corrida
(versión de SUMO, huellas SHA-256 de la red, la demanda y la configuración).

Ejemplo (demanda alta, 30 semillas, todas las estrategias):
    python campana_paralela.py --cfg escenarios/lima-centro/comparacion.sumocfg \
        --semillas 1-30 --salida resultados/multibaseline_ALTA30.json
"""
import argparse
import hashlib
import json
import multiprocessing as mp
import platform
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))


def parsear_semillas(texto: str):
    semillas = []
    for parte in texto.split(','):
        if '-' in parte:
            a, b = parte.split('-')
            semillas.extend(range(int(a), int(b) + 1))
        else:
            semillas.append(int(parte))
    return semillas


def _trabajo(args):
    cfg, semilla, pasos, estrategia, intervalo = args
    import comparacion_multibaseline as M
    try:
        r = M.ejecutar_estrategia(cfg, semilla, pasos, estrategia, intervalo)
        r['seed'] = semilla
        return estrategia, semilla, r, None
    except Exception as e:  # una réplica fallida no debe abortar la campaña
        return estrategia, semilla, None, repr(e)


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def huellas_entradas(cfg: Path) -> dict:
    texto = cfg.read_text(encoding='utf-8')
    huellas = {cfg.name: _sha256(cfg)}
    for etiqueta in ('net-file', 'route-files'):
        m = re.search(rf'<{etiqueta} value="([^"]+)"', texto)
        if m and (cfg.parent / m.group(1)).exists():
            huellas[m.group(1)] = _sha256(cfg.parent / m.group(1))
    return huellas


def version_sumo() -> str:
    try:
        salida = subprocess.run(['sumo', '--version'], capture_output=True,
                                text=True, check=True).stdout
        return salida.splitlines()[0].strip()
    except Exception:
        return 'desconocida'


def campana(cfg: Path, semillas, estrategias, pasos, intervalo, workers):
    import comparacion_multibaseline as M
    trabajos = [(str(cfg), s, pasos, e, intervalo)
                for e in estrategias for s in semillas]
    por_estrategia = {e: [] for e in estrategias}
    errores = []
    with mp.get_context('spawn').Pool(workers) as pool:
        for k, (e, s, r, err) in enumerate(pool.imap_unordered(_trabajo, trabajos), 1):
            if err:
                errores.append({'estrategia': e, 'seed': s, 'error': err})
                print(f'[{k}/{len(trabajos)}] {e} seed {s}: ERROR {err}', flush=True)
            else:
                por_estrategia[e].append(r)
                print(f'[{k}/{len(trabajos)}] {e:12s} seed {s:>3} '
                      f'tviaje={r["tviaje_media_s"]:.1f} demora={r["demora_media_s"]:.1f} '
                      f'thr={r["throughput"]}', flush=True)
    for e in estrategias:
        por_estrategia[e].sort(key=lambda r: r['seed'])
    return {
        'generado': datetime.now().isoformat(timespec='seconds'),
        'cfg': cfg.name, 'pasos': pasos, 'intervalo_control': intervalo,
        'semillas': list(semillas),
        'motor': 'libsumo' if M.USANDO_LIBSUMO else 'traci',
        'limites_verde': [M.T_MIN, M.T_MAX],
        'sumo': version_sumo(), 'python': platform.python_version(),
        'huellas_sha256': huellas_entradas(cfg),
        'errores': errores, 'por_estrategia': por_estrategia,
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('--cfg', default=str(AQUI / 'escenarios/lima-centro/comparacion.sumocfg'))
    ap.add_argument('--semillas', default='1-30')
    ap.add_argument('--estrategias', default=','.join(['fijo', 'actuated', 'webster',
                    'webster_mod', 'maxpressure', 'difuso']))
    ap.add_argument('--pasos', type=int, default=700)
    ap.add_argument('--intervalo', type=int, default=25)
    ap.add_argument('--workers', type=int, default=max(1, (mp.cpu_count() or 2) - 2))
    ap.add_argument('--salida', required=True)
    ap.add_argument('--anexar', default='',
                    help='JSON previo al que se añaden las estrategias ejecutadas '
                         '(mismas semillas y configuración)')
    a = ap.parse_args()
    out = campana(Path(a.cfg).resolve(), parsear_semillas(a.semillas),
                  a.estrategias.split(','), a.pasos, a.intervalo, a.workers)
    if a.anexar:
        previo = json.loads(Path(a.anexar).read_text(encoding='utf-8'))
        for clave in ('cfg', 'pasos', 'intervalo_control', 'semillas'):
            if previo[clave] != out[clave]:
                sys.exit(f'No se puede anexar: {clave} difiere del JSON previo.')
        if previo['huellas_sha256'] != out['huellas_sha256']:
            sys.exit('No se puede anexar: las huellas de red/demanda difieren.')
        previo['por_estrategia'].update(out['por_estrategia'])
        previo['errores'] = previo.get('errores', []) + out['errores']
        previo.setdefault('anexos', []).append(
            {'generado': out['generado'], 'estrategias': a.estrategias.split(',')})
        out = previo
    destino = Path(a.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Guardado en', destino)
