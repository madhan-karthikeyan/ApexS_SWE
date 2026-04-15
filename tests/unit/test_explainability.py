from app.models.story import UserStory
from app.services.explainability_engine import ExplainabilityEngine
from app.services.optimization_engine import OptimizationResult


def test_explanations_generated():
    selected = [UserStory(story_id="US1", sprint_id="SP1", title="A", story_points=3, business_value=8, risk_score=0.2, depends_on=[], required_skill=None)]
    rejected = [UserStory(story_id="US2", sprint_id="SP1", title="B", story_points=13, business_value=4, risk_score=0.9, depends_on=[], required_skill=None)]
    result = OptimizationResult(selected, rejected, 8, 0.2, 3, "ok", 0.7, ["Backend"])
    exps = ExplainabilityEngine().generate(result, {"value_weight": 0.5, "urgency_weight": 0.3, "alignment_weight": 0.2})
    assert len(exps) == 2
    assert all("SHAP" not in (e.reason or "") for e in exps)


def test_selected_story_has_positive_confidence():
    selected = [UserStory(story_id="US1", sprint_id="SP1", title="A", story_points=2, business_value=9, risk_score=0.1, depends_on=[], required_skill=None)]
    result = OptimizationResult(selected, [], 9, 0.1, 2, "ok", 0.7, ["Backend"])
    exps = ExplainabilityEngine().generate(result, {"value_weight": 0.5, "urgency_weight": 0.3, "alignment_weight": 0.2})
    assert exps[0].is_selected is True
    assert exps[0].confidence_score > 0


def test_rejected_story_has_rejection_reason():
    rejected = [UserStory(story_id="US2", sprint_id="SP1", title="Risky", story_points=8, business_value=8, risk_score=0.95, depends_on=[], required_skill=None)]
    result = OptimizationResult([], rejected, 0, 0, 0, "ok", 0.7, ["Backend"])
    exps = ExplainabilityEngine().generate(result, {"value_weight": 0.5, "urgency_weight": 0.3, "alignment_weight": 0.2})
    assert exps[0].is_selected is False
    assert exps[0].rejection_reason is not None
