from __future__ import annotations


def _login(client, role: str):
    if role == "parent":
        return client.post(
            "/api/login", json={"email": "meera@familyloop.demo", "password": "parent"}
        )
    return client.post(
        "/api/login", json={"email": "aarav@familyloop.demo", "password": "aarav"}
    )


def test_child_cannot_write_policy(client):
    _login(client, "child")
    res = client.post("/api/setup", json={"age": 13})
    assert res.status_code == 403


def test_demo_script_sunday_climax(client):
    """Video path: setup → Reddit pending → Discord paste → ignore → Sunday."""
    parent = _login(client, "parent")
    assert parent.status_code == 200

    setup = client.post(
        "/api/setup",
        json={
            "age": 13,
            "school_hours": {"start": "08:00", "end": "15:00"},
            "ask_first": ["new_app", "new_contact", "social"],
            "hard_no": ["gambling"],
            "youtube_after_homework": True,
            "sports_phone_preset": True,
            "daily_cap_minutes": 120,
        },
    )
    assert setup.status_code == 200
    assert setup.json()["state"]["policy"]["age"] == 13

    locks = client.post(
        "/api/locks",
        json={
            "screen_time_on": True,
            "ask_to_install": True,
            "youtube_supervised": True,
            "roblox_pin": True,
            "downtime_school_hours": True,
        },
    )
    assert locks.status_code == 200
    assert locks.json()["state"]["locks_complete"] is True

    child = _login(client, "child")
    assert child.status_code == 200
    ask = client.post(
        "/api/asks",
        json={
            "kind": "visit_site",
            "subject": "Reddit",
            "detail": "r/learnpython",
            "costs_money": False,
        },
    )
    assert ask.status_code == 200
    pending = [r for r in ask.json()["state"]["requests"] if r["status"] == "pending"]
    assert pending
    assert pending[0]["subject"] == "Reddit"

    _login(client, "parent")
    sat = client.post("/api/demo/saturday")
    assert sat.status_code == 200
    ping = client.post("/api/ping")
    assert ping.status_code == 200
    assert ping.json()["state"]["open_ping"]

    _login(client, "child")
    snap = client.post(
        "/api/checkin",
        json={"raw_list": "YouTube 40\nDiscord 25\nWhatsApp 12", "kind": "random"},
    )
    assert snap.status_code == 200
    latest = snap.json()["state"]["snapshots"][-1]
    assert "Discord" in latest["new_unapproved"]

    # Parent ignores Reddit on purpose.
    _login(client, "parent")
    client.post("/api/demo/sunday")
    digest = client.post("/api/digest")
    assert digest.status_code == 200
    board = digest.json()["state"]["latest_digest"]
    red_blob = " ".join(item["title"] + " " + item["detail"] for item in board["red"])
    needs_blob = " ".join(item["title"] for item in board["needs_you"])
    assert "Discord" in red_blob
    assert "Reddit" in red_blob
    assert "Reddit" in needs_blob
    assert digest.json()["state"]["outbox"]
    assert "We do not control the device" in board["disclaimer"]
