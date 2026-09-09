from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FAMILY_LOOP_MODEL", "mock")
    monkeypatch.setenv("FAMILY_LOOP_DATA", str(tmp_path / "family.json"))

    import app.agents.desk as desk
    from app.seed import demo_start_state
    from app.store import reset_store

    reset_store(tmp_path / "family.json", demo_start_state())
    desk._ORCH = None

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
