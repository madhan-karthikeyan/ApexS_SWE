from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from app.services.context_extractor import ExtractedContext

try:
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
except Exception:  # pragma: no cover
    LogisticRegression = None
    Ridge = None
    accuracy_score = None
    f1_score = None
    mean_absolute_error = None
    r2_score = None
    roc_auc_score = None
    train_test_split = None
    StandardScaler = None


logger = logging.getLogger(__name__)


class WeightLearningModel:
    FEATURE_NAMES = ["story_points", "business_value", "risk_score"]
    SIGN_ALIGNMENT = {
        "story_points": -1.0,
        "business_value": 1.0,
        "risk_score": -1.0,
    }

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = int(random_state)

    def _context_fallback(self, sample_count: int, context: ExtractedContext, model_type: str, reason: str) -> tuple[dict, dict]:
        base = np.array([context.urgency_weight, context.value_weight, context.alignment_weight], dtype=float)
        total = float(base.sum())
        if total <= 0:
            base = np.array([0.33, 0.34, 0.33], dtype=float)
            total = float(base.sum())
        normalized = base / total
        weights = {
            "urgency_weight": float(normalized[0]),
            "value_weight": float(normalized[1]),
            "alignment_weight": float(normalized[2]),
        }
        feature_importance = {
            "story_points": float(normalized[0]),
            "business_value": float(normalized[1]),
            "risk_score": float(normalized[2]),
        }
        metrics = {
            "sample_count": int(sample_count),
            "train_count": int(sample_count),
            "test_count": 0,
            "mae": None,
            "r2": None,
            "accuracy": None,
            "f1": None,
            "roc_auc": None,
            "feature_importance": feature_importance,
            "feature_coefficients": {k: 0.0 for k in self.FEATURE_NAMES},
            "model_type": model_type,
            "fallback_reason": reason,
            "random_state": self.random_state,
        }
        logger.info("Weight learning fallback used (%s): %s", model_type, reason)
        logger.info("Fallback weights: %s", weights)
        return weights, metrics

    def _prepare_frame(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        x_frame = pd.DataFrame(index=df.index)
        for feature in self.FEATURE_NAMES:
            if feature in df.columns:
                x_frame[feature] = pd.to_numeric(df[feature], errors="coerce").fillna(0.0)
            else:
                x_frame[feature] = 0.0
        y_series = pd.to_numeric(df.get("sprint_completed", 0.0), errors="coerce").fillna(0.0)
        y_binary = (y_series >= 0.5).astype(int)
        return x_frame.values, y_binary.values

    def _coefficients_to_weights(self, coefficients: dict[str, float], context: ExtractedContext) -> tuple[dict[str, float], dict[str, float]]:
        aligned = []
        for feature in self.FEATURE_NAMES:
            coef = float(coefficients.get(feature, 0.0))
            aligned.append(max(0.0, self.SIGN_ALIGNMENT[feature] * coef))
        importance = np.array(aligned, dtype=float)
        if float(importance.sum()) <= 0.0:
            context_base = np.array([context.urgency_weight, context.value_weight, context.alignment_weight], dtype=float)
            context_total = float(context_base.sum())
            importance = context_base / context_total if context_total > 0 else np.array([0.33, 0.34, 0.33], dtype=float)
        else:
            importance = importance / float(importance.sum())

        weights = {
            "urgency_weight": float(importance[0]),
            "value_weight": float(importance[1]),
            "alignment_weight": float(importance[2]),
        }
        feature_importance = {
            "story_points": float(importance[0]),
            "business_value": float(importance[1]),
            "risk_score": float(importance[2]),
        }
        return weights, feature_importance

    def train(self, df: pd.DataFrame, context: ExtractedContext) -> dict:
        weights, _ = self.train_with_metrics(df, context)
        return weights

    def train_with_metrics(self, df: pd.DataFrame, context: ExtractedContext) -> tuple[dict, dict]:
        if df.empty:
            return self._context_fallback(
                sample_count=0,
                context=context,
                model_type="context-fallback-empty",
                reason="empty_dataset",
            )

        if (
            LogisticRegression is None
            or Ridge is None
            or StandardScaler is None
            or train_test_split is None
            or mean_absolute_error is None
            or r2_score is None
            or accuracy_score is None
            or f1_score is None
            or roc_auc_score is None
        ):
            return self._context_fallback(
                sample_count=len(df),
                context=context,
                model_type="context-fallback-sklearn-missing",
                reason="sklearn_unavailable",
            )

        if len(df) < 10:
            return self._context_fallback(
                sample_count=len(df),
                context=context,
                model_type="context-fallback-small-sample",
                reason="sample_count_below_10",
            )

        X, y = self._prepare_frame(df)
        if len(np.unique(y)) < 2:
            return self._context_fallback(
                sample_count=len(df),
                context=context,
                model_type="context-fallback-single-class",
                reason="target_has_single_class",
            )

        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=self.random_state,
                stratify=y,
            )
        except ValueError:
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=self.random_state,
            )

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = LogisticRegression(
            solver="liblinear",
            random_state=self.random_state,
            max_iter=1000,
        )
        model.fit(X_train_scaled, y_train)

        y_test_prob = model.predict_proba(X_test_scaled)[:, 1]
        y_test_pred = (y_test_prob >= 0.5).astype(int)

        coefficients = {feature: float(model.coef_[0][idx]) for idx, feature in enumerate(self.FEATURE_NAMES)}
        weights, feature_importance = self._coefficients_to_weights(coefficients, context)

        mae = float(mean_absolute_error(y_test, y_test_prob)) if len(y_test) else None
        try:
            r2 = float(r2_score(y_test, y_test_prob)) if len(np.unique(y_test)) > 1 else None
        except Exception:
            r2 = None
        accuracy = float(accuracy_score(y_test, y_test_pred)) if len(y_test) else None
        f1 = float(f1_score(y_test, y_test_pred, zero_division=0)) if len(y_test) else None
        try:
            roc_auc = float(roc_auc_score(y_test, y_test_prob)) if len(np.unique(y_test)) > 1 else None
        except Exception:
            roc_auc = None

        metrics: dict[str, Any] = {
            "sample_count": int(len(df)),
            "train_count": int(len(X_train)),
            "test_count": int(len(X_test)),
            "mae": mae,
            "r2": r2,
            "accuracy": accuracy,
            "f1": f1,
            "roc_auc": roc_auc,
            "feature_importance": feature_importance,
            "feature_coefficients": coefficients,
            "model_type": "logistic-regression-train-test-sign-mapped",
            "fallback_reason": None,
            "random_state": self.random_state,
        }

        logger.info("Learned weights: %s", weights)
        logger.info("Learning metrics: %s", metrics)
        return weights, metrics
