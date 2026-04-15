from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ExtractedContext:
    team_id: str | None = None
    urgency_weight: float = 0.33
    value_weight: float = 0.34
    alignment_weight: float = 0.33
    velocity: float | None = None
    completion_rate: float | None = None
    skill_distribution: dict[str, float] | None = None
    avg_risk_tolerance: float | None = None
    value_completion_correlation: float | None = None


class ContextExtractor:
    def extract(self, df: pd.DataFrame, team_capacity: int) -> ExtractedContext:
        if df.empty:
            return ExtractedContext(velocity=0.0, completion_rate=0.0, skill_distribution={})

        velocity = float(df.groupby("sprint_id")["story_points"].sum().mean()) if "sprint_id" in df.columns else float(df["story_points"].sum())
        completion_rate = float(df["sprint_completed"].mean()) if "sprint_completed" in df.columns else 0.0
        skill_dist = df["required_skill"].fillna("Unknown").value_counts(normalize=True).to_dict() if "required_skill" in df.columns else {}
        completed = df[df.get("sprint_completed", 0) == 1] if "sprint_completed" in df.columns else df
        avg_risk = float(completed["risk_score"].mean()) if not completed.empty and "risk_score" in completed.columns else 0.0
        value_correlation = 0.0
        if "business_value" in df.columns and "sprint_completed" in df.columns and len(df["business_value"].dropna()) > 1:
            corr = df["business_value"].corr(df["sprint_completed"])
            value_correlation = float(corr) if pd.notna(corr) else 0.0

        score_base = max(team_capacity, 1)
        urgency = min(1.0, velocity / score_base) if score_base else 0.33
        value_weight = min(1.0, max(0.1, value_correlation + 0.5))
        alignment = min(1.0, max(0.1, 1.0 - avg_risk))
        total = urgency + value_weight + alignment

        return ExtractedContext(
            urgency_weight=urgency / total,
            value_weight=value_weight / total,
            alignment_weight=alignment / total,
            velocity=velocity,
            completion_rate=completion_rate,
            skill_distribution=skill_dist,
            avg_risk_tolerance=avg_risk,
            value_completion_correlation=value_correlation,
        )
