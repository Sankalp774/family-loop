from __future__ import annotations

from typing import Any

from app.config import (
    ASK_FIRST_CHOICES,
    HARD_NO_CHOICES,
    LOCK_ITEMS,
    PARENT_NOTE_DEFAULT,
)
from app.clock import iso


DEFAULT_ASK_FIRST = [
    "new_app",
    "new_contact",
    "social",
    "in_app_purchase",
    "extra_time_over_cap",
]
DEFAULT_HARD_NO = ["gambling", "dating", "unsupervised_late_night_youtube"]


def default_policy(child: dict[str, Any] | None = None) -> dict[str, Any]:
    kid = child or {"id": "aarav", "name": "Aarav", "age": 13}
    return {
        "child_id": kid.get("id", "aarav"),
        "child_name": kid.get("name", "Aarav"),
        "age": int(kid.get("age") or 13),
        "school_hours": {"start": "08:00", "end": "15:00", "days": [0, 1, 2, 3, 4]},
        "ask_first": list(DEFAULT_ASK_FIRST),
        "hard_no": list(DEFAULT_HARD_NO),
        "youtube_after_homework": True,
        "sports_phone_preset": True,
        "daily_cap_minutes": 120,
        "approved_apps": [
            "YouTube",
            "WhatsApp",
            "Khan Academy",
            "Google Classroom",
            "Maps",
            "Phone",
        ],
        "notes": PARENT_NOTE_DEFAULT,
        "sports_days": [1, 3],
        "sports_hours": {"start": "16:30", "end": "18:00"},
        "homework_done_after": "17:00",
        "written_at": iso(),
        "written_by": "setup_coach",
    }


def policy_from_answers(answers: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    base = default_policy(child)
    if answers.get("age"):
        base["age"] = int(answers["age"])
    school = answers.get("school_hours") or {}
    if school.get("start"):
        base["school_hours"]["start"] = school["start"]
    if school.get("end"):
        base["school_hours"]["end"] = school["end"]
    if answers.get("ask_first"):
        base["ask_first"] = list(answers["ask_first"])
    if answers.get("hard_no"):
        base["hard_no"] = list(answers["hard_no"])
    if "youtube_after_homework" in answers:
        base["youtube_after_homework"] = bool(answers["youtube_after_homework"])
    if "sports_phone_preset" in answers:
        base["sports_phone_preset"] = bool(answers["sports_phone_preset"])
    if answers.get("daily_cap_minutes"):
        base["daily_cap_minutes"] = int(answers["daily_cap_minutes"])
    if "approved_apps" in answers and answers["approved_apps"] is not None:
        apps = [str(item).strip() for item in answers["approved_apps"] if str(item).strip()]
        if apps:
            base["approved_apps"] = apps
    if answers.get("sports_days") is not None:
        base["sports_days"] = [int(d) for d in answers["sports_days"]]
    sports_hours = answers.get("sports_hours") or {}
    if sports_hours.get("start"):
        base["sports_hours"]["start"] = sports_hours["start"]
    if sports_hours.get("end"):
        base["sports_hours"]["end"] = sports_hours["end"]
    if answers.get("homework_done_after"):
        base["homework_done_after"] = answers["homework_done_after"]
    if answers.get("child_name"):
        base["child_name"] = answers["child_name"]
    if answers.get("notes"):
        base["notes"] = answers["notes"]
    else:
        base["notes"] = PARENT_NOTE_DEFAULT
    base["written_at"] = iso()
    return base


def _label(choices: list[dict[str, str]], key: str) -> str:
    for item in choices:
        if item["key"] == key:
            return item["label"]
    return key.replace("_", " ")


def policy_card(policy: dict[str, Any] | None, child: dict[str, Any] | None = None) -> dict[str, Any]:
    """Plain-language house rules. Parents should never have to read JSON."""
    kid = (child or {}).get("name") or (policy or {}).get("child_name") or "Aarav"
    if not policy:
        return {
            "saved": False,
            "headline": f"No house rules on file for {kid} yet.",
            "sentences": [
                "Fill the form in everyday words. The desk writes the policy for you.",
                PARENT_NOTE_DEFAULT,
            ],
            "ask_first": [],
            "hard_no": [],
            "notes": PARENT_NOTE_DEFAULT,
            "apps": [],
        }
    school = policy.get("school_hours") or {}
    cap = int(policy.get("daily_cap_minutes") or 120)
    hours = cap / 60
    cap_words = f"{cap} minutes" if cap % 60 else f"{int(hours)} hour" + ("s" if hours != 1 else "")
    ask = [_label(ASK_FIRST_CHOICES, k) for k in policy.get("ask_first") or []]
    hard = [_label(HARD_NO_CHOICES, k) for k in policy.get("hard_no") or []]
    sentences = [
        f"{kid} is {policy.get('age')}.",
        f"School is {school.get('start', '08:00')}–{school.get('end', '15:00')} on weekdays. We will not ping during class.",
        f"Ask you first for: {', '.join(ask) or 'nothing extra'}." ,
        f"Never allowed: {', '.join(hard) or 'nothing listed'}.",
    ]
    if policy.get("youtube_after_homework"):
        after = policy.get("homework_done_after") or "17:00"
        sentences.append(f"YouTube extra time waits until after homework ({after}).")
    else:
        sentences.append("YouTube extra time still needs a yes from you.")
    if policy.get("sports_phone_preset"):
        days = policy.get("sports_days") or [1, 3]
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        named = ", ".join(day_names[d] for d in days if 0 <= d < 7)
        hours_s = policy.get("sports_hours") or {"start": "16:30", "end": "18:00"}
        sentences.append(
            f"Sports-phone: Maps and Phone extra time is allowed at practice ({named} {hours_s.get('start')}–{hours_s.get('end')})."
        )
    sentences.append(f"Daily screen-time cap is {cap_words} (from the pasted list, not from the phone OS).")
    if policy.get("notes"):
        sentences.append(policy["notes"])
    sentences.append("We do not control the device. These are house rules for the inbox.")
    return {
        "saved": True,
        "headline": f"House rules for {kid}",
        "sentences": sentences,
        "ask_first": ask,
        "hard_no": hard,
        "notes": policy.get("notes") or PARENT_NOTE_DEFAULT,
        "apps": policy.get("approved_apps") or [],
        "school": school,
        "age": policy.get("age"),
        "youtube_after_homework": bool(policy.get("youtube_after_homework")),
        "sports_phone_preset": bool(policy.get("sports_phone_preset")),
        "daily_cap_minutes": cap,
    }


def locks_complete(locks: dict[str, Any]) -> bool:
    return all(bool(locks.get(item["key"])) for item in LOCK_ITEMS)


def approved_app_names(state: dict[str, Any]) -> set[str]:
    policy = state.get("policy") or default_policy(state.get("child"))
    names = {norm(name) for name in policy.get("approved_apps", [])}
    for decision in state.get("decisions", []):
        if decision.get("status") == "allowed" and decision.get("subject"):
            names.add(norm(decision["subject"]))
    for override in state.get("overrides", []):
        if override.get("status") == "allowed" and override.get("subject"):
            names.add(norm(override["subject"]))
    return names


def norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())
