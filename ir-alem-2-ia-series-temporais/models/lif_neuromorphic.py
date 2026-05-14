"""
Classificador neuromorfico baseado em LIF (Leaky Integrate-and-Fire).

Ideia
-----
Convertemos a serie temporal de BPM em uma cadeia de spikes alimentando
um neuronio LIF. Quanto mais a serie se afasta da faixa "saudavel" mais
spikes o neuronio produz na janela de 30 s. Um classificador linear
extremamente simples (threshold sobre a taxa de disparo) basta para
separar normal vs arritmico - ilustrando o ganho de eficiencia
energetica/computacional caracteristico de hardware neuromorfico (Loihi,
SpiNNaker, etc.) versus modelos densos tradicionais.

Implementacao
-------------
Para cada amostra t da serie:
    encoded = max(0, |bpm_t - 80| - 10) / 100   # quanto fora do normal
    V = V + dt * (-V / tau + encoded * gain)    # equacao LIF
    se V > Vth -> spike, V = V_reset

O *firing rate* (taxa de disparo) na janela serve de feature unica e e
classificado com um threshold otimizado em treino.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass
class LIFParams:
    dt: float       = 1.0     # passo (s) - amostragem a 1 Hz
    tau: float      = 4.0     # constante de decaimento (s) - reativo a transientes
    gain: float     = 8.0     # ganho de codificacao
    v_th: float     = 1.0     # limiar de disparo
    v_reset: float  = 0.0
    bpm_center: float = 80.0
    bpm_tolerance: float = 20.0   # faixa silenciosa: 60..100 bpm


def encode(bpm_series: np.ndarray, p: LIFParams) -> np.ndarray:
    """BPM -> sinal de excitacao normalizado, sempre >= 0."""
    return np.maximum(0.0,
                      np.abs(bpm_series - p.bpm_center) - p.bpm_tolerance) / 100.0


def firing_rate(bpm_series: np.ndarray, p: LIFParams = LIFParams()) -> float:
    """Retorna a taxa de disparo (Hz) de um LIF alimentado pela serie."""
    inp = encode(bpm_series, p)
    V = 0.0
    spikes = 0
    for x in inp:
        V = V + p.dt * (-V / p.tau + x * p.gain)
        if V > p.v_th:
            spikes += 1
            V = p.v_reset
    return spikes / (len(bpm_series) * p.dt)


def firing_rates_batch(X: np.ndarray, p: LIFParams = LIFParams()) -> np.ndarray:
    return np.array([firing_rate(row, p) for row in X], dtype=np.float32)


class LIFClassifier:
    """
    Classificador LIF + threshold. Treinar busca o threshold otimo
    sobre o conjunto de treino (max F1).
    """

    def __init__(self, params: LIFParams | None = None) -> None:
        self.params = params or LIFParams()
        self.threshold_: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LIFClassifier":
        rates = firing_rates_batch(X, self.params)
        # busca grid no intervalo [min, max]
        cand = np.linspace(rates.min(), rates.max(), 100)
        best_f1 = -1.0
        best_t  = float(cand[0])
        for t in cand:
            pred = (rates > t).astype(int)
            tp = int(((pred == 1) & (y == 1)).sum())
            fp = int(((pred == 1) & (y == 0)).sum())
            fn = int(((pred == 0) & (y == 1)).sum())
            if tp == 0:
                continue
            prec = tp / (tp + fp)
            rec  = tp / (tp + fn)
            f1   = 2 * prec * rec / (prec + rec)
            if f1 > best_f1:
                best_f1 = f1
                best_t  = float(t)
        self.threshold_ = best_t
        self.train_f1_  = best_f1
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        rates = firing_rates_batch(X, self.params)
        return (rates > self.threshold_).astype(int)

    def predict_score(self, X: np.ndarray) -> np.ndarray:
        """Retorna a taxa de disparo (score continuo)."""
        return firing_rates_batch(X, self.params)
