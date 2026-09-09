from __future__ import annotations

from typing import Any

from app.clock import iso, now
from app.pings import missed_saturday
from app.policy import locks_complete
from app.snapshots import total_minutes


def build_digest(state: dict[str, Any]) -> dict[str, Any]:
    """Sunday page. Only three buckets: Red, Needs you, Green."""
    red: list[dict[str, str]] = []
    needs: list[dict[str, str]] = []
    green: list[dict[str, str]] = []

    locks = state.get("locks") or {}
    if not locks_complete(locks):
        red.append(
            {
                "code": "locks_incomplete",
                "title": "Locks not finished. Detection is weak.",
                "detail": "Screen Time / Digital Wellbeing checklist still has open boxes. Family Loop is an inbox, not the OS.",
            }
        )

    if missed_saturday(state):
        red.append(
            {
                "code": "no_saturday_file",
                "title": "No Saturday Screen Time file",
                "detail": "Aarav did not paste last Saturday’s app list. We cannot see new installs without it.",
            }
        )

    missed_pings = [
        p
        for p in state.get("pings") or []
        if p.get("missed") or (p.get("due") and not p.get("submitted_at") and not p.get("missed"))
    ]
    # A still-open ping on Sunday is a miss.
    if missed_pings:
        red.append(
            {
                "code": "missed_random_ask",
                "title": "Missed random Screen Time ask",
                "detail": f"{len(missed_pings)} ping(s) were not answered.",
            }
        )

    unapproved: list[str] = []
    for snap in state.get("snapshots") or []:
        for name in snap.get("new_unapproved") or []:
            if name not in unapproved:
                unapproved.append(name)
    if unapproved:
        red.append(
            {
                "code": "unapproved_new_app",
                "title": "New app never approved",
                "detail": ", ".join(unapproved) + " showed up on a pasted snapshot and was never allowed.",
            }
        )

    pending = [r for r in state.get("requests") or [] if r.get("status") == "pending"]
    for req in pending:
        needs.append(
            {
                "code": "pending_ask",
                "title": f"{req.get('kind')}: {req.get('subject')}",
                "detail": req.get("reason") or "Waiting on a parent yes/no.",
                "request_id": req.get("id"),
            }
        )
        red.append(
            {
                "code": "ignored_ask",
                "title": f"Ignored ask: {req.get('subject')}",
                "detail": "Still pending when Sunday ran. Parent did not show up for the yes/no.",
                "request_id": req.get("id"),
            }
        )

    saturday = _latest_saturday(state)
    cap = (state.get("policy") or {}).get("daily_cap_minutes") or 120
    if saturday:
        green.append(
            {
                "code": "checkin_on_time",
                "title": "Saturday check-in on time",
                "detail": f"Snapshot {saturday.get('date')} filed with {len(saturday.get('apps') or [])} apps.",
            }
        )
        if not (saturday.get("new_unapproved") or []):
            green.append(
                {
                    "code": "no_new_apps",
                    "title": "No new apps on the Saturday file",
                    "detail": "Diff against the approved list was empty.",
                }
            )
        if total_minutes(saturday.get("apps") or []) <= cap:
            green.append(
                {
                    "code": "under_cap",
                    "title": "Time under cap",
                    "detail": f"{total_minutes(saturday.get('apps') or [])} minutes vs {cap} minute cap (from the pasted snapshot, not from the OS).",
                }
            )

    if not red and not needs:
        if not green:
            green.append(
                {
                    "code": "quiet_week",
                    "title": "Quiet week",
                    "detail": "No reds, no pending asks.",
                }
            )

    child = (state.get("child") or {}).get("name") or "Aarav"
    parent = (state.get("parent") or {}).get("name") or "Meera"
    letter = render_letter(parent, child, red, needs, green)
    whatsapp = render_whatsapp(parent, child, red, needs, green)

    return {
        "id": None,
        "ran_at": iso(),
        "weekday": now().strftime("%A"),
        "red": red,
        "needs_you": needs,
        "green": green,
        "letter": letter,
        "whatsapp": whatsapp,
        "disclaimer": "We do not control the device. Vendor Screen Time numbers are whatever a human pasted. Simulated OS feeds are labelled as such.",
    }


def render_letter(
    parent: str,
    child: str,
    red: list[dict[str, str]],
    needs: list[dict[str, str]],
    green: list[dict[str, str]],
) -> str:
    lines = [
        f"Sunday desk for {parent} — {child}’s week",
        "",
        "Family Loop is an inbox. The phone OS is the lock.",
        "",
        "RED",
    ]
    if red:
        for item in red:
            lines.append(f"• {item['title']} — {item['detail']}")
    else:
        lines.append("• none")
    lines += ["", "NEEDS YOU"]
    if needs:
        for item in needs:
            lines.append(f"• {item['title']} — {item['detail']}")
    else:
        lines.append("• none")
    lines += ["", "GREEN"]
    if green:
        for item in green:
            lines.append(f"• {item['title']} — {item['detail']}")
    else:
        lines.append("• none")
    return "\n".join(lines)


def render_whatsapp(
    parent: str,
    child: str,
    red: list[dict[str, str]],
    needs: list[dict[str, str]],
    green: list[dict[str, str]],
) -> str:
    red_titles = ", ".join(i["title"] for i in red) or "none"
    need_titles = ", ".join(i["title"] for i in needs) or "none"
    green_titles = ", ".join(i["title"] for i in green) or "none"
    return (
        f"Family Loop · Sunday\n"
        f"{parent}, {child}’s week is on the desk.\n"
        f"Red: {red_titles}\n"
        f"Needs you: {need_titles}\n"
        f"Green: {green_titles}\n"
        f"We do not control the device."
    )


def _latest_saturday(state: dict[str, Any]) -> dict[str, Any] | None:
    for snap in reversed(state.get("snapshots") or []):
        if snap.get("kind") == "saturday":
            return snap
    return None
