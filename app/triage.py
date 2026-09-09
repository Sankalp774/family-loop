from __future__ import annotations

from typing import Any

from app.config import PURCHASE_HINTS, SOCIAL_SUBJECTS
from app.policy import approved_app_names, default_policy, norm


MUST_ASK = (
    "new app, new contact, first blocked category, or anything that costs money "
    "must wait for a parent. No silent yes on social / purchase / new contact."
)


def evaluate_request(state: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Deterministic desk. The agent may explain this, it may not override it."""
    policy = state.get("policy") or default_policy(state.get("child"))
    kind = request.get("kind") or "visit_site"
    subject = (request.get("subject") or "").strip()
    detail = (request.get("detail") or "").strip()
    costs = bool(request.get("costs_money")) or _looks_like_purchase(subject, detail)
    social = _is_social(subject, kind)
    hard_no = _hits_hard_no(policy, subject, detail)

    if hard_no:
        return {
            "action": "deny",
            "must_ask_parent": False,
            "reason": f"Hard-no list: {hard_no}. {MUST_ASK}",
        }

    if kind == "new_contact" or costs or kind == "install_app":
        return {
            "action": "ask_parent",
            "must_ask_parent": True,
            "reason": _reason(kind, subject, costs, social, "new install or money or a new person"),
        }

    if social:
        return {
            "action": "ask_parent",
            "must_ask_parent": True,
            "reason": _reason(kind, subject, costs, True, "social is never a silent yes"),
        }

    if kind == "extra_time":
        return _extra_time(policy, subject, detail, state)

    # First blocked category / unknown site
    if kind == "visit_site" and subject:
        known = approved_app_names(state)
        if norm(subject) not in known:
            return {
                "action": "ask_parent",
                "must_ask_parent": True,
                "reason": _reason(
                    kind,
                    subject,
                    costs,
                    social,
                    "first time this site/app shows up against the policy",
                ),
            }

    last_week = _similar_decision(state, kind, subject)
    if last_week == "allowed" and not social and not costs:
        return {
            "action": "allow",
            "must_ask_parent": False,
            "reason": f"Same ask as last week ({subject}) was allowed. Not social, not a purchase, not a new contact.",
        }
    if last_week == "denied":
        return {
            "action": "deny",
            "must_ask_parent": False,
            "reason": f"Same ask as last week ({subject}) was denied. Parent can override.",
        }

    return {
        "action": "ask_parent",
        "must_ask_parent": True,
        "reason": _reason(kind, subject, costs, social, "policy says ask first"),
    }


def _extra_time(policy: dict[str, Any], subject: str, detail: str, state: dict[str, Any]) -> dict[str, Any]:
    name = norm(subject)
    if policy.get("sports_phone_preset") and name in {"maps", "phone", "calls"}:
        return {
            "action": "allow",
            "must_ask_parent": False,
            "reason": "Sports-phone preset: Maps/Phone extra time is allowed. This is not a new app.",
        }
    if policy.get("youtube_after_homework") and name == "youtube" and "after homework" in detail.lower():
        return {
            "action": "allow",
            "must_ask_parent": False,
            "reason": "YouTube-after-homework is on. Extra time is allowed only because the child marked homework done. Not a new app.",
        }
    return {
        "action": "ask_parent",
        "must_ask_parent": True,
        "reason": _reason("extra_time", subject, False, _is_social(subject, "extra_time"), "over-cap extra time waits for a parent"),
    }


def _reason(kind: str, subject: str, costs: bool, social: bool, extra: str) -> str:
    bits = [f"{kind} ‘{subject}’."]
    if social:
        bits.append("Social.")
    if costs:
        bits.append("Looks like it costs money.")
    bits.append(extra + ".")
    bits.append(MUST_ASK)
    return " ".join(bits)


def _is_social(subject: str, kind: str) -> bool:
    name = norm(subject)
    if name in SOCIAL_SUBJECTS:
        return True
    if "social" in name:
        return True
    return False


def _looks_like_purchase(subject: str, detail: str) -> bool:
    blob = f"{subject} {detail}".lower()
    return any(hint in blob for hint in PURCHASE_HINTS)


def _hits_hard_no(policy: dict[str, Any], subject: str, detail: str) -> str | None:
    blob = f"{subject} {detail}".lower()
    for item in policy.get("hard_no") or []:
        token = norm(item)
        if token and token in blob:
            return item
    return None


def _similar_decision(state: dict[str, Any], kind: str, subject: str) -> str | None:
    target = (norm(kind), norm(subject))
    for row in reversed(state.get("decisions") or []):
        if (norm(row.get("kind", "")), norm(row.get("subject", ""))) == target:
            return row.get("status")
    return None
