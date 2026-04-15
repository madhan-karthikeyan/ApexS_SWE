import app.services.optimization_engine as optimization_module
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


def test_high_risk_story_excluded_by_threshold():
    stories = [
        UserStory(story_id="US1", sprint_id="SP1", title="Risky", story_points=5, business_value=10, risk_score=0.95, depends_on=[], required_skill=None)
    ]
    result = OptimizationEngine().solve(stories, weights, capacity=30, risk_threshold=0.7, available_skills=[])
    assert len(result.selected_stories) == 0


def test_dependency_missing_parent_excludes_child():
    stories = [
        UserStory(story_id="US2", sprint_id="SP1", title="Child", story_points=3, business_value=9, risk_score=0.1, depends_on=["US1"], required_skill=None)
    ]
    result = OptimizationEngine().solve(stories, weights, capacity=30, risk_threshold=0.8, available_skills=[])
    assert len(result.selected_stories) == 0


def test_empty_backlog_returns_empty_result():
    result = OptimizationEngine().solve([], weights, capacity=30, risk_threshold=0.8, available_skills=[])
    assert result.capacity_used == 0
    assert result.total_value == 0.0
    assert len(result.selected_stories) == 0


def test_lower_capacity_reduces_selected_count():
    stories = [
        UserStory(story_id="US1", sprint_id="SP1", title="A", story_points=5, business_value=8, risk_score=0.1, depends_on=[], required_skill=None),
        UserStory(story_id="US2", sprint_id="SP1", title="B", story_points=5, business_value=7, risk_score=0.2, depends_on=[], required_skill=None),
        UserStory(story_id="US3", sprint_id="SP1", title="C", story_points=5, business_value=6, risk_score=0.3, depends_on=[], required_skill=None),
    ]
    high_capacity = OptimizationEngine().solve(stories, weights, capacity=15, risk_threshold=1.0, available_skills=[])
    low_capacity = OptimizationEngine().solve(stories, weights, capacity=5, risk_threshold=1.0, available_skills=[])
    assert len(low_capacity.selected_stories) <= len(high_capacity.selected_stories)


def test_lower_risk_threshold_reduces_selected_count():
    stories = [
        UserStory(story_id="US1", sprint_id="SP1", title="Safe", story_points=3, business_value=6, risk_score=0.2, depends_on=[], required_skill=None),
        UserStory(story_id="US2", sprint_id="SP1", title="Risky", story_points=3, business_value=9, risk_score=0.9, depends_on=[], required_skill=None),
    ]
    high_threshold = OptimizationEngine().solve(stories, weights, capacity=10, risk_threshold=1.0, available_skills=[])
    low_threshold = OptimizationEngine().solve(stories, weights, capacity=10, risk_threshold=0.3, available_skills=[])
    assert len(low_threshold.selected_stories) <= len(high_threshold.selected_stories)


def test_greedy_fallback_used_when_milp_unavailable(monkeypatch):
    stories = [
        UserStory(story_id="US1", sprint_id="SP1", title="A", story_points=5, business_value=9, risk_score=0.1, depends_on=[], required_skill=None),
        UserStory(story_id="US2", sprint_id="SP1", title="B", story_points=3, business_value=8, risk_score=0.2, depends_on=[], required_skill=None),
        UserStory(story_id="US3", sprint_id="SP1", title="C", story_points=8, business_value=7, risk_score=0.1, depends_on=["US1"], required_skill=None),
    ]
    monkeypatch.setattr(optimization_module, "LpBinary", None)
    result = OptimizationEngine().solve(stories, weights, capacity=10, risk_threshold=0.8, available_skills=[])
    assert result.solver_status.startswith("greedy-fallback:")
    assert sum(s.story_points for s in result.selected_stories) <= 10
    assert result.warnings


def test_scoring_is_bounded_and_distribution_available():
    stories = [
        UserStory(story_id="US1", sprint_id="SP1", title="A", story_points=13, business_value=10, risk_score=0.0, depends_on=[], required_skill=None),
        UserStory(story_id="US2", sprint_id="SP1", title="B", story_points=1, business_value=1, risk_score=1.0, depends_on=[], required_skill=None),
    ]
    result = OptimizationEngine().solve(stories, weights, capacity=20, risk_threshold=1.0, available_skills=[])
    assert 0.0 <= result.score_distribution["min"] <= 1.0
    assert 0.0 <= result.score_distribution["max"] <= 1.0
    assert 0.0 <= result.score_distribution["mean"] <= 1.0


def test_feasibility_counts_track_filter_reasons():
    stories = [
        UserStory(story_id="US1", sprint_id="SP1", title="Risk", story_points=3, business_value=9, risk_score=0.9, depends_on=[], required_skill=None, status="backlog"),
        UserStory(story_id="US2", sprint_id="SP1", title="Skill", story_points=3, business_value=8, risk_score=0.1, depends_on=[], required_skill="frontend", status="backlog"),
        UserStory(story_id="US3", sprint_id="SP1", title="Dep", story_points=3, business_value=8, risk_score=0.1, depends_on=["MISSING"], required_skill=None, status="backlog"),
        UserStory(story_id="US4", sprint_id="SP1", title="Done", story_points=3, business_value=8, risk_score=0.1, depends_on=[], required_skill=None, status=" done "),
    ]
    result = OptimizationEngine().solve(stories, weights, capacity=20, risk_threshold=0.5, available_skills=["backend"])
    counts = result.feasibility_counts
    assert counts["total"] == 4
    assert counts["filtered_by_risk"] == 1
    assert counts["filtered_by_skill"] == 1
    assert counts["filtered_by_dependency"] == 1
    assert counts["filtered_by_status"] == 1


def test_skill_and_status_normalization_in_feasibility():
    stories = [
        UserStory(story_id="US1", sprint_id="SP1", title="A", story_points=3, business_value=9, risk_score=0.1, depends_on=[], required_skill=" FrontEnd ", status=" BackLog "),
    ]
    result = OptimizationEngine().solve(stories, weights, capacity=20, risk_threshold=0.8, available_skills=[" frontend "])
    assert len(result.selected_stories) == 1


def test_constraint_toggle_disables_risk_filter():
    stories = [
        UserStory(story_id="US1", sprint_id="SP1", title="Risky", story_points=3, business_value=10, risk_score=0.95, depends_on=[], required_skill=None),
    ]
    strict_result = OptimizationEngine(enforce_risk=True).solve(stories, weights, capacity=10, risk_threshold=0.7, available_skills=[])
    relaxed_result = OptimizationEngine(enforce_risk=False).solve(stories, weights, capacity=10, risk_threshold=0.7, available_skills=[])
    assert len(strict_result.selected_stories) == 0
    assert len(relaxed_result.selected_stories) == 1


def test_baseline_modes_available_and_deterministic():
    stories = [
        UserStory(story_id="US1", sprint_id="SP1", title="A", story_points=3, business_value=7, risk_score=0.2, depends_on=[], required_skill="backend"),
        UserStory(story_id="US2", sprint_id="SP1", title="B", story_points=5, business_value=8, risk_score=0.3, depends_on=[], required_skill="frontend"),
    ]
    engine = OptimizationEngine(random_seed=123)
    context_weights = {"urgency_weight": 0.3, "value_weight": 0.4, "alignment_weight": 0.3}
    learned_weights = {"urgency_weight": 0.2, "value_weight": 0.5, "alignment_weight": 0.3}
    baseline = engine.solve_baseline(
        stories=stories,
        mode="random_feasible",
        context_weights=context_weights,
        learned_weights=learned_weights,
        capacity=8,
        risk_threshold=1.0,
        available_skills=[],
        random_seed=123,
    )
    baseline2 = engine.solve_baseline(
        stories=stories,
        mode="random_feasible",
        context_weights=context_weights,
        learned_weights=learned_weights,
        capacity=8,
        risk_threshold=1.0,
        available_skills=[],
        random_seed=123,
    )
    assert baseline.solver_status.startswith("baseline:random_feasible")
    assert [s.story_id for s in baseline.selected_stories] == [s.story_id for s in baseline2.selected_stories]
