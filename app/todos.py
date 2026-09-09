from __future__ import annotations

from typing import Any

from app.clock import iso
from app.ids import new_id
from app.store import get_store


def add_todo(date: str, title: str, by: str) -> dict[str, Any]:
    text = (title or "").strip()
    if not text:
        return {"ok": False, "reason": "Write a to-do first."}
    day = (date or "")[:10]
    if len(day) != 10:
        return {"ok": False, "reason": "Pick a day on the calendar."}
    item = {
        "id": new_id("todo"),
        "date": day,
        "title": text,
        "done": False,
        "by": by,
        "created_at": iso(),
    }

    def mutate(data):
        data.setdefault("todos", []).append(item)

    get_store().update(mutate)
    return {"ok": True, "todo": item}


def patch_todo(todo_id: str, *, title: str | None = None, done: bool | None = None) -> dict[str, Any]:
    found: dict[str, Any] = {}

    def mutate(data):
        for item in data.get("todos") or []:
            if item.get("id") == todo_id:
                if title is not None:
                    item["title"] = title.strip() or item["title"]
                if done is not None:
                    item["done"] = bool(done)
                item["updated_at"] = iso()
                found.update(item)
                break

    get_store().update(mutate)
    if not found:
        return {"ok": False, "reason": "To-do not found."}
    return {"ok": True, "todo": found}


def delete_todo(todo_id: str) -> dict[str, Any]:
    removed = {"id": None}

    def mutate(data):
        before = data.get("todos") or []
        data["todos"] = [item for item in before if item.get("id") != todo_id]
        if len(data["todos"]) != len(before):
            removed["id"] = todo_id

    get_store().update(mutate)
    if not removed["id"]:
        return {"ok": False, "reason": "To-do not found."}
    return {"ok": True, "id": todo_id}
