from app.agents.specialists import orchestrator


def test_orchestrator_is_a_strands_agent_with_specialists():
    desk = orchestrator()
    names = set(desk.tool_names)
    assert "setup_coach" in names
    assert "request_triage" in names
    assert "checkin_runner" in names
    assert "digest_writer" in names
    assert "override_clerk" in names
