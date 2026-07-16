from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Iterable, Sequence


REQUIRED_OUTPUT_COLUMNS = [
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

SKILL_KEYWORDS = ["backend", "frontend", "database", "testing", "devops", "qa", "mobile", "api"]

PRIORITY_VALUE_MAP = {
    "critical": 10,
    "highest": 10,
    "high": 8,
    "medium": 6,
    "normal": 6,
    "low": 3,
    "lowest": 2,
}

PRIORITY_RISK_MAP = {
    "critical": 0.9,
    "highest": 0.85,
    "high": 0.7,
    "medium": 0.45,
    "normal": 0.45,
    "low": 0.2,
    "lowest": 0.1,
}


def detect_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except Exception:
        return ","


def read_rows(path: Path, delimiter: str | None) -> list[dict[str, str]]:
    actual_delimiter = delimiter or detect_delimiter(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=actual_delimiter)
        return [{(key or "").strip(): (value or "").strip() for key, value in row.items()} for row in reader]


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def first_non_empty(row: dict[str, str], candidates: Sequence[str]) -> str:
    normalized = {normalize_name(key): value for key, value in row.items()}
    for candidate in candidates:
        candidate_norm = normalize_name(candidate)
        for key, value in normalized.items():
            if key == candidate_norm and value:
                return value.strip()
    return ""


def find_value_by_keywords(row: dict[str, str], keywords: Iterable[str]) -> str:
    text = " | ".join(value for value in row.values() if value).lower()
    for keyword in keywords:
        if keyword in text:
            return keyword.title() if keyword != "qa" else "Testing"
    return ""


def parse_int(value: str, default: int = 0) -> int:
    if not value:
        return default
    match = re.search(r"-?\d+", str(value))
    return int(match.group()) if match else default


def parse_float(value: str, default: float = 0.0) -> float:
    if not value:
        return default
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", "."))
    return float(match.group()) if match else default


def parse_bool(value: str | None) -> int:
    if not value:
        return 0
    normalized = value.strip().lower()
    return int(normalized in {"1", "true", "yes", "y", "done", "closed", "complete", "completed", "resolved"})


def split_multi(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[;,|/]+", value)
    cleaned = [part.strip() for part in parts if part.strip()]
    return cleaned


def infer_priority_score(row: dict[str, str]) -> tuple[float, float]:
    raw_priority = first_non_empty(row, ["priority", "issue priority", "severity"])
    normalized = normalize_name(raw_priority)
    if normalized in PRIORITY_VALUE_MAP:
        return float(PRIORITY_VALUE_MAP[normalized]), float(PRIORITY_RISK_MAP[normalized])

    issue_type = normalize_name(first_non_empty(row, ["issue type", "type", "task type"]))
    if issue_type in {"bug", "defect", "incident"}:
        return 7.0, 0.8
    if issue_type in {"epic", "feature"}:
        return 8.0, 0.5
    if issue_type in {"spike", "research"}:
        return 5.0, 0.6

    return 6.0, 0.4


def infer_skill(row: dict[str, str]) -> str:
    explicit = first_non_empty(row, ["required_skill", "skill", "component", "team", "assignee"])
    if explicit:
        for skill in ["Backend", "Frontend", "Database", "Testing", "DevOps"]:
            if skill.lower() in explicit.lower():
                return skill
        return explicit

    keyword_skill = find_value_by_keywords(row, SKILL_KEYWORDS)
    if keyword_skill:
        if keyword_skill.lower() == "Qa":
            return "Testing"
        return keyword_skill
    return ""


def infer_completed(row: dict[str, str]) -> int:
    candidates = [
        first_non_empty(row, ["sprint_completed", "completed", "done", "is_done"]),
        first_non_empty(row, ["status", "resolution"]),
    ]
    for candidate in candidates:
        if candidate:
            return parse_bool(candidate)
    status = normalize_name(first_non_empty(row, ["status", "resolution"]))
    return int(status in {"done", "closed", "resolved", "complete", "completed", "shipped"})


def infer_dependencies(row: dict[str, str]) -> str:
    raw = first_non_empty(row, ["depends_on", "dependencies", "blocks", "blocked by", "parent", "epic link", "linked issues"])
    deps = split_multi(raw)
    return "|".join(deps)


def infer_story_id(row: dict[str, str], index: int) -> str:
    existing = first_non_empty(row, ["story_id", "id", "issue key", "issue_key", "key", "ticket", "ticket_id"])
    if existing:
        return existing
    return f"ST-{index:05d}"


def infer_title(row: dict[str, str]) -> str:
    title = first_non_empty(row, ["title", "summary", "name", "issue summary", "subject"])
    if title:
        return title
    description = first_non_empty(row, ["description", "details", "story"])
    return description[:120] if description else "Untitled Story"


def infer_description(row: dict[str, str]) -> str:
    return first_non_empty(row, ["description", "details", "story", "notes", "comments"])


def infer_story_points(row: dict[str, str]) -> int:
    value = first_non_empty(row, ["story_points", "story points", "points", "estimate", "estimation", "effort"])
    if value:
        return max(parse_int(value, 0), 0)
    raw = first_non_empty(row, ["size", "complexity"])
    if raw:
        return max(parse_int(raw, 0), 0)
    return 1


def infer_business_value(row: dict[str, str]) -> float:
    value = first_non_empty(row, ["business_value", "business value", "value", "priority value", "impact"])
    if value:
        return max(parse_float(value, 0.0), 0.0)
    priority_value, _ = infer_priority_score(row)
    return priority_value


def infer_risk_score(row: dict[str, str]) -> float:
    value = first_non_empty(row, ["risk_score", "risk score", "risk", "severity", "complexity"])
    if value:
        parsed = parse_float(value, 0.0)
        if parsed > 1:
            return min(parsed / 10.0, 1.0)
        return min(max(parsed, 0.0), 1.0)
    _, risk = infer_priority_score(row)
    return risk


def infer_sprint_id(row: dict[str, str], default_sprint_id: str, index: int) -> str:
    value = first_non_empty(row, ["sprint_id", "sprint id", "sprint", "iteration", "iteration id"])
    if value:
        return value
    return default_sprint_id or f"SPRINT-{index:03d}"


def row_to_platform_schema(row: dict[str, str], index: int, default_sprint_id: str) -> dict[str, str]:
    business_value = infer_business_value(row)
    risk_score = infer_risk_score(row)
    required_skill = infer_skill(row)
    story_points = infer_story_points(row)
    return {
        "story_id": infer_story_id(row, index),
        "title": infer_title(row),
        "description": infer_description(row),
        "story_points": str(story_points),
        "business_value": f"{business_value:.2f}",
        "risk_score": f"{min(max(risk_score, 0.0), 1.0):.2f}",
        "required_skill": required_skill,
        "sprint_id": infer_sprint_id(row, default_sprint_id, index),
        "sprint_completed": str(infer_completed(row)),
        "depends_on": infer_dependencies(row),
        "status": first_non_empty(row, ["status", "state", "resolution"]) or "backlog",
    }


def convert(input_path: Path, output_path: Path, delimiter: str | None, default_sprint_id: str) -> int:
    rows = read_rows(input_path, delimiter)
    if not rows:
        raise ValueError("Input file is empty or could not be parsed.")

    converted = [row_to_platform_schema(row, index + 1, default_sprint_id) for index, row in enumerate(rows)]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(converted)

    return len(converted)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Jira/Kaggle sprint exports into Apex Sprint Planner CSV format.",
    )
    parser.add_argument("input", type=Path, help="Input CSV export from Jira or Kaggle.")
    parser.add_argument("output", type=Path, help="Output CSV path for the Apex upload format.")
    parser.add_argument(
        "--delimiter",
        default=None,
        help="Input delimiter. Defaults to auto-detect among comma, semicolon, tab, and pipe.",
    )
    parser.add_argument(
        "--default-sprint-id",
        default="SPRINT-001",
        help="Fallback sprint id when the source file does not include one.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    count = convert(args.input, args.output, args.delimiter, args.default_sprint_id)
    print(f"Converted {count} rows -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())