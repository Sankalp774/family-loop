from __future__ import annotations


def test_parent_can_edit_family_and_asks(client):
    client.post("/api/login", json={"email": "meera@familyloop.demo", "password": "parent"})
    family = client.patch(
        "/api/family",
        json={"parent_name": "Meera Sharma", "child_name": "Aarav Sharma", "city": "Bengaluru"},
    )
    assert family.status_code == 200
    assert family.json()["state"]["parent"]["name"] == "Meera Sharma"
    assert family.json()["state"]["child"]["name"] == "Aarav Sharma"

    setup = client.post(
        "/api/setup",
        json={
            "age": 13,
            "approved_apps": ["YouTube", "WhatsApp", "Chess"],
            "sports_days": [2, 4],
            "child_name": "Aarav Sharma",
        },
    )
    assert setup.status_code == 200
    assert "Chess" in setup.json()["state"]["policy"]["approved_apps"]
    assert setup.json()["state"]["policy"]["sports_days"] == [2, 4]

    ask = client.post("/api/asks", json={"kind": "visit_site", "subject": "Reddit", "detail": "homework"})
    req_id = ask.json()["state"]["requests"][-1]["id"]
    patched = client.patch(
        f"/api/asks/{req_id}",
        json={"subject": "Reddit programming", "parent_note": "After homework only", "status": "allowed"},
    )
    assert patched.status_code == 200
    row = next(r for r in patched.json()["state"]["requests"] if r["id"] == req_id)
    assert row["subject"] == "Reddit programming"
    assert row["parent_note"] == "After homework only"

    letter = client.post("/api/outbox", json={"channel": "whatsapp", "body": "Sunday is quiet."})
    assert letter.status_code == 200
    assert letter.json()["state"]["outbox"][-1]["body"] == "Sunday is quiet."
