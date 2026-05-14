"""
Baseline tradicional: regressão logística sobre features estatísticas
extraídas da janela de 30 s de BPM.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    LogisticRegression(max_iter=500, C=1.0, n_jobs=None)),
    ])


def predict(model: Pipeline, X_feat: np.ndarray) -> np.ndarray:
    return model.predict(X_feat)


def predict_proba(model: Pipeline, X_feat: np.ndarray) -> np.ndarray:
    return model.predict_proba(X_feat)[:, 1]
