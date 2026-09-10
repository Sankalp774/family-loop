from __future__ import annotations

from typing import Any

from app.agents.tools import issue_random_ping, save_screen_time_snapshot, write_sunday_digest, send_digest_message
from app.clock import this_saturday_morning, this_sunday_evening
from app.clock import set_override as set_clock
from app.store import get_store


def saturday_simulation() -> dict[str, Any]:
    """Deterministic demo: Saturday ping → Discord snapshot → family state."""
    steps: list[dict[str, str]] = []
    set_clock(this_saturday_morning())
    steps.append({"at": "18:00", "text": "Calendar advanced to Saturday"})
    issue_random_ping(force=True)
    steps.append({"at": "18:05", "text": "Check-in requested"})
    save_screen_time_snapshot("YouTube 40\nDiscord 25\nWhatsApp 12", kind="saturday")
    steps.append({"at": "18:10", "text": "Snapshot received"})
    steps.append({"at": "18:11", "text": "Discord detected — not on the approved list"})
    pending = [r for r in get_store().snapshot().get("requests") or [] if r.get("status") == "pending"]
    if pending:
        steps.append({"at": "18:12", "text": f"Pending request found: {pending[0].get('subject')}"})
    else:
        steps.append({"at": "18:12", "text": "No pending parent decision on file yet"})
    steps.append({"at": "18:13", "text": "Family state updated"})
    return {"kind": "saturday", "steps": steps, "state": get_store().snapshot()}


def fast_forward() -> dict[str, Any]:
    """Today → Saturday → Sunday in one run for the video."""
    sat = saturday_simulation()
    set_clock(this_sunday_evening())
    steps = list(sat["steps"])
    steps.append({"at": "19:00", "text": "Calendar advanced to Sunday"})
    write_sunday_digest("")
    send_digest_message("whatsapp")
    steps.append({"at": "19:05", "text": "Sunday digest prepared"})
    steps.append({"at": "19:06", "text": "Simulated WhatsApp filed"})
    return {"kind": "fast_forward", "steps": steps, "state": get_store().snapshot()}
