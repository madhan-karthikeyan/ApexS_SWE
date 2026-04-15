from __future__ import annotations

import argparse
import csv
import importlib.util
import os
import re
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


WORKSPACE_DIR = Path(__file__).resolve().parent
REPO_ROOT = WORKSPACE_DIR.parent
DEFAULT_EXPORT_DIR = WORKSPACE_DIR / "exports"
DEFAULT_OUTPUT_PATH = WORKSPACE_DIR / "paper_datasets" / "tawos_apex_clean.csv"
DEFAULT_SQL_DUMP = WORKSPACE_DIR / "raw" / "TAWOS.sql"
VALID_PROJECT_KEY = re.compile(r"^[A-Z0-9_]+$")

PROJECT_COLUMNS = [
    "ID",
    "Project_Key",
    "Name",
    "URL",
    "Description",
    "Start_Date",
    "Last_Update_Date",
    "SP_Field_ID",
    "Repository_ID",
]

ISSUE_COLUMNS = [
    "ID",
    "Jira_ID",
    "Issue_Key",
    "URL",
    "Title",
    "Description",
    "Description_Text",
    "Description_Code",
    "Type",
    "Priority",
    "Status",
    "Resolution",
    "Creation_Date",
    "Estimation_Date",
    "Resolution_Date",
    "Last_Updated",
    "Story_Point",
    "Timespent",
    "In_Progress_Minutes",
    "Total_Effort_Minutes",
    "Resolution_Time_Minutes",
    "Title_Changed_After_Estimation",
    "Description_Changed_After_Estimation",
    "Story_Point_Changed_After_Estimation",
    "Pull_Request_URL",
    "Creator_ID",
    "Reporter_ID",
    "Assignee_ID",
    "Project_ID",
    "Sprint_ID",
]

ISSUE_LINK_COLUMNS = [
    "ID",
    "Issue_ID",
    "Name",
    "Description",
    "Direction",
    "Target_Issue_ID",
]

COMMENT_COLUMNS = [
    "ID",
    "Comment",
    "Comment_Text",
    "Comment_Code",
    "Creation_Date",
    "Author_ID",
    "Issue_ID",
]

CHANGE_LOG_COLUMNS = [
    "ID",
    "Field_Name",
    "Previous_Value_ID",
    "New_Value_ID",
    "Previous_Value_String",
    "New_Value_String",
    "ChangeType",
    "Creation_Date",
    "Author_ID",
    "Issue_ID",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export selected TAWOS projects and build one ApexS-ready CSV."
    )
    parser.add_argument(
        "--project-keys",
        nargs="+",
        default=["XD", "USERGRID", "MESOS"],
        help="Project keys to export from TAWOS, for example XD USERGRID MESOS.",
    )
    parser.add_argument(
        "--source",
        choices=["auto", "mysql", "sql-dump"],
        default="auto",
        help="Data source to use. 'auto' tries MySQL first and falls back to the SQL dump.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional SQLAlchemy URL. If omitted, the script reads tawos/.env.",
    )
    parser.add_argument(
        "--sql-dump",
        type=Path,
        default=DEFAULT_SQL_DUMP,
        help="Path to the downloaded TAWOS.sql dump.",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help="Directory for filtered raw CSV exports.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Final ApexS-ready CSV output path.",
    )
    parser.add_argument(
        "--default-sprint-id",
        default="SPR-TAWOS",
        help="Fallback sprint id when TAWOS sprint data is missing.",
    )
    parser.add_argument(
        "--include-supporting-tables",
        action="store_true",
        help="Also export filtered Comment and Change_Log tables.",
    )
    return parser.parse_args()


def load_environment() -> None:
    env_path = WORKSPACE_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def normalize_project_keys(project_keys: list[str]) -> list[str]:
    normalized: list[str] = []
    for key in project_keys:
        clean = (key or "").strip().upper()
        if not clean:
            continue
        if not VALID_PROJECT_KEY.fullmatch(clean):
            raise ValueError(f"Invalid project key: {key!r}")
        if clean not in normalized:
            normalized.append(clean)
    if not normalized:
        raise ValueError("At least one valid project key is required.")
    return normalized


def build_database_url(explicit_url: str | None) -> str:
    if explicit_url:
        return explicit_url

    host = os.getenv("TAWOS_DB_HOST", "127.0.0.1")
    port = os.getenv("TAWOS_DB_PORT", "3306")
    database = os.getenv("TAWOS_DB_NAME", "TAWOS_DB")
    user = os.getenv("TAWOS_DB_USER", "root")
    password = os.getenv("TAWOS_DB_PASSWORD", "")

    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{database}?charset=utf8mb4"
    )


def build_project_filter(project_keys: list[str]) -> tuple[str, dict[str, Any]]:
    placeholders: list[str] = []
    params: dict[str, Any] = {}
    for index, project_key in enumerate(project_keys):
        name = f"project_key_{index}"
        placeholders.append(f":{name}")
        params[name] = project_key
    return ", ".join(placeholders), params


def export_query(engine: Any, query: str, params: dict[str, Any], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with engine.connect() as connection:
        dataframe = pd.read_sql_query(text(query), connection, params=params)
    dataframe.to_csv(output_path, index=False)
    return len(dataframe.index)


def load_converter_module() -> Any:
    converter_path = REPO_ROOT / "scripts" / "convert_tawos_export.py"
    spec = importlib.util.spec_from_file_location("convert_tawos_export_module", converter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load converter module from {converter_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_queries(project_keys: list[str]) -> tuple[dict[str, str], dict[str, Any]]:
    placeholder_block, params = build_project_filter(project_keys)
    selected_projects_cte = (
        "WITH selected_projects AS ("
        f"SELECT ID FROM Project WHERE Project_Key IN ({placeholder_block})"
        ") "
    )

    queries = {
        "selected_projects.csv": (
            f"SELECT * FROM Project WHERE Project_Key IN ({placeholder_block}) ORDER BY Project_Key"
        ),
        "selected_issues.csv": (
            selected_projects_cte
            + "SELECT * FROM Issue "
            + "WHERE Project_ID IN (SELECT ID FROM selected_projects)"
        ),
        "selected_issue_links.csv": (
            selected_projects_cte
            + "SELECT * FROM Issue_Link "
            + "WHERE Issue_ID IN ("
            + "SELECT ID FROM Issue WHERE Project_ID IN (SELECT ID FROM selected_projects)"
            + ") OR Target_Issue_ID IN ("
            + "SELECT ID FROM Issue WHERE Project_ID IN (SELECT ID FROM selected_projects)"
            + ")"
        ),
        "selected_comments.csv": (
            selected_projects_cte
            + "SELECT * FROM Comment "
            + "WHERE Issue_ID IN ("
            + "SELECT ID FROM Issue WHERE Project_ID IN (SELECT ID FROM selected_projects)"
            + ")"
        ),
        "selected_change_log.csv": (
            selected_projects_cte
            + "SELECT * FROM Change_Log "
            + "WHERE Issue_ID IN ("
            + "SELECT ID FROM Issue WHERE Project_ID IN (SELECT ID FROM selected_projects)"
            + ")"
        ),
    }
    return queries, params


def write_csv(rows: Iterable[dict[str, Any]], fieldnames: list[str], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def unescape_mysql_string(value: str) -> str:
    result: list[str] = []
    index = 0
    mapping = {
        "0": "\0",
        "b": "\b",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "Z": "\x1a",
        "'": "'",
        '"': '"',
        "\\": "\\",
    }
    while index < len(value):
        char = value[index]
        if char != "\\" or index + 1 >= len(value):
            result.append(char)
            index += 1
            continue
        index += 1
        escaped = value[index]
        result.append(mapping.get(escaped, escaped))
        index += 1
    return "".join(result)


def parse_sql_token(token: str) -> Any:
    text = token.strip()
    if text == "NULL":
        return None
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return unescape_mysql_string(text[1:-1])
    return text


def iter_insert_rows(insert_values: str) -> Iterable[list[Any]]:
    index = 0
    length = len(insert_values)
    while index < length:
        while index < length and insert_values[index] != "(":
            index += 1
        if index >= length:
            return

        index += 1
        token_chars: list[str] = []
        row: list[Any] = []
        in_string = False
        escape = False

        while index < length:
            char = insert_values[index]
            if in_string:
                token_chars.append(char)
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == "'":
                    in_string = False
                index += 1
                continue

            if char == "'":
                in_string = True
                token_chars.append(char)
                index += 1
                continue

            if char == ",":
                row.append(parse_sql_token("".join(token_chars)))
                token_chars = []
                index += 1
                continue

            if char == ")":
                row.append(parse_sql_token("".join(token_chars)))
                yield row
                token_chars = []
                index += 1
                break

            token_chars.append(char)
            index += 1


def iter_table_rows(sql_dump: Path, table_name: str, columns: list[str]) -> Iterable[dict[str, Any]]:
    prefix = f"INSERT INTO `{table_name}` VALUES "
    with sql_dump.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        for line in handle:
            if not line.startswith(prefix):
                continue

            payload = line[len(prefix):].rstrip()
            if payload.endswith(";"):
                payload = payload[:-1]

            for values in iter_insert_rows(payload):
                if len(values) != len(columns):
                    raise ValueError(
                        f"Unexpected column count for {table_name}: expected {len(columns)}, got {len(values)}"
                    )
                yield {column: value for column, value in zip(columns, values)}


def export_from_sql_dump(
    sql_dump: Path,
    project_keys: list[str],
    export_dir: Path,
    include_supporting_tables: bool,
) -> dict[str, int]:
    if not sql_dump.exists():
        raise FileNotFoundError(f"SQL dump not found: {sql_dump}")

    project_key_set = set(project_keys)
    counts: dict[str, int] = {}

    selected_projects = [
        row
        for row in iter_table_rows(sql_dump, "Project", PROJECT_COLUMNS)
        if (row.get("Project_Key") or "").strip().upper() in project_key_set
    ]
    if not selected_projects:
        raise ValueError(f"No matching projects found in SQL dump for: {', '.join(project_keys)}")

    selected_project_ids = {str(row["ID"]) for row in selected_projects if row.get("ID") is not None}
    counts["selected_projects.csv"] = write_csv(selected_projects, PROJECT_COLUMNS, export_dir / "selected_projects.csv")

    selected_issues = [
        row
        for row in iter_table_rows(sql_dump, "Issue", ISSUE_COLUMNS)
        if str(row.get("Project_ID")) in selected_project_ids
    ]
    if not selected_issues:
        raise ValueError("No issues matched the selected TAWOS projects.")

    selected_issue_ids = {str(row["ID"]) for row in selected_issues if row.get("ID") is not None}
    counts["selected_issues.csv"] = write_csv(selected_issues, ISSUE_COLUMNS, export_dir / "selected_issues.csv")

    selected_issue_links = [
        row
        for row in iter_table_rows(sql_dump, "Issue_Link", ISSUE_LINK_COLUMNS)
        if str(row.get("Issue_ID")) in selected_issue_ids or str(row.get("Target_Issue_ID")) in selected_issue_ids
    ]
    counts["selected_issue_links.csv"] = write_csv(
        selected_issue_links,
        ISSUE_LINK_COLUMNS,
        export_dir / "selected_issue_links.csv",
    )

    if include_supporting_tables:
        selected_comments = [
            row
            for row in iter_table_rows(sql_dump, "Comment", COMMENT_COLUMNS)
            if str(row.get("Issue_ID")) in selected_issue_ids
        ]
        counts["selected_comments.csv"] = write_csv(
            selected_comments,
            COMMENT_COLUMNS,
            export_dir / "selected_comments.csv",
        )

        selected_change_log = [
            row
            for row in iter_table_rows(sql_dump, "Change_Log", CHANGE_LOG_COLUMNS)
            if str(row.get("Issue_ID")) in selected_issue_ids
        ]
        counts["selected_change_log.csv"] = write_csv(
            selected_change_log,
            CHANGE_LOG_COLUMNS,
            export_dir / "selected_change_log.csv",
        )

    return counts


def export_from_mysql(
    database_url: str,
    project_keys: list[str],
    export_dir: Path,
    include_supporting_tables: bool,
) -> dict[str, int]:
    engine = create_engine(database_url)
    queries, params = build_queries(project_keys)
    counts: dict[str, int] = {}

    always_export = [
        "selected_projects.csv",
        "selected_issues.csv",
        "selected_issue_links.csv",
    ]
    optional_export = [
        "selected_comments.csv",
        "selected_change_log.csv",
    ]

    for filename in always_export:
        counts[filename] = export_query(engine, queries[filename], params, export_dir / filename)

    if include_supporting_tables:
        for filename in optional_export:
            counts[filename] = export_query(engine, queries[filename], params, export_dir / filename)

    return counts


def print_export_counts(counts: dict[str, int], export_dir: Path) -> None:
    for filename, count in counts.items():
        print(f"Exported {count:,} rows -> {export_dir / filename}")


def main() -> None:
    args = parse_args()
    load_environment()

    project_keys = normalize_project_keys(args.project_keys)
    export_dir = args.export_dir

    print(f"Exporting TAWOS projects: {', '.join(project_keys)}")

    counts: dict[str, int]
    if args.source == "mysql":
        counts = export_from_mysql(
            database_url=build_database_url(args.database_url),
            project_keys=project_keys,
            export_dir=export_dir,
            include_supporting_tables=args.include_supporting_tables,
        )
    elif args.source == "sql-dump":
        counts = export_from_sql_dump(
            sql_dump=args.sql_dump,
            project_keys=project_keys,
            export_dir=export_dir,
            include_supporting_tables=args.include_supporting_tables,
        )
    else:
        try:
            counts = export_from_mysql(
                database_url=build_database_url(args.database_url),
                project_keys=project_keys,
                export_dir=export_dir,
                include_supporting_tables=args.include_supporting_tables,
            )
            print("Used MySQL source.")
        except Exception as exc:
            print(f"MySQL export unavailable ({exc}). Falling back to SQL dump.")
            counts = export_from_sql_dump(
                sql_dump=args.sql_dump,
                project_keys=project_keys,
                export_dir=export_dir,
                include_supporting_tables=args.include_supporting_tables,
            )
            print("Used SQL dump source.")

    print_export_counts(counts, export_dir)

    converter = load_converter_module()
    converted_count = converter.convert_tawos_export(
        input_path=export_dir / "selected_issues.csv",
        output_path=args.output,
        links_path=export_dir / "selected_issue_links.csv",
        comments_path=(export_dir / "selected_comments.csv") if (export_dir / "selected_comments.csv").exists() else None,
        change_log_path=(export_dir / "selected_change_log.csv") if (export_dir / "selected_change_log.csv").exists() else None,
        default_sprint_id=args.default_sprint_id,
    )

    print(f"Built {converted_count:,} ApexS rows -> {args.output}")


if __name__ == "__main__":
    main()
