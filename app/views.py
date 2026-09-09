from __future__ import annotations

from typing import Any

from app.calendar import family_calendar
from app.config import ASK_FIRST_CHOICES, HARD_NO_CHOICES, KIND_CHOICES, LOCK_ITEMS, PARENT_NOTE_DEFAULT
from app.pings import open_ping, saturday_due
from app.policy import locks_complete, policy_card


def public_state(state: dict[str, Any], role: str) -> dict[str, Any]:
    ping = open_ping(state)
    latest_digest = (state.get("digests") or [{}])[-1] if state.get("digests") else None
    payload = {
        "family_id": state.get("family_id"),
        "child": state.get("child"),
        "parent": state.get("parent") if role == "parent" else {"name": state.get("parent", {}).get("name")},
        "policy": state.get("policy"),
        "policy_card": policy_card(state.get("policy"), state.get("child")),
        "calendar": family_calendar(state),
        "choices": {
            "ask_first": ASK_FIRST_CHOICES,
            "hard_no": HARD_NO_CHOICES,
            "kinds": KIND_CHOICES,
            "parent_note_default": PARENT_NOTE_DEFAULT,
        },
        "locks": state.get("locks"),
        "locks_complete": locks_complete(state.get("locks") or {}),
        "lock_items": LOCK_ITEMS,
        "requests": _requests_for(state, role),
        "snapshots": state.get("snapshots") or [],
        "open_ping": ping if role == "child" or role == "parent" else None,
        "saturday_due": saturday_due(state),
        "disclaimer": "We do not control the device.",
        "clock": state.get("clock"),
        "outbox": state.get("outbox") or [] if role == "parent" else [],
        "latest_digest": latest_digest if role == "parent" else _family_digest(latest_digest),
        "agent_log": (state.get("agent_log") or [])[-20:] if role == "parent" else [],
        "overrides": state.get("overrides") or [] if role == "parent" else [],
        "todos": state.get("todos") or [],
        "events": state.get("events") or [],
    }
    if role == "child":
        payload["banner"] = _child_banner(state, ping)
    return payload


def _requests_for(state: dict[str, Any], role: str) -> list[dict[str, Any]]:
    rows = state.get("requests") or []
    if role == "parent":
        return rows
    # Child sees own asks, never parent-only notes.
    clean = []
    for row in rows:
        clean.append(
            {
                "id": row.get("id"),
                "kind": row.get("kind"),
                "subject": row.get("subject"),
                "detail": row.get("detail"),
                "status": row.get("status"),
                "filed_at": row.get("filed_at"),
            }
        )
    return clean


def _family_digest(digest: dict[str, Any] | None) -> dict[str, Any] | None:
    if not digest:
        return None
    return {
        "ran_at": digest.get("ran_at"),
        "green": digest.get("green"),
        "disclaimer": digest.get("disclaimer"),
    }


def _child_banner(state: dict[str, Any], ping: dict[str, Any] | None) -> dict[str, Any] | None:
    if ping:
        return {
            "kind": "random_ask",
            "title": "Screen Time check-in",
            "body": "Paste this week’s app list and minutes. Family Loop cannot see the phone. If you skip this, Sunday goes Red.",
        }
    if saturday_due(state):
        return {
            "kind": "saturday",
            "title": "Saturday Screen Time file",
            "body": "Required. Paste or type the app list from Screen Time / Digital Wellbeing.",
        }
    return None
