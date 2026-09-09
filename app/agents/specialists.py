from __future__ import annotations

from strands import Agent, tool

from app.agents.hooks import DeskGuardrails
from app.agents.model import build_model
from app.agents.tools import (
    file_child_request,
    get_family_state,
    issue_random_ping,
    list_pending_requests,
    list_recent_decisions,
    mark_ping_missed,
    record_parent_decision,
    save_family_policy,
    save_locks_checklist,
    save_screen_time_snapshot,
    send_digest_message,
    write_sunday_digest,
)

DISCLAIMER = (
    "We do not control the device. Never claim you locked a phone, uninstalled an app, "
    "or called Screen Time / Family Link APIs. Vendor feeds are simulated except the "
    "snapshot a human pasted. No silent yes on social, purchases, or new contacts."
)


def _agent(name: str, description: str, prompt: str, tools: list) -> Agent:
    return Agent(
        name=name,
        description=description,
        system_prompt=prompt,
        tools=tools,
        model=build_model(),
        callback_handler=None,
        hooks=[DeskGuardrails()],
    )


def setup_agent() -> Agent:
    return _agent(
        "setup_coach",
        "Turns parent answers into a saved Family Policy JSON and lock checklist.",
        f"""You are the setup coach for Family Loop, a family desk for Meera and Aarav in Bengaluru.
Ask only what you need: age, school hours, ask-first list, hard-no list, YouTube-after-homework,
sports-phone preset. Then call save_family_policy. For the enablement checklist, call save_locks_checklist.
Do not chat in circles. The artifact is the policy JSON.
{DISCLAIMER}""",
        [save_family_policy, save_locks_checklist, get_family_state],
    )


def checkin_agent() -> Agent:
    return _agent(
        "checkin_runner",
        "Issues Saturday and random Screen Time pings and stores pasted snapshots.",
        f"""You run Screen Time check-ins. Call issue_random_ping for a surprise ask,
save_screen_time_snapshot when a child pastes an app list, mark_ping_missed when they ignore it.
Random pings: max 1/day, 3/week, never during school hours unless the parent forced a demo ping.
{DISCLAIMER}""",
        [issue_random_ping, save_screen_time_snapshot, mark_ping_missed, get_family_state],
    )


def triage_agent() -> Agent:
    return _agent(
        "request_triage",
        "Allows, denies, or escalates a child ask against policy and last week's decisions.",
        f"""You triage child asks. Always call file_child_request. The tool applies the policy
and last week's decisions. You may explain the reason; you may not silently allow social,
a purchase, a new contact, or a new app.
{DISCLAIMER}""",
        [file_child_request, list_recent_decisions, get_family_state],
    )


def digest_agent() -> Agent:
    return _agent(
        "digest_writer",
        "Writes the Sunday Red / Needs you / Green digest and sends the WhatsApp-shaped message.",
        f"""You write Sunday. Call write_sunday_digest, then send_digest_message.
Only three sections: Red, Needs you, Green. Do not invent extra categories.
{DISCLAIMER}""",
        [write_sunday_digest, send_digest_message, get_family_state],
    )


def override_agent() -> Agent:
    return _agent(
        "override_clerk",
        "Logs parent allow/deny and one-off overrides such as Discord once.",
        f"""You are the override clerk. Call record_parent_decision. If the parent disagrees
with triage, that is an override and must be logged. The child cannot approve themselves.
{DISCLAIMER}""",
        [record_parent_decision, list_pending_requests, get_family_state],
    )


@tool
def setup_coach(query: str) -> str:
    """Setup coach: parent answers → Family Policy JSON + checklist.

    Args:
        query: Setup answers or a question about the policy.
    """
    try:
        return str(setup_agent()(query))
    except Exception as exc:
        return f"setup_coach error: {exc}"


@tool
def checkin_runner(query: str) -> str:
    """Check-in runner: Saturday file, random ping, pasted snapshots.

    Args:
        query: Ping, snapshot paste, or missed-ping instruction.
    """
    try:
        return str(checkin_agent()(query))
    except Exception as exc:
        return f"checkin_runner error: {exc}"


@tool
def request_triage(query: str) -> str:
    """Request triage: allow / deny / ask parent for a child ask.

    Args:
        query: The child's ask with kind, subject, detail.
    """
    try:
        return str(triage_agent()(query))
    except Exception as exc:
        return f"request_triage error: {exc}"


@tool
def digest_writer(query: str) -> str:
    """Digest writer: Sunday Red / Needs you / Green + outbox message.

    Args:
        query: Instruction to run or explain Sunday.
    """
    try:
        return str(digest_agent()(query))
    except Exception as exc:
        return f"digest_writer error: {exc}"


@tool
def override_clerk(query: str) -> str:
    """Override clerk: parent yes/no and one-off exceptions.

    Args:
        query: Parent decision on a pending request.
    """
    try:
        return str(override_agent()(query))
    except Exception as exc:
        return f"override_clerk error: {exc}"


def orchestrator() -> Agent:
    return Agent(
        name="family_desk",
        description="Routes new asks, pings, setup, Sunday, and overrides to specialists.",
        system_prompt=f"""You are the Family Loop desk for one family: parent Meera, child Aarav.

Route:
- first-time setup, policy, checklist → setup_coach
- Saturday file, random ping, snapshot paste → checkin_runner
- child ask (install, site, extra time, new contact) → request_triage
- Sunday / digest / WhatsApp letter → digest_writer
- parent allow/deny / override → override_clerk

Do not answer as a chatbot when a specialist should file something.
{DISCLAIMER}""",
        tools=[setup_coach, checkin_runner, request_triage, digest_writer, override_clerk],
        model=build_model(),
        callback_handler=None,
        hooks=[DeskGuardrails()],
    )
