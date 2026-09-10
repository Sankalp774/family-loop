from __future__ import annotations

from app.intelligence import family_state, request_history, timeline, what_changed
from app.policy import policy_from_answers
from app.store import empty_state


def test_request_history_counts_repeats():
    state = empty_state()
    state["requests"] = [
        {"subject": "Reddit", "status": "pending", "filed_at": "2026-09-06T18:00:00+05:30"},
        {"subject": "Reddit", "status": "pending", "filed_at": "2026-09-08T18:00:00+05:30"},
        {"subject": "Reddit", "status": "pending", "filed_at": "2026-09-10T18:00:00+05:30"},
    ]
    hist = request_history(state, "Reddit")
    assert hist["requests"] == 3
    assert hist["first_requested"] == "2026-09-06"
    assert hist["current_status"] == "pending"


def test_family_state_flags_waiting_and_discord():
    state = empty_state()
    state["policy"] = policy_from_answers({}, state["child"])
    state["requests"] = [
        {"id": "req_r", "subject": "Reddit", "kind": "visit_site", "status": "pending", "filed_at": "2026-09-08T18:00:00+05:30", "reason": "social"}
    ]
    state["snapshots"] = [
        {"date": "2026-09-12", "kind": "saturday", "apps": [{"name": "Discord", "minutes": 25}], "new_unapproved": ["Discord"]}
    ]
    cmd = family_state(state)
    assert cmd["decisions_waiting"] == 1
    assert cmd["exceptions"] == 1
    assert cmd["health_tone"] == "red"
    titles = [i["title"] for i in cmd["needs_you"]]
    assert "Discord" in titles
    assert "Reddit" in titles


def test_timeline_and_what_changed_are_visible_memory():
    state = empty_state()
    state["requests"] = [
        {"subject": "Reddit", "kind": "visit_site", "status": "pending", "filed_at": "2026-09-08T18:22:00+05:30"}
    ]
    state["snapshots"] = [
        {"date": "2026-09-12", "apps": [{"name": "YouTube", "minutes": 40}], "new_unapproved": []}
    ]
    days = timeline(state)
    assert days
    changed = what_changed(state)
    assert "summary" in changed


def test_parent_can_resolve_discord_exception(client):
    client.post("/api/login", json={"email": "meera@familyloop.demo", "password": "parent"})
    client.post("/api/setup", json={"age": 13})
    client.post("/api/demo/simulate-saturday")
    before = client.get("/api/me").json()["state"]["command"]
    assert before["exceptions"] >= 1
    child = client.post("/api/login", json={"email": "aarav@familyloop.demo", "password": "aarav"})
    blocked = client.post("/api/exceptions", json={"subject": "Discord", "status": "allowed"})
    assert blocked.status_code == 403
    client.post("/api/login", json={"email": "meera@familyloop.demo", "password": "parent"})
    allowed = client.post("/api/exceptions", json={"subject": "Discord", "status": "allowed"})
    assert allowed.status_code == 200
    assert allowed.json()["state"]["command"]["exceptions"] == 0
    assert "Discord" in allowed.json()["state"]["policy"]["approved_apps"]


def test_fast_forward_detects_discord(client):
    client.post("/api/login", json={"email": "meera@familyloop.demo", "password": "parent"})
    client.post("/api/setup", json={"age": 13})
    client.post(
        "/api/asks",
        json={"kind": "visit_site", "subject": "Reddit", "detail": "learn python"},
    )
    run = client.post("/api/demo/fast-forward")
    assert run.status_code == 200
    blob = " ".join(s["text"] for s in run.json()["steps"])
    assert "Discord" in blob
    digest = run.json()["state"]["latest_digest"]
    red = " ".join(i["title"] + i["detail"] for i in digest["red"])
    assert "Discord" in red
    assert digest.get("what_changed") or run.json()["state"].get("what_changed")
