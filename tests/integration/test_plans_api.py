from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import time

from app.main import app
from app.core.config import settings


client = TestClient(app)


def test_health_root():
    response = client.get("/")
    assert response.status_code == 200


def test_dataset_upload_missing_required_column_returns_400(tmp_path):
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_text("story_id,story_points,risk_score\nUS1,5,0.2\n", encoding="utf-8")

    with csv_path.open("rb") as f:
        response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("invalid.csv", f, "text/csv")},
            data={"team_id": "00000000-0000-0000-0000-000000000001"},
        )

    assert response.status_code == 400
    assert "Missing columns" in response.json()["detail"]


def test_generate_plan_with_missing_sprint_returns_404():
    response = client.post(
        "/api/v1/plans/generate",
        json={
            "sprint_id": "00000000-0000-0000-0000-000000000099",
            "capacity": 30,
            "risk_threshold": 0.7,
            "available_skills": ["Backend"],
        },
    )
    assert response.status_code == 404


def test_approve_missing_plan_returns_404():
    response = client.put("/api/v1/plans/00000000-0000-0000-0000-000000000099/approve")
    assert response.status_code == 404


def test_export_missing_plan_returns_404():
    response = client.post("/api/v1/plans/00000000-0000-0000-0000-000000000099/export?format=json")
    assert response.status_code == 404


def test_reports_metrics_endpoint_returns_payload():
    response = client.get("/api/v1/reports/00000000-0000-0000-0000-000000000001/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert "sprint_velocity" in payload
    assert "business_value" in payload
    assert "risk_selected" in payload
    assert "risk_rejected" in payload
    assert "learning_sample_count" in payload
    assert "learning_model_type" in payload


def test_health_endpoint_returns_service_checks():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert "status" in payload
    assert "checks" in payload
    assert "database" in payload["checks"]


def test_concurrent_uploads_with_same_filename_preserve_independent_previews():
    team_id = "00000000-0000-0000-0000-000000000001"
    csv_one = (
        "story_id,story_points,business_value,risk_score\n"
        "US1,5,8,0.2\n"
    ).encode("utf-8")
    csv_two = (
        "story_id,story_points,business_value,risk_score\n"
        "US2,3,7,0.1\n"
        "US3,2,6,0.2\n"
    ).encode("utf-8")

    def upload(content: bytes):
        local_client = TestClient(app)
        response = local_client.post(
            "/api/v1/datasets/upload",
            files={"file": ("shared.csv", content, "text/csv")},
            data={"team_id": team_id},
        )
        assert response.status_code == 200
        return response.json()["upload_id"], response.json()["rows"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(upload, csv_one)
        second_future = executor.submit(upload, csv_two)
        first_upload_id, first_rows = first_future.result()
        second_upload_id, second_rows = second_future.result()

    first_preview = client.get(f"/api/v1/datasets/{first_upload_id}/preview")
    second_preview = client.get(f"/api/v1/datasets/{second_upload_id}/preview")

    assert first_preview.status_code == 200
    assert second_preview.status_code == 200
    assert first_preview.json()["rows"] == first_rows
    assert second_preview.json()["rows"] == second_rows
    assert first_preview.json()["preview"][0]["story_id"] != second_preview.json()["preview"][0]["story_id"]


def test_generate_requires_auth_when_enforced():
    original = settings.enforce_auth
    settings.enforce_auth = True
    try:
        response = client.post(
            "/api/v1/plans/generate",
            json={
                "sprint_id": "00000000-0000-0000-0000-000000000099",
                "capacity": 30,
                "risk_threshold": 0.7,
                "available_skills": ["Backend"],
            },
        )
        assert response.status_code == 401
    finally:
        settings.enforce_auth = original


def test_generate_plan_pipeline_completes_with_valid_seed_data(tmp_path):
    # 1) Upload a valid dataset
    csv_path = tmp_path / "valid.csv"
    csv_path.write_text(
        "story_id,story_points,business_value,risk_score,sprint_id,sprint_completed,required_skill\n"
        "US1,5,8,0.2,SP1,1,Backend\n",
        encoding="utf-8",
    )
    with csv_path.open("rb") as f:
        upload_response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("valid.csv", f, "text/csv")},
            data={"team_id": "00000000-0000-0000-0000-000000000001"},
        )
    assert upload_response.status_code == 200

    # 2) Create sprint
    sprint_response = client.post(
        "/api/v1/sprints/",
        json={
            "team_id": "00000000-0000-0000-0000-000000000001",
            "goal": "Deliver highest value stories",
            "capacity": 30,
            "status": "planning",
        },
    )
    assert sprint_response.status_code == 200
    sprint_id = sprint_response.json()["sprint_id"]

    # 3) Add story
    story_response = client.post(
        "/api/v1/stories/",
        json={
            "sprint_id": sprint_id,
            "title": "Backend auth",
            "description": "Auth implementation",
            "story_points": 5,
            "business_value": 8,
            "risk_score": 0.2,
            "required_skill": "Backend",
            "depends_on": [],
            "status": "backlog",
        },
    )
    assert story_response.status_code == 200

    # 4) Trigger generation and poll status
    gen_response = client.post(
        "/api/v1/plans/generate",
        json={
            "sprint_id": sprint_id,
            "capacity": 30,
            "risk_threshold": 0.7,
            "available_skills": ["Backend"],
        },
    )
    assert gen_response.status_code == 200
    job_id = gen_response.json()["job_id"]

    plan_id = None
    for _ in range(40):
        status_response = client.get(f"/api/v1/plans/status/{job_id}")
        assert status_response.status_code == 200
        payload = status_response.json()
        if payload.get("status") == "complete":
            plan_id = payload.get("plan_id")
            break
        time.sleep(0.2)

    assert plan_id is not None

    explain_response = client.get(f"/api/v1/plans/{plan_id}/explain")
    assert explain_response.status_code == 200


def test_end_to_end_stage_flow_with_checks(tmp_path):
    team_id = "00000000-0000-0000-0000-000000000001"

    # Stage 1: upload dataset
    csv_path = tmp_path / "dataset.csv"
    csv_path.write_text(
        "story_id,title,story_points,business_value,risk_score,required_skill,sprint_id,sprint_completed,depends_on,status\n"
        "US-1,Core API,5,9,0.2,Backend,SP1,1,,backlog\n"
        "US-2,UI Dashboard,5,8,0.3,Frontend,SP1,1,,backlog\n"
        "US-3,Reports,3,6,0.4,Backend,SP1,1,US-1,backlog\n"
        "US-4,High Risk Spike,3,10,0.95,Backend,SP1,0,,backlog\n",
        encoding="utf-8",
    )
    with csv_path.open("rb") as f:
        upload_response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("dataset.csv", f, "text/csv")},
            data={"team_id": team_id},
        )
    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    assert upload_payload["upload_id"]
    assert upload_payload["rows"] == 4
    assert upload_payload["is_valid"] is True

    # Stage 2: create sprint and generate plan
    sprint_response = client.post(
        "/api/v1/sprints/",
        json={
            "team_id": team_id,
            "goal": "Deliver value with low risk",
            "capacity": 10,
            "status": "planning",
        },
    )
    assert sprint_response.status_code == 200
    sprint_id = sprint_response.json()["sprint_id"]

    generate_response = client.post(
        "/api/v1/plans/generate",
        json={
            "sprint_id": sprint_id,
            "capacity": 10,
            "risk_threshold": 0.7,
            "available_skills": ["Backend", "Frontend"],
        },
    )
    assert generate_response.status_code == 200
    job_id = generate_response.json()["job_id"]
    assert job_id

    # Stage 3: poll status transitions
    plan_id = None
    seen_steps = set()
    for _ in range(80):
        status_response = client.get(f"/api/v1/plans/status/{job_id}")
        assert status_response.status_code == 200
        status_payload = status_response.json()
        seen_steps.add(status_payload.get("step"))
        if status_payload.get("status") == "complete":
            assert status_payload.get("progress") == 100
            plan_id = status_payload.get("plan_id")
            break
        time.sleep(0.15)

    assert plan_id is not None
    assert "done" in seen_steps

    # Stage 4: generated plan
    plan_response = client.get(f"/api/v1/plans/{plan_id}")
    assert plan_response.status_code == 200
    plan = plan_response.json()
    assert plan["status"] == "draft"
    assert plan["capacity_used"] <= 10
    assert len(plan["selected_stories"]) > 0

    stories_response = client.get(f"/api/v1/plans/{plan_id}/stories")
    assert stories_response.status_code == 200
    stories = stories_response.json()
    assert len(stories) > 0

    # Stage 5 + 6: quality and explainability
    explain_response = client.get(f"/api/v1/plans/{plan_id}/explain")
    assert explain_response.status_code == 200
    explanations = explain_response.json()
    assert len(explanations) >= len(stories)
    assert any(e.get("reason") for e in explanations)

    selected_story_ids = [s["story_id"] for s in stories]
    assert len(selected_story_ids) == len(set(selected_story_ids))

    for selected in stories:
        assert selected["risk_score"] <= 0.7
        deps = selected.get("depends_on") or []
        for dep in deps:
            assert dep in selected_story_ids

    # Stage 7: approve
    approve_response = client.put(f"/api/v1/plans/{plan_id}/approve")
    assert approve_response.status_code == 200
    approved_plan = client.get(f"/api/v1/plans/{plan_id}").json()
    assert approved_plan["status"] == "approved"

    # Stage 8: export
    export_csv = client.post(f"/api/v1/plans/{plan_id}/export?format=csv")
    assert export_csv.status_code == 200
    assert "Summary" in export_csv.text

    export_json = client.post(f"/api/v1/plans/{plan_id}/export?format=json")
    assert export_json.status_code == 200
    exported_stories = export_json.json()["stories"]
    assert len(exported_stories) == len(stories)

    # Stage 9: regression rerun with lower capacity + lower risk threshold
    modify_response = client.put(
        f"/api/v1/plans/{plan_id}/modify",
        json={
            "capacity": 5,
            "risk_threshold": 0.3,
            "available_skills": ["Backend", "Frontend"],
        },
    )
    assert modify_response.status_code == 200
    job_id_2 = modify_response.json()["job_id"]

    second_plan_id = None
    for _ in range(80):
        status_response = client.get(f"/api/v1/plans/status/{job_id_2}")
        payload = status_response.json()
        if payload.get("status") == "complete":
            second_plan_id = payload.get("plan_id")
            break
        time.sleep(0.15)

    assert second_plan_id is not None
    assert second_plan_id != plan_id

    second_plan = client.get(f"/api/v1/plans/{second_plan_id}").json()
    second_stories = client.get(f"/api/v1/plans/{second_plan_id}/stories").json()
    assert second_plan["capacity_used"] <= 5
    assert len(second_stories) <= len(stories)
