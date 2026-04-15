import pandas as pd

from app.services.context_extractor import ExtractedContext
from app.services.weight_learning import WeightLearningModel


def test_weight_learning_fallback_for_small_dataset():
    df = pd.DataFrame(
        [
            {"story_points": 5, "business_value": 8, "risk_score": 0.2, "sprint_completed": 1},
            {"story_points": 3, "business_value": 6, "risk_score": 0.1, "sprint_completed": 1},
        ]
    )
    context = ExtractedContext(urgency_weight=0.2, value_weight=0.5, alignment_weight=0.3)
    weights, metrics = WeightLearningModel().train_with_metrics(df, context)

    assert round(sum(weights.values()), 6) == 1.0
    assert metrics["sample_count"] == 2
    assert metrics["model_type"].startswith("context-fallback")
    assert metrics["mae"] is None
    assert metrics["r2"] is None


def test_weight_learning_train_test_metrics_and_importance_sum():
    rows = []
    for idx in range(30):
        rows.append(
            {
                "story_points": (idx % 8) + 1,
                "business_value": (idx % 10) + 1,
                "risk_score": (idx % 5) / 5,
                "sprint_completed": 1 if idx % 3 else 0,
            }
        )
    df = pd.DataFrame(rows)
    context = ExtractedContext(urgency_weight=0.33, value_weight=0.34, alignment_weight=0.33)
    weights, metrics = WeightLearningModel().train_with_metrics(df, context)

    assert round(sum(weights.values()), 6) == 1.0
    assert metrics["sample_count"] == 30
    assert metrics["mae"] is not None
    assert metrics["model_type"] == "logistic-regression-train-test-sign-mapped"
    assert metrics["accuracy"] is not None
    assert metrics["f1"] is not None
    assert metrics["roc_auc"] is not None
    assert round(sum(metrics["feature_importance"].values()), 6) == 1.0


def test_weight_learning_skips_r2_when_test_target_variance_zero():
    rows = []
    for idx in range(20):
        rows.append(
            {
                "story_points": (idx % 13) + 1,
                "business_value": 8,
                "risk_score": 0.2,
                "sprint_completed": 1,
            }
        )
    df = pd.DataFrame(rows)
    context = ExtractedContext(urgency_weight=0.3, value_weight=0.4, alignment_weight=0.3)
    _, metrics = WeightLearningModel().train_with_metrics(df, context)

    assert metrics["model_type"].startswith("context-fallback")
    assert metrics["fallback_reason"] == "target_has_single_class"
