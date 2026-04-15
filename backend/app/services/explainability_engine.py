from __future__ import annotations

from typing import List

from app.models.explanation import Explanation
from app.models.story import UserStory
from app.services.optimization_engine import OptimizationEngine, OptimizationResult
from app.services.preprocessing import normalize_skill, normalize_status


class ExplainabilityEngine:
    @staticmethod
    def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(maximum, float(value)))

    @staticmethod
    def _normalized_weights(weights: dict) -> dict[str, float]:
        raw = {
            "urgency_weight": max(0.0, float(weights.get("urgency_weight", 0.33))),
            "value_weight": max(0.0, float(weights.get("value_weight", 0.33))),
            "alignment_weight": max(0.0, float(weights.get("alignment_weight", 0.33))),
        }
        total = raw["urgency_weight"] + raw["value_weight"] + raw["alignment_weight"]
        if total <= 0:
            return {"urgency_weight": 0.33, "value_weight": 0.34, "alignment_weight": 0.33}
        return {key: value / total for key, value in raw.items()}

    def _score_components(self, story: UserStory, weights: dict) -> dict[str, float]:
        normalized_weights = self._normalized_weights(weights)
        normalized_story_points = self._clamp(float(story.story_points) / OptimizationEngine.STORY_POINTS_MAX)
        normalized_business_value = self._clamp(float(story.business_value) / OptimizationEngine.BUSINESS_VALUE_MAX)
        normalized_risk_score = self._clamp(float(story.risk_score))

        effort_component = self._clamp(1.0 - normalized_story_points)
        value_component = normalized_business_value
        risk_component = self._clamp(1.0 - normalized_risk_score)

        urgency_contribution = normalized_weights["urgency_weight"] * effort_component
        value_contribution = normalized_weights["value_weight"] * value_component
        alignment_contribution = normalized_weights["alignment_weight"] * risk_component
        score = self._clamp(urgency_contribution + value_contribution + alignment_contribution)
        return {
            "score": score,
            "urgency_contribution": urgency_contribution,
            "value_contribution": value_contribution,
            "alignment_contribution": alignment_contribution,
            "normalized_story_points": normalized_story_points,
            "normalized_business_value": normalized_business_value,
            "normalized_risk_score": normalized_risk_score,
        }

    def generate(self, result: OptimizationResult, weights: dict) -> List[Explanation]:
        explanations: list[Explanation] = []
        selected_ids = {s.story_id for s in result.selected_stories}
        selected_points = sum(s.story_points for s in result.selected_stories)

        for story in result.selected_stories:
            components = self._score_components(story, weights)
            value_contribution = components["value_contribution"]
            risk_impact = -components["alignment_contribution"]
            alignment_score = components["urgency_contribution"]
            confidence = self._clamp(components["score"])

            reason_parts = [
                f"normalized objective score {components['score']:.3f}",
                f"value contribution {value_contribution:.3f}",
                f"effort contribution {alignment_score:.3f}",
                f"risk contribution {components['alignment_contribution']:.3f}",
            ]
            if story.business_value >= 7:
                reason_parts.append("high business value")
            if story.risk_score < 0.3:
                reason_parts.append("low risk")
            if story.story_points <= 5:
                reason_parts.append("low effort")

            reason = "Selected because " + "; ".join(reason_parts) + "."
            explanations.append(
                Explanation(
                    plan_id="",
                    story_id=story.story_id,
                    is_selected=True,
                    reason=reason,
                    value_weight=round(value_contribution, 3),
                    risk_impact=round(risk_impact, 3),
                    alignment_score=round(alignment_score, 3),
                    confidence_score=round(confidence, 3),
                    rejection_reason=None,
                )
            )

        for story in result.rejected_stories:
            status = normalize_status(story.status)
            required_skill = normalize_skill(story.required_skill) if story.required_skill else None
            if story.risk_score > result.risk_threshold:
                rejection_reason = f"Risk score {story.risk_score:.2f} exceeds threshold {result.risk_threshold:.2f}."
            elif required_skill and result.available_skills and required_skill not in result.available_skills:
                rejection_reason = f"Required skill '{required_skill}' not available in team."
            elif status and status in OptimizationEngine.NON_PLANNABLE_STATUSES:
                rejection_reason = f"Status '{status}' is not plannable."
            elif any(dep not in selected_ids for dep in (story.depends_on or [])):
                rejection_reason = "Dependencies are not satisfied in the selected plan."
            elif selected_points + story.story_points > max(result.capacity_limit, result.capacity_used):
                rejection_reason = "Would exceed sprint capacity."
            else:
                components = self._score_components(story, weights)
                rejection_reason = (
                    "Lower priority than selected stories under current objective; "
                    f"score={components['score']:.3f}."
                )

            explanations.append(
                Explanation(
                    plan_id="",
                    story_id=story.story_id,
                    is_selected=False,
                    reason=rejection_reason,
                    value_weight=None,
                    risk_impact=None,
                    alignment_score=None,
                    confidence_score=0.0,
                    rejection_reason=rejection_reason,
                )
            )
        return explanations
