"""Une las siete estrategias archivadas con las dos réplicas nuevas completas."""
import argparse
import json
from pathlib import Path


def unir(base, nuevas):
    for clave in ('cfg', 'pasos', 'semillas', 'huellas_sha256', 'sumo'):
        if base[clave] != nuevas[clave]:
            raise ValueError(f'Campañas incompatibles: {clave}')
    if nuevas['errores']:
        raise ValueError(f'Hay {len(nuevas["errores"])} réplicas fallidas')
    esperado = set(base['semillas'])
    for estrategia, replicas in nuevas['por_estrategia'].items():
        if {r['seed'] for r in replicas} != esperado or len(replicas) != len(esperado):
            raise ValueError(f'Semillas incompletas o repetidas: {estrategia}')
        if estrategia in base['por_estrategia']:
            raise ValueError(f'Estrategia ya archivada: {estrategia}')
        base['por_estrategia'][estrategia] = replicas
    base['anexo_experimento'] = {
        'control_params': nuevas['control_params'],
        'generado': nuevas['generado'],
        'estrategias': list(nuevas['por_estrategia']),
    }
    return base


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('base', type=Path)
    p.add_argument('nuevas', type=Path)
    p.add_argument('salida', type=Path)
    a = p.parse_args()
    resultado = unir(json.loads(a.base.read_text(encoding='utf-8')),
                     json.loads(a.nuevas.read_text(encoding='utf-8')))
    a.salida.write_text(json.dumps(resultado, indent=2, ensure_ascii=False),
                        encoding='utf-8')
