"""
Inferencia de la CNN-LSTM en el lazo de control real.

PredictorICV carga los artefactos de ia/artifacts/ y expone predecir(ventana):
recibe la ventana CRUDA (W x F, mismo orden que ia.secuencias.CARACTERISTICAS,
que es el vector que arma ControladorDifusoPredictivo), escala con el
escalador del entrenamiento y devuelve [ICV_NS, ICV_EO] del próximo intervalo.

Cualquier problema (artefactos ausentes, forma inválida) levanta excepción:
el controlador la captura y cae al difuso base (fallback trazado).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import torch

from .secuencias import CARACTERISTICAS, EscaladorMinMax
from .modelo import ModeloCNNLSTM

DIR_ARTIFACTS_DEFECTO = Path(__file__).resolve().parent / 'artifacts'


class PredictorICV:
    """Predictor de ICV futuro por eje, listo para el lazo de control."""

    def __init__(self, modelo: ModeloCNNLSTM, escalador: EscaladorMinMax,
                 config: Dict):
        self.modelo = modelo.eval()
        self.escalador = escalador
        self.config = config
        self.ventana = int(config['ventana'])

    @classmethod
    def cargar(cls, ruta_artefactos: Optional[str] = None) -> 'PredictorICV':
        carpeta = Path(ruta_artefactos) if ruta_artefactos else DIR_ARTIFACTS_DEFECTO
        ruta_modelo = carpeta / 'modelo_cnn_lstm.pt'
        ruta_escalador = carpeta / 'escalador.json'
        ruta_config = carpeta / 'config.json'
        for r in (ruta_modelo, ruta_escalador, ruta_config):
            if not r.exists():
                raise FileNotFoundError(
                    f'Artefacto de IA no encontrado: {r} '
                    f'(entrenar primero: python -m ia.entrenamiento)')

        config = json.loads(ruta_config.read_text(encoding='utf-8'))
        if config.get('caracteristicas') != CARACTERISTICAS:
            raise ValueError('El modelo fue entrenado con OTRAS características; '
                             're-entrenar (ia.entrenamiento).')
        escalador = EscaladorMinMax.desde_dict(
            json.loads(ruta_escalador.read_text(encoding='utf-8')))
        modelo = ModeloCNNLSTM(**config['hiperparametros'])
        modelo.load_state_dict(torch.load(ruta_modelo, map_location='cpu',
                                          weights_only=True))
        return cls(modelo, escalador, config)

    def predecir(self, ventana: Sequence[Sequence[float]]) -> List[float]:
        """[ICV_NS, ICV_EO] futuros a partir de la ventana cruda W x F."""
        if len(ventana) != self.ventana:
            raise ValueError(f'Ventana de {len(ventana)} intervalos; '
                             f'el modelo requiere {self.ventana}')
        n_car = len(CARACTERISTICAS)
        if any(len(v) != n_car for v in ventana):
            raise ValueError(f'Cada vector debe tener {n_car} características '
                             f'(orden de ia.secuencias.CARACTERISTICAS)')

        escalada = [self.escalador.transformar_vector(v) for v in ventana]
        x = torch.tensor([escalada], dtype=torch.float32)
        with torch.no_grad():
            salida = self.modelo(x)[0]
        return [float(salida[0]), float(salida[1])]
