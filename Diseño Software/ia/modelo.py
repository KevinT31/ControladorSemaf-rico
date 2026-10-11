"""
Arquitectura CNN-LSTM para predicción de cola por fase a corto plazo.

Conv1d extrae patrones locales entre intervalos consecutivos (formación y
disolución de colas); la LSTM modela la dependencia temporal de la ventana;
la cabeza densa con sigmoide emite la cola futura normalizada en [0,1].
"""
from __future__ import annotations

import torch
from torch import nn


class ModeloCNNLSTM(nn.Module):
    def __init__(self, n_caracteristicas: int, canales: int = 32,
                 oculto: int = 64, capas_lstm: int = 1,
                 dropout: float = 0.10, n_salidas: int = 2):
        super().__init__()
        self.convoluciones = nn.Sequential(
            nn.Conv1d(n_caracteristicas, canales, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv1d(canales, canales, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        self.lstm = nn.LSTM(canales, oculto, num_layers=capas_lstm,
                            batch_first=True)
        self.cabeza = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(oculto, n_salidas),
            nn.Sigmoid(),
        )
        self.hiperparametros = {
            'n_caracteristicas': n_caracteristicas, 'canales': canales,
            'oculto': oculto, 'capas_lstm': capas_lstm,
            'dropout': dropout, 'n_salidas': n_salidas,
        }

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, ventana, características) -> Conv1d espera (B, C, W)
        z = self.convoluciones(x.permute(0, 2, 1)).permute(0, 2, 1)
        salida, _ = self.lstm(z)
        return self.cabeza(salida[:, -1, :])  # último estado temporal
