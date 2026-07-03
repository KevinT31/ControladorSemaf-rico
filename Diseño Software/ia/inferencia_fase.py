"""
Inferencia de la CNN-LSTM de cola por fase, para el lazo difuso_ia.

PredictorFase.predecir_lote recibe las ventanas de TODAS las fases de un
semáforo (lista de W x F, ya normalizadas [0,1] por construcción) y devuelve
la cola normalizada prevista por fase en el siguiente tick de rejilla.
Cualquier problema levanta excepción: difuso_ia la captura y opera con β=0.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import torch

from .secuencias_fase import CARACTERISTICAS_FASE
from .modelo import ModeloCNNLSTM

DIR_ARTIFACTS_DEFECTO = Path(__file__).resolve().parent / 'artifacts_fase'


class PredictorFase:
    def __init__(self, modelo: ModeloCNNLSTM, config: Dict):
        self.modelo = modelo.eval()
        self.config = config
        self.ventana = int(config['ventana'])

    @classmethod
    def cargar(cls, ruta_artefactos: Optional[str] = None) -> 'PredictorFase':
        carpeta = Path(ruta_artefactos) if ruta_artefactos else DIR_ARTIFACTS_DEFECTO
        ruta_modelo = carpeta / 'modelo_fase.pt'
        ruta_config = carpeta / 'config.json'
        for r in (ruta_modelo, ruta_config):
            if not r.exists():
                raise FileNotFoundError(
                    f'Artefacto no encontrado: {r} '
                    f'(entrenar: python -m ia.entrenamiento_fase)')
        config = json.loads(ruta_config.read_text(encoding='utf-8'))
        if config.get('caracteristicas') != CARACTERISTICAS_FASE:
            raise ValueError('Modelo entrenado con OTRAS características de fase; '
                             're-entrenar (ia.entrenamiento_fase).')
        modelo = ModeloCNNLSTM(**config['hiperparametros'])
        modelo.load_state_dict(torch.load(ruta_modelo, map_location='cpu',
                                          weights_only=True))
        return cls(modelo, config)

    def predecir_lote(self, ventanas: Sequence[Sequence[Sequence[float]]]
                      ) -> List[float]:
        """cola_n prevista por cada ventana (una por fase del semáforo)."""
        n_car = len(CARACTERISTICAS_FASE)
        for v in ventanas:
            if len(v) != self.ventana or any(len(x) != n_car for x in v):
                raise ValueError(
                    f'Ventana inválida: se requiere {self.ventana} x {n_car}')
        x = torch.tensor(list(ventanas), dtype=torch.float32)
        with torch.no_grad():
            salida = self.modelo(x)
        return [float(s[0]) for s in salida]
