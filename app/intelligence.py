from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.clock import live_now, now
from app.policy import approved_app_names, locks_complete, norm
from app.snapshots import total_minutes


def request_history(state: dict[str, Any], subject: str) -> dict[str, Any]:
    key = norm(subject)
    rows = [r for r in (state.get("requests") or []) if norm(r.get("subject") or "") == key]
    first = rows[0]["filed_at"] if rows else None
    last = rows[-1] if rows else None
    pending = [r for r in rows if r.get("status") == "pending"]
    days = 0
    if pending:
        try:
            start = datetime.fromisoformat(str(pending[0].get("filed_at")))
            days = max((now() - start).days, 0)
        except Exception:
            days = 0
    last_decision = None
    for row in reversed(state.get("decisions") or []):
        if norm(row.get("subject") or "") == key:
            last_decision = row.get("status")
            break
    return {
        "subject": subject,
        "first_requested": (first or "")[:10] or None,
        "requests": len(rows),
        "previous_decision": last_decision,
        "current_status": last.get("status") if last else None,
        "pending_days": days,
        "ids": [r.get("id") for r in pending],
    }


def week_snapshots(state: dict[str, Any], days: int = 7) -> list[dict[str, Any]]:
    cutoff = (now() - timedelta(days=days)).date().isoformat()
    return [s for s in (state.get("snapshots") or []) if str(s.get("date") or "")[:10] >= cutoff]


def family_state(state: dict[str, Any]) -> dict[str, Any]:
    pending = [r for r in (state.get("requests") or []) if r.get("status") == "pending"]
    allowed = approved_app_names(state)
    resolved = {norm(row.get("subject") or ""): row.get("status") for row in (state.get("exception_log") or [])}
    unapproved: list[str] = []
    for snap in state.get("snapshots") or []:
        for name in snap.get("new_unapproved") or []:
            key = norm(name)
            if key in allowed or key in resolved:
                continue
            if name not in unapproved:
                unapproved.append(name)
    snaps = week_snapshots(state, 14)
    expected = 2  # saturday + at least one ping window
    received = len(snaps)
    reliability = min(100, int(100 * received / max(expected, 1))) if snaps or expected else 0
    if received >= 6:
        reliability = min(100, int(100 * received / 7))
    cap = int((state.get("policy") or {}).get("daily_cap_minutes") or 120)
    under = 0
    total = 0
    for snap in snaps:
        total += 1
        if total_minutes(snap.get("apps") or []) <= cap:
            under += 1
    adherence = int(100 * under / total) if total else 100
    waiting = len(pending)
    exceptions = len(unapproved)
    if exceptions:
        health = "exception"
        health_label = "Exception"
        health_tone = "red"
    elif waiting:
        health = "attention"
        health_label = "Needs you"
        health_tone = "amber"
    else:
        health = "stable"
        health_label = "Stable"
        health_tone = "green"
    child = (state.get("child") or {}).get("name") or "Aarav"
    parent = (state.get("parent") or {}).get("name") or "Meera"
    sunday = _days_until_sunday()
    headline = (
        f"Nothing urgent today. {waiting} item{'s' if waiting != 1 else ''} waiting for {parent}."
        if health != "exception"
        else f"{exceptions} exception{'s' if exceptions != 1 else ''} detected. {parent} should look."
    )
    if not waiting and not exceptions:
        headline = f"Nothing urgent today. Two quiet signals: check-ins and no new apps."
        if reliability:
            headline = f"Nothing urgent today. Routine is stable."
    return {
        "health": health,
        "health_label": health_label,
        "health_tone": health_tone,
        "headline": headline,
        "routine": "Stable" if reliability >= 70 else "Uneven",
        "decisions_waiting": waiting,
        "exceptions": exceptions,
        "days_until_review": sunday,
        "child": {
            "name": child,
            "adherence": adherence,
            "reliability": reliability,
            "unresolved": waiting,
            "new_apps": exceptions,
        },
        "needs_you": _needs_you(state, pending, unapproved),
        "today": _today_plan(state),
        "week": {
            "adherence": adherence,
            "checkins": f"{received} / 7",
            "checkins_n": received,
            "new_apps": exceptions,
            "pending": waiting,
        },
        "locks_complete": locks_complete(state.get("locks") or {}),
        "attention": {
            "urgent": exceptions,
            "decisions": waiting,
            "informational": max(received, 0) + len(state.get("digests") or []),
            "line": (
                f"{exceptions} urgent · {waiting} decision · "
                f"{max(received, 0) + len(state.get('digests') or [])} informational"
            ),
        },
    }


def _needs_you(state: dict[str, Any], pending: list[dict], unapproved: list[str]) -> list[dict[str, Any]]:
    items = []
    for name in unapproved:
        items.append(
            {
                "tone": "red",
                "subject": name,
                "kind": "unapproved_app",
                "id": f"app:{name}",
                "title": name,
                "why": f"{name} isn’t on the approved list. New apps require parent approval.",
                "rule": "New apps require parent approval.",
                "detail": "Detected on a pasted Screen Time snapshot.",
            }
        )
    for req in pending:
        hist = request_history(state, req.get("subject") or "")
        items.append(
            {
                "tone": "amber",
                "subject": req.get("subject"),
                "kind": req.get("kind"),
                "id": req.get("id"),
                "title": req.get("subject"),
                "why": req.get("reason") or "Waiting on a parent yes/no.",
                "rule": "Social / new app / new contact / money must ask parent.",
                "detail": f"Requested {hist['requests']} time(s). Pending {hist['pending_days']} day(s).",
                "history": hist,
            }
        )
    return items


def _today_plan(state: dict[str, Any]) -> list[dict[str, str]]:
    today = live_now().date().isoformat()
    rows = [{"time": "08:00", "title": "School"}, {"time": "17:00", "title": "Homework window"}]
    for ev in state.get("events") or []:
        if str(ev.get("date") or "")[:10] == today:
            rows.append(
                {
                    "time": ev.get("start_time") or "All day",
                    "title": ev.get("title") or "Event",
                }
            )
    rows.sort(key=lambda r: r["time"])
    return rows[:6]


def _days_until_sunday() -> int:
    return (6 - live_now().weekday()) % 7


def timeline(state: dict[str, Any], limit: int = 40) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for req in state.get("requests") or []:
        events.append(
            {
                "at": req.get("filed_at") or "",
                "tone": "amber" if req.get("status") == "pending" else "green",
                "title": f"{req.get('subject')} requested",
                "detail": f"{req.get('kind')} · {req.get('status')}",
                "kind": "ask",
            }
        )
        if req.get("decided_at"):
            events.append(
                {
                    "at": req.get("decided_at"),
                    "tone": "green" if req.get("status") == "allowed" else "red",
                    "title": f"{req.get('subject')} {req.get('status')}",
                    "detail": req.get("parent_note") or req.get("reason") or "",
                    "kind": "decision",
                }
            )
    for snap in state.get("snapshots") or []:
        new = snap.get("new_unapproved") or []
        events.append(
            {
                "at": f"{snap.get('date')}T17:30:00",
                "tone": "red" if new else "green",
                "title": "New app detected" if new else "Screen Time snapshot received",
                "detail": ", ".join(new) if new else f"{len(snap.get('apps') or [])} apps pasted",
                "kind": "snapshot",
            }
        )
    for ping in state.get("pings") or []:
        events.append(
            {
                "at": ping.get("created_at") or "",
                "tone": "red" if ping.get("missed") else "green",
                "title": "Random ping missed" if ping.get("missed") else "Random Screen Time ask",
                "detail": "answered" if ping.get("submitted_at") else ("missed" if ping.get("missed") else "due"),
                "kind": "ping",
            }
        )
    for dig in state.get("digests") or []:
        events.append(
            {
                "at": dig.get("ran_at") or "",
                "tone": "green",
                "title": "Sunday digest filed",
                "detail": "Red / Needs you / Green",
                "kind": "digest",
            }
        )
    events.sort(key=lambda e: str(e.get("at") or ""), reverse=True)
    grouped: list[dict[str, Any]] = []
    by_day: dict[str, list] = {}
    for item in events[:limit]:
        day = str(item.get("at") or "")[:10] or "undated"
        by_day.setdefault(day, []).append(item)
    for day, items in by_day.items():
        grouped.append({"date": day, "items": items})
    grouped.sort(key=lambda g: g["date"], reverse=True)
    return grouped


def what_changed(state: dict[str, Any]) -> dict[str, Any]:
    snaps = week_snapshots(state, 14)
    older = [s for s in (state.get("snapshots") or []) if s not in snaps][-3:]
    this_min = sum(total_minutes(s.get("apps") or []) for s in snaps[-2:]) if snaps else 0
    prev_min = sum(total_minutes(s.get("apps") or []) for s in older[-2:]) if older else this_min
    screen_delta = 0
    if prev_min:
        screen_delta = int(round(100 * (this_min - prev_min) / prev_min))
    week = family_state(state)["week"]
    pending = [r for r in (state.get("requests") or []) if r.get("status") == "pending"]
    resolved = [
        r
        for r in (state.get("requests") or [])
        if r.get("status") in {"allowed", "denied"} and str(r.get("decided_at") or "")[:10] >= (now() - timedelta(days=7)).date().isoformat()
    ]
    new_asks = [
        r
        for r in (state.get("requests") or [])
        if str(r.get("filed_at") or "")[:10] >= (now() - timedelta(days=7)).date().isoformat()
    ]
    unapproved: list[str] = []
    for snap in snaps:
        for name in snap.get("new_unapproved") or []:
            if name not in unapproved:
                unapproved.append(name)
    summary = "The week was mostly stable."
    if unapproved:
        summary = (
            f"The week was mostly stable. The main exception was {unapproved[0]}, "
            "which appeared in the latest snapshot without an approval record."
        )
    if pending:
        oldest = pending[0].get("subject")
        hist = request_history(state, oldest or "")
        summary += f" {oldest} has remained unresolved for {hist['pending_days']} day(s)."
    return {
        "screen_delta": screen_delta,
        "reliability": week["checkins"],
        "approved_apps": len(approved_app_names(state)),
        "new_requests": len(new_asks),
        "resolved": len(resolved),
        "still_waiting": len(pending),
        "exceptions": unapproved,
        "summary": summary.strip(),
    }


def patterns(state: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    by_subject: dict[str, list] = {}
    for req in state.get("requests") or []:
        by_subject.setdefault(norm(req.get("subject") or ""), []).append(req)
    for key, rows in by_subject.items():
        pending = [r for r in rows if r.get("status") == "pending"]
        if len(rows) >= 2 and pending:
            subject = rows[-1].get("subject")
            hist = request_history(state, subject)
            found.append(
                {
                    "kind": "repeat_ask",
                    "subject": subject,
                    "request_id": pending[-1].get("id"),
                    "title": f"{subject} has been requested repeatedly.",
                    "body": (
                        f"{subject} was requested {hist['requests']} times. "
                        f"Still pending {hist['pending_days']} day(s). "
                        "Would you like to review it? The agent recommends; Meera decides."
                    ),
                }
            )
    health = family_state(state)
    pending = [r for r in (state.get("requests") or []) if r.get("status") == "pending"]
    if health["child"]["reliability"] >= 80 and health["child"]["new_apps"] == 0 and pending:
        req = pending[0]
        found.append(
            {
                "kind": "good_week",
                "subject": req.get("subject"),
                "request_id": req.get("id"),
                "title": "A quiet stretch of check-ins.",
                "body": (
                    f"Check-in reliability is {health['child']['reliability']}% and there are no new-app "
                    f"violations. You may want to review the pending {req.get('subject')} request."
                ),
            }
        )
    return found[:3]


def memory_view(state: dict[str, Any]) -> dict[str, Any]:
    policy = state.get("policy") or {}
    approvals = []
    for name in (policy.get("approved_apps") or [])[:12]:
        approvals.append({"name": name, "status": "allowed"})
    for req in state.get("requests") or []:
        if req.get("status") == "pending":
            approvals.append({"name": req.get("subject"), "status": "pending"})
        elif req.get("status") == "denied":
            approvals.append({"name": req.get("subject"), "status": "denied"})
    health = family_state(state)
    return {
        "policy": {
            "ask_first": policy.get("ask_first") or [],
            "hard_no": policy.get("hard_no") or [],
            "youtube": "After homework" if policy.get("youtube_after_homework") else "Ask first",
        },
        "people": [
            {"name": (state.get("parent") or {}).get("name") or "Meera", "role": "Parent"},
            {"name": (state.get("child") or {}).get("name") or "Aarav", "role": "Child"},
        ],
        "approvals": approvals[-16:],
        "routines": ["Saturday → check-in", "Sunday → review"],
        "patterns": [
            f"{health['week']['checkins']} check-ins",
            f"{health['decisions_waiting']} unresolved requests",
        ],
    }


def resolve_exception(subject: str, status: str, by: str = "parent") -> dict[str, Any]:
    """Allow a new-app exception into the approved list, or record a deny. Not an OS write."""
    from app.clock import iso
    from app.ids import new_id
    from app.store import get_store

    if status not in {"allowed", "denied"}:
        return {"ok": False, "reason": "status must be allowed or denied"}
    name = (subject or "").strip()
    if not name:
        return {"ok": False, "reason": "missing app name"}

    def mutate(data):
        log = data.setdefault("exception_log", [])
        log.append(
            {
                "id": new_id("exc"),
                "subject": name,
                "status": status,
                "at": iso(),
                "by": by,
            }
        )
        data.setdefault("decisions", []).append(
            {
                "id": new_id("dec"),
                "kind": "install_app",
                "subject": name,
                "status": status,
                "reason": "Parent resolved a new-app exception from a snapshot.",
                "at": iso(),
                "by": by,
            }
        )
        if status == "allowed":
            policy = data.get("policy") or {}
            apps = list(policy.get("approved_apps") or [])
            if name not in apps:
                apps.append(name)
            policy["approved_apps"] = apps
            data["policy"] = policy

    get_store().update(mutate)
    return {"ok": True, "subject": name, "status": status}


def extra_time_context(state: dict[str, Any]) -> dict[str, Any]:
    current = now()
    today = current.date().isoformat()
    homework_done = False
    sports_soon = False
    school_tomorrow = current.weekday() < 4 or current.weekday() == 6
    for ev in state.get("events") or []:
        if str(ev.get("date") or "")[:10] != today:
            continue
        title = (ev.get("title") or "").lower()
        if "homework" in title:
            homework_done = True
        if "sport" in title or "cricket" in title:
            sports_soon = True
    for todo in state.get("todos") or []:
        if str(todo.get("date") or "")[:10] == today and "homework" in (todo.get("title") or "").lower():
            if todo.get("done"):
                homework_done = True
    return {
        "now": current.strftime("%H:%M"),
        "homework_done": homework_done,
        "school_tomorrow": school_tomorrow,
        "sports_soon": sports_soon,
        "eligible_to_recommend": homework_done and school_tomorrow,
        "note": (
            "Homework looks complete and tomorrow is a school day. "
            "Parent approval still required because extra time exceeds the normal allowance."
            if homework_done
            else "Parent approval required. Calendar does not show homework marked done."
        ),
    }


def sunday_steps(state: dict[str, Any]) -> list[str]:
    pending = [r for r in (state.get("requests") or []) if r.get("status") == "pending"]
    unapproved: list[str] = []
    for snap in state.get("snapshots") or []:
        unapproved.extend(snap.get("new_unapproved") or [])
    steps = [
        "Loaded family policy",
        "Reviewed 7 days of events",
        "Compared Screen Time snapshot",
    ]
    if unapproved:
        steps.append(f"Detected new application: {unapproved[-1]}")
    else:
        steps.append("No unapproved apps in the latest snapshot")
    if pending:
        steps.append(f"Found unresolved request: {pending[0].get('subject')}")
    else:
        steps.append("No unresolved parent decisions")
    steps.append("Checked Saturday ping")
    steps.append("Classified Red / Needs you / Green")
    steps.append("Filed Sunday digest")
    return steps
