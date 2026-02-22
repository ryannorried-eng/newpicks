from __future__ import annotations

import os
import pickle
from datetime import UTC, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

from app.ml.features import FEATURE_NAMES

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/models/nba_model.pkl")
SCALER_PATH = os.environ.get("SCALER_PATH", "/app/models/nba_scaler.pkl")
META_PATH = os.environ.get("MODEL_META_PATH", "/app/models/nba_meta.pkl")


class NBAPredictor:
    def __init__(self) -> None:
        self.model: LogisticRegression | None = None
        self.scaler: StandardScaler | None = None
        self.is_trained = False
        self.training_accuracy = 0.0
        self.cv_accuracy = 0.0
        self.n_training_samples = 0
        self.last_trained: datetime | None = None
        self.top_features: list[tuple[str, float]] = []

    def train(self, X: np.ndarray, y: np.ndarray) -> dict:
        if len(y) < 20:
            raise ValueError("Need at least 20 training samples")

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs", random_state=42)
        self.model.fit(X_scaled, y)

        self.is_trained = True
        self.n_training_samples = len(y)
        self.training_accuracy = float(self.model.score(X_scaled, y))
        cv_folds = min(5, len(y))
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=cv_folds, scoring="accuracy")
        self.cv_accuracy = float(cv_scores.mean())

        importances = dict(zip(FEATURE_NAMES, self.model.coef_[0].tolist(), strict=False))
        self.top_features = sorted(importances.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
        self.last_trained = datetime.now(UTC)

        self.save()

        return {
            "training_accuracy": self.training_accuracy,
            "cv_accuracy": self.cv_accuracy,
            "cv_std": float(cv_scores.std()),
            "n_samples": self.n_training_samples,
            "top_features": self.top_features,
            "last_trained": self.last_trained.isoformat(),
        }

    def predict_home_win_prob(self, features: list[float]) -> float:
        if not self.is_trained or self.model is None or self.scaler is None:
            raise ValueError("Model not trained yet")
        X = np.array([features])
        X_scaled = self.scaler.transform(X)
        return float(self.model.predict_proba(X_scaled)[0][1])

    def save(self) -> None:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        with open(MODEL_PATH, "wb") as file:
            pickle.dump(self.model, file)
        with open(SCALER_PATH, "wb") as file:
            pickle.dump(self.scaler, file)
        with open(META_PATH, "wb") as file:
            pickle.dump(
                {
                    "training_accuracy": self.training_accuracy,
                    "cv_accuracy": self.cv_accuracy,
                    "n_training_samples": self.n_training_samples,
                    "last_trained": self.last_trained,
                    "top_features": self.top_features,
                },
                file,
            )

    def load(self) -> bool:
        try:
            with open(MODEL_PATH, "rb") as file:
                self.model = pickle.load(file)
            with open(SCALER_PATH, "rb") as file:
                self.scaler = pickle.load(file)
            if os.path.exists(META_PATH):
                with open(META_PATH, "rb") as file:
                    meta = pickle.load(file)
                    self.training_accuracy = meta.get("training_accuracy", 0.0)
                    self.cv_accuracy = meta.get("cv_accuracy", 0.0)
                    self.n_training_samples = meta.get("n_training_samples", 0)
                    self.last_trained = meta.get("last_trained")
                    self.top_features = meta.get("top_features", [])
            self.is_trained = True
            return True
        except FileNotFoundError:
            return False


predictor = NBAPredictor()
predictor.load()
