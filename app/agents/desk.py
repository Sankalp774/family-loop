from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.model import model_label
from app.agents.specialists import orchestrator
from app.agents.tools import (
    file_child_request,
    issue_random_ping,
    record_parent_decision,
    save_family_policy,
    save_locks_checklist,
    save_screen_time_snapshot,
    send_digest_message,
    write_sunday_digest,
)
from app.clock import iso
from app.store import get_store

log = logging.getLogger("family_loop.desk")

_ORCH = None


def get_orchestrator():
    global _ORCH
    if _ORCH is None:
        _ORCH = orchestrator()
    return _ORCH


def run_desk(event: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Always go through a Strands Agent. Deterministic tools still own the store."""
    body = payload or {}
    prompt = (
        f"EVENT: {event}\n"
        f"Call the matching specialist and its tools. Do not skip the tool call.\n"
        f"PAYLOAD:\n{json.dumps(body, ensure_ascii=False)}"
    )
    agent_text = ""
    used_agent = True
    try:
        result = get_orchestrator()(prompt)
        agent_text = str(result)
    except Exception as exc:
        log.warning("orchestrator failed (%s); filing via deterministic tools", exc)
        used_agent = False
        agent_text = str(exc)
        get_store().log_agent(
            {
                "at": iso(),
                "agent": "family_desk",
                "event": event,
                "summary": f"Agent error: {exc}",
            }
        )
    if not _applied(event, body):
        filed = _fallback(event, body)
        agent_text = (agent_text + "\n" + filed).strip()
        get_store().log_agent(
            {
                "at": iso(),
                "agent": "family_desk",
                "event": event,
                "summary": "Deterministic tools filed the artifact after the agent turn.",
            }
        )
    get_store().log_agent(
        {
            "at": iso(),
            "agent": "family_desk",
            "event": event,
            "model": model_label(),
            "summary": agent_text[:400],
        }
    )
    return {
        "event": event,
        "model": model_label(),
        "used_strands": True,
        "used_agent_loop": used_agent,
        "text": agent_text,
        "state": get_store().snapshot(),
    }


def _applied(event: str, body: dict[str, Any]) -> bool:
    state = get_store().snapshot()
    if event in {"setup", "policy"}:
        return bool(state.get("policy"))
    if event == "locks":
        locks = state.get("locks") or {}
        return all(bool(locks.get(k)) == bool(body.get(k)) for k in body)
    if event in {"new_ask", "ask"}:
        subject = (body.get("subject") or "").lower()
        return any(
            (r.get("subject") or "").lower() == subject for r in state.get("requests") or []
        )
    if event == "ping":
        return bool(state.get("pings"))
    if event in {"snapshot", "saturday"}:
        return bool(state.get("snapshots"))
    if event in {"sunday", "digest"}:
        return bool(state.get("digests"))
    if event in {"override", "decide"}:
        rid = body.get("request_id")
        for req in state.get("requests") or []:
            if req.get("id") == rid:
                return req.get("status") in {"allowed", "denied"}
        return False
    return True


def _fallback(event: str, body: dict[str, Any]) -> str:
    """Same tools the specialists call, so a Bedrock outage still demos the desk."""
    if event in {"setup", "policy"}:
        return save_family_policy(
            age=int(body.get("age") or 13),
            school_start=(body.get("school_hours") or {}).get("start", "08:00"),
            school_end=(body.get("school_hours") or {}).get("end", "15:00"),
            ask_first=body.get("ask_first") or ["new_app", "new_contact", "social", "in_app_purchase"],
            hard_no=body.get("hard_no") or ["gambling", "dating"],
            youtube_after_homework=bool(body.get("youtube_after_homework", True)),
            sports_phone_preset=bool(body.get("sports_phone_preset", True)),
            daily_cap_minutes=int(body.get("daily_cap_minutes") or 120),
            notes=body.get("notes") or "",
        )
    if event == "locks":
        return save_locks_checklist(
            screen_time_on=bool(body.get("screen_time_on")),
            ask_to_install=bool(body.get("ask_to_install")),
            youtube_supervised=bool(body.get("youtube_supervised")),
            roblox_pin=bool(body.get("roblox_pin")),
            downtime_school_hours=bool(body.get("downtime_school_hours")),
        )
    if event in {"new_ask", "ask"}:
        return file_child_request(
            kind=body.get("kind") or "visit_site",
            subject=body.get("subject") or "",
            detail=body.get("detail") or "",
            costs_money=bool(body.get("costs_money")),
            kid=body.get("kid") or "aarav",
        )
    if event == "ping":
        return issue_random_ping(force=bool(body.get("force", True)))
    if event in {"snapshot", "saturday"}:
        return save_screen_time_snapshot(
            raw_list=body.get("raw_list") or "",
            kind=body.get("kind") or ("saturday" if event == "saturday" else "random"),
            kid=body.get("kid") or "aarav",
        )
    if event in {"sunday", "digest"}:
        written = write_sunday_digest("")
        email = send_digest_message("email")
        whatsapp = send_digest_message("whatsapp")
        return json.dumps(
            {
                "digest": json.loads(written),
                "email": json.loads(email),
                "whatsapp": json.loads(whatsapp),
            }
        )
    if event in {"override", "decide"}:
        return record_parent_decision(
            request_id=body.get("request_id") or "",
            status=body.get("status") or "denied",
            note=body.get("note") or "",
        )
    return json.dumps({"ok": False, "reason": f"unknown event {event}"})
