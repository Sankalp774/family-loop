from __future__ import annotations

import re
from typing import Any

from app.policy import approved_app_names, norm


def parse_app_list(raw: str) -> list[dict[str, Any]]:
    """Accept 'YouTube 45' lines, CSV, or a pasted iOS-style list."""
    text = (raw or "").strip()
    if not text:
        return []
    apps: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip().strip("-•").strip()
        if not line:
            continue
        if "," in line and not re.search(r"\d", line.split(",")[0]):
            # name,minutes
            parts = [p.strip() for p in line.split(",")]
            name = parts[0]
            minutes = _int(parts[1] if len(parts) > 1 else "0")
            apps.append({"name": name, "minutes": minutes})
            continue
        match = re.match(r"(.+?)\s+(\d+)\s*(m|min|mins|minutes)?\s*$", line, re.I)
        if match:
            apps.append({"name": match.group(1).strip(), "minutes": int(match.group(2))})
        else:
            apps.append({"name": line, "minutes": 0})
    return apps


def diff_new_unapproved(state: dict[str, Any], apps: list[dict[str, Any]]) -> list[str]:
    allowed = approved_app_names(state)
    new: list[str] = []
    seen: set[str] = set()
    for app in apps:
        name = app.get("name") or ""
        key = norm(name)
        if not key or key in seen:
            continue
        seen.add(key)
        if key not in allowed:
            new.append(name)
    return new


def total_minutes(apps: list[dict[str, Any]]) -> int:
    return sum(int(app.get("minutes") or 0) for app in apps)


def _int(value: str) -> int:
    digits = re.sub(r"[^\d]", "", value or "")
    return int(digits) if digits else 0
