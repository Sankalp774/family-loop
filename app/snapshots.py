from __future__ import annotations

import re
from typing import Any

from app.policy import approved_app_names, norm


_SKIP = {
    "screen time",
    "digital wellbeing",
    "today",
    "this week",
    "last 7 days",
    "show more",
    "see all",
    "notifications",
    "pickups",
    "first used",
}

_DURATION = re.compile(
    r"^(?:(\d+)\s*(?:h|hr|hrs|hour|hours))?\s*"
    r"(?:(\d+)\s*(?:m|min|mins|minute|minutes))?\s*$",
    re.I,
)
_INLINE = re.compile(
    r"(.+?)\s+"
    r"(?:(\d+)\s*(?:h|hr|hrs|hour|hours))?\s*"
    r"(?:(\d+)\s*(?:m|min|mins|minute|minutes)|(\d+))\s*$",
    re.I,
)


def parse_app_list(raw: str) -> list[dict[str, Any]]:
    """Accept pasted lists, CSV, or OCR from a Screen Time / Digital Wellbeing photo."""
    text = (raw or "").strip()
    if not text:
        return []
    apps: list[dict[str, Any]] = []
    pending_name = None
    for line in text.splitlines():
        line = line.strip().strip("-•●").strip()
        if not line or norm(line) in _SKIP:
            continue
        if "," in line and not re.search(r"\d", line.split(",")[0]):
            parts = [p.strip() for p in line.split(",")]
            apps.append({"name": parts[0], "minutes": _int(parts[1] if len(parts) > 1 else "0")})
            pending_name = None
            continue
        dur = _DURATION.match(line)
        if dur and (dur.group(1) or dur.group(2)) and pending_name:
            apps.append({"name": pending_name, "minutes": _hours_mins(dur.group(1), dur.group(2))})
            pending_name = None
            continue
        inline = _INLINE.match(line)
        if inline and (inline.group(2) or inline.group(3) or inline.group(4)):
            minutes = _hours_mins(inline.group(2), inline.group(3) or inline.group(4))
            apps.append({"name": inline.group(1).strip(), "minutes": minutes})
            pending_name = None
            continue
        pending_name = line
        apps.append({"name": line, "minutes": 0})
    return _dedupe(apps)


def _hours_mins(hours: str | None, minutes: str | None) -> int:
    return int(hours or 0) * 60 + int(minutes or 0)


def _dedupe(apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for app in apps:
        key = norm(app["name"])
        if not key:
            continue
        if key not in by_name or app["minutes"] > by_name[key]["minutes"]:
            by_name[key] = app
    return list(by_name.values())


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
