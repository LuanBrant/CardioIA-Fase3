"""
Gerador de séries temporais sintéticas de BPM para o estudo
"CardioIA - Ir Além 2" (séries temporais + IA).

Saída: matriz `X` (n_amostras, T) com séries de batimentos cardíacos
amostradas a 1 Hz por 30 s, e vetor `y` com rótulo:
    0 = normal (ritmo sinusal entre 60 e 100 bpm com pequena variabilidade)
    1 = arrítmico (taqui/bradi, com picos de variabilidade)

Função pública: `make_dataset(n_per_class=300, seed=42)`.
"""
from __future__ import annotations

import numpy as np

SAMPLING_FREQ = 1     # Hz (1 amostra por segundo)
DURATION      = 30    # segundos
T             = SAMPLING_FREQ * DURATION


def _normal_series(rng: np.random.Generator) -> np.ndarray:
    # base entre 60 e 105 (inclui taquicardia sinusal leve por estresse/exercicio
    # e ritmo basal de atletas) - sobrepoe parcialmente com a classe arritmica
    base = rng.uniform(58, 105)
    drift = rng.normal(0, 0.8, T).cumsum() * 0.1
    noise = rng.normal(0, 4.5, T)
    series = base + drift + noise
    return np.clip(series, 45, 130)


def _arrhythmic_series(rng: np.random.Generator) -> np.ndarray:
    # ritmos com BPM sustentado fora do envelope OU com altissima
    # variabilidade (proxy de fibrilacao). O range parcialmente sobrepoe
    # com normal para criar dificuldade do problema.
    kind = rng.integers(0, 3)
    if kind == 0:       # taquicardia sustentada
        base = rng.uniform(115, 175)
    elif kind == 1:     # bradicardia
        base = rng.uniform(28, 48)
    else:               # variabilidade extrema (FA), base normal
        base = rng.uniform(70, 100)

    drift = rng.normal(0, 1.5, T).cumsum() * 0.15
    noise_std = 6.0 if kind != 2 else 18.0     # FA = muito ruido
    noise = rng.normal(0, noise_std, T)
    spikes = np.zeros(T)
    n_spikes = rng.integers(2, 7)
    idx = rng.choice(T, size=n_spikes, replace=False)
    spikes[idx] = rng.normal(0, 22, n_spikes)
    series = base + drift + noise + spikes
    return np.clip(series, 25, 220)


def make_dataset(n_per_class: int = 300, seed: int = 42):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for _ in range(n_per_class):
        X.append(_normal_series(rng))
        y.append(0)
    for _ in range(n_per_class):
        X.append(_arrhythmic_series(rng))
        y.append(1)
    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int64)
    # shuffle
    perm = rng.permutation(len(X))
    return X[perm], y[perm]


def hand_crafted_features(X: np.ndarray) -> np.ndarray:
    """Estatísticas para a regressão logística (baseline tradicional)."""
    mean = X.mean(axis=1, keepdims=True)
    std  = X.std(axis=1, keepdims=True)
    pmax = X.max(axis=1, keepdims=True)
    pmin = X.min(axis=1, keepdims=True)
    diff = np.abs(np.diff(X, axis=1)).mean(axis=1, keepdims=True)
    return np.hstack([mean, std, pmax, pmin, diff])


if __name__ == "__main__":
    X, y = make_dataset(50)
    print("X shape:", X.shape, "y shape:", y.shape)
    print("Classes:", np.unique(y, return_counts=True))
    print("Features amostra:", hand_crafted_features(X[:3]))
