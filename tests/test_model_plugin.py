from __future__ import annotations

from app.agents.roster import agents_for_event


def test_event_wakes_desk_and_specialist():
    assert agents_for_event("new_ask") == ["family_desk", "request_triage"]
    assert agents_for_event("sunday") == ["family_desk", "digest_writer"]
    assert agents_for_event("setup") == ["family_desk", "setup_coach"]


def test_ui_offers_bedrock_and_lmstudio(client):
    info = client.get("/api/model").json()
    ids = {opt["id"] for opt in info["options"]}
    assert ids == {"bedrock", "lmstudio"}
    assert len(info["agents"]) == 6


def test_selecting_lmstudio_stays_selected_without_server(client):
    ok = client.post("/api/model", json={"mode": "lmstudio", "base_url": "http://192.168.31.64:1234"})
    assert ok.status_code == 200
    assert ok.json()["mode"] == "lmstudio"


def test_ask_returns_active_agents(client):
    client.post("/api/login", json={"email": "aarav@familyloop.demo", "password": "aarav"})
    ask = client.post("/api/asks", json={"kind": "visit_site", "subject": "Reddit"})
    assert ask.status_code == 200
    agents = ask.json()["agent"]["active_agents"]
    assert "family_desk" in agents
    assert "request_triage" in agents
