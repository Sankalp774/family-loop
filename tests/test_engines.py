from __future__ import annotations

from app.digest import build_digest
from app.policy import policy_from_answers
from app.snapshots import diff_new_unapproved, parse_app_list
from app.store import empty_state
from app.triage import evaluate_request


def test_reddit_is_never_a_silent_yes():
    state = empty_state()
    state["policy"] = policy_from_answers({"age": 13}, state["child"])
    verdict = evaluate_request(
        state, {"kind": "visit_site", "subject": "Reddit", "detail": "learn python"}
    )
    assert verdict["action"] == "ask_parent"
    assert verdict["must_ask_parent"] is True


def test_new_contact_and_money_ask_parent():
    state = empty_state()
    state["policy"] = policy_from_answers({}, state["child"])
    contact = evaluate_request(
        state, {"kind": "new_contact", "subject": "roblox_user_99", "detail": "squad"}
    )
    money = evaluate_request(
        state,
        {
            "kind": "install_app",
            "subject": "SomeGame",
            "detail": "needs Robux",
            "costs_money": True,
        },
    )
    assert contact["action"] == "ask_parent"
    assert money["action"] == "ask_parent"


def test_sports_phone_preset_allows_maps():
    state = empty_state()
    state["policy"] = policy_from_answers({"sports_phone_preset": True}, state["child"])
    verdict = evaluate_request(state, {"kind": "extra_time", "subject": "Maps"})
    assert verdict["action"] == "allow"


def test_snapshot_reads_hours_from_ocr_style_list():
    apps = parse_app_list("YouTube\n1h 12m\nWhatsApp 45m\nDiscord 30")
    by_name = {a["name"]: a["minutes"] for a in apps}
    assert by_name["YouTube"] == 72
    assert by_name["WhatsApp"] == 45
    assert by_name["Discord"] == 30


def test_snapshot_flags_discord():
    state = empty_state()
    state["policy"] = policy_from_answers({}, state["child"])
    apps = parse_app_list("YouTube 40\nDiscord 25\nWhatsApp 10")
    new = diff_new_unapproved(state, apps)
    assert "Discord" in new
    assert "YouTube" not in new


def test_digest_red_discord_and_ignored_reddit():
    state = empty_state()
    state["policy"] = policy_from_answers({}, state["child"])
    state["locks"] = {
        "screen_time_on": True,
        "ask_to_install": True,
        "youtube_supervised": True,
        "roblox_pin": True,
        "downtime_school_hours": True,
        "locks_claimed_on": "2026-09-06",
    }
    state["snapshots"] = [
        {
            "kind": "saturday",
            "date": "2026-09-06",
            "apps": [{"name": "Discord", "minutes": 25}],
            "new_unapproved": ["Discord"],
        }
    ]
    state["requests"] = [
        {
            "id": "req_reddit",
            "kind": "visit_site",
            "subject": "Reddit",
            "status": "pending",
            "reason": "social",
        }
    ]
    digest = build_digest(state)
    red_codes = {item["code"] for item in digest["red"]}
    assert "unapproved_new_app" in red_codes
    assert "ignored_ask" in red_codes
    assert any("Reddit" in item["title"] for item in digest["needs_you"])
    assert "Discord" in digest["letter"]
