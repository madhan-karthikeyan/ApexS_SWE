from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.models.story import UserStory
from app.services.context_extractor import ContextExtractor
from app.services.optimization_engine import OptimizationEngine
from app.services.preprocessing import normalize_skill, normalize_skills, normalize_status, parse_depends_on
from app.services.weight_learning import WeightLearningModel


def _to_story(row: dict[str, Any], sprint_id: str) -> UserStory:
    story_id = str(row.get("story_id") or "")
    return UserStory(
        story_id=story_id,
        sprint_id=sprint_id,
        title=str(row.get("title") or f"Story {story_id}"),
        description=str(row.get("description") or ""),
        story_points=max(int(float(row.get("story_points") or 1)), 1),
        business_value=float(row.get("business_value") or 0.0),
        risk_score=float(row.get("risk_score") or 0.0),
        required_skill=normalize_skill(row.get("required_skill")),
        depends_on=parse_depends_on(row.get("depends_on")),
        status=normalize_status(row.get("status")) or "backlog",
    )


def run_pipeline_harness(dataset_path: str | None = None, capacity: int = 40, risk_threshold: float = 0.7) -> dict[str, Any]:
    # Default to the project dataset used for ApexS validation.
    path = Path(dataset_path or "tawos/paper_datasets/tawos_apex_clean.csv")
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[3] / path

    df = pd.read_csv(path)
    context = ContextExtractor().extract(df, team_capacity=capacity)
    weights, metrics = WeightLearningModel().train_with_metrics(df, context)

    sprint_id = str(df.get("sprint_id", pd.Series(["HARNESS-SPRINT"])).iloc[0])
    stories = [_to_story(row, sprint_id=sprint_id) for row in df.to_dict(orient="records") if row.get("story_id")]
    available_skills = normalize_skills([value for value in df.get("required_skill", pd.Series(dtype=str)).dropna().tolist()])

    result = OptimizationEngine().solve(
        stories=stories,
        weights=weights,
        capacity=capacity,
        risk_threshold=risk_threshold,
        available_skills=available_skills,
    )

    report = {
        "weights": weights,
        "metrics": metrics,
        "selected_stories_count": len(result.selected_stories),
        "total_value": float(result.total_value),
        "avg_risk": float(result.total_risk),
    }

    print("weights:", report["weights"])
    print("metrics:", report["metrics"])
    print("selected_stories_count:", report["selected_stories_count"])
    print("total_value:", report["total_value"])
    print("avg_risk:", report["avg_risk"])
    return report


if __name__ == "__main__":
    run_pipeline_harness()
