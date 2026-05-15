from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from sklearn.linear_model import LogisticRegression


@dataclass
class CalibrationConfig:
    n_dimensions: int = 8
    synthetic_samples: int = 10000
    random_seed: int = 42


class CalibrationModel:
    """Platt-scaled calibration model for compatibility confidence estimation.

    Inputs:
        score_vector: ndarray shape (8,) — per-dimension compatibility scores in [0,1]
        signal_coverage: float in [0, 1] — fraction of signals observed vs total possible

    Output:
        calibrated_confidence: float in [0, 1]
    """

    def __init__(self, model: LogisticRegression | None = None, n_dimensions: int = 8) -> None:
        self.n_dimensions = n_dimensions
        self.model = model or LogisticRegression()

    def _feature_vector(self, score_vector: np.ndarray, signal_coverage: float) -> np.ndarray:
        scores = np.asarray(score_vector, dtype=np.float64)
        if scores.shape[0] != self.n_dimensions:
            raise ValueError(f"Expected {self.n_dimensions} dimensions, got {scores.shape[0]}")
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        coverage = float(np.clip(signal_coverage, 0.0, 1.0))
        return np.array(
            [
                mean_score,
                std_score,
                np.min(scores),
                np.max(scores),
                1.0 / (1.0 + std_score),   # consistency
                coverage,
                coverage ** 2,
                mean_score * coverage,
            ],
            dtype=np.float64,
        )

    @classmethod
    def from_synthetic_data(cls, config: CalibrationConfig | None = None) -> "CalibrationModel":
        """Fit on synthetic data using a Platt-scaling logistic regression."""
        config = config or CalibrationConfig()
        rng = np.random.default_rng(config.random_seed)
        X, y = [], []
        for _ in range(config.synthetic_samples):
            coverage = rng.uniform(0.1, 1.0)
            observed_mask = rng.uniform(0, 1, config.n_dimensions) < coverage
            latent = rng.normal(0.0, 1.0)
            noise = rng.normal(0.0, max(0.15, 1.0 - coverage), config.n_dimensions)
            scores = np.clip(1 / (1 + np.exp(-(latent + noise))), 0.0, 1.0)
            scores[~observed_mask] = 0.5
            std_score = np.std(scores)
            mean_score = np.mean(scores)
            certainty = (
                2.4 * coverage
                + 1.6 / (1.0 + std_score)
                + 0.5 * abs(mean_score - 0.5)
                - 1.8 * (1.0 - coverage) * abs(mean_score - 0.5)
                + rng.normal(0.0, 0.35)
            )
            X.append(cls(n_dimensions=config.n_dimensions)._feature_vector(scores, coverage))
            y.append(rng.binomial(1, 1 / (1 + np.exp(-certainty))))
        fitted = cls(model=LogisticRegression(max_iter=1000), n_dimensions=config.n_dimensions)
        fitted.model.fit(np.asarray(X, dtype=np.float64), np.asarray(y, dtype=np.int32))
        return fitted

    def predict_confidence(self, score_vector: np.ndarray, signal_coverage: float) -> float:
        """Return calibrated probability that the compatibility prediction is reliable."""
        features = self._feature_vector(score_vector, signal_coverage).reshape(1, -1)
        return float(np.clip(self.model.predict_proba(features)[0, 1], 0.0, 1.0))

    def to_json(self) -> str:
        return json.dumps(
            {
                "n_dimensions": self.n_dimensions,
                "coef": self.model.coef_.tolist(),
                "intercept": self.model.intercept_.tolist(),
                "classes": self.model.classes_.tolist(),
            }
        )

    @classmethod
    def from_json(cls, data: str) -> "CalibrationModel":
        payload = json.loads(data)
        model = LogisticRegression()
        model.classes_ = np.asarray(payload["classes"])
        model.coef_ = np.asarray(payload["coef"])
        model.intercept_ = np.asarray(payload["intercept"])
        return cls(model=model, n_dimensions=payload["n_dimensions"])

    def calibration_plot_data(
        self, predicted_probs: np.ndarray, true_labels: np.ndarray, bins: int = 10
    ) -> Dict[str, List[float]]:
        predicted_probs = np.asarray(predicted_probs)
        true_labels = np.asarray(true_labels)
        bin_edges = np.linspace(0.0, 1.0, bins + 1)
        predicted_means, observed_freqs, bin_centers, counts = [], [], [], []
        for i in range(bins):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            mask = (predicted_probs >= lo) & (predicted_probs <= hi if i == bins - 1 else predicted_probs < hi)
            if np.sum(mask) == 0:
                continue
            predicted_means.append(float(np.mean(predicted_probs[mask])))
            observed_freqs.append(float(np.mean(true_labels[mask])))
            bin_centers.append(float((lo + hi) / 2.0))
            counts.append(int(np.sum(mask)))
        return {"bin_centers": bin_centers, "predicted": predicted_means, "observed": observed_freqs, "counts": counts}
