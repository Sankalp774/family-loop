from __future__ import annotations

import json
from typing import Any

from strands import tool

from app.clock import iso, now
from app.digest import build_digest
from app.ids import new_id
from app.pings import can_issue_ping, ping_record
from app.policy import locks_complete, policy_from_answers
from app.snapshots import diff_new_unapproved, parse_app_list, total_minutes
from app.intelligence import extra_time_context, request_history, sunday_steps, what_changed
from app.store import get_store
from app.triage import evaluate_request


def _state() -> dict[str, Any]:
    return get_store().snapshot()


@tool
def get_family_state(query: str = "") -> str:
    """Read the family store: policy, locks, pending asks, snapshots, pings.

    Args:
        query: Optional filter note. Ignored; the whole desk is returned.
    """
    state = _state()
    slim = {
        "policy": state.get("policy"),
        "locks": state.get("locks"),
        "locks_complete": locks_complete(state.get("locks") or {}),
        "pending": [r for r in state.get("requests") or [] if r.get("status") == "pending"],
        "snapshots": state.get("snapshots"),
        "pings": state.get("pings"),
        "decisions": (state.get("decisions") or [])[-8:],
        "disclaimer": "We do not control the device.",
    }
    return json.dumps(slim, ensure_ascii=False)


@tool
def save_family_policy(
    age: int,
    school_start: str,
    school_end: str,
    ask_first: list[str],
    hard_no: list[str],
    youtube_after_homework: bool,
    sports_phone_preset: bool,
    daily_cap_minutes: int = 120,
    notes: str = "",
) -> str:
    """Write the Family Policy JSON from the parent's setup answers. Not a chat log.

    Args:
        age: Child's age
        school_start: School start HH:MM
        school_end: School end HH:MM
        ask_first: Categories that always wait for a parent
        hard_no: Categories that are denied without asking
        youtube_after_homework: Allow YouTube extra time after homework
        sports_phone_preset: Allow Maps/Phone extra time for practice
        daily_cap_minutes: Soft daily cap used on Sunday
        notes: Optional parent note
    """
    store = get_store()

    def mutate(data):
        answers = {
            "age": age,
            "school_hours": {"start": school_start, "end": school_end},
            "ask_first": ask_first,
            "hard_no": hard_no,
            "youtube_after_homework": youtube_after_homework,
            "sports_phone_preset": sports_phone_preset,
            "daily_cap_minutes": daily_cap_minutes,
            "notes": notes,
        }
        data["policy"] = policy_from_answers(answers, data.get("child") or {})
        data["child"]["age"] = int(age)

    state = store.update(mutate)
    return json.dumps(
        {
            "saved": True,
            "policy": state["policy"],
            "note": "Policy is on file. Phones still enforce. We do not control the device.",
        },
        ensure_ascii=False,
    )


@tool
def save_locks_checklist(
    screen_time_on: bool,
    ask_to_install: bool,
    youtube_supervised: bool,
    roblox_pin: bool,
    downtime_school_hours: bool,
) -> str:
    """Save the Digital Wellbeing / Screen Time enablement checklist. Parent ticks. We do not flip OS bits.

    Args:
        screen_time_on: Screen Time or Digital Wellbeing is on
        ask_to_install: Ask-to-install is on
        youtube_supervised: YouTube supervised account
        roblox_pin: Roblox PIN set
        downtime_school_hours: OS downtime covers school hours
    """
    claimed = iso() if any(
        [screen_time_on, ask_to_install, youtube_supervised, roblox_pin, downtime_school_hours]
    ) else None

    def mutate(data):
        data["locks"] = {
            "screen_time_on": screen_time_on,
            "ask_to_install": ask_to_install,
            "youtube_supervised": youtube_supervised,
            "roblox_pin": roblox_pin,
            "downtime_school_hours": downtime_school_hours,
            "locks_claimed_on": claimed if locks_complete({
                "screen_time_on": screen_time_on,
                "ask_to_install": ask_to_install,
                "youtube_supervised": youtube_supervised,
                "roblox_pin": roblox_pin,
                "downtime_school_hours": downtime_school_hours,
            }) else data.get("locks", {}).get("locks_claimed_on"),
        }
        if locks_complete(data["locks"]):
            data["locks"]["locks_claimed_on"] = claimed

    state = get_store().update(mutate)
    complete = locks_complete(state["locks"])
    return json.dumps(
        {
            "locks": state["locks"],
            "complete": complete,
            "sunday": "Green on locks" if complete else "Sunday Red: Locks not finished. Detection is weak.",
            "disclaimer": "We do not control the device. This is a claimed checklist, not an API write.",
        }
    )


@tool
def file_child_request(
    kind: str,
    subject: str,
    detail: str = "",
    costs_money: bool = False,
    kid: str = "aarav",
) -> str:
    """File a child ask (install app, visit site, extra time, new contact) and triage it against policy.

    Args:
        kind: install_app | visit_site | extra_time | new_contact
        subject: App, site, or person name
        detail: Why they are asking
        costs_money: True if it costs money
        kid: Child id
    """
    store = get_store()
    state = store.snapshot()
    request = {
        "id": new_id("req"),
        "kid": kid,
        "kind": kind,
        "subject": subject,
        "detail": detail,
        "costs_money": costs_money,
        "filed_at": iso(),
        "status": "pending",
        "source": "child",
    }
    hist = request_history(state, subject)
    cal = extra_time_context(state) if kind == "extra_time" else None
    verdict = evaluate_request(state, request)
    if verdict["action"] == "allow":
        request["status"] = "allowed"
        request["decided_at"] = iso()
        request["decided_by"] = "request_triage"
    elif verdict["action"] == "deny":
        request["status"] = "denied"
        request["decided_at"] = iso()
        request["decided_by"] = "request_triage"
    else:
        request["status"] = "pending"
        request["decided_by"] = None
    request["triage"] = verdict["action"]
    request["reason"] = verdict["reason"]
    request["must_ask_parent"] = verdict["must_ask_parent"]
    request["history"] = hist
    if cal:
        request["calendar_context"] = cal

    def mutate(data):
        data.setdefault("requests", []).append(request)
        if request["status"] in {"allowed", "denied"}:
            data.setdefault("decisions", []).append(
                {
                    "id": new_id("dec"),
                    "kind": kind,
                    "subject": subject,
                    "status": request["status"],
                    "reason": request["reason"],
                    "at": iso(),
                    "by": "request_triage",
                }
            )

    store.update(mutate)
    return json.dumps(
        {
            "request": request,
            "history": hist,
            "calendar": cal,
            "note": "Parent only sees this if triage is ask_parent. We do not install anything.",
        },
        ensure_ascii=False,
    )


@tool
def get_request_history(subject: str) -> str:
    """Longitudinal memory for one subject: first asked, count, last decision, days pending.

    Args:
        subject: App or site name, e.g. Reddit
    """
    return json.dumps(request_history(_state(), subject), ensure_ascii=False)


@tool
def get_week_context(query: str = "") -> str:
    """Last 7–14 days of snapshots, pending asks, and what changed.

    Args:
        query: Unused.
    """
    state = _state()
    return json.dumps(
        {
            "what_changed": what_changed(state),
            "pending": [r for r in (state.get("requests") or []) if r.get("status") == "pending"],
            "snapshots": (state.get("snapshots") or [])[-4:],
        },
        ensure_ascii=False,
    )


@tool
def get_calendar_context(query: str = "") -> str:
    """Today's calendar plus homework/sports signals for extra-time asks.

    Args:
        query: Unused.
    """
    return json.dumps(extra_time_context(_state()), ensure_ascii=False)


@tool
def list_recent_decisions(query: str = "") -> str:
    """List last week's allow/deny/override decisions so triage can stay consistent.

    Args:
        query: Unused. Returns recent decisions.
    """
    state = _state()
    return json.dumps((state.get("decisions") or [])[-12:], ensure_ascii=False)


@tool
def issue_random_ping(force: bool = False) -> str:
    """Issue a random Screen Time ask. Max 1/day, 3/week, never during school hours unless force (demo button).

    Args:
        force: Parent clicked Simulate random ask. Judges will not wait for a clock.
    """
    store = get_store()
    state = store.snapshot()
    gate = can_issue_ping(state, force=force)
    if not gate["ok"]:
        return json.dumps({"issued": False, "reason": gate["reason"]})
    ping = ping_record(force=force, reason=gate["reason"])
    ping["id"] = new_id("ping")

    def mutate(data):
        data.setdefault("pings", []).append(ping)

    store.update(mutate)
    return json.dumps(
        {
            "issued": True,
            "ping": ping,
            "child_banner": "Paste app list + minutes. This is a human paste, not an OS API.",
        }
    )


@tool
def save_screen_time_snapshot(
    raw_list: str,
    kind: str = "random",
    kid: str = "aarav",
) -> str:
    """Save a Screen Time / Digital Wellbeing snapshot the child pasted. Diff vs approved apps.

    Args:
        raw_list: Pasted app list, one app per line, optional minutes
        kind: saturday | random
        kid: Child id
    """
    store = get_store()
    state = store.snapshot()
    apps = parse_app_list(raw_list)
    new_apps = diff_new_unapproved(state, apps)
    saved_kind = kind if kind in {"saturday", "random"} else "random"
    if now().weekday() == 5:
        saved_kind = "saturday"
    snap = {
        "id": new_id("snap"),
        "kid": kid,
        "date": now().date().isoformat(),
        "kind": saved_kind,
        "also_random": kind == "random",
        "apps": apps,
        "minutes_total": total_minutes(apps),
        "source": "human_paste",
        "new_unapproved": new_apps,
        "note": "Human-pasted snapshot. Not a vendor feed. We do not control the device.",
    }

    def mutate(data):
        data.setdefault("snapshots", []).append(snap)
        # Close the open ping if any.
        for ping in reversed(data.get("pings") or []):
            if ping.get("due") and not ping.get("submitted_at") and not ping.get("missed"):
                ping["submitted_at"] = iso()
                ping["due"] = False
                ping["snapshot_id"] = snap["id"]
                break

    store.update(mutate)
    red = (
        f"New app never approved: {', '.join(new_apps)}. Sunday will go Red."
        if new_apps
        else "No new unapproved apps in this paste."
    )
    return json.dumps({"snapshot": snap, "sunday_hint": red}, ensure_ascii=False)


@tool
def mark_ping_missed(ping_id: str = "") -> str:
    """Mark an unanswered random ask as missed. Sunday Red.

    Args:
        ping_id: Ping id, or empty to mark the open ping
    """
    found = {"id": None}

    def mutate(data):
        for ping in reversed(data.get("pings") or []):
            if ping_id and ping.get("id") != ping_id:
                continue
            if ping.get("due") and not ping.get("submitted_at"):
                ping["missed"] = True
                ping["due"] = False
                ping["missed_at"] = iso()
                found["id"] = ping.get("id")
                break

    get_store().update(mutate)
    return json.dumps({"missed": bool(found["id"]), "ping_id": found["id"]})


@tool
def write_sunday_digest(query: str = "") -> str:
    """Build the Sunday digest with only Red / Needs you / Green, then keep it on the desk.

    Args:
        query: Unused. Digest is computed from the store.
    """
    store = get_store()
    digest = build_digest(store.snapshot())
    digest["id"] = new_id("dig")

    def mutate(data):
        # Open pings become misses when Sunday runs.
        for ping in data.get("pings") or []:
            if ping.get("due") and not ping.get("submitted_at"):
                ping["missed"] = True
                ping["due"] = False
                ping["missed_at"] = iso()
        digest_full = build_digest(data)
        digest_full["id"] = digest["id"]
        digest_full["steps"] = sunday_steps(data)
        digest_full["what_changed"] = what_changed(data)
        data.setdefault("digests", []).append(digest_full)
        digest.update(digest_full)

    store.update(mutate)
    digest["steps"] = sunday_steps(store.snapshot())
    digest["what_changed"] = what_changed(store.snapshot())
    return json.dumps(digest, ensure_ascii=False)


@tool
def send_digest_message(channel: str = "whatsapp") -> str:
    """Send the latest Sunday digest as a page + a WhatsApp-shaped message (outbox).

    Args:
        channel: whatsapp | email
    """
    store = get_store()
    state = store.snapshot()
    digests = state.get("digests") or []
    if not digests:
        return json.dumps({"sent": False, "reason": "No digest on the desk. Run write_sunday_digest first."})
    latest = digests[-1]
    message = {
        "id": new_id("msg"),
        "channel": channel,
        "at": iso(),
        "to": "Meera",
        "from": "Family Loop",
        "body": latest.get("whatsapp") if channel == "whatsapp" else latest.get("letter"),
        "simulated": True,
        "label": "Simulated WhatsApp" if channel == "whatsapp" else "Simulated email",
    }

    def mutate(data):
        data.setdefault("outbox", []).append(message)

    store.update(mutate)
    return json.dumps({"sent": True, "message": message}, ensure_ascii=False)


@tool
def record_parent_decision(
    request_id: str,
    status: str,
    note: str = "",
) -> str:
    """Parent allow/deny on a pending ask. Logs an override when it disagrees with triage.

    Args:
        request_id: Request id
        status: allowed | denied
        note: Optional parent note
    """
    if status not in {"allowed", "denied"}:
        return json.dumps({"ok": False, "reason": "status must be allowed or denied"})
    found: dict[str, Any] = {}

    def mutate(data):
        for req in data.get("requests") or []:
            if req.get("id") == request_id:
                previous = req.get("triage")
                req["status"] = status
                req["decided_at"] = iso()
                req["decided_by"] = "parent"
                req["parent_note"] = note
                found.update(req)
                decision = {
                    "id": new_id("dec"),
                    "kind": req.get("kind"),
                    "subject": req.get("subject"),
                    "status": status,
                    "reason": note or req.get("reason"),
                    "at": iso(),
                    "by": "parent",
                }
                data.setdefault("decisions", []).append(decision)
                if previous and previous != status and previous != ("allow" if status == "allowed" else "deny"):
                    data.setdefault("overrides", []).append(
                        {
                            "id": new_id("ovr"),
                            "request_id": request_id,
                            "subject": req.get("subject"),
                            "status": status,
                            "triage_had": previous,
                            "note": note or f"Parent {status} {req.get('subject')} once.",
                            "at": iso(),
                        }
                    )
                break

    get_store().update(mutate)
    if not found:
        return json.dumps({"ok": False, "reason": "request not found"})
    return json.dumps({"ok": True, "request": found}, ensure_ascii=False)


@tool
def list_pending_requests(query: str = "") -> str:
    """List asks waiting on a parent yes/no.

    Args:
        query: Unused.
    """
    pending = [r for r in _state().get("requests") or [] if r.get("status") == "pending"]
    return json.dumps(pending, ensure_ascii=False)
