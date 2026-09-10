from __future__ import annotations

from app.digest import build_digest
from app.intelligence import family_state, request_history
from app.policy import policy_from_answers
from app.store import empty_state
from app.triage import evaluate_request


def test_child_cannot_approve_own_request(client):
    client.post("/api/login", json={"email": "aarav@familyloop.demo", "password": "aarav"})
    ask = client.post("/api/asks", json={"kind": "visit_site", "subject": "Reddit", "detail": "learn"})
    req_id = ask.json()["state"]["requests"][-1]["id"]
    denied = client.post(f"/api/asks/{req_id}/decide", json={"status": "allowed"})
    assert denied.status_code == 403


def test_model_cannot_bypass_must_ask_on_repeated_reddit():
    state = empty_state()
    state["policy"] = policy_from_answers({}, state["child"])
    state["requests"] = [
        {"subject": "Reddit", "kind": "visit_site", "status": "pending", "filed_at": "2026-09-06T10:00:00+05:30"}
        for _ in range(3)
    ]
    state["decisions"] = [{"kind": "visit_site", "subject": "Reddit", "status": "allowed"}]
    verdict = evaluate_request(state, {"kind": "visit_site", "subject": "Reddit", "detail": "again"})
    assert verdict["action"] == "ask_parent"
    assert verdict["must_ask_parent"] is True
    hist = request_history(state, "Reddit")
    assert hist["requests"] == 3


def test_override_is_recorded(client):
    client.post("/api/login", json={"email": "meera@familyloop.demo", "password": "parent"})
    client.post("/api/setup", json={"age": 13})
    client.post("/api/login", json={"email": "aarav@familyloop.demo", "password": "aarav"})
    ask = client.post("/api/asks", json={"kind": "visit_site", "subject": "Reddit"})
    req_id = [r for r in ask.json()["state"]["requests"] if r["subject"] == "Reddit"][-1]["id"]
    client.post("/api/login", json={"email": "meera@familyloop.demo", "password": "parent"})
    decided = client.post(f"/api/asks/{req_id}/decide", json={"status": "allowed", "note": "Once."})
    assert decided.status_code == 200
    assert decided.json()["state"]["overrides"]


def test_new_app_creates_exception(client):
    client.post("/api/login", json={"email": "meera@familyloop.demo", "password": "parent"})
    client.post("/api/setup", json={"age": 13})
    client.post("/api/demo/simulate-saturday")
    cmd = client.get("/api/me").json()["state"]["command"]
    assert cmd["exceptions"] >= 1
    assert any(i["title"] == "Discord" for i in cmd["needs_you"])


def test_sunday_digest_is_deterministic():
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
        {"id": "req_reddit", "kind": "visit_site", "subject": "Reddit", "status": "pending", "reason": "social"}
    ]
    a = build_digest(state)
    b = build_digest(state)
    assert [i["code"] for i in a["red"]] == [i["code"] for i in b["red"]]
    assert [i["title"] for i in a["needs_you"]] == [i["title"] for i in b["needs_you"]]


def test_failed_agent_still_files_ask(client, monkeypatch):
    client.post("/api/login", json={"email": "aarav@familyloop.demo", "password": "aarav"})

    def boom(*_a, **_k):
        raise RuntimeError("bedrock down")

    monkeypatch.setattr("app.agents.desk.get_orchestrator", lambda: boom)
    ask = client.post("/api/asks", json={"kind": "visit_site", "subject": "Reddit", "detail": "learn"})
    assert ask.status_code == 200
    pending = [r for r in ask.json()["state"]["requests"] if r["subject"] == "Reddit"]
    assert pending
    assert pending[-1]["status"] == "pending"


def test_fast_forward_matches_live_simulation(client):
    client.post("/api/login", json={"email": "meera@familyloop.demo", "password": "parent"})
    client.post("/api/setup", json={"age": 13})
    client.post("/api/asks", json={"kind": "visit_site", "subject": "Reddit"})
    live = client.post("/api/demo/simulate-saturday")
    assert live.status_code == 200
    live_exc = live.json()["state"]["command"]["exceptions"]
    client.post("/api/demo/reset")
    client.post("/api/setup", json={"age": 13})
    client.post("/api/asks", json={"kind": "visit_site", "subject": "Reddit"})
    ff = client.post("/api/demo/fast-forward")
    assert ff.json()["state"]["command"]["exceptions"] == live_exc
    assert ff.json()["state"]["latest_digest"]
