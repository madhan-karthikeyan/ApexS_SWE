from app.models.story import UserStory
from app.services.explainability_engine import ExplainabilityEngine
from app.services.optimization_engine import OptimizationResult


def test_explanations_generated():
    selected = [UserStory(story_id="US1", sprint_id="SP1", title="A", story_points=3, business_value=8, risk_score=0.2, depends_on=[], required_skill=None)]
    rejected = [UserStory(story_id="US2", sprint_id="SP1", title="B", story_points=13, business_value=4, risk_score=0.9, depends_on=[], required_skill=None)]
    result = OptimizationResult(selected, rejected, 8, 0.2, 3, "ok", 0.7, ["Backend"])
    exps = ExplainabilityEngine().generate(result, {"value_weight": 0.5, "urgency_weight": 0.3, "alignment_weight": 0.2})
    assert len(exps) == 2
    assert any(e.is_selected for e in exps)
    assert any(not e.is_selected for e in exps)
    assert all("SHAP" not in (e.reason or "") for e in exps)
