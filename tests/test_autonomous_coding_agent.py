import tools.autonomous_coding_agent as agent


def test_test_snapshot_uses_configured_test_command(monkeypatch):
    calls = []

    def fake_sh(*args, timeout=120):
        calls.append((args, timeout))
        return 0, "configured test pass"

    monkeypatch.setenv("AUTONOMOUS_TEST_COMMAND", "py -m pytest -q")
    monkeypatch.setattr(agent, "sh", fake_sh)

    result = agent.test_snapshot()

    assert "exit_code=0" in result
    assert calls == [(("py", "-m", "pytest", "-q"), agent.TEST_TIMEOUT)]
