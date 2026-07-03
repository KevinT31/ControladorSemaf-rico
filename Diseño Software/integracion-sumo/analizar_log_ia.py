# -*- coding: utf-8 -*-
"""
Análisis post-hoc de la traza por inferencia de difuso_ia (log_ia CSV).

Cruza cada predicción/veto registrado en las filas `decision` con la cola
REAL observada en la siguiente fila `muestra` de la misma (tls, fase), para
responder con datos (no con supuestos):

  - MAE online de la CNN-LSTM (global y por régimen de densidad de red).
  - VETOS: cuántos acertaron (llegó cola >= umbral al siguiente tick: el
    salto habría desatendido un pelotón real) y cuántos fueron FALSOS
    (no llegó nada: el veto retuvo verde sin necesidad).
  - FALSOS PERMISOS: fases sin cola actual ni predicha (candidatas a salto
    no vetadas) donde SÍ llegó cola real al siguiente tick (la IA debió
    vetar y no lo hizo).

Uso (desde integracion-sumo/):
  python analizar_log_ia.py resultados/logs_ia/multibaseline_MEDIA10/difuso_ia_seed*.csv
"""
import argparse
import csv
import glob
import json
import statistics as st
from collections import defaultdict


def _f(x, defecto=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return defecto


def analizar(rutas, umbral=1.0, grid=15, gate_dens=4.0):
    muestras = defaultdict(dict)      # (archivo, tls, fase) -> {t: cola}
    decisiones = []
    for ruta in rutas:
        with open(ruta, newline='', encoding='utf-8') as f:
            for fila in csv.DictReader(f):
                clave = (ruta, fila['tls'], fila['fase_idx'])
                t = _f(fila['t'])
                if fila['evento'] == 'muestra':
                    muestras[clave][t] = _f(fila['cola_veh'], 0.0)
                elif fila['evento'] == 'decision':
                    decisiones.append((clave, t, fila))

    errores = []                       # (|pred-real|, dens_red)
    vetos = {'acertados': 0, 'falsos': 0, 'sin_muestra': 0}
    permisos = {'correctos': 0, 'falsos': 0}
    n_pred = 0
    for clave, t, fila in decisiones:
        pred = _f(fila['cola_pred_veh'])
        if pred is None:
            continue
        n_pred += 1
        # cola real en el siguiente tick de rejilla posterior a la decisión
        t_next = (int(t) // grid + 1) * grid
        real = muestras[clave].get(float(t_next))
        if real is None:
            if fila['vetada'] == '1':
                vetos['sin_muestra'] += 1
            continue
        dens = _f(fila['dens_red'], 0.0)
        errores.append((abs(pred - real), dens))
        if fila['vetada'] == '1':
            if real >= umbral:
                vetos['acertados'] += 1
            else:
                vetos['falsos'] += 1
        else:
            cola = _f(fila['cola_veh'], 0.0)
            if fila['seleccionada'] != '1' and cola < umbral and pred < umbral:
                # candidata a salto no vetada: ¿llegó cola de verdad?
                if real >= umbral:
                    permisos['falsos'] += 1
                else:
                    permisos['correctos'] += 1

    def _mae(pares):
        return round(st.mean(e for e, _ in pares), 3) if pares else None

    por_regimen = {
        'dens<=2 (baja)': [p for p in errores if p[1] <= 2.0],
        f'2<dens<={gate_dens:g} (media)': [p for p in errores
                                           if 2.0 < p[1] <= gate_dens],
        f'dens>{gate_dens:g} (gate cerrado/sombra)': [p for p in errores
                                                      if p[1] > gate_dens],
    }
    total_v = vetos['acertados'] + vetos['falsos']
    total_p = permisos['correctos'] + permisos['falsos']
    return {
        'archivos': len(rutas),
        'predicciones_evaluadas': n_pred,
        'con_muestra_siguiente': len(errores),
        'mae_online_veh': _mae(errores),
        'mae_por_regimen': {k: {'n': len(v), 'mae': _mae(v)}
                            for k, v in por_regimen.items()},
        'vetos': {**vetos,
                  'precision': round(vetos['acertados'] / total_v, 3)
                  if total_v else None},
        'permisos_de_salto': {**permisos,
                              'tasa_falso_permiso':
                              round(permisos['falsos'] / total_p, 3)
                              if total_p else None},
        'umbral_veh': umbral,
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('rutas', nargs='+', help='CSV(s) de log_ia (admite glob)')
    ap.add_argument('--umbral', type=float, default=1.0)
    ap.add_argument('--grid', type=int, default=15)
    a = ap.parse_args()
    rutas = sorted(r for patron in a.rutas for r in glob.glob(patron))
    if not rutas:
        raise SystemExit('sin archivos que analizar')
    print(json.dumps(analizar(rutas, umbral=a.umbral, grid=a.grid),
                     indent=2, ensure_ascii=False))
