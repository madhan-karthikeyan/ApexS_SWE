from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


KEY_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")


def to_story_points(value: float) -> int:
    if pd.isna(value):
        return 1
    v = float(value)
    if v <= 0:
        return 1

    # Many Jira exports are in seconds; convert to hours for bucketing.
    if v > 100:
        hours = v / 3600.0
        if hours <= 1:
            return 1
        if hours <= 3:
            return 2
        if hours <= 6:
            return 3
        if hours <= 12:
            return 5
        if hours <= 24:
            return 8
        return 13

    if v <= 1:
        return 1
    if v <= 2:
        return 2
    if v <= 3:
        return 3
    if v <= 5:
        return 5
    if v <= 8:
        return 8
    return 13


def normalize_skill(raw: str) -> str:
    text = (raw or "").lower()
    if any(k in text for k in ["frontend", "web", "ui", "react", "angular", "vue", "css", "html"]):
        return "Frontend"
    if any(k in text for k in ["database", "db", "query", "storage", "shard", "replication", "index"]):
        return "Database"
    if any(k in text for k in ["test", "qa", "verification", "benchmark", "quality"]):
        return "Testing"
    if any(k in text for k in ["devops", "deploy", "kubernetes", "ci", "cd", "release", "ops", "pipeline", "infra"]):
        return "DevOps"
    if any(k in text for k in ["mobile", "android", "ios"]):
        return "Frontend"
    return "Backend"


def normalize_status(raw: str) -> str:
    s = (raw or "").strip().lower()
    if any(k in s for k in ["done", "closed", "resolved", "complete", "fixed", "accepted", "shipped"]):
        return "done"
    if any(k in s for k in ["blocked", "waiting", "on hold"]):
        return "blocked"
    if any(k in s for k in ["in progress", "review", "implementing", "investigating", "working"]):
        return "in_progress"
    return "backlog"


def derive_business_value(title: str, points: int, risk: float, status_norm: str, base: float) -> float:
    text = f"{title}".lower()
    domain_bonus = 0.0
    if any(k in text for k in ["security", "fraud", "payment", "checkout", "auth", "incident", "critical"]):
        domain_bonus += 1.5
    if any(k in text for k in ["docs", "documentation", "typo", "style", "cleanup", "refactor"]):
        domain_bonus -= 1.0

    status_bonus = 0.0
    if status_norm == "done":
        status_bonus += 0.5
    elif status_norm == "blocked":
        status_bonus -= 0.5

    complexity_bonus = 1.0 if points >= 8 else (0.4 if points <= 3 else 0.0)

    value = 5.0 + domain_bonus + status_bonus + (1.0 - risk) * 2.0 + complexity_bonus
    if not pd.isna(base):
        value = (value + float(base)) / 2.0
    return round(min(max(value, 3.0), 10.0), 2)


def derive_risk(title: str, status_norm: str, base: float) -> float:
    text = title.lower()
    risk = float(base) if not pd.isna(base) else 0.4

    if status_norm == "done":
        risk -= 0.1
    elif status_norm == "blocked":
        risk += 0.2
    elif status_norm == "backlog":
        risk += 0.05

    if any(k in text for k in ["security", "fraud", "payment", "migration", "deploy", "kubernetes", "distributed"]):
        risk += 0.15
    if any(k in text for k in ["docs", "typo", "ui", "style", "label"]):
        risk -= 0.1

    return round(min(max(risk, 0.05), 0.95), 2)


def extract_dependencies(dep_raw: str, story_id: str) -> str:
    deps = []
    for key in KEY_PATTERN.findall(dep_raw or ""):
        if key != story_id and key not in deps:
            deps.append(key)
    return "|".join(deps)


def clean_dataset(input_path: Path, output_path: Path) -> int:
    df = pd.read_csv(input_path)

    df["story_id"] = df["story_id"].astype(str).str.strip()
    df = df[df["story_id"] != ""].copy()
    df = df.drop_duplicates(subset=["story_id"], keep="first")

    df["title"] = df["title"].fillna("Untitled Story").astype(str).str.strip().str.slice(0, 180)
    df["description"] = df["description"].fillna("").astype(str).str.slice(0, 2000)

    df["story_points"] = pd.to_numeric(df["story_points"], errors="coerce").fillna(1).apply(to_story_points)

    status_norm = df["status"].fillna("").astype(str).apply(normalize_status)
    df["status"] = status_norm

    base_risk = pd.to_numeric(df["risk_score"], errors="coerce").fillna(0.4)
    df["risk_score"] = [derive_risk(t, s, r) for t, s, r in zip(df["title"], status_norm, base_risk)]

    base_value = pd.to_numeric(df["business_value"], errors="coerce")
    df["business_value"] = [
        derive_business_value(t, int(p), float(r), s, b)
        for t, p, r, s, b in zip(df["title"], df["story_points"], df["risk_score"], status_norm, base_value)
    ]

    df["required_skill"] = df["required_skill"].fillna("").astype(str).apply(normalize_skill)
    df["depends_on"] = [extract_dependencies(dep, sid) for dep, sid in zip(df["depends_on"].fillna(""), df["story_id"])]

    comp = pd.to_numeric(df["sprint_completed"], errors="coerce")
    df["sprint_completed"] = comp.where(comp.isin([0, 1]), None)
    df["sprint_completed"] = df["sprint_completed"].fillna((status_norm == "done").astype(int)).astype(int)

    df["sprint_id"] = df["sprint_id"].fillna("SPR-UNK").astype(str).str.strip()
    df.loc[df["sprint_id"] == "", "sprint_id"] = "SPR-UNK"

    final_cols = [
        "story_id",
        "title",
        "description",
        "story_points",
        "business_value",
        "risk_score",
        "required_skill",
        "sprint_id",
        "sprint_completed",
        "depends_on",
        "status",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df[final_cols].to_csv(output_path, index=False)
    return len(df)


if __name__ == "__main__":
    src = Path("tmp/public_jira_dataset_final.csv")
    dst = Path("tmp/public_jira_dataset_final_clean.csv")
    count = clean_dataset(src, dst)
    print(f"Cleaned {count} rows -> {dst}")
