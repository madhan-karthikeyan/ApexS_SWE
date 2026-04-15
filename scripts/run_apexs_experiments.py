from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.models.story import UserStory
from app.services.context_extractor import ContextExtractor
from app.services.optimization_engine import OptimizationEngine
from app.services.preprocessing import normalize_skill, normalize_skills, normalize_status, parse_depends_on
from app.services.weight_learning import WeightLearningModel


DATASETS = {
    "spring_xd": ROOT / "files/cleaned_datasets/spring_xd_clean.csv",
    "usergrid": ROOT / "files/cleaned_datasets/usergrid_clean.csv",
    "aurora": ROOT / "files/cleaned_datasets/aurora_clean.csv",
    "tawos": ROOT / "tawos/paper_datasets/tawos_apex_clean.csv",
}

BASELINE_MODES = [
    "fixed_weight_milp",
    "context_only",
    "greedy_feasible",
    "random_feasible",
]

ABLATION_CONFIGS = {
    "all_constraints": dict(enforce_capacity=True, enforce_risk=True, enforce_skill=True, enforce_dependencies=True),
    "no_risk": dict(enforce_capacity=True, enforce_risk=False, enforce_skill=True, enforce_dependencies=True),
    "no_skill": dict(enforce_capacity=True, enforce_risk=True, enforce_skill=False, enforce_dependencies=True),
    "no_dependency": dict(enforce_capacity=True, enforce_risk=True, enforce_skill=True, enforce_dependencies=False),
    "no_capacity": dict(enforce_capacity=False, enforce_risk=True, enforce_skill=True, enforce_dependencies=True),
}


def set_global_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


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


def _to_story(row: dict[str, Any], sprint_id: str) -> UserStory:
    story_id = str(row.get("story_id") or "")
    return UserStory(
        story_id=story_id,
        sprint_id=sprint_id,
        title=str(row.get("title") or f"Story {story_id}"),
        description=str(row.get("description") or ""),
        story_points=max(_safe_int(row.get("story_points"), 1), 1),
        business_value=_safe_float(row.get("business_value"), 0.0),
        risk_score=_safe_float(row.get("risk_score"), 0.0),
        required_skill=normalize_skill(row.get("required_skill")),
        depends_on=parse_depends_on(row.get("depends_on")),
        status=normalize_status(row.get("status")) or "backlog",
    )


def _dataset_stats(df: pd.DataFrame) -> dict[str, Any]:
    dep_rows = 0
    if "depends_on" in df.columns:
        dep_rows = int(df["depends_on"].fillna("").astype(str).str.strip().ne("").sum())
    sprint_groups = int(df["sprint_id"].nunique()) if "sprint_id" in df.columns else 0
    return {
        "stories": int(len(df)),
        "sprint_groups": sprint_groups,
        "dependency_rows": dep_rows,
        "mean_business_value": float(pd.to_numeric(df.get("business_value", 0.0), errors="coerce").fillna(0.0).mean()),
        "mean_risk": float(pd.to_numeric(df.get("risk_score", 0.0), errors="coerce").fillna(0.0).mean()),
    }


@dataclass
class ExperimentRun:
    dataset: str
    seed: int
    mode: str
    ablation: str
    solver_status: str
    selected_count: int
    total_value: float
    capacity_used: int
    avg_risk: float
    objective_score: float
    skill_coverage: float
    sprint_completion_ratio: float | None
    runtime_ms: float
    feasibility_total: int
    filtered_by_risk: int
    filtered_by_skill: int
    filtered_by_dependency: int
    filtered_by_status: int
    score_min: float
    score_max: float
    score_mean: float


def _result_to_run(dataset: str, seed: int, mode: str, ablation: str, result) -> ExperimentRun:
    counts = result.feasibility_counts or {}
    score_dist = result.score_distribution or {}
    return ExperimentRun(
        dataset=dataset,
        seed=seed,
        mode=mode,
        ablation=ablation,
        solver_status=result.solver_status,
        selected_count=result.selected_count,
        total_value=float(result.total_value),
        capacity_used=int(result.capacity_used),
        avg_risk=float(result.total_risk),
        objective_score=float(result.objective_score),
        skill_coverage=float(result.skill_coverage),
        sprint_completion_ratio=result.sprint_completion_ratio,
        runtime_ms=float(result.runtime_ms),
        feasibility_total=int(counts.get("total", 0)),
        filtered_by_risk=int(counts.get("filtered_by_risk", 0)),
        filtered_by_skill=int(counts.get("filtered_by_skill", 0)),
        filtered_by_dependency=int(counts.get("filtered_by_dependency", 0)),
        filtered_by_status=int(counts.get("filtered_by_status", 0)),
        score_min=float(score_dist.get("min", 0.0)),
        score_max=float(score_dist.get("max", 0.0)),
        score_mean=float(score_dist.get("mean", 0.0)),
    )


def run_experiments(capacity: int = 30, risk_threshold: float = 0.7, seeds: list[int] | None = None) -> dict[str, Any]:
    seeds = seeds or [42, 43, 44]
    output_dir = ROOT / "files" / "experiment_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_runs: list[ExperimentRun] = []
    summaries: dict[str, Any] = {}

    started = time.perf_counter()
    for dataset_name, dataset_path in DATASETS.items():
        df = pd.read_csv(dataset_path)
        df_latest = _latest_by_story(df)
        dataset_summary = _dataset_stats(df_latest)
        summaries[dataset_name] = {"dataset_path": str(dataset_path), "stats": dataset_summary, "runs": []}

        available_skills = normalize_skills(df_latest.get("required_skill", pd.Series(dtype=str)).dropna().tolist())
        sprint_id = str(df_latest.get("sprint_id", pd.Series([f"{dataset_name}-sprint"])).iloc[0])
        stories = [_to_story(row, sprint_id) for row in df_latest.to_dict(orient="records") if row.get("story_id")]

        for seed in seeds:
            set_global_seed(seed)
            context = ContextExtractor().extract(df_latest, team_capacity=capacity)
            learner = WeightLearningModel(random_state=seed)
            learned_weights, learning_metrics = learner.train_with_metrics(df_latest, context)
            context_weights = {
                "urgency_weight": context.urgency_weight,
                "value_weight": context.value_weight,
                "alignment_weight": context.alignment_weight,
            }

            for ablation_name, ablation_cfg in ABLATION_CONFIGS.items():
                engine = OptimizationEngine(random_seed=seed, **ablation_cfg)
                main_result = engine.solve(stories, learned_weights, capacity, risk_threshold, available_skills)
                run = _result_to_run(dataset_name, seed, "learned_milp", ablation_name, main_result)
                all_runs.append(run)
                summaries[dataset_name]["runs"].append(
                    {
                        **asdict(run),
                        "learning_metrics": learning_metrics,
                        "learned_weights": learned_weights,
                        "context_weights": context_weights,
                    }
                )

                if ablation_name == "all_constraints":
                    for baseline in BASELINE_MODES:
                        baseline_result = engine.solve_baseline(
                            stories=stories,
                            mode=baseline,
                            context_weights=context_weights,
                            learned_weights=learned_weights,
                            capacity=capacity,
                            risk_threshold=risk_threshold,
                            available_skills=available_skills,
                            random_seed=seed,
                        )
                        baseline_run = _result_to_run(dataset_name, seed, baseline, ablation_name, baseline_result)
                        all_runs.append(baseline_run)
                        summaries[dataset_name]["runs"].append(
                            {
                                **asdict(baseline_run),
                                "learning_metrics": learning_metrics,
                                "learned_weights": learned_weights,
                                "context_weights": context_weights,
                            }
                        )

    run_rows = [asdict(run) for run in all_runs]
    run_df = pd.DataFrame(run_rows)

    aggregate = (
        run_df.groupby(["dataset", "mode", "ablation"], dropna=False)
        .agg(
            selected_count_mean=("selected_count", "mean"),
            selected_count_std=("selected_count", "std"),
            total_value_mean=("total_value", "mean"),
            total_value_std=("total_value", "std"),
            avg_risk_mean=("avg_risk", "mean"),
            avg_risk_std=("avg_risk", "std"),
            runtime_ms_mean=("runtime_ms", "mean"),
            runtime_ms_std=("runtime_ms", "std"),
            objective_score_mean=("objective_score", "mean"),
            objective_score_std=("objective_score", "std"),
        )
        .reset_index()
    )

    ended = time.perf_counter()
    metadata = {
        "capacity": capacity,
        "risk_threshold": risk_threshold,
        "seeds": seeds,
        "dataset_paths": {k: str(v) for k, v in DATASETS.items()},
        "runtime_s": float(ended - started),
    }

    run_df.to_csv(output_dir / "experiment_runs.csv", index=False)
    aggregate.to_csv(output_dir / "experiment_aggregate.csv", index=False)
    (output_dir / "experiment_summary.json").write_text(
        json.dumps({"metadata": metadata, "datasets": summaries}, indent=2),
        encoding="utf-8",
    )

    return {
        "metadata": metadata,
        "datasets": summaries,
        "runs_csv": str(output_dir / "experiment_runs.csv"),
        "aggregate_csv": str(output_dir / "experiment_aggregate.csv"),
        "summary_json": str(output_dir / "experiment_summary.json"),
    }


if __name__ == "__main__":
    result = run_experiments()
    print(json.dumps(result, indent=2))
