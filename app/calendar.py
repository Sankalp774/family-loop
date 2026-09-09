from __future__ import annotations

import calendar as cal
from datetime import date, timedelta
from typing import Any

from app.clock import now
from app.config import KIND_CHOICES
from app.events import COLOR, calendar_meta, expand_events
from app.policy import default_policy


def _kind_label(kind: str) -> str:
    for item in KIND_CHOICES:
        if item["key"] == kind:
            return item["label"]
    return str(kind or "").replace("_", " ")


WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def family_calendar(state: dict[str, Any], year: int | None = None, month: int | None = None) -> dict[str, Any]:
    current = now()
    today = current.date()
    year = year or today.year
    month = month or today.month
    policy = state.get("policy") or default_policy(state.get("child"))
    planned = _planned_week(policy, state.get("child") or {})
    derived = _dated_events(state)
    first = date(year, month, 1)
    last = _shift_month(year, month, 1)
    last_day = date(last["year"], last["month"], 1) - timedelta(days=1)
    occurrences = expand_events(state.get("events") or [], first - timedelta(days=7), last_day + timedelta(days=7))
    by_day: dict[str, list[dict[str, Any]]] = {}
    for occ in occurrences:
        by_day.setdefault(occ["occurrence_date"], []).append(_chip(occ, source="user"))

    weeks: list[list[dict[str, Any]]] = []
    for week in cal.Calendar(firstweekday=0).monthdatescalendar(year, month):
        row = []
        for day in week:
            key = day.isoformat()
            tags: list[str] = []
            system: list[dict[str, Any]] = []
            if day.weekday() == 5:
                tags.append("submission")
                system.append(_system_chip("screen", "Screen Time due", "all day", day, kind="submission"))
            elif day.weekday() == 6:
                tags.append("evaluation")
                system.append(_system_chip("family", "Sunday evaluation", "19:00", day, kind="evaluation"))
            for plan in planned.get(day.weekday(), []):
                system.append(
                    _system_chip(
                        "school" if plan["kind"] in {"school", "youtube"} else ("sports" if plan["kind"] == "sports" else "screen"),
                        plan["title"],
                        plan.get("detail") or "",
                        day,
                    )
                )
            for extra in derived.get(key, []):
                system.append(
                    _system_chip("screen" if extra["kind"] in {"snapshot", "ping", "digest"} else "personal", extra["title"], extra.get("detail") or "", day)
                )
            if day == today:
                tags.append("today")
            if day < today:
                tags.append("past")
            todos = [
                item
                for item in (state.get("todos") or [])
                if str(item.get("date", ""))[:10] == key
            ]
            items = system + by_day.get(key, [])
            items.sort(key=lambda e: (not e.get("all_day"), e.get("start_time") or "00:00", e.get("title") or ""))
            row.append(
                {
                    "date": key,
                    "day": day.day,
                    "in_month": day.month == month,
                    "weekday": day.weekday(),
                    "weekday_name": WEEKDAYS[day.weekday()],
                    "tags": tags,
                    "past": day < today,
                    "events": system,
                    "items": items,
                    "todos": todos,
                }
            )
        weeks.append(row)

    upcoming = []
    for week in weeks:
        for day in week:
            if not day["in_month"] or day["date"] < today.isoformat():
                continue
            for item in day["items"]:
                if item.get("readonly") and item.get("calendar") in {"school"}:
                    continue
                upcoming.append({**item, "date": day["date"]})
            if len(upcoming) >= 12:
                break
        if len(upcoming) >= 12:
            break

    return {
        "year": year,
        "month": month,
        "title": date(year, month, 1).strftime("%B %Y"),
        "today": today.isoformat(),
        "clock": current.isoformat(timespec="seconds"),
        "weeks": weeks,
        "calendars": calendar_meta(),
        "legend": [
            {"tag": "submission", "color": "yellow", "label": "Saturday — submission"},
            {"tag": "evaluation", "color": "green", "label": "Sunday — evaluation"},
            {"tag": "today", "color": "ink", "label": "Today"},
            {"tag": "past", "color": "cross", "label": "Passed days are crossed out"},
        ],
        "planned": planned,
        "from_saved_policy": bool(state.get("policy")),
        "prev": _shift_month(year, month, -1),
        "next": _shift_month(year, month, 1),
        "upcoming": upcoming[:12],
        "event_count": sum(1 for w in weeks for d in w if d["in_month"] for i in d["items"] if not i.get("readonly")),
    }


def _chip(occ: dict[str, Any], source: str) -> dict[str, Any]:
    cal = occ.get("calendar") or "family"
    return {
        "id": occ.get("id"),
        "title": occ.get("title"),
        "notes": occ.get("notes") or "",
        "location": occ.get("location") or "",
        "date": occ.get("occurrence_date") or occ.get("date"),
        "end_date": occ.get("end_date"),
        "all_day": bool(occ.get("all_day")),
        "start_time": occ.get("start_time"),
        "end_time": occ.get("end_time"),
        "calendar": cal,
        "color": occ.get("color") or COLOR.get(cal, "#0f766e"),
        "who": occ.get("who") or "family",
        "repeat": occ.get("repeat") or "none",
        "repeat_until": occ.get("repeat_until"),
        "important": bool(occ.get("important")),
        "readonly": bool(occ.get("readonly") or source == "system"),
        "created_by": occ.get("created_by"),
        "source": occ.get("source") or source,
        "kind": occ.get("kind") or cal,
        "when": _when_label(occ),
    }


def _system_chip(calendar: str, title: str, detail: str, day: date, kind: str | None = None) -> dict[str, Any]:
    start = None
    if "–" in detail and ":" in detail:
        start = detail.split("–")[0].strip()[:5]
        if len(start) != 5:
            start = None
    return {
        "id": None,
        "title": title,
        "notes": detail,
        "location": "",
        "date": day.isoformat(),
        "end_date": None,
        "all_day": start is None,
        "start_time": start,
        "end_time": None,
        "calendar": calendar,
        "color": COLOR.get(calendar, "#64748b"),
        "who": "family",
        "repeat": "weekly",
        "repeat_until": None,
        "important": calendar == "important",
        "readonly": True,
        "created_by": "system",
        "source": "system",
        "kind": kind or calendar,
        "when": start or "All day",
    }


def _when_label(occ: dict[str, Any]) -> str:
    if occ.get("all_day") or not occ.get("start_time"):
        return "All day"
    if occ.get("end_time"):
        return f"{occ['start_time']}–{occ['end_time']}"
    return str(occ.get("start_time"))


def _shift_month(year: int, month: int, delta: int) -> dict[str, int]:
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return {"year": year, "month": month}


def _planned_week(policy: dict[str, Any], child: dict[str, Any]) -> dict[int, list[dict[str, str]]]:
    name = child.get("name") or policy.get("child_name") or "Aarav"
    school = policy.get("school_hours") or {"start": "08:00", "end": "15:00"}
    planned: dict[int, list[dict[str, str]]] = {i: [] for i in range(7)}
    for weekday in school.get("days") or [0, 1, 2, 3, 4]:
        planned[weekday].append(
            {
                "kind": "school",
                "title": f"{name} at school",
                "detail": f"{school.get('start')}–{school.get('end')} · no random pings",
            }
        )
    if policy.get("sports_phone_preset"):
        hours = policy.get("sports_hours") or {"start": "16:30", "end": "18:00"}
        for weekday in policy.get("sports_days") or [1, 3]:
            planned[weekday].append(
                {
                    "kind": "sports",
                    "title": "Sports practice",
                    "detail": f"{hours.get('start')}–{hours.get('end')}",
                }
            )
    return planned


def _dated_events(state: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}

    def add(day: str, event: dict[str, str]) -> None:
        if not day:
            return
        out.setdefault(day[:10], []).append(event)

    for req in state.get("requests") or []:
        add(
            str(req.get("filed_at") or ""),
            {
                "kind": "ask",
                "title": f"Ask: {req.get('subject')}",
                "detail": f"{_kind_label(req.get('kind') or '')} · {req.get('status')}",
            },
        )
    for snap in state.get("snapshots") or []:
        add(
            str(snap.get("date") or ""),
            {
                "kind": "snapshot",
                "title": "Screen Time file",
                "detail": f"{len(snap.get('apps') or [])} apps pasted",
            },
        )
    return out
