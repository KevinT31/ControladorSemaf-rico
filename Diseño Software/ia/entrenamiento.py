"""
Entrenamiento de la CNN-LSTM desde el dataset real (data/splits/).

Lee train/val/test generados por experimentos.dataset (split POR CORRIDA, sin
fuga), ajusta el escalador SOLO con train, entrena con Adam + MSE y parada
temprana sobre val, y evalúa en test contra la LÍNEA BASE DE PERSISTENCIA
(ICV_{t+1} = ICV_t): si la red no supera a persistencia, no aporta.

Artefactos (ia/artifacts/): modelo_cnn_lstm.pt, escalador.json, config.json.

CLI (desde 'Diseño Software/'):
  python -m ia.entrenamiento --epocas 150 --paciencia 20
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

RAIZ_SOFTWARE = Path(__file__).resolve().parent.parent   # Diseño Software/
for _p in (str(RAIZ_SOFTWARE), str(RAIZ_SOFTWARE / 'integracion-sumo')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ia.secuencias import (CARACTERISTICAS, OBJETIVOS, VENTANA_DEFECTO,
                           EscaladorMinMax, construir_secuencias)  # noqa: E402
from ia.modelo import ModeloCNNLSTM  # noqa: E402

DIR_ARTIFACTS = Path(__file__).resolve().parent / 'artifacts'
RUTA_MODELO = DIR_ARTIFACTS / 'modelo_cnn_lstm.pt'
RUTA_ESCALADOR = DIR_ARTIFACTS / 'escalador.json'
RUTA_CONFIG = DIR_ARTIFACTS / 'config.json'


def _tensores(filas: List[Dict], ventana: int,
              escalador: Optional[EscaladorMinMax]
              ) -> Tuple[torch.Tensor, torch.Tensor, EscaladorMinMax]:
    X, y = construir_secuencias(filas, ventana=ventana)
    if not X:
        raise ValueError('Partición sin secuencias suficientes '
                         f'(ventana={ventana}); generar más corridas.')
    if escalador is None:
        escalador = EscaladorMinMax().ajustar(X)
    Xs = escalador.transformar(X)
    return (torch.tensor(Xs, dtype=torch.float32),
            torch.tensor(y, dtype=torch.float32), escalador)


def _metricas(pred: torch.Tensor, real: torch.Tensor) -> Dict[str, float]:
    err = pred - real
    out = {'mse': float((err ** 2).mean()),
           'mae': float(err.abs().mean()),
           'rmse': float(math.sqrt(float((err ** 2).mean())))}
    for j, nombre in enumerate(OBJETIVOS):
        out[f'mae_{nombre}'] = float(err[:, j].abs().mean())
    return out


def _persistencia(X: torch.Tensor, y: torch.Tensor,
                  escalador: EscaladorMinMax) -> Dict[str, float]:
    """Línea base: predecir que el ICV futuro = ICV del último intervalo.

    X está escalado; se des-escalan las columnas de ICV para comparar en
    unidades reales de ICV [0,1].
    """
    idx = [CARACTERISTICAS.index(c) for c in OBJETIVOS]
    ultimo = X[:, -1, idx].clone()
    for k, j in enumerate(idx):
        rango = escalador.maximos[j] - escalador.minimos[j]
        ultimo[:, k] = ultimo[:, k] * rango + escalador.minimos[j]
    return _metricas(ultimo, y)


def entrenar(epocas: int = 150, ventana: int = VENTANA_DEFECTO,
             lr: float = 1e-3, batch: int = 64, paciencia: int = 20,
             canales: int = 32, oculto: int = 64, semilla: int = 7) -> Dict:
    from experimentos.dataset import cargar_particion

    torch.manual_seed(semilla)
    t0 = time.time()

    escalador: Optional[EscaladorMinMax] = None
    tensores = {}
    for nombre in ('train', 'val', 'test'):
        X, y, escalador = _tensores(cargar_particion(nombre), ventana, escalador)
        tensores[nombre] = (X, y)
    n_train, n_val, n_test = (len(tensores[k][0]) for k in ('train', 'val', 'test'))
    print(f'Secuencias: train={n_train} val={n_val} test={n_test} '
          f'(ventana={ventana}, {len(CARACTERISTICAS)} características)')

    modelo = ModeloCNNLSTM(len(CARACTERISTICAS), canales=canales, oculto=oculto)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=lr)
    perdida = nn.MSELoss()
    cargador = DataLoader(TensorDataset(*tensores['train']),
                          batch_size=batch, shuffle=True)

    mejor_val = float('inf')
    mejor_estado = None
    mejor_epoca = 0
    sin_mejora = 0
    for epoca in range(1, epocas + 1):
        modelo.train()
        for Xb, yb in cargador:
            optimizador.zero_grad()
            perdida(modelo(Xb), yb).backward()
            optimizador.step()

        modelo.eval()
        with torch.no_grad():
            val_mse = float(perdida(modelo(tensores['val'][0]),
                                    tensores['val'][1]))
        if val_mse < mejor_val - 1e-6:
            mejor_val, mejor_epoca, sin_mejora = val_mse, epoca, 0
            mejor_estado = {k: v.clone() for k, v in modelo.state_dict().items()}
        else:
            sin_mejora += 1
        if epoca % 10 == 0 or sin_mejora == 0:
            print(f'  época {epoca:3d}  val_mse={val_mse:.6f}'
                  f'{"  *" if sin_mejora == 0 else ""}')
        if sin_mejora >= paciencia:
            print(f'  parada temprana en época {epoca} '
                  f'(mejor: {mejor_epoca}, val_mse={mejor_val:.6f})')
            break

    if mejor_estado is not None:
        modelo.load_state_dict(mejor_estado)
    modelo.eval()
    with torch.no_grad():
        met_test = _metricas(modelo(tensores['test'][0]), tensores['test'][1])
        met_persist = _persistencia(*tensores['test'], escalador)

    config = {
        'entrenado_en': datetime.now().isoformat(timespec='seconds'),
        'ventana': ventana,
        'caracteristicas': CARACTERISTICAS,
        'objetivos': OBJETIVOS,
        'hiperparametros': modelo.hiperparametros,
        'optimizacion': {'lr': lr, 'batch': batch, 'epocas_max': epocas,
                         'paciencia': paciencia, 'semilla': semilla,
                         'mejor_epoca': mejor_epoca,
                         'mejor_val_mse': round(mejor_val, 6)},
        'secuencias': {'train': n_train, 'val': n_val, 'test': n_test},
        'metricas_test': {k: round(v, 6) for k, v in met_test.items()},
        'baseline_persistencia_test': {k: round(v, 6)
                                       for k, v in met_persist.items()},
        'supera_persistencia': met_test['mae'] < met_persist['mae'],
        'duracion_s': round(time.time() - t0, 1),
    }

    DIR_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    torch.save(modelo.state_dict(), RUTA_MODELO)
    RUTA_ESCALADOR.write_text(json.dumps(escalador.como_dict(), indent=2),
                              encoding='utf-8')
    RUTA_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False),
                           encoding='utf-8')

    print(f"\nTest  : MAE={met_test['mae']:.4f}  RMSE={met_test['rmse']:.4f}  "
          f"(NS {met_test['mae_icv_ns']:.4f} / EO {met_test['mae_icv_ew']:.4f})")
    print(f"Persistencia: MAE={met_persist['mae']:.4f}  "
          f"RMSE={met_persist['rmse']:.4f}")
    print(f"¿Supera a persistencia?: {'SÍ' if config['supera_persistencia'] else 'NO'}")
    print(f'Artefactos en {DIR_ARTIFACTS}')
    return config


def main(argv: Optional[List[str]] = None) -> Dict:
    p = argparse.ArgumentParser(description='Entrenar CNN-LSTM de ICV')
    p.add_argument('--epocas', type=int, default=150)
    p.add_argument('--ventana', type=int, default=VENTANA_DEFECTO)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--batch', type=int, default=64)
    p.add_argument('--paciencia', type=int, default=20)
    p.add_argument('--canales', type=int, default=32)
    p.add_argument('--oculto', type=int, default=64)
    p.add_argument('--semilla', type=int, default=7)
    a = p.parse_args(argv)
    return entrenar(epocas=a.epocas, ventana=a.ventana, lr=a.lr, batch=a.batch,
                    paciencia=a.paciencia, canales=a.canales, oculto=a.oculto,
                    semilla=a.semilla)


if __name__ == '__main__':
    main()
