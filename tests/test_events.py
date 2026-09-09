from __future__ import annotations


def _login(client, role: str):
    if role == "parent":
        return client.post(
            "/api/login", json={"email": "meera@familyloop.demo", "password": "parent"}
        )
    return client.post(
        "/api/login", json={"email": "aarav@familyloop.demo", "password": "aarav"}
    )


def _items_on(state, day: str):
    days = [d for w in state["calendar"]["weeks"] for d in w]
    cell = next(d for d in days if d["date"] == day)
    return cell["items"]


def test_parent_creates_important_event_child_can_edit(client):
    _login(client, "parent")
    created = client.post(
        "/api/events",
        json={
            "title": "Dentist",
            "date": "2026-09-15",
            "all_day": False,
            "start_time": "10:00",
            "end_time": "10:30",
            "calendar": "important",
            "who": "child",
            "important": True,
        },
    )
    assert created.status_code == 200
    event_id = created.json()["event"]["id"]
    titles = [i["title"] for i in _items_on(created.json()["state"], "2026-09-15")]
    assert "Dentist" in titles

    _login(client, "child")
    patched = client.patch(
        f"/api/events/{event_id}",
        json={"title": "Dentist — Aarav", "start_time": "10:15", "end_time": "10:45", "all_day": False, "date": "2026-09-15"},
    )
    assert patched.status_code == 200
    assert patched.json()["event"]["title"] == "Dentist — Aarav"

    deleted = client.delete(f"/api/events/{event_id}")
    assert deleted.status_code == 200
    titles = [i["title"] for i in _items_on(deleted.json()["state"], "2026-09-15")]
    assert "Dentist — Aarav" not in titles


def test_weekly_repeat_expands_through_the_month(client):
    _login(client, "parent")
    created = client.post(
        "/api/events",
        json={
            "title": "Piano",
            "date": "2026-09-07",
            "all_day": False,
            "start_time": "17:00",
            "end_time": "17:45",
            "calendar": "personal",
            "repeat": "weekly",
            "repeat_until": "2026-09-30",
        },
    )
    assert created.status_code == 200
    days = [d for w in created.json()["state"]["calendar"]["weeks"] for d in w if d["in_month"]]
    piano_days = [d["date"] for d in days if any(i["title"] == "Piano" for i in d["items"])]
    assert "2026-09-07" in piano_days
    assert "2026-09-14" in piano_days
    assert "2026-09-21" in piano_days
    assert "2026-09-28" in piano_days
