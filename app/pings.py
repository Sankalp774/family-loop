from __future__ import annotations

from datetime import datetime
from typing import Any

from app.clock import is_school_hours, iso, now, week_start


def can_issue_ping(state: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    current = now()
    policy = state.get("policy") or {}
    pings = state.get("pings") or []
    today = [p for p in pings if _same_day(p, current)]
    this_week = [p for p in pings if _same_week(p, current)]

    if not force and is_school_hours(current, policy):
        return {
            "ok": False,
            "reason": "School hours. Family Loop will not ping during class. Try after 15:00, or use Simulate random ask (demo).",
        }
    if not force and len(today) >= 1:
        return {"ok": False, "reason": "Already pinged today (max 1/day)."}
    if not force and len(this_week) >= 3:
        return {"ok": False, "reason": "Already pinged three times this week (max 3/week)."}
    return {"ok": True, "reason": "Ping allowed."}


def open_ping(state: dict[str, Any]) -> dict[str, Any] | None:
    for ping in reversed(state.get("pings") or []):
        if ping.get("due") and not ping.get("submitted_at") and not ping.get("missed"):
            return ping
    return None


def _has_snapshot_on(state: dict[str, Any], date: str) -> bool:
    for snap in state.get("snapshots") or []:
        if str(snap.get("date", "")).startswith(date):
            return True
    return False


def saturday_due(state: dict[str, Any], current: datetime | None = None) -> bool:
    current = current or now()
    if current.weekday() != 5:
        return False
    return not _has_snapshot_on(state, current.date().isoformat())


def missed_saturday(state: dict[str, Any], current: datetime | None = None) -> bool:
    current = current or now()
    from datetime import timedelta

    if current.weekday() == 5:
        return False
    days_since_sat = (current.weekday() - 5) % 7
    saturday = (current - timedelta(days=days_since_sat)).date().isoformat()
    return not _has_snapshot_on(state, saturday)


def _same_day(ping: dict[str, Any], current: datetime) -> bool:
    stamp = ping.get("created_at") or ""
    try:
        return stamp[:10] == current.date().isoformat()
    except Exception:
        return False


def _same_week(ping: dict[str, Any], current: datetime) -> bool:
    stamp = ping.get("created_at") or ""
    try:
        dt = datetime.fromisoformat(stamp)
        return dt >= week_start(current)
    except Exception:
        return False


def ping_record(*, force: bool, reason: str) -> dict[str, Any]:
    return {
        "id": None,  # filled by caller
        "created_at": iso(),
        "due": True,
        "submitted_at": None,
        "missed": False,
        "force": force,
        "reason": reason,
        "kind": "random",
    }
