from __future__ import annotations


def _login(client, role: str):
    if role == "parent":
        return client.post(
            "/api/login", json={"email": "meera@familyloop.demo", "password": "parent"}
        )
    return client.post(
        "/api/login", json={"email": "aarav@familyloop.demo", "password": "aarav"}
    )


def test_parent_and_child_can_edit_daily_todos(client):
    _login(client, "parent")
    added = client.post("/api/todos", json={"date": "2026-09-12", "title": "Pack cricket kit"})
    assert added.status_code == 200
    todo_id = added.json()["todo"]["id"]
    days = [d for w in added.json()["state"]["calendar"]["weeks"] for d in w]
    sat = next(d for d in days if d["date"] == "2026-09-12")
    assert any(t["title"] == "Pack cricket kit" for t in sat["todos"])

    _login(client, "child")
    ticked = client.patch(f"/api/todos/{todo_id}", json={"done": True})
    assert ticked.status_code == 200
    assert ticked.json()["todo"]["done"] is True

    deleted = client.delete(f"/api/todos/{todo_id}")
    assert deleted.status_code == 200
    leftover = [t for t in deleted.json()["state"]["todos"] if t["id"] == todo_id]
    assert leftover == []
