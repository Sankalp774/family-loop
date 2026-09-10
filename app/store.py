from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.config import DATA_PATH

_lock = threading.RLock()
_STORE: "Store | None" = None


def empty_state() -> dict[str, Any]:
    return {
        "family_id": "sharma",
        "child": {
            "id": "aarav",
            "name": "Aarav",
            "age": 13,
            "grade": "Class 8",
            "city": "Bengaluru",
        },
        "parent": {"id": "meera", "name": "Meera"},
        "policy": None,
        "locks": {
            "screen_time_on": False,
            "ask_to_install": False,
            "youtube_supervised": False,
            "roblox_pin": False,
            "downtime_school_hours": False,
            "locks_claimed_on": None,
        },
        "requests": [],
        "snapshots": [],
        "pings": [],
        "overrides": [],
        "decisions": [],
        "digests": [],
        "outbox": [],
        "agent_log": [],
        "todos": [],
        "events": [],
        "exception_log": [],
        "clock": None,
        "disclaimer": "We do not control the device.",
    }


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(empty_state())

    def _read(self) -> dict[str, Any]:
        with self.path.open() as handle:
            return json.load(handle)

    def _write(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        tmp.replace(self.path)

    def snapshot(self) -> dict[str, Any]:
        with _lock:
            return deepcopy(self._read())

    def update(self, mutator) -> dict[str, Any]:
        with _lock:
            data = self._read()
            mutator(data)
            self._write(data)
            return deepcopy(data)

    def replace(self, data: dict[str, Any]) -> dict[str, Any]:
        with _lock:
            self._write(data)
            return deepcopy(data)

    def clock_override(self) -> str | None:
        return self.snapshot().get("clock")

    def set_clock(self, stamp: str | None) -> None:
        def mutate(data):
            data["clock"] = stamp

        self.update(mutate)

    def append(self, key: str, item: dict[str, Any]) -> dict[str, Any]:
        def mutate(data):
            data.setdefault(key, []).append(item)

        return self.update(mutate)

    def log_agent(self, entry: dict[str, Any]) -> None:
        def mutate(data):
            log = data.setdefault("agent_log", [])
            log.append(entry)
            data["agent_log"] = log[-80:]

        self.update(mutate)


def get_store() -> Store:
    global _STORE
    if _STORE is None:
        _STORE = Store(DATA_PATH)
    return _STORE


def reset_store(path: Path, data: dict[str, Any] | None = None) -> Store:
    global _STORE
    _STORE = Store(path)
    _STORE.replace(data or empty_state())
    return _STORE
