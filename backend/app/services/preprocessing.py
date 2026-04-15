from __future__ import annotations

from typing import Any


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        # Handle pandas/numpy NaN values without importing pandas globally.
        return bool(value != value)
    except Exception:
        return False


def normalize_status(status: Any) -> str:
    if _is_missing(status):
        return ""
    return str(status).strip().lower()


def normalize_skill(skill: Any, available_skills: list[str] | None = None) -> str | None:
    if _is_missing(skill):
        return None
    normalized = str(skill).strip().lower()
    if not normalized:
        return None
    if not available_skills:
        return normalized
    normalized_available = {str(item).strip().lower() for item in available_skills if not _is_missing(item)}
    if normalized in normalized_available:
        return normalized
    return None


def normalize_skills(skills: list[str] | None) -> list[str]:
    if not skills:
        return []
    deduped: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        normalized = normalize_skill(skill)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def parse_depends_on(depends_on: Any) -> list[str]:
    if _is_missing(depends_on):
        return []

    if isinstance(depends_on, list):
        values = depends_on
    elif isinstance(depends_on, tuple):
        values = list(depends_on)
    else:
        raw = str(depends_on)
        if not raw.strip():
            return []
        # Parse common CSV-style and delimiter-separated dependency formats.
        for sep in [",", ";", "|"]:
            raw = raw.replace(sep, " ")
        values = raw.split()

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        if _is_missing(value):
            continue
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return cleaned
