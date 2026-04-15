from __future__ import annotations

import argparse
import csv
import sys
import re
from collections import defaultdict
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

PRIORITY_VALUE_MAP = {
    "blocker": 1.25,
    "critical": 1.15,
    "highest": 1.10,
    "high": 0.75,
    "major": 0.60,
    "medium": 0.15,
    "normal": 0.10,
    "minor": -0.25,
    "low": -0.45,
    "trivial": -0.80,
    "lowest": -0.90,
}

PRIORITY_RISK_MAP = {
    "critical": 0.90,
    "highest": 0.85,
    "high": 0.70,
    "medium": 0.45,
    "normal": 0.45,
    "low": 0.20,
    "lowest": 0.10,
}

SKILL_RULES = {
    "Frontend": (
        " ui ",
        "admin ui",
        "browser",
        "page",
        "screen",
        "layout",
        "html",
        "css",
        "javascript",
        "react",
        "angular",
        "vue",
        "flo",
        "logout",
        "login page",
    ),
    "Database": (
        "database",
        "jdbc",
        "sql",
        "rdbms",
        "schema",
        "query",
        "metadata",
        "repository",
        "index",
        "hdfs",
        "hive",
        "oracle",
        "mysql",
        "postgres",
        "db ",
    ),
    "Testing": (
        "test",
        "tests",
        "testing",
        "integration test",
        "unit test",
        "acceptance test",
        "flaky",
        "qa",
        "coverage",
        "benchmark",
        "assert",
    ),
    "DevOps": (
        "deploy",
        "deployment",
        "docker",
        "kubernetes",
        "k8s",
        "mesos",
        "yarn",
        "ambari",
        "build",
        "release",
        "upgrade",
        "bump",
        "artifact",
        "cluster",
        "container",
        "containers",
        "pipeline",
        "infra",
        "cf ",
        "lattice",
    ),
    "Backend": (
        "backend",
        "api",
        "service",
        "server",
        "stream",
        "job",
        "batch",
        "module",
        "rabbit",
        "kafka",
        "zookeeper",
        "auth",
        "ldap",
        "security",
        "integration",
        "converter",
        "serializer",
        "message",
        "endpoint",
        "shell",
        "command",
    ),
}

ISSUE_TYPE_VALUE_MAP = {
    "bug": 0.35,
    "defect": 0.35,
    "incident": 0.45,
    "story": 0.40,
    "new feature": 0.45,
    "feature": 0.40,
    "improvement": 0.15,
    "task": 0.00,
    "technical task": -0.10,
    "documentation": -0.60,
    "doc": -0.60,
    "sub task": -0.45,
    "subtask": -0.45,
    "epic": -0.55,
    "test": -0.15,
    "spike": 0.10,
}

DOC_KEYWORDS = (
    "docs",
    "doc",
    "doc ",
    "documentation",
    "javadoc",
    "readme",
    "guide",
    "tutorial",
    "example",
    "typo",
    "spelling",
    "grammar",
)

MAINTENANCE_KEYWORDS = (
    "cleanup",
    "clean up",
    "refactor",
    "rename",
    "remove unused",
    "deprecated",
    "deprecation",
    "housekeeping",
    "minor",
    "maintenance",
)

CUSTOMER_FACING_KEYWORDS = (
    "user",
    "customer",
    "client",
    "ui",
    "login",
    "auth",
    "permission",
    "security",
    "api",
    "rest",
    "web",
    "mobile",
    "browser",
    "dashboard",
)

RELEASE_FIELD_NAMES = {
    "fix version",
    "fix version/s",
    "version",
    "versions",
    "target version",
    "target version/s",
    "affected version",
    "affected version/s",
    "release",
}


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def detect_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except Exception:
        return ","


def read_rows(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(min(sys.maxsize, 2147483647))
    delimiter = detect_delimiter(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return [{(key or "").strip(): (value or "").strip() for key, value in row.items()} for row in reader]


def first_non_empty(row: dict[str, str], candidates: Sequence[str]) -> str:
    normalized = {normalize_name(key): value for key, value in row.items()}
    for candidate in candidates:
        candidate_norm = normalize_name(candidate)
        for key, value in normalized.items():
            if key == candidate_norm and value:
                return value.strip()
    return ""


def parse_int(value: str, default: int = 0) -> int:
    match = re.search(r"-?\d+", str(value or ""))
    return int(match.group()) if match else default


def parse_float(value: str, default: float = 0.0) -> float:
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or "").replace(",", "."))
    return float(match.group()) if match else default


def parse_bool(value: str | None) -> int:
    text = (value or "").strip().lower()
    return int(text in {"1", "true", "yes", "y", "done", "closed", "complete", "completed", "resolved"})


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def count_occurrences(text: str, keywords: Sequence[str]) -> int:
    haystack = f" {normalize_name(text)} "
    return sum(1 for keyword in keywords if keyword in haystack)


def count_rows_by_issue(path: Path | None) -> dict[str, int]:
    if path is None or not path.exists():
        return {}

    counts: dict[str, int] = defaultdict(int)
    delimiter = detect_delimiter(path)
    csv.field_size_limit(min(sys.maxsize, 2147483647))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            normalized = {(key or "").strip(): (value or "").strip() for key, value in row.items()}
            issue_id = first_non_empty(normalized, ["Issue_ID", "Issue ID"])
            if issue_id:
                counts[issue_id] += 1
    return dict(counts)


def collect_release_linked_issues(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()

    linked: set[str] = set()
    delimiter = detect_delimiter(path)
    csv.field_size_limit(min(sys.maxsize, 2147483647))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            normalized = {(key or "").strip(): (value or "").strip() for key, value in row.items()}
            issue_id = first_non_empty(normalized, ["Issue_ID", "Issue ID"])
            if not issue_id:
                continue

            field_name = normalize_name(first_non_empty(normalized, ["Field_Name", "Field Name"]))
            if field_name in RELEASE_FIELD_NAMES:
                linked.add(issue_id)
                continue

            previous_value = normalize_name(first_non_empty(normalized, ["Previous_Value_String", "Previous Value String"]))
            new_value = normalize_name(first_non_empty(normalized, ["New_Value_String", "New Value String"]))
            if "release" in previous_value or "release" in new_value:
                linked.add(issue_id)
    return linked


def count_reopen_events(path: Path | None) -> dict[str, int]:
    if path is None or not path.exists():
        return {}

    counts: dict[str, int] = defaultdict(int)
    delimiter = detect_delimiter(path)
    csv.field_size_limit(min(sys.maxsize, 2147483647))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            normalized = {(key or "").strip(): (value or "").strip() for key, value in row.items()}
            issue_id = first_non_empty(normalized, ["Issue_ID", "Issue ID"])
            if not issue_id:
                continue

            field_name = normalize_name(first_non_empty(normalized, ["Field_Name", "Field Name"]))
            previous_value = normalize_name(first_non_empty(normalized, ["Previous_Value_String", "Previous Value String"]))
            new_value = normalize_name(first_non_empty(normalized, ["New_Value_String", "New Value String"]))

            if field_name == "status" and ("reopen" in previous_value or "reopen" in new_value):
                counts[issue_id] += 1
            elif field_name == "status" and previous_value in {"resolved", "closed", "done"} and new_value in {"open", "in progress", "accepted"}:
                counts[issue_id] += 1
            elif field_name == "resolution" and previous_value and not new_value:
                counts[issue_id] += 1
    return dict(counts)


def derive_story_points(row: dict[str, str]) -> int:
    explicit = first_non_empty(row, ["Story_Point", "Story Point", "story_points"])
    if explicit:
        raw_points = max(parse_int(explicit, 0), 0)
        if raw_points <= 1:
            return 1
        if raw_points <= 2:
            return 2
        if raw_points <= 3:
            return 3
        if raw_points <= 5:
            return 5
        if raw_points <= 8:
            return 8
        return 13

    minutes = parse_float(first_non_empty(row, ["Resolution_Time_Minutes", "In_Progress_Time", "Total_Effort_Time"]), 0.0)
    if minutes <= 60:
        return 1
    if minutes <= 180:
        return 2
    if minutes <= 360:
        return 3
    if minutes <= 720:
        return 5
    if minutes <= 1440:
        return 8
    return 13


def normalize_status(raw_status: str, raw_resolution: str) -> str:
    text = f"{raw_status} {raw_resolution}".strip().lower()
    if any(token in text for token in ["done", "closed", "resolved", "complete", "fixed", "accepted", "shipped"]):
        return "done"
    if any(token in text for token in ["blocked", "waiting", "on hold"]):
        return "blocked"
    if any(token in text for token in ["in progress", "review", "implementing", "investigating", "working"]):
        return "in_progress"
    return "backlog"


def derive_business_value(
    row: dict[str, str],
    status: str,
    story_points: int,
    dependency_count: int = 0,
    comment_count: int = 0,
    change_count: int = 0,
    release_linked: bool = False,
) -> float:
    priority = normalize_name(first_non_empty(row, ["Priority", "Issue Priority"]))
    issue_type = normalize_name(first_non_empty(row, ["Type", "Issue Type"]))
    resolution = normalize_name(first_non_empty(row, ["Resolution"]))
    title = first_non_empty(row, ["Title", "Summary"])
    description = first_non_empty(row, ["Description_Text", "Description"])
    text = normalize_name(f"{title} {description}")

    value = 5.05
    value += PRIORITY_VALUE_MAP.get(priority, 0.05)
    value += ISSUE_TYPE_VALUE_MAP.get(issue_type, 0.0)

    if resolution == "duplicate" or "duplicate" in text or "duplicated" in text:
        value -= 0.85

    if any(keyword in text for keyword in DOC_KEYWORDS):
        value -= 0.65

    if any(keyword in text for keyword in MAINTENANCE_KEYWORDS):
        value -= 0.35

    if priority in {"low", "lowest", "trivial", "minor"} and issue_type in {"task", "technical task", "improvement"}:
        value -= 0.25

    if issue_type in {"bug", "defect", "incident", "story", "feature", "new feature"} and any(
        keyword in text for keyword in CUSTOMER_FACING_KEYWORDS
    ):
        value += 0.30

    if release_linked:
        value += 0.45

    if first_non_empty(row, ["Pull_Request_URL", "Pull Request URL"]):
        value += 0.15

    if dependency_count >= 2:
        value += 0.15
    elif dependency_count == 1:
        value += 0.08

    engagement_bonus = 0.0
    if comment_count >= 8:
        engagement_bonus += 0.25
    elif comment_count >= 4:
        engagement_bonus += 0.15
    elif comment_count >= 2:
        engagement_bonus += 0.08

    if change_count >= 12:
        engagement_bonus += 0.25
    elif change_count >= 6:
        engagement_bonus += 0.15
    elif change_count >= 3:
        engagement_bonus += 0.08
    value += min(engagement_bonus, 0.45)

    if priority in {"blocker", "critical", "highest"}:
        value += 0.25

    if status == "blocked":
        value += 0.20

    if 5 <= story_points <= 13 and issue_type in {"story", "feature", "new feature", "bug", "defect"}:
        value += 0.10

    return round(clamp(value, 3.0, 8.5), 2)


def derive_risk_score(
    row: dict[str, str],
    status: str,
    dependency_count: int = 0,
    comment_count: int = 0,
    change_count: int = 0,
    reopen_count: int = 0,
) -> float:
    priority = normalize_name(first_non_empty(row, ["Priority", "Issue Priority"]))
    issue_type = normalize_name(first_non_empty(row, ["Type", "Issue Type"]))
    resolution = normalize_name(first_non_empty(row, ["Resolution"]))
    minutes = parse_float(first_non_empty(row, ["Resolution_Time_Minutes", "In_Progress_Time", "Total_Effort_Time"]), 0.0)
    title = first_non_empty(row, ["Title", "Summary"])
    description = first_non_empty(row, ["Description_Text", "Description"])
    text = normalize_name(f"{title} {description}")

    risk = {
        "blocker": 0.55,
        "critical": 0.52,
        "highest": 0.50,
        "high": 0.42,
        "major": 0.40,
        "medium": 0.31,
        "normal": 0.30,
        "minor": 0.24,
        "low": 0.20,
        "trivial": 0.16,
        "lowest": 0.14,
    }.get(priority, 0.28)

    if issue_type in {"bug", "defect", "incident", "spike"}:
        risk += 0.08
    elif issue_type in {"story", "feature", "new feature"}:
        risk += 0.03
    elif issue_type in {"documentation", "doc"}:
        risk -= 0.10

    if minutes >= 10080:
        risk += 0.16
    elif minutes >= 2880:
        risk += 0.10
    elif minutes >= 1440:
        risk += 0.07
    elif minutes >= 480:
        risk += 0.04
    elif minutes >= 120:
        risk += 0.02

    if parse_bool(first_non_empty(row, ["Story_Point_Changed_After_Estimation"])):
        risk += 0.12
    if parse_bool(first_non_empty(row, ["Title_Changed_After_Estimation"])):
        risk += 0.05
    if parse_bool(first_non_empty(row, ["Description_Changed_After_Estimation"])):
        risk += 0.05

    risk += min(dependency_count * 0.04, 0.12)

    if comment_count >= 8:
        risk += 0.06
    elif comment_count >= 4:
        risk += 0.04
    elif comment_count >= 2:
        risk += 0.02

    if change_count >= 15:
        risk += 0.12
    elif change_count >= 8:
        risk += 0.08
    elif change_count >= 4:
        risk += 0.04

    if reopen_count:
        risk += min(0.10 + (reopen_count - 1) * 0.03, 0.16)

    if resolution == "duplicate" or "duplicate" in text:
        risk -= 0.12
    if any(keyword in text for keyword in DOC_KEYWORDS):
        risk -= 0.05
    if any(keyword in text for keyword in MAINTENANCE_KEYWORDS):
        risk -= 0.04

    if status == "done":
        risk -= 0.08
    elif status == "blocked":
        risk += 0.08
    elif status == "in_progress":
        risk += 0.03

    return round(clamp(risk, 0.12, 0.88), 2)


def infer_skill(row: dict[str, str]) -> str:
    explicit = first_non_empty(row, ["Component", "Components", "Component_Name", "component", "components"])
    title = first_non_empty(row, ["Title", "Summary"])
    description = first_non_empty(row, ["Description_Text", "Description"])

    title_scores: dict[str, int] = {}
    body_scores: dict[str, int] = {}
    for skill, keywords in SKILL_RULES.items():
        title_scores[skill] = count_occurrences(title, keywords)
        body_scores[skill] = count_occurrences(f"{explicit} {description}", keywords)

    weighted_scores = {
        skill: title_scores[skill] * 3 + body_scores[skill]
        for skill in SKILL_RULES
    }

    # Frontend should require clear UI-facing evidence, not a single incidental mention.
    if weighted_scores["Frontend"] <= 2:
        weighted_scores["Frontend"] = 0

    # Testing should be driven by explicit testing vocabulary.
    if title_scores["Testing"] == 0 and body_scores["Testing"] <= 1:
        weighted_scores["Testing"] = 0

    if title_scores["DevOps"] > 0:
        weighted_scores["DevOps"] += 1
    if title_scores["Backend"] > 0:
        weighted_scores["Backend"] += 1

    best_skill = max(weighted_scores, key=weighted_scores.get)
    if weighted_scores[best_skill] <= 0:
        return "Backend"

    if best_skill in {"DevOps", "Backend"} and weighted_scores["Backend"] >= weighted_scores["DevOps"] and "deploy" not in normalize_name(title):
        return "Backend"

    return best_skill


def derive_story_id(row: dict[str, str], index: int) -> str:
    key = first_non_empty(row, ["Key", "Issue Key", "Issue_Key", "story_id"])
    if key:
        return key
    issue_id = first_non_empty(row, ["ID", "Issue_ID", "Issue ID"])
    if issue_id:
        return f"TAWOS-{issue_id}"
    return f"TAWOS-{index:06d}"


def derive_sprint_id(row: dict[str, str], story_id: str, default_sprint_id: str) -> str:
    explicit = first_non_empty(row, ["Sprint_ID", "Sprint ID", "Sprint"])
    if explicit:
        return explicit

    project_key = story_id.split("-", 1)[0] if "-" in story_id else "TAWOS"
    creation_date = first_non_empty(row, ["Creation_Date", "Creation Date"])
    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", creation_date)
    year = year_match.group(1) if year_match else "UNK"
    return f"{default_sprint_id}-{project_key}-{year}"


def should_include_issue(issue_type: str) -> bool:
    normalized = normalize_name(issue_type)
    return normalized not in {"epic", "sub task", "subtask"}


def resolve_dependencies(
    links_rows: list[dict[str, str]] | None,
    id_to_story_id: dict[str, str],
) -> dict[str, str]:
    if not links_rows:
        return {}

    dependencies: dict[str, set[str]] = defaultdict(set)

    for row in links_rows:
        source_id = first_non_empty(row, ["Issue_ID", "Issue ID", "Source_Issue_ID", "Source Issue ID"])
        target_id = first_non_empty(row, ["Target_Issue_ID", "Target Issue ID", "Linked_Issue_ID", "Linked Issue ID"])
        source_story = id_to_story_id.get(source_id)
        target_story = id_to_story_id.get(target_id)
        if not source_story or not target_story or source_story == target_story:
            continue

        link_name = first_non_empty(row, ["Name", "Link_Name", "Issue_Link_Type"]).lower()
        link_desc = first_non_empty(row, ["Description", "Link_Description", "Relation"]).lower()
        direction = first_non_empty(row, ["Direction"]).lower()

        if "blocked by" in link_desc or "depends on" in link_desc or "requires" in link_desc or "parent" in link_desc:
            dependencies[source_story].add(target_story)
        elif "blocks" in link_desc or "is depended on by" in link_desc or "is required by" in link_desc:
            dependencies[target_story].add(source_story)
        elif "depend" in link_name:
            if direction == "outbound":
                dependencies[source_story].add(target_story)
            elif direction == "inbound":
                dependencies[target_story].add(source_story)

    return {story_id: "|".join(sorted(values)) for story_id, values in dependencies.items()}


def convert_tawos_export(
    input_path: Path,
    output_path: Path,
    links_path: Path | None = None,
    comments_path: Path | None = None,
    change_log_path: Path | None = None,
    project_id: str | None = None,
    project_key: str | None = None,
    default_sprint_id: str = "SPR-TAWOS",
) -> int:
    rows = read_rows(input_path)
    if not rows:
        raise ValueError("Input file is empty or could not be parsed.")

    filtered: list[dict[str, str]] = []
    for row in rows:
        if project_id and first_non_empty(row, ["Project_ID", "Project ID"]) != project_id:
            continue

        story_id = derive_story_id(row, len(filtered) + 1)
        if project_key and not story_id.startswith(project_key):
            continue

        issue_type = first_non_empty(row, ["Type", "Issue Type"])
        if not should_include_issue(issue_type):
            continue

        enriched = dict(row)
        enriched["_story_id"] = story_id
        filtered.append(enriched)

    if not filtered:
        raise ValueError("No issues matched the selected TAWOS filters.")

    id_to_story_id = {
        first_non_empty(row, ["ID", "Issue_ID", "Issue ID"]): row["_story_id"]
        for row in filtered
        if first_non_empty(row, ["ID", "Issue_ID", "Issue ID"])
    }
    link_rows = read_rows(links_path) if links_path else None
    dependency_map = resolve_dependencies(link_rows, id_to_story_id)
    comment_count_by_issue = count_rows_by_issue(comments_path)
    change_count_by_issue = count_rows_by_issue(change_log_path)
    release_linked_issues = collect_release_linked_issues(change_log_path)
    reopen_count_by_issue = count_reopen_events(change_log_path)

    converted: list[dict[str, str]] = []
    for index, row in enumerate(filtered, start=1):
        story_id = row["_story_id"] or derive_story_id(row, index)
        issue_id = first_non_empty(row, ["ID", "Issue_ID", "Issue ID"])
        status = normalize_status(
            first_non_empty(row, ["Status"]),
            first_non_empty(row, ["Resolution"]),
        )
        story_points = derive_story_points(row)
        sprint_id = derive_sprint_id(row, story_id, default_sprint_id)
        depends_on = dependency_map.get(story_id, "")
        dependency_count = 0 if not depends_on else depends_on.count("|") + 1

        converted.append(
            {
                "story_id": story_id,
                "title": first_non_empty(row, ["Title", "Summary"]) or "Untitled Story",
                "description": first_non_empty(row, ["Description_Text", "Description"])[:2000],
                "story_points": str(story_points),
                "business_value": (
                    f"{derive_business_value(
                        row,
                        status,
                        story_points,
                        dependency_count=dependency_count,
                        comment_count=comment_count_by_issue.get(issue_id, 0),
                        change_count=change_count_by_issue.get(issue_id, 0),
                        release_linked=issue_id in release_linked_issues,
                    ):.2f}"
                ),
                "risk_score": (
                    f"{derive_risk_score(
                        row,
                        status,
                        dependency_count=dependency_count,
                        comment_count=comment_count_by_issue.get(issue_id, 0),
                        change_count=change_count_by_issue.get(issue_id, 0),
                        reopen_count=reopen_count_by_issue.get(issue_id, 0),
                    ):.2f}"
                ),
                "required_skill": infer_skill(row),
                "sprint_id": sprint_id,
                "sprint_completed": str(int(status == "done")),
                "depends_on": depends_on,
                "status": status,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(converted)

    return len(converted)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert a TAWOS issue export into ApexS upload format.")
    parser.add_argument("input", type=Path, help="CSV export of TAWOS Issue records.")
    parser.add_argument("output", type=Path, help="Output CSV path in ApexS upload format.")
    parser.add_argument("--links", type=Path, default=None, help="Optional CSV export of TAWOS Issue_Link records.")
    parser.add_argument("--comments", type=Path, default=None, help="Optional CSV export of TAWOS Comment records.")
    parser.add_argument("--change-log", type=Path, default=None, help="Optional CSV export of TAWOS Change_Log records.")
    parser.add_argument("--project-id", type=str, default=None, help="Optional TAWOS Project_ID filter.")
    parser.add_argument("--project-key", type=str, default=None, help="Optional issue key prefix filter, e.g. MESOS.")
    parser.add_argument("--default-sprint-id", type=str, default="SPR-TAWOS", help="Fallback sprint id if Sprint_ID is missing.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    count = convert_tawos_export(
        input_path=args.input,
        output_path=args.output,
        links_path=args.links,
        comments_path=args.comments,
        change_log_path=args.change_log,
        project_id=args.project_id,
        project_key=args.project_key,
        default_sprint_id=args.default_sprint_id,
    )
    print(f"Converted {count} TAWOS issues -> {args.output}")


if __name__ == "__main__":
    main()
