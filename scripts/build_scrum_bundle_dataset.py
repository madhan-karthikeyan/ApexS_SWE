from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


OUTPUT_COLUMNS = [
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
    "source_bundle",
    "issue_type",
    "priority_id",
    "assignee",
    "sprint_name",
    "sprint_start_date",
    "sprint_end_date",
    "sprint_complete_date",
    "sprint_length",
    "team_size",
    "completed_velocity",
    "added_mid_sprint",
    "issue_links_count",
    "blocked_by_count",
    "blocks_count",
    "watch_count",
    "comment_count",
    "votes",
]

PRIORITY_VALUE_MAP = {
    1: 1.00,
    2: 0.82,
    3: 0.62,
    4: 0.42,
    5: 0.22,
}

PRIORITY_RISK_MAP = {
    1: 0.90,
    2: 0.76,
    3: 0.58,
    4: 0.38,
    5: 0.20,
}

SKILL_PATTERNS = {
    "Backend": {
        "api": 2.0,
        "rest": 2.0,
        "service": 1.8,
        "server": 1.6,
        "runtime": 1.5,
        "scheduler": 1.6,
        "registry": 1.3,
        "module": 1.0,
        "client": 1.0,
        "http": 1.2,
        "thrift": 1.4,
        "stream": 1.2,
        "channel": 1.2,
        "cron": 1.0,
        "executor": 1.6,
        "preemptor": 1.7,
        "scheduler": 1.7,
        "scheduling": 1.5,
        "thread": 1.2,
        "async": 1.2,
        "lock": 1.0,
        "quota": 1.0,
    },
    "Frontend": {
        "ui": 2.0,
        "page": 1.8,
        "navbar": 2.4,
        "logo": 1.8,
        "javascript": 1.8,
        "browser": 1.5,
        "web": 1.3,
        "screen": 1.6,
        "visual": 1.3,
        "view": 1.0,
        "shell ui": 1.2,
    },
    "Database": {
        "database": 2.2,
        "sql": 1.8,
        "jdbc": 1.8,
        "redis": 1.8,
        "hdfs": 2.0,
        "h2": 1.8,
        "store": 1.5,
        "lockstore": 2.2,
        "quotastore": 2.2,
        "persistence": 1.7,
        "index": 1.4,
        "query": 1.2,
        "cassandra": 1.8,
        "elasticsearch": 1.8,
        "storage": 1.6,
        "mysql": 1.8,
        "entity": 1.0,
        "collection": 1.0,
    },
    "Testing": {
        "test": 2.0,
        "tests": 2.0,
        "testing": 2.0,
        "junit": 2.0,
        "integration": 1.6,
        "flaky": 2.2,
        "checkstyle": 2.2,
        "jshint": 2.0,
        "fail": 1.6,
        "broken": 1.4,
        "assert": 1.4,
        "harness": 1.8,
        "validation": 1.0,
    },
    "DevOps": {
        "deploy": 2.1,
        "build": 1.8,
        "packaging": 1.8,
        "gradle": 1.8,
        "maven": 1.8,
        "release": 1.8,
        "config": 1.1,
        "bootstrap": 1.4,
        "port": 1.2,
        "log": 1.2,
        "logging": 1.2,
        "script": 1.5,
        "shell": 1.4,
        "upgrade": 1.2,
        "install": 1.3,
        "runtime node": 1.5,
    },
}

ISSUE_TYPE_VALUE_SIGNAL = {
    "story": 0.72,
    "bug": 0.68,
    "improvement": 0.60,
    "task": 0.52,
    "technical task": 0.48,
    "wish": 0.40,
}

ISSUE_TYPE_RISK_SIGNAL = {
    "story": 0.50,
    "bug": 0.72,
    "improvement": 0.42,
    "task": 0.55,
    "technical task": 0.62,
    "wish": 0.35,
}

TEXT_VALUE_HINTS = {
    "release": 0.10,
    "customer": 0.08,
    "roadmap": 0.08,
    "sla": 0.08,
    "performance": 0.06,
    "security": 0.10,
    "api": 0.04,
    "deploy": 0.05,
    "ui": 0.04,
}

TEXT_RISK_HINTS = {
    "flaky": 0.18,
    "fail": 0.10,
    "broken": 0.10,
    "exception": 0.10,
    "error": 0.10,
    "migration": 0.08,
    "async": 0.08,
    "parallel": 0.08,
    "refactor": 0.06,
    "cleanup": 0.04,
    "remove": 0.04,
    "upgrade": 0.05,
    "packaging": 0.05,
}


@dataclass
class ScoreProfile:
    p90_story_points: float
    p90_watch_count: float
    p90_comment_count: float
    p90_votes: float
    p90_issue_links: float
    p90_blocked_by: float
    p90_blocks: float
    p90_fix_versions: float
    p90_affected_versions: float


def _safe_quantile(values: pd.Series, default: float = 1.0) -> float:
    clean = pd.to_numeric(values, errors="coerce").fillna(0)
    if clean.empty:
        return default
    quantile = float(clean.quantile(0.90))
    return quantile if quantile > 0 else default


def _scaled(value: Any, cap: float) -> float:
    number = float(_to_int(value, 0))
    if cap <= 0:
        return 0.0
    return max(0.0, min(number / cap, 1.0))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _normalize_text(*parts: Any) -> str:
    text = " ".join(_to_text(part) for part in parts if _to_text(part))
    return re.sub(r"\s+", " ", text.strip().lower())


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _to_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() == "null":
        return ""
    return text


def _to_int(value: Any, default: int = 0) -> int:
    text = _to_text(value)
    if not text:
        return default
    try:
        return int(float(text))
    except Exception:
        return default


def _pick_story_points(row: pd.Series) -> int:
    for key in ("currentStoryPoint", "storyPoint", "initialStoryPoint"):
        value = _to_int(row.get(key), 0)
        if value > 0:
            return value
    return 1


def _priority_id(row: pd.Series) -> int:
    for key in ("priorityId", "priority"):
        value = _to_int(row.get(key), 0)
        if value > 0:
            return value
    return 3


def _text_hint_score(text: str, weights: dict[str, float]) -> float:
    score = 0.0
    for phrase, weight in weights.items():
        if phrase in text:
            score += weight
    return score


def _contains_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase).replace(r"\ ", r"\s+")
    pattern = rf"(?<!\w){escaped}(?!\w)"
    return re.search(pattern, text) is not None


def _skill_scores(text: str, issue_type: str) -> dict[str, float]:
    scores = {skill: 0.0 for skill in SKILL_PATTERNS}
    for skill, patterns in SKILL_PATTERNS.items():
        for phrase, weight in patterns.items():
            if _contains_phrase(text, phrase):
                scores[skill] += weight

    normalized_type = issue_type.lower()
    if normalized_type == "bug":
        scores["Testing"] += 0.4
        scores["Backend"] += 0.2
    elif normalized_type == "technical task":
        scores["Backend"] += 0.3
        scores["DevOps"] += 0.2
    elif normalized_type == "story":
        scores["Backend"] += 0.1
    return scores


def _infer_skill_from_text(row: pd.Series) -> tuple[str, float]:
    text = _normalize_text(row.get("summary"), row.get("description"), row.get("issueType"))
    scores = _skill_scores(text, _to_text(row.get("issueType")))
    best_skill = max(scores, key=scores.get)
    return (best_skill, scores[best_skill]) if scores[best_skill] > 0 else ("", 0.0)


def _derive_assignee_skill_map(df: pd.DataFrame) -> dict[str, str]:
    by_assignee: dict[str, list[str]] = {}
    for _, row in df.iterrows():
        assignee = _to_text(row.get("assignee"))
        skill = _to_text(row.get("_initial_skill"))
        confidence = float(row.get("_initial_skill_confidence", 0.0) or 0.0)
        if not assignee or not skill or confidence < 1.4:
            continue
        by_assignee.setdefault(assignee, []).append(skill)

    mapping: dict[str, str] = {}
    for assignee, skills in by_assignee.items():
        counts = Counter(skills)
        top_skill, top_count = counts.most_common(1)[0]
        if len(skills) >= 5 and top_count / len(skills) >= 0.72:
            mapping[assignee] = top_skill
    return mapping


def _final_skill(row: pd.Series, assignee_skill_map: dict[str, str]) -> str:
    text_skill = _to_text(row.get("_initial_skill"))
    text_confidence = float(row.get("_initial_skill_confidence", 0.0) or 0.0)
    if text_skill and text_confidence >= 1.0:
        return text_skill

    assignee = _to_text(row.get("assignee"))
    if assignee and assignee in assignee_skill_map:
        return assignee_skill_map[assignee]

    issue_type = _to_text(row.get("issueType")).lower()
    if issue_type == "technical task":
        return "Backend"
    return text_skill


def _business_value(row: pd.Series, priority_id: int, story_points: int, profile: ScoreProfile) -> float:
    text = _normalize_text(row.get("summary"), row.get("description"))
    priority_signal = PRIORITY_VALUE_MAP.get(priority_id, 0.62)
    issue_type_signal = ISSUE_TYPE_VALUE_SIGNAL.get(_to_text(row.get("issueType")).lower(), 0.55)
    engagement_signal = (
        0.35 * _scaled(row.get("watchcount"), profile.p90_watch_count)
        + 0.30 * _scaled(row.get("commentCount"), profile.p90_comment_count)
        + 0.20 * _scaled(row.get("votes"), profile.p90_votes)
        + 0.15 * _scaled(row.get("issueLinks"), profile.p90_issue_links)
    )
    release_signal = (
        0.60 * _scaled(row.get("fixVersions"), profile.p90_fix_versions)
        + 0.40 * _scaled(row.get("affectedVersions"), profile.p90_affected_versions)
    )
    size_signal = _scaled(story_points, profile.p90_story_points)
    text_signal = min(_text_hint_score(text, TEXT_VALUE_HINTS), 0.20)

    composite = (
        0.48 * priority_signal
        + 0.18 * issue_type_signal
        + 0.16 * engagement_signal
        + 0.08 * release_signal
        + 0.05 * size_signal
        + 0.05 * text_signal
    )
    return round(_clamp(1.0 + 9.0 * composite, 1.0, 10.0), 2)


def _risk_score(row: pd.Series, priority_id: int, story_points: int, profile: ScoreProfile) -> float:
    text = _normalize_text(row.get("summary"), row.get("description"))
    priority_signal = PRIORITY_RISK_MAP.get(priority_id, 0.58)
    issue_type_signal = ISSUE_TYPE_RISK_SIGNAL.get(_to_text(row.get("issueType")).lower(), 0.55)
    complexity_signal = _scaled(story_points, profile.p90_story_points)
    dependency_signal = (
        0.40 * _scaled(row.get("blockedBy"), profile.p90_blocked_by)
        + 0.30 * _scaled(row.get("blocks"), profile.p90_blocks)
        + 0.30 * _scaled(row.get("issueLinks"), profile.p90_issue_links)
    )
    volatility_signal = (
        0.60 * _scaled(row.get("commentCount"), profile.p90_comment_count)
        + 0.40 * _scaled(row.get("watchcount"), profile.p90_watch_count)
    )
    text_signal = min(_text_hint_score(text, TEXT_RISK_HINTS), 0.25)

    composite = (
        0.28 * priority_signal
        + 0.22 * issue_type_signal
        + 0.22 * complexity_signal
        + 0.18 * dependency_signal
        + 0.05 * volatility_signal
        + 0.05 * text_signal
    )
    return round(_clamp(composite, 0.05, 1.0), 2)


def _sprint_completed(status: str) -> int:
    return int(status.strip().lower() == "completed")


def _prepare_issue_rows(issues: pd.DataFrame) -> pd.DataFrame:
    issues = _normalize_columns(issues)
    issues["pair_key"] = issues["key"].map(_to_text) + "|" + issues["sprint"].map(lambda v: str(_to_int(v, 0)))
    issues["key_only"] = issues["key"].map(_to_text)
    issues = issues.drop_duplicates(subset=["pair_key"], keep="last")
    return issues


def _prepare_summary_rows(summary: pd.DataFrame) -> pd.DataFrame:
    summary = _normalize_columns(summary)
    summary["issueKey"] = summary["issueKey"].map(_to_text)
    summary["sprintId"] = summary["sprintId"].map(lambda v: str(_to_int(v, 0)))
    summary["status"] = summary["status"].map(_to_text)
    summary["pair_key"] = summary["issueKey"] + "|" + summary["sprintId"]
    summary = summary.drop_duplicates(subset=["pair_key", "status"], keep="last")
    return summary


def _prepare_sprint_rows(sprints: pd.DataFrame) -> pd.DataFrame:
    sprints = _normalize_columns(sprints)
    if "totalNumberOfIssues" in sprints.columns and "total" not in sprints.columns:
        sprints["total"] = sprints["totalNumberOfIssues"]
    if "issuesCompletedInAnotherSprintEstimateSum1" in sprints.columns and "issuesCompletedInAnotherSprintEstimateSum" not in sprints.columns:
        sprints["issuesCompletedInAnotherSprintEstimateSum"] = sprints["issuesCompletedInAnotherSprintEstimateSum1"]
    sprints["sprintId"] = sprints["sprintId"].map(lambda v: str(_to_int(v, 0)))
    sprints = sprints.drop_duplicates(subset=["sprintId"], keep="last")
    return sprints


def _build_score_profile(merged: pd.DataFrame) -> ScoreProfile:
    story_points = merged.apply(_pick_story_points, axis=1)
    return ScoreProfile(
        p90_story_points=_safe_quantile(story_points, 8.0),
        p90_watch_count=_safe_quantile(merged.get("watchcount", pd.Series(dtype=float)), 3.0),
        p90_comment_count=_safe_quantile(merged.get("commentCount", pd.Series(dtype=float)), 4.0),
        p90_votes=_safe_quantile(merged.get("votes", pd.Series(dtype=float)), 1.0),
        p90_issue_links=_safe_quantile(merged.get("issueLinks", pd.Series(dtype=float)), 3.0),
        p90_blocked_by=_safe_quantile(merged.get("blockedBy", pd.Series(dtype=float)), 1.0),
        p90_blocks=_safe_quantile(merged.get("blocks", pd.Series(dtype=float)), 1.0),
        p90_fix_versions=_safe_quantile(merged.get("fixVersions", pd.Series(dtype=float)), 1.0),
        p90_affected_versions=_safe_quantile(merged.get("affectedVersions", pd.Series(dtype=float)), 1.0),
    )


def build_dataset(issues_path: Path, summary_path: Path, sprints_path: Path, output_path: Path, source_bundle: str) -> int:
    issues = _prepare_issue_rows(pd.read_csv(issues_path))
    summary = _prepare_summary_rows(pd.read_csv(summary_path))
    sprints = _prepare_sprint_rows(pd.read_csv(sprints_path))

    merged = summary.merge(
        issues,
        how="left",
        left_on="pair_key",
        right_on="pair_key",
        suffixes=("", "_issue"),
    )

    issue_fallback = issues.drop_duplicates(subset=["key_only"], keep="last").set_index("key_only")

    merged = merged.copy()
    merged["_initial_skill"], merged["_initial_skill_confidence"] = zip(*merged.apply(_infer_skill_from_text, axis=1))
    assignee_skill_map = _derive_assignee_skill_map(merged)
    score_profile = _build_score_profile(merged)

    rows: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        if not _to_text(row.get("key")):
            fallback = issue_fallback.loc[_to_text(row.get("issueKey"))] if _to_text(row.get("issueKey")) in issue_fallback.index else None
            if fallback is not None:
                for col, value in fallback.items():
                    if col not in row.index or not _to_text(row.get(col)):
                        row[col] = value

        sprint_row = sprints[sprints["sprintId"] == _to_text(row.get("sprintId"))]
        sprint_data = sprint_row.iloc[0] if not sprint_row.empty else pd.Series(dtype=object)

        status = _to_text(row.get("status"))
        priority_id = _priority_id(row)
        story_points = _pick_story_points(row)
        required_skill = _final_skill(row, assignee_skill_map)
        rows.append(
            {
                "story_id": _to_text(row.get("issueKey")) or _to_text(row.get("key")),
                "title": _to_text(row.get("summary")),
                "description": _to_text(row.get("description")),
                "story_points": story_points,
                "business_value": _business_value(row, priority_id, story_points, score_profile),
                "risk_score": _risk_score(row, priority_id, story_points, score_profile),
                "required_skill": required_skill,
                "sprint_id": _to_text(row.get("sprintId")),
                "sprint_completed": _sprint_completed(status),
                "depends_on": "",
                "status": status,
                "source_bundle": source_bundle,
                "issue_type": _to_text(row.get("issueType")),
                "priority_id": priority_id,
                "assignee": _to_text(row.get("assignee")),
                "sprint_name": _to_text(sprint_data.get("sprintName")),
                "sprint_start_date": _to_text(sprint_data.get("sprintStartDate")),
                "sprint_end_date": _to_text(sprint_data.get("sprintEndDate")),
                "sprint_complete_date": _to_text(sprint_data.get("sprintCompleteDate")),
                "sprint_length": _to_int(sprint_data.get("SprintLength"), 0),
                "team_size": _to_int(sprint_data.get("NoOfDevelopers"), 0),
                "completed_velocity": _to_int(sprint_data.get("completedIssuesEstimateSum"), 0),
                "added_mid_sprint": _to_int(sprint_data.get("issueKeysAddedDuringSprint"), 0),
                "issue_links_count": _to_int(row.get("issueLinks"), 0),
                "blocked_by_count": _to_int(row.get("blockedBy"), 0),
                "blocks_count": _to_int(row.get("blocks"), 0),
                "watch_count": _to_int(row.get("watchcount"), 0),
                "comment_count": _to_int(row.get("commentCount"), 0),
                "votes": _to_int(row.get("votes"), 0),
            }
        )

    output = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    output = output[output["story_id"].astype(str).str.len() > 0]
    output = output.drop_duplicates(subset=["story_id", "sprint_id", "status"], keep="last")
    output = output.sort_values(by=["sprint_id", "story_id", "status"], kind="stable")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    return len(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a clean Apex-ready CSV from a scrum bundle.")
    parser.add_argument("--issues", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--sprints", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-bundle", type=str, required=True)
    args = parser.parse_args()

    rows = build_dataset(
        issues_path=args.issues,
        summary_path=args.summary,
        sprints_path=args.sprints,
        output_path=args.output,
        source_bundle=args.source_bundle,
    )
    print(f"Built {rows} rows -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
