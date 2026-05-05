from __future__ import annotations

from goal_prompt_generator import prepare_goal_prompt, validate_optimized_markdown


def test_generate_software_goal_file_has_required_contract(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prepared = prepare_goal_prompt("Build a Next.js design system with tests")

    assert prepared.file_path.parent == tmp_path
    assert prepared.file_path.name == "nextjs-design-system-tests-goal.md"
    assert prepared.file_path.exists()
    assert prepared.source_prompt_hash
    assert prepared.status == "generated"

    text = prepared.file_path.read_text()
    assert text == prepared.goal_text
    assert text.startswith("---\ngenerated_by: goal-prompt-generator")
    assert 'goal_prompt_generator_version: "1.0.1"' in text
    assert "optimized_for: hermes-agent-goal" in text
    assert "optimization_status: optimized" in text
    assert "## Non-Execution Guardrail" in text
    assert "Do not execute this prompt while generating it." in text
    assert "## Isolated Generation Boundary" in text
    assert "automatically from Hermes Agent's `/goal` command" in text
    assert "## Autonomous Execution Requirement" in text
    assert "## Software Development Constraints" in text
    assert "200 LOC maximum per file" in text
    assert "BOOTSTRAP / RED / GREEN / REFACTOR" in text
    assert validate_optimized_markdown(text).valid is True


def test_non_software_goal_keeps_autonomy_without_software_constraints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prepared = prepare_goal_prompt("Write a heartfelt poem about the ocean at sunrise")

    text = prepared.goal_text
    assert "## Autonomous Execution Requirement" in text
    assert "## Isolated Generation Boundary" in text
    assert "## Software Development Constraints" not in text
    assert 'domain: "creative-writing"' in text


def test_uncertain_prompt_uses_stricter_software_constraints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prepared = prepare_goal_prompt("Improve this")

    assert 'domain: "uncertain"' in prepared.goal_text
    assert "## Software Development Constraints" in prepared.goal_text


def test_existing_valid_generated_file_is_reused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = prepare_goal_prompt("Create a Python CLI for invoices")
    second = prepare_goal_prompt(str(first.file_path))

    assert second.status == "reused"
    assert second.file_path == first.file_path
    assert second.goal_text == first.goal_text
    assert second.title == first.title
    assert len(list(tmp_path.glob("*.md"))) == 1


def test_invalid_generated_file_is_regenerated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    broken = tmp_path / "broken-goal.md"
    broken.write_text("---\ngenerated_by: goal-prompt-generator\n---\n# Missing sections\n")

    prepared = prepare_goal_prompt(str(broken))

    assert prepared.status == "regenerated"
    assert prepared.file_path != broken
    assert prepared.file_path.exists()
    assert "## Acceptance Criteria" in prepared.goal_text

    incomplete = prepared.goal_text.replace('goal_prompt_generator_version: "1.0.1"\n', "")
    validation = validate_optimized_markdown(incomplete)
    assert not validation.valid
    assert any("goal_prompt_generator_version" in reason for reason in validation.reasons)


def test_filename_collisions_append_numeric_suffix(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = prepare_goal_prompt("Build a Stripe credit system")
    second = prepare_goal_prompt("Build a Stripe credit system")

    assert first.file_path.name == "stripe-credit-system-goal.md"
    assert second.file_path.name == "stripe-credit-system-goal-2.md"
