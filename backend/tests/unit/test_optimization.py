from app.models.story import UserStory
from app.services.optimization_engine import OptimizationEngine


weights = {"value_weight": 0.5, "urgency_weight": 0.3, "alignment_weight": 0.2}


def test_optimization_respects_capacity():
    stories = [
        UserStory(story_id="US1", sprint_id="SP1", title="A", story_points=20, business_value=10, risk_score=0.1, depends_on=[], required_skill=None),
        UserStory(story_id="US2", sprint_id="SP1", title="B", story_points=20, business_value=9, risk_score=0.1, depends_on=[], required_skill=None),
    ]
    result = OptimizationEngine().solve(stories, weights, capacity=25, risk_threshold=0.8, available_skills=[])
    assert sum(s.story_points for s in result.selected_stories) <= 25


def test_high_risk_story_excluded():
    stories = [UserStory(story_id="US1", sprint_id="SP1", title="A", story_points=5, business_value=10, risk_score=0.95, depends_on=[], required_skill=None)]
    result = OptimizationEngine().solve(stories, weights, capacity=30, risk_threshold=0.7, available_skills=[])
    assert len(result.selected_stories) == 0


def test_dependency_constraint():
    child = UserStory(story_id="US2", sprint_id="SP1", title="B", story_points=3, business_value=9, risk_score=0.1, depends_on=["US1"], required_skill=None)
    result = OptimizationEngine().solve([child], weights, capacity=30, risk_threshold=0.8, available_skills=[])
    assert len(result.selected_stories) == 0
