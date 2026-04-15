from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

BASE_URL = "http://localhost:8000"
CAPACITY = 30
RISK_THRESHOLD = 0.7
DATASETS = {
    "Spring XD": Path("D:/SE/files/cleaned_datasets/spring_xd_clean.csv"),
    "Usergrid": Path("D:/SE/files/cleaned_datasets/usergrid_clean.csv"),
    "Aurora": Path("D:/SE/files/cleaned_datasets/aurora_clean.csv"),
    "TAWOS": Path("D:/SE/tawos/paper_datasets/tawos_apex_clean.csv"),
}
NON_PLANNABLE = {"done", "closed", "resolved", "completed"}


@dataclass
class RunMetrics:
    selected: int
    deliv_bv: float
    used_sp: int
    avg_risk: float
    dep_sat: float
    sprint_compl: float
    skill_cov: float


@dataclass
class BaselineMetrics:
    selected: int
    deliv_bv: float
    used_sp: int
    avg_risk: float
    dep_sat: float


def _parse_depends_on(value: Any) -> list[str]:
    if value is None:
        return []
    try:
        if pd.isna(value):
            return []
    except Exception:
        pass
    raw = str(value).strip()
    if not raw:
        return []
    for sep in [",", ";", "|"]:
        raw = raw.replace(sep, " ")
    return [tok for tok in raw.split() if tok]


def _norm_status(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip().lower()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def _latest_by_story(df: pd.DataFrame) -> pd.DataFrame:
    if "story_id" not in df.columns:
        return df.copy()
    return df.drop_duplicates(subset=["story_id"], keep="last").copy()


def _dep_satisfaction(selected_ids: set[str], selected_rows: list[dict[str, Any]], by_id: dict[str, dict[str, Any]]) -> float:
    dep_edges = 0
    dep_ok = 0
    for row in selected_rows:
        story_id = str(row.get("story_id", ""))
        source = by_id.get(story_id, {})
        for dep in _parse_depends_on(source.get("depends_on")):
            dep_edges += 1
            if dep in selected_ids:
                dep_ok += 1
    if dep_edges == 0:
        return 1.0
    return dep_ok / dep_edges


def _skill_coverage(selected_rows: list[dict[str, Any]], feasible_rows: list[dict[str, Any]]) -> float:
    feasible_skills = {str(r.get("required_skill", "")).strip() for r in feasible_rows if str(r.get("required_skill", "")).strip()}
    selected_skills = {str(r.get("required_skill", "")).strip() for r in selected_rows if str(r.get("required_skill", "")).strip()}
    if not feasible_skills:
        return 1.0
    return len(selected_skills) / len(feasible_skills)


def baseline_rank(df: pd.DataFrame, capacity: int, risk_threshold: float) -> tuple[BaselineMetrics, list[dict[str, Any]], list[dict[str, Any]]]:
    d = _latest_by_story(df)
    rows = d.to_dict(orient="records")
    by_id: dict[str, dict[str, Any]] = {}
    for r in rows:
        sid = str(r.get("story_id", "")).strip()
        if sid:
            by_id[sid] = r

    feasible: list[dict[str, Any]] = []
    for r in by_id.values():
        status = _norm_status(r.get("status"))
        if status in NON_PLANNABLE:
            continue
        if _safe_float(r.get("risk_score"), 0.0) > risk_threshold:
            continue
        deps = _parse_depends_on(r.get("depends_on"))
        if any(dep not in by_id for dep in deps):
            continue
        feasible.append(r)

    ranked = sorted(
        feasible,
        key=lambda r: (_safe_float(r.get("business_value"), 0.0), -_safe_float(r.get("risk_score"), 0.0), -_safe_int(r.get("story_points"), 1)),
        reverse=True,
    )

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    used_capacity = 0

    changed = True
    while changed:
        changed = False
        for r in ranked:
            sid = str(r.get("story_id", "")).strip()
            if not sid or sid in selected_ids:
                continue
            sp = max(_safe_int(r.get("story_points"), 1), 1)
            deps = _parse_depends_on(r.get("depends_on"))
            if used_capacity + sp > capacity:
                continue
            if any(dep not in selected_ids for dep in deps):
                continue
            selected.append(r)
            selected_ids.add(sid)
            used_capacity += sp
            changed = True
            break

    selected_count = len(selected)
    deliv_bv = float(sum(_safe_float(r.get("business_value"), 0.0) for r in selected))
    avg_risk = float(sum(_safe_float(r.get("risk_score"), 0.0) for r in selected) / selected_count) if selected_count else 0.0
    dep_sat = _dep_satisfaction(selected_ids, selected, by_id)

    metrics = BaselineMetrics(
        selected=selected_count,
        deliv_bv=deliv_bv,
        used_sp=used_capacity,
        avg_risk=avg_risk,
        dep_sat=dep_sat,
    )
    return metrics, selected, feasible


def run_apex_for_dataset(client: httpx.Client, team_id: str, csv_path: Path) -> dict[str, Any]:
    with csv_path.open("rb") as f:
        upload = client.post(
            f"{BASE_URL}/api/v1/datasets/upload",
            files={"file": (csv_path.name, f, "text/csv")},
            data={"team_id": team_id},
            timeout=180,
        )
    upload.raise_for_status()

    sprint = client.post(
        f"{BASE_URL}/api/v1/sprints/",
        json={"team_id": team_id, "goal": f"paper-run-{csv_path.stem}", "capacity": CAPACITY, "status": "planning"},
        timeout=60,
    )
    sprint.raise_for_status()
    sprint_id = sprint.json()["sprint_id"]

    # Empty list means no skill filter in current optimization engine.
    gen = client.post(
        f"{BASE_URL}/api/v1/plans/generate",
        json={"sprint_id": sprint_id, "capacity": CAPACITY, "risk_threshold": RISK_THRESHOLD, "available_skills": []},
        timeout=60,
    )
    gen.raise_for_status()
    job_id = gen.json()["job_id"]

    status = {"status": "processing"}
    for _ in range(2400):
        st = client.get(f"{BASE_URL}/api/v1/plans/status/{job_id}", timeout=60)
        st.raise_for_status()
        status = st.json()
        if status.get("status") in {"complete", "failed"}:
            break
        import time
        time.sleep(1)
    if status.get("status") != "complete":
        raise RuntimeError(f"Job failed for {csv_path.name}: {status}")

    plan_id = status["plan_id"]
    plan = client.get(f"{BASE_URL}/api/v1/plans/{plan_id}", timeout=60)
    stories = client.get(f"{BASE_URL}/api/v1/plans/{plan_id}/stories", timeout=60)
    explanations = client.get(f"{BASE_URL}/api/v1/plans/{plan_id}/explain", timeout=60)
    selected_explanations = client.get(f"{BASE_URL}/api/v1/plans/{plan_id}/explain", params={"selected": "true"}, timeout=60)
    rejected_explanations = client.get(f"{BASE_URL}/api/v1/plans/{plan_id}/explain", params={"selected": "false"}, timeout=60)
    for r in [plan, stories, explanations, selected_explanations, rejected_explanations]:
        r.raise_for_status()

    return {
        "sprint_id": sprint_id,
        "plan_id": plan_id,
        "plan": plan.json(),
        "selected_stories": stories.json(),
        "explanations": explanations.json(),
        "selected_explanations": selected_explanations.json(),
        "rejected_explanations": rejected_explanations.json(),
    }


def main() -> None:
    out_dir = Path("D:/SE/files")
    out_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client() as client:
        health = client.get(f"{BASE_URL}/health", timeout=30)
        health.raise_for_status()

        teams = client.get(f"{BASE_URL}/api/v1/teams/", timeout=30)
        teams.raise_for_status()
        team_list = teams.json()
        if not team_list:
            raise RuntimeError("No teams available in backend")
        team_id = team_list[0]["team_id"]

        results: dict[str, Any] = {}

        for name, path in DATASETS.items():
            df = pd.read_csv(path)
            df_latest = _latest_by_story(df)
            by_id = {str(r.get("story_id", "")).strip(): r for r in df_latest.to_dict(orient="records") if str(r.get("story_id", "")).strip()}

            apex = run_apex_for_dataset(client, team_id, path)
            selected_rows = apex["selected_stories"]
            selected_ids = {str(r.get("story_id", "")) for r in selected_rows}

            # Feasible set for skill coverage denominator.
            feasible_rows = []
            for row in by_id.values():
                status = _norm_status(row.get("status"))
                if status in NON_PLANNABLE:
                    continue
                if _safe_float(row.get("risk_score"), 0.0) > RISK_THRESHOLD:
                    continue
                deps = _parse_depends_on(row.get("depends_on"))
                if any(dep not in by_id for dep in deps):
                    continue
                feasible_rows.append(row)

            selected_count = len(selected_rows)
            avg_selected_risk = float(
                sum(_safe_float(r.get("risk_score"), 0.0) for r in selected_rows) / selected_count
            ) if selected_count else 0.0

            dep_sat = _dep_satisfaction(selected_ids, selected_rows, by_id)

            sprint_completed_vals = []
            for r in selected_rows:
                src = by_id.get(str(r.get("story_id", "")), {})
                if "sprint_completed" in src:
                    sprint_completed_vals.append(_safe_float(src.get("sprint_completed"), 0.0))
            sprint_completion = float(sum(sprint_completed_vals) / len(sprint_completed_vals)) if sprint_completed_vals else 0.0

            skill_cov = _skill_coverage(selected_rows, feasible_rows)

            apex_metrics = RunMetrics(
                selected=selected_count,
                deliv_bv=float(apex["plan"].get("total_value", 0.0)),
                used_sp=int(apex["plan"].get("capacity_used", 0)),
                avg_risk=avg_selected_risk,
                dep_sat=dep_sat,
                sprint_compl=sprint_completion,
                skill_cov=skill_cov,
            )

            baseline_metrics, baseline_selected, _ = baseline_rank(df_latest, CAPACITY, RISK_THRESHOLD)

            results[name] = {
                "dataset_path": str(path),
                "apex": apex_metrics.__dict__,
                "baseline": baseline_metrics.__dict__,
                "apex_plan_id": apex["plan_id"],
                "apex_sprint_id": apex["sprint_id"],
                "apex_selected_story_ids": [r.get("story_id") for r in selected_rows],
                "baseline_selected_story_ids": [r.get("story_id") for r in baseline_selected],
                "rejected_explanations": apex["rejected_explanations"],
            }

        # Build one case study from TAWOS run.
        tawos = results["TAWOS"]
        tawos_df = _latest_by_story(pd.read_csv(DATASETS["TAWOS"]))
        by_id_tawos = {str(r.get("story_id", "")).strip(): r for r in tawos_df.to_dict(orient="records") if str(r.get("story_id", "")).strip()}

        selected_ids = set(tawos["apex_selected_story_ids"])
        selected_case = []
        for sid in tawos["apex_selected_story_ids"][:3]:
            row = by_id_tawos.get(str(sid), {})
            selected_case.append({
                "story_id": sid,
                "title": str(row.get("title", ""))[:90],
                "sp": _safe_int(row.get("story_points"), 0),
                "bv": _safe_float(row.get("business_value"), 0.0),
                "risk": _safe_float(row.get("risk_score"), 0.0),
                "skill": str(row.get("required_skill", ""))[:20],
                "sel": "Y",
                "explanation": "Selected by weighted value-risk-effort objective under constraints.",
            })

        rejected_case = []
        for exp in tawos.get("rejected_explanations", [])[:2]:
            sid = exp.get("story_id")
            row = by_id_tawos.get(str(sid), {})
            rejected_case.append({
                "story_id": sid,
                "title": str(row.get("title", ""))[:90],
                "sp": _safe_int(row.get("story_points"), 0),
                "bv": _safe_float(row.get("business_value"), 0.0),
                "risk": _safe_float(row.get("risk_score"), 0.0),
                "skill": str(row.get("required_skill", ""))[:20],
                "sel": "N",
                "explanation": str(exp.get("rejection_reason") or "Rejected by feasibility/priority constraints.")[:110],
            })

        results["case_study"] = selected_case + rejected_case
        results["config"] = {
            "capacity": CAPACITY,
            "risk_threshold": RISK_THRESHOLD,
            "available_skills": "none-filtered (empty list passed)",
            "run_mode": "backend local mode",
        }

        out_json = out_dir / "paper_table_metrics.json"
        out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")

        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
