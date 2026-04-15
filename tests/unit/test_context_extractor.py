from app.services.context_extractor import ContextExtractor
import pandas as pd


def test_context_extractor_returns_weights():
    df = pd.DataFrame([
        {"sprint_id": "SP1", "story_points": 5, "business_value": 8, "risk_score": 0.2, "required_skill": "Backend", "sprint_completed": 1},
        {"sprint_id": "SP1", "story_points": 3, "business_value": 6, "risk_score": 0.1, "required_skill": "Frontend", "sprint_completed": 1},
    ])
    ctx = ContextExtractor().extract(df, team_capacity=20)
    assert ctx.urgency_weight > 0
    assert ctx.value_weight > 0
    assert ctx.alignment_weight > 0
