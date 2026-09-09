from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.clock import iso
from app.ids import new_id
from app.store import get_store

CALENDARS = [
    {"key": "family", "label": "Family", "color": "#0f766e"},
    {"key": "important", "label": "Important", "color": "#dc2626"},
    {"key": "school", "label": "School", "color": "#2563eb"},
    {"key": "sports", "label": "Sports", "color": "#16a34a"},
    {"key": "screen", "label": "Screen Time", "color": "#ca8a04"},
    {"key": "personal", "label": "Personal", "color": "#ea580c"},
]
CAL_KEYS = {c["key"] for c in CALENDARS}
COLOR = {c["key"]: c["color"] for c in CALENDARS}
WHO_KEYS = {"family", "parent", "child"}
REPEAT_KEYS = {"none", "weekly", "monthly"}


def calendar_meta() -> list[dict[str, str]]:
    return list(CALENDARS)


def add_event(payload: dict[str, Any], by: str) -> dict[str, Any]:
    event, error = _normalize(payload, by=by, existing=None)
    if error:
        return {"ok": False, "reason": error}
    event["id"] = new_id("evt")
    event["created_at"] = iso()
    event["created_by"] = by
    event["source"] = "user"

    def mutate(data):
        data.setdefault("events", []).append(event)

    get_store().update(mutate)
    return {"ok": True, "event": event}


def patch_event(event_id: str, payload: dict[str, Any], by: str) -> dict[str, Any]:
    found: dict[str, Any] = {}

    def mutate(data):
        for item in data.get("events") or []:
            if item.get("id") == event_id:
                found.update(item)
                merged = {**item, **{k: v for k, v in payload.items() if v is not None}}
                event, error = _normalize(merged, by=by, existing=item)
                if error:
                    found["error"] = error
                    return
                event["id"] = item["id"]
                event["created_at"] = item.get("created_at")
                event["created_by"] = item.get("created_by") or by
                event["source"] = "user"
                event["updated_at"] = iso()
                event["updated_by"] = by
                item.clear()
                item.update(event)
                found.clear()
                found.update(item)
                break

    get_store().update(mutate)
    if found.get("error"):
        return {"ok": False, "reason": found["error"]}
    if not found:
        return {"ok": False, "reason": "Event not found."}
    return {"ok": True, "event": found}


def delete_event(event_id: str) -> dict[str, Any]:
    removed = {"id": None}

    def mutate(data):
        before = data.get("events") or []
        data["events"] = [item for item in before if item.get("id") != event_id]
        if len(data["events"]) != len(before):
            removed["id"] = event_id

    get_store().update(mutate)
    if not removed["id"]:
        return {"ok": False, "reason": "Event not found."}
    return {"ok": True, "id": event_id}


def expand_events(events: list[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    """Turn stored events (including weekly/monthly repeat) into dated occurrences."""
    out: list[dict[str, Any]] = []
    for event in events or []:
        for day in _occurrence_dates(event, start, end):
            item = dict(event)
            item["occurrence_date"] = day.isoformat()
            item["color"] = COLOR.get(event.get("calendar") or "family", "#0f766e")
            item["readonly"] = event.get("source") == "system"
            out.append(item)
    out.sort(key=lambda e: (e.get("occurrence_date"), not e.get("all_day"), e.get("start_time") or "99:99"))
    return out


def _occurrence_dates(event: dict[str, Any], start: date, end: date) -> list[date]:
    raw = str(event.get("date") or "")[:10]
    try:
        origin = date.fromisoformat(raw)
    except ValueError:
        return []
    until = origin
    if event.get("repeat_until"):
        try:
            until = date.fromisoformat(str(event["repeat_until"])[:10])
        except ValueError:
            until = origin
    repeat = event.get("repeat") or "none"
    if repeat not in REPEAT_KEYS:
        repeat = "none"
    days: list[date] = []
    if repeat == "none":
        last = origin
        if event.get("end_date"):
            try:
                last = date.fromisoformat(str(event["end_date"])[:10])
            except ValueError:
                last = origin
        cur = origin
        while cur <= last:
            if start <= cur <= end:
                days.append(cur)
            cur += timedelta(days=1)
        return days
    cur = origin
    guard = 0
    while cur <= end and cur <= until and guard < 400:
        if cur >= start:
            days.append(cur)
        if repeat == "weekly":
            cur += timedelta(days=7)
        else:
            cur = _add_month(cur)
        guard += 1
    return days


def _add_month(day: date) -> date:
    month = day.month + 1
    year = day.year
    if month > 12:
        month = 1
        year += 1
    last = _last_day(year, month)
    return date(year, month, min(day.day, last))


def _last_day(year: int, month: int) -> int:
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    return (nxt - timedelta(days=1)).day


def _normalize(payload: dict[str, Any], by: str, existing: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    title = str(payload.get("title") or "").strip()
    if not title:
        return None, "Give the event a title."
    day = str(payload.get("date") or "")[:10]
    try:
        date.fromisoformat(day)
    except ValueError:
        return None, "Pick a valid date."
    cal = payload.get("calendar") or "family"
    if cal not in CAL_KEYS:
        cal = "family"
    who = payload.get("who") or "family"
    if who not in WHO_KEYS:
        who = "family"
    repeat = payload.get("repeat") or "none"
    if repeat not in REPEAT_KEYS:
        repeat = "none"
    all_day = bool(payload.get("all_day", True if not payload.get("start_time") else False))
    start_time = _hhmm(payload.get("start_time")) if not all_day else None
    end_time = _hhmm(payload.get("end_time")) if not all_day else None
    if start_time and end_time and end_time <= start_time:
        return None, "End time must be after start time."
    end_date = str(payload.get("end_date") or day)[:10]
    try:
        if date.fromisoformat(end_date) < date.fromisoformat(day):
            return None, "End date cannot be before the start date."
    except ValueError:
        end_date = day
    until = payload.get("repeat_until")
    if until:
        until = str(until)[:10]
        try:
            date.fromisoformat(until)
        except ValueError:
            until = None
    event = {
        "title": title[:140],
        "notes": str(payload.get("notes") or "")[:500],
        "date": day,
        "end_date": end_date if end_date != day else None,
        "all_day": all_day,
        "start_time": start_time,
        "end_time": end_time,
        "calendar": cal,
        "who": who,
        "repeat": repeat,
        "repeat_until": until,
        "important": bool(payload.get("important")),
        "location": str(payload.get("location") or "")[:120],
    }
    return event, None


def _hhmm(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.strptime(text[:5], "%H:%M")
        return parsed.strftime("%H:%M")
    except ValueError:
        return None
