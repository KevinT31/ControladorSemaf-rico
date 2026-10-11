"""Calcula el objetivo registrado por par escenario-semilla de validación."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent / 'resultados'


def leer(nombre):
    return json.loads((BASE / nombre).read_text(encoding='utf-8'))


if __name__ == '__main__':
    objetivos = {'difuso_fase': [], 'difuso_ia': []}
    for escenario in ('ALTA', 'MEDIA'):
        fase = leer(f'difuso_fase_{escenario}_desarrollo.json')
        ia = leer(f'difuso_ia_abierta_{escenario}_validacion.json')
        fijo = {r['seed']: r for r in fase['por_estrategia']['fijo']}
        for estrategia, datos in (('difuso_fase', fase), ('difuso_ia', ia)):
            for r in datos['por_estrategia'][estrategia]:
                if r['seed'] < 201:
                    continue
                f = fijo[r['seed']]
                j = (0.5 * r['tviaje_media_s'] / f['tviaje_media_s'] +
                     0.5 * r['demora_media_s'] / f['demora_media_s'])
                objetivos[estrategia].append(j)
                print(escenario, estrategia, r['seed'], round(j, 5),
                      'predicciones', r['diagnostico_control']['predicciones'],
                      'vetos', r['diagnostico_control']['vetos_skip'])
    for estrategia, valores in objetivos.items():
        print('J medio', estrategia, sum(valores) / len(valores))
