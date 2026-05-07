from __future__ import annotations

from types import SimpleNamespace

from goal_prompt_generator.research import _firecrawl_auth, research_evidence


def test_research_evidence_records_available_tools(tmp_path, monkeypatch):
    maps = tmp_path / "research" / "url-maps"
    maps.mkdir(parents=True)
    (maps / "claude-code.json").write_text(
        '{"success": true, "data": {"links": [{"url": "https://code.claude.com/docs/en/worktrees"}]}}',
        encoding="utf-8",
    )

    def command_path(name: str) -> str:
        return f"/bin/{name}"

    def command_result(args, capture_output, text, timeout):
        command = " ".join(args)
        if command == "firecrawl --version":
            return SimpleNamespace(returncode=0, stdout="1.16.0\n", stderr="")
        if command == "firecrawl --status":
            return SimpleNamespace(returncode=0, stdout="Authenticated via FIRECRAWL_API_KEY\n", stderr="")
        if command == "opensrc --version":
            return SimpleNamespace(returncode=0, stdout="opensrc 0.7.2\n", stderr="")
        raise AssertionError(command)

    monkeypatch.setattr("goal_prompt_generator.research.shutil.which", command_path)
    monkeypatch.setattr("goal_prompt_generator.research.subprocess.run", command_result)

    evidence = research_evidence(tmp_path)

    assert evidence["firecrawl"]["cli_version"] == "1.16.0"
    assert evidence["firecrawl"]["auth"] == "authenticated"
    assert evidence["opensrc"]["cli_version"] == "unavailable"
    assert evidence["opensrc"]["cache_root"]
    assert evidence["opensrc"]["divergences"]


def test_research_evidence_records_unavailable_tools(tmp_path, monkeypatch):
    monkeypatch.setattr("goal_prompt_generator.research.shutil.which", lambda name: None)

    evidence = research_evidence(tmp_path)

    assert evidence["firecrawl"]["cli_version"] == "unavailable"
    assert evidence["firecrawl"]["auth"] == "unavailable"
    assert evidence["opensrc"]["cli_version"] == "unavailable"


def test_firecrawl_auth_downgrades_on_live_http_rst_markers():
    clean = "Authenticated via FIRECRAWL_API_KEY\n"
    assert _firecrawl_auth(clean) == "authenticated"
    for marker in ("ECONNRESET", "Connection reset", "fetch failed", "Could not fetch"):
        banner = f"Authenticated via FIRECRAWL_API_KEY\nlive probe: {marker} on api.firecrawl.dev\n"
        assert _firecrawl_auth(banner) == "unavailable", marker
    assert _firecrawl_auth("missing key") == "unavailable"
    assert _firecrawl_auth("") == "unavailable"


def test_firecrawl_evidence_downgrades_authenticated_without_cached_maps(tmp_path, monkeypatch):
    monkeypatch.setattr("goal_prompt_generator.research.shutil.which", lambda name: f"/bin/{name}")

    def command_result(args, capture_output, text, timeout):
        cmd = " ".join(args)
        if cmd == "firecrawl --version":
            return SimpleNamespace(returncode=0, stdout="1.16.0\n", stderr="")
        if cmd == "firecrawl --status":
            return SimpleNamespace(returncode=0, stdout="Authenticated via FIRECRAWL_API_KEY\n", stderr="")
        if cmd == "opensrc --version":
            return SimpleNamespace(returncode=0, stdout="opensrc 0.7.2\n", stderr="")
        raise AssertionError(cmd)

    monkeypatch.setattr("goal_prompt_generator.research.subprocess.run", command_result)
    evidence = research_evidence(tmp_path)
    assert evidence["firecrawl"]["auth"] == "unavailable"
    assert evidence["firecrawl"]["required_maps_present"] == {}


def test_firecrawl_evidence_uses_downgrade_helper(tmp_path, monkeypatch):
    monkeypatch.setattr("goal_prompt_generator.research.shutil.which", lambda name: f"/bin/{name}")

    def command_result(args, capture_output, text, timeout):
        cmd = " ".join(args)
        if cmd == "firecrawl --version":
            return SimpleNamespace(returncode=0, stdout="1.16.0\n", stderr="")
        if cmd == "firecrawl --status":
            return SimpleNamespace(returncode=0, stdout="Authenticated via FIRECRAWL_API_KEY\nfetch failed: ECONNRESET\n", stderr="")
        if cmd == "opensrc --version":
            return SimpleNamespace(returncode=0, stdout="opensrc 0.7.2\n", stderr="")
        raise AssertionError(cmd)

    monkeypatch.setattr("goal_prompt_generator.research.subprocess.run", command_result)
    evidence = research_evidence(tmp_path)
    assert evidence["firecrawl"]["auth"] == "unavailable"
