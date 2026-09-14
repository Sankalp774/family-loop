from __future__ import annotations

from app.agents.roster import agents_for_event


def test_event_wakes_desk_and_specialist():
    assert agents_for_event("new_ask") == ["family_desk", "request_triage"]
    assert agents_for_event("sunday") == ["family_desk", "digest_writer"]
    assert agents_for_event("setup") == ["family_desk", "setup_coach"]


def test_scripted_mode_is_default(client):
    health = client.get("/api/health").json()
    assert health["mode"] in {"scripted", "mock"}
    info = client.get("/api/model").json()
    assert info["mode"] == "scripted"
    ids = {opt["id"] for opt in info["options"]}
    assert {"scripted", "lmstudio", "bedrock"} <= ids
    assert len(info["agents"]) == 6


def test_switching_to_lmstudio_without_server_stays_scripted(client):
    bad = client.post("/api/model", json={"mode": "lmstudio"})
    assert bad.status_code in {503, 400}
    still = client.get("/api/model").json()
    assert still["mode"] == "scripted"


def test_ask_returns_active_agents(client):
    client.post("/api/login", json={"email": "aarav@familyloop.demo", "password": "aarav"})
    ask = client.post("/api/asks", json={"kind": "visit_site", "subject": "Reddit"})
    assert ask.status_code == 200
    agents = ask.json()["agent"]["active_agents"]
    assert "family_desk" in agents
    assert "request_triage" in agents
