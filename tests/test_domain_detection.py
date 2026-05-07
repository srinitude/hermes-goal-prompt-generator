from __future__ import annotations

from goal_prompt_generator import prepare_goal_prompt


def test_hermes_daytona_migration_is_software_development_goal(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    prepared = prepare_goal_prompt("plan for moving my entire hermes setup to daytona")

    assert 'domain: "software-development"' in prepared.goal_text
    assert 'domain_confidence: "high"' in prepared.goal_text
    assert "## Software Development Constraints" in prepared.goal_text
    assert "At the end of the goal execution, perform a ruthless cleanup pass" in prepared.goal_text
    assert "## Software Engineering Core Principles" in prepared.goal_text
