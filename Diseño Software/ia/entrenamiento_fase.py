"""
Entrena la CNN-LSTM de cola por fase desde data/fases_lima_centro.csv
(recolectada por difuso_ia con `recolector`). Split por SEMILLA de corrida,
comparación contra persistencia, artefactos en ia/artifacts_fase/.

CLI (desde 'Diseño Software/'):
  python -m ia.entrenamiento_fase --epocas 60
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

RAIZ_SOFTWARE = Path(__file__).resolve().parent.parent
if str(RAIZ_SOFTWARE) not in sys.path:
    sys.path.insert(0, str(RAIZ_SOFTWARE))

from ia.secuencias_fase import (CARACTERISTICAS_FASE, NORMALIZACION_FASE,
                                VENTANA_DEFECTO, construir_secuencias,
                                leer_series, particionar_series)  # noqa: E402
from ia.modelo import ModeloCNNLSTM  # noqa: E402

RUTA_DATOS_DEFECTO = RAIZ_SOFTWARE / 'data' / 'fases_lima_centro.csv'
DIR_ARTIFACTS = Path(__file__).resolve().parent / 'artifacts_fase'


def _metricas(pred: torch.Tensor, real: torch.Tensor) -> Dict[str, float]:
    err = pred - real
    return {'mse': float((err ** 2).mean()),
            'mae': float(err.abs().mean()),
            'rmse': float(math.sqrt(float((err ** 2).mean())))}


def entrenar(ruta_datos: Path = RUTA_DATOS_DEFECTO, epocas: int = 60,
             ventana: int = VENTANA_DEFECTO, lr: float = 1e-3,
             batch: int = 256, paciencia: int = 10, canales: int = 16,
             oculto: int = 32, semilla: int = 7) -> Dict:
    torch.manual_seed(semilla)
    t0 = time.time()

    series = leer_series(Path(ruta_datos))
    partes = particionar_series(series)
    tensores = {}
    for nombre, subser in partes.items():
        X, y = construir_secuencias(subser, ventana=ventana)
        if not X:
            raise ValueError(f'Partición {nombre} sin secuencias')
        tensores[nombre] = (torch.tensor(X, dtype=torch.float32),
                            torch.tensor(y, dtype=torch.float32))
    n_tr, n_va, n_te = (len(tensores[k][0]) for k in ('train', 'val', 'test'))
    print(f'Series: {len(series)} | secuencias train={n_tr} val={n_va} '
          f'test={n_te} (ventana={ventana})')

    modelo = ModeloCNNLSTM(len(CARACTERISTICAS_FASE), canales=canales,
                           oculto=oculto, n_salidas=1)
    opt = torch.optim.Adam(modelo.parameters(), lr=lr)
    perdida = nn.MSELoss()
    cargador = DataLoader(TensorDataset(*tensores['train']),
                          batch_size=batch, shuffle=True)

    mejor_val, mejor_estado, mejor_epoca, sin_mejora = float('inf'), None, 0, 0
    for epoca in range(1, epocas + 1):
        modelo.train()
        for Xb, yb in cargador:
            opt.zero_grad()
            perdida(modelo(Xb), yb).backward()
            opt.step()
        modelo.eval()
        with torch.no_grad():
            val = float(perdida(modelo(tensores['val'][0]), tensores['val'][1]))
        if val < mejor_val - 1e-6:
            mejor_val, mejor_epoca, sin_mejora = val, epoca, 0
            mejor_estado = {k: v.clone() for k, v in modelo.state_dict().items()}
        else:
            sin_mejora += 1
        if epoca % 5 == 0 or sin_mejora == 0:
            print(f'  época {epoca:3d}  val_mse={val:.6f}'
                  f'{"  *" if sin_mejora == 0 else ""}')
        if sin_mejora >= paciencia:
            print(f'  parada temprana en época {epoca} (mejor: {mejor_epoca})')
            break

    if mejor_estado is not None:
        modelo.load_state_dict(mejor_estado)
    modelo.eval()
    with torch.no_grad():
        met = _metricas(modelo(tensores['test'][0]), tensores['test'][1])
    # persistencia: cola futura = cola del último tick de la ventana
    idx = CARACTERISTICAS_FASE.index('cola_n')
    persist = tensores['test'][0][:, -1, idx:idx + 1]
    met_p = _metricas(persist, tensores['test'][1])

    config = {
        'entrenado_en': datetime.now().isoformat(timespec='seconds'),
        'datos': str(ruta_datos), 'ventana': ventana,
        'caracteristicas': CARACTERISTICAS_FASE, 'objetivo': 'cola_n',
        # constantes con las que difuso_ia normalizó los datos; se validan al
        # cargar el modelo para impedir desalineamiento train/inferencia
        'normalizacion': dict(NORMALIZACION_FASE),
        'hiperparametros': modelo.hiperparametros,
        'optimizacion': {'lr': lr, 'batch': batch, 'epocas_max': epocas,
                         'paciencia': paciencia, 'semilla': semilla,
                         'mejor_epoca': mejor_epoca,
                         'mejor_val_mse': round(mejor_val, 6)},
        'secuencias': {'train': n_tr, 'val': n_va, 'test': n_te},
        'metricas_test': {k: round(v, 6) for k, v in met.items()},
        'baseline_persistencia_test': {k: round(v, 6) for k, v in met_p.items()},
        'supera_persistencia': met['mae'] < met_p['mae'],
        'duracion_s': round(time.time() - t0, 1),
    }
    DIR_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    torch.save(modelo.state_dict(), DIR_ARTIFACTS / 'modelo_fase.pt')
    (DIR_ARTIFACTS / 'config.json').write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"\nTest: MAE={met['mae']:.4f} RMSE={met['rmse']:.4f} | "
          f"persistencia MAE={met_p['mae']:.4f}")
    print(f"¿Supera a persistencia?: {'SÍ' if config['supera_persistencia'] else 'NO'}")
    print(f'Artefactos en {DIR_ARTIFACTS}')
    return config


def main(argv: Optional[List[str]] = None) -> Dict:
    p = argparse.ArgumentParser(description='Entrenar CNN-LSTM de cola por fase')
    p.add_argument('--datos', default=str(RUTA_DATOS_DEFECTO))
    p.add_argument('--epocas', type=int, default=60)
    p.add_argument('--ventana', type=int, default=VENTANA_DEFECTO)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--batch', type=int, default=256)
    p.add_argument('--paciencia', type=int, default=10)
    a = p.parse_args(argv)
    return entrenar(Path(a.datos), epocas=a.epocas, ventana=a.ventana,
                    lr=a.lr, batch=a.batch, paciencia=a.paciencia)


if __name__ == '__main__':
    main()
