from __future__ import annotations

from app.calendar import family_calendar
from app.policy import policy_card, policy_from_answers
from app.store import empty_state


def test_saturday_is_yellow_submission_sunday_is_green_evaluation():
    state = empty_state()
    state["policy"] = policy_from_answers({}, state["child"])
    board = family_calendar(state, year=2026, month=9)
    saturdays = [d for week in board["weeks"] for d in week if d["in_month"] and d["weekday"] == 5]
    sundays = [d for week in board["weeks"] for d in week if d["in_month"] and d["weekday"] == 6]
    assert saturdays
    assert all("submission" in d["tags"] for d in saturdays)
    assert all(any(e["kind"] == "submission" for e in d["events"]) for d in saturdays)
    assert sundays
    assert all("evaluation" in d["tags"] for d in sundays)
    assert all(any(e["kind"] == "evaluation" for e in d["events"]) for d in sundays)


def test_eleventh_is_live_today_not_crossed(monkeypatch):
    from datetime import datetime

    from app.clock import TZ

    monkeypatch.setattr(
        "app.calendar.live_now",
        lambda: datetime(2026, 9, 11, 10, 15, tzinfo=TZ),
    )
    state = empty_state()
    board = family_calendar(state, year=2026, month=9)
    assert board["today"] == "2026-09-11"
    day = next(d for week in board["weeks"] for d in week if d["date"] == "2026-09-11")
    assert day["past"] is False
    assert "past" not in day["tags"]
    assert "today" in day["tags"]
    tenth = next(d for week in board["weeks"] for d in week if d["date"] == "2026-09-10")
    assert tenth["past"] is True


def test_past_days_are_crossed():
    state = empty_state()
    board = family_calendar(state, year=2026, month=9)
    today = board["today"]
    past = [d for week in board["weeks"] for d in week if d["in_month"] and d["date"] < today]
    future = [d for week in board["weeks"] for d in week if d["in_month"] and d["date"] > today]
    assert past
    assert all(d["past"] and "past" in d["tags"] for d in past)
    assert all(not d["past"] for d in future)


def test_policy_card_uses_parent_notes_not_json_keys():
    state = empty_state()
    policy = policy_from_answers({"age": 13, "notes": ""}, state["child"])
    card = policy_card(policy, state["child"])
    blob = " ".join(card["sentences"])
    assert "Sports-phone preset" in blob
    assert "YouTube extra time waits until after homework" in blob
    assert "ask_first" not in blob
    assert card["saved"] is True
