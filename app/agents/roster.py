from __future__ import annotations

AGENTS = [
    {
        "id": "family_desk",
        "short": "desk",
        "name": "Desk",
        "title": "Family desk",
        "color": "#9a3b38",
        "line": "Orchestrator. Routes the job, then steps aside.",
    },
    {
        "id": "setup_coach",
        "short": "setup",
        "name": "Coach",
        "title": "Setup coach",
        "color": "#1f1d1b",
        "line": "Writes the Family Policy. Does not only chat.",
    },
    {
        "id": "request_triage",
        "short": "triage",
        "name": "Triage",
        "title": "Request triage",
        "color": "#5c5346",
        "line": "Allow, deny, or ask parent. No silent yes on social.",
    },
    {
        "id": "checkin_runner",
        "short": "check",
        "name": "Check-in",
        "title": "Check-in runner",
        "color": "#3d6b52",
        "line": "Saturday file and random Screen Time pings.",
    },
    {
        "id": "digest_writer",
        "short": "digest",
        "name": "Digest",
        "title": "Digest writer",
        "color": "#3f4a44",
        "line": "Sunday Red / Needs you / Green.",
    },
    {
        "id": "override_clerk",
        "short": "clerk",
        "name": "Clerk",
        "title": "Override clerk",
        "color": "#6f6b66",
        "line": "Logs Meera’s yes/no. Aarav cannot approve himself.",
    },
]

_EVENT = {
    "setup": ["setup_coach"],
    "policy": ["setup_coach"],
    "locks": ["setup_coach"],
    "new_ask": ["request_triage"],
    "ask": ["request_triage"],
    "ping": ["checkin_runner"],
    "snapshot": ["checkin_runner"],
    "saturday": ["checkin_runner"],
    "sunday": ["digest_writer"],
    "digest": ["digest_writer"],
    "decide": ["override_clerk"],
    "override": ["override_clerk"],
}


def agents_for_event(event: str) -> list[str]:
    specialists = _EVENT.get(event, [])
    return ["family_desk", *specialists]
