from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from goal_prompt_generator import build_optimized_markdown, prepare_goal_prompt, validate_optimized_markdown

CLEANUP_REQUIREMENT = "At the end of the goal execution, perform a ruthless cleanup pass over the final diff. Remove every code change, file change, configuration change, dependency change, test change, documentation change, or generated artifact that is unrelated, incidental, speculative, exploratory, redundant, or extraneous to the successful completion of the approved goal. The final submitted change set must contain only the minimum necessary changes required to satisfy the goal and its validation criteria. If the goal is executed within a brownfield codebase, preserve the repository’s existing intent, architecture, conventions, abstractions, naming patterns, style, behavior, public contracts, tests, workflows, and integration assumptions unless the approved goal explicitly requires changing them. Before marking the goal complete, verify that the final change set does not introduce regressions, does not conflict with the surrounding repository context, does not degrade existing behavior, and does not leave behind temporary implementation scaffolding, abandoned experiments, dead code, unused dependencies, unused exports, debug logs, placeholder logic, TODOs, mocks, stubs, or broad refactors that are not required by the goal. If a change was made during execution but is not necessary for the final validated solution, revert it before completion."
PRINCIPLE_MARKERS = [
    "## Software Engineering Core Principles",
    "Treat programs as descriptions before execution",
    "Make expected failure part of the domain model",
    "Use structured concurrency instead of ad hoc async work",
    "Can every operation state its success type, expected failures, dependencies, and side effects?",
    "Engineer software as explicit, typed, observable, cancellable, resource-safe workflows",
]
BUILTIN_SRC = Path(os.environ.get("GOAL_PROMPT_GENERATOR_BUILTIN_SRC", "/Users/kiren/.hermes/skills/software-development/goal-prompt-generator/src"))


def builtin_markdown(prompt: str, now: datetime) -> str:
    if not BUILTIN_SRC.exists():
        pytest.skip(f"built-in goal-prompt-generator source not found: {BUILTIN_SRC}")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BUILTIN_SRC) + os.pathsep + env.get("PYTHONPATH", "")
    code = """
import json
import sys
from datetime import datetime
from goal_prompt_generator import build_optimized_markdown

print(json.dumps(build_optimized_markdown(sys.argv[1], datetime.fromisoformat(sys.argv[2]))))
"""
    result = subprocess.run(
        [sys.executable, "-c", code, prompt, now.isoformat()],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(result.stdout)


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
    assert 'goal_prompt_generator_version: "1.3.0"' in text
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
    assert CLEANUP_REQUIREMENT in text
    assert all(marker in text for marker in PRINCIPLE_MARKERS)
    assert validate_optimized_markdown(text).valid is True


def test_non_software_goal_keeps_autonomy_without_software_constraints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prepared = prepare_goal_prompt("Write a heartfelt poem about the ocean at sunrise")

    text = prepared.goal_text
    assert "## Autonomous Execution Requirement" in text
    assert "## Isolated Generation Boundary" in text
    assert "## Software Development Constraints" not in text
    assert CLEANUP_REQUIREMENT not in text
    assert all(marker not in text for marker in PRINCIPLE_MARKERS)
    assert 'domain: "creative-writing"' in text


def test_built_in_and_shareable_outputs_match_for_software_prompt():
    prompt = "Add pytest coverage for the package CLI"
    now = datetime(2026, 5, 5, 19, 30, tzinfo=timezone.utc)

    shareable = build_optimized_markdown(prompt, now)
    builtin = builtin_markdown(prompt, now)

    assert shareable == builtin
    assert CLEANUP_REQUIREMENT in shareable
    assert all(marker in shareable for marker in PRINCIPLE_MARKERS)
    assert "200 LOC maximum per file" in shareable


def test_validator_rejects_software_prompt_missing_core_principles():
    text = build_optimized_markdown("Refactor a Python package with tests")
    section_start = text.index("## Software Engineering Core Principles")
    section_end = text.index("## Acceptance Criteria")
    missing_principles = text[:section_start] + text[section_end:]

    validation = validate_optimized_markdown(missing_principles)

    assert validation.valid is False
    assert "software engineering core principles missing" in validation.reasons


def test_validator_rejects_software_prompt_missing_cleanup_requirement():
    text = build_optimized_markdown("Refactor a Python package with tests")
    missing_cleanup = text.replace(f"\n\n{CLEANUP_REQUIREMENT}", "")

    validation = validate_optimized_markdown(missing_cleanup)

    assert validation.valid is False
    assert "software-development cleanup requirement missing" in validation.reasons


def test_uncertain_prompt_uses_stricter_software_constraints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prepared = prepare_goal_prompt("Improve this")

    assert 'domain: "uncertain"' in prepared.goal_text
    assert "## Software Development Constraints" in prepared.goal_text
    assert CLEANUP_REQUIREMENT not in prepared.goal_text
    assert all(marker not in prepared.goal_text for marker in PRINCIPLE_MARKERS)


def test_existing_valid_generated_file_is_reused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = prepare_goal_prompt("Create a Python CLI for invoices")
    second = prepare_goal_prompt(str(first.file_path), allow_existing_path=True)

    assert second.status == "reused"
    assert second.file_path == first.file_path
    assert second.goal_text == first.goal_text
    assert second.title == first.title
    assert len(list(tmp_path.glob("*.md"))) == 1


def test_invalid_generated_file_is_regenerated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    broken = tmp_path / "broken-goal.md"
    broken.write_text("---\ngenerated_by: goal-prompt-generator\n---\n# Missing sections\n")

    prepared = prepare_goal_prompt(str(broken), allow_existing_path=True)

    assert prepared.status == "regenerated"
    assert prepared.file_path != broken
    assert prepared.file_path.exists()
    assert "## Acceptance Criteria" in prepared.goal_text

    incomplete = prepared.goal_text.replace('goal_prompt_generator_version: "1.3.0"\n', "")
    validation = validate_optimized_markdown(incomplete)
    assert not validation.valid
    assert any("goal_prompt_generator_version" in reason for reason in validation.reasons)


def test_filename_collisions_append_numeric_suffix(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = prepare_goal_prompt("Build a Stripe credit system")
    second = prepare_goal_prompt("Build a Stripe credit system")

    assert first.file_path.name == "stripe-credit-system-goal.md"
    assert second.file_path.name == "stripe-credit-system-goal-2.md"


REQUIRED_CLAUDE_FLAGS = (
    "--p",
    "--add-dir",
    "--agent",
    "--allow-dangerously-skip-permissions",
    "--dangerously-skip-permissions",
    "--debug-file",
    "--effort max",
    "--include-hook-events",
    "--output-format stream-json",
    "--include-partial-messages",
    "--input-format stream-json",
    "--json-schema",
    "--settings",
    "--strict-mcp-config",
    "--system-prompt-file",
    "--tools",
    "--verbose",
    "--worktree",
)


def test_generated_markdown_includes_coding_agent_execution_contract(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prepared = prepare_goal_prompt("Build a Next.js admin panel with tests")
    text = prepared.goal_text

    assert "## Coding Agent Execution Contract" in text
    assert "claude --p <instructions-from-hermes-agent>" in text
    for flag in REQUIRED_CLAUDE_FLAGS:
        assert flag in text, f"required claude CLI flag missing in generated Markdown: {flag}"


def test_non_software_goal_also_carries_coding_agent_execution_contract(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    prepared = prepare_goal_prompt("Write a heartfelt poem about the ocean at sunrise")
    text = prepared.goal_text

    assert "## Coding Agent Execution Contract" in text
    for flag in REQUIRED_CLAUDE_FLAGS:
        assert flag in text, f"required claude CLI flag missing in non-software Markdown: {flag}"


def test_validator_rejects_markdown_missing_coding_agent_execution_contract():
    text = build_optimized_markdown("Refactor a Python package with tests")
    section_start = text.index("## Coding Agent Execution Contract")
    truncated = text[:section_start].rstrip() + "\n"

    validation = validate_optimized_markdown(truncated)

    assert validation.valid is False
    assert "claude CLI execution contract missing" in validation.reasons
    assert any(reason.startswith("required claude CLI flag missing:") for reason in validation.reasons)


def test_validator_rejects_markdown_with_dropped_claude_flag():
    text = build_optimized_markdown("Refactor a Python package with tests")
    tampered = text.replace("--worktree", "--workt-typo")

    validation = validate_optimized_markdown(tampered)

    assert validation.valid is False
    assert "required claude CLI flag missing: --worktree" in validation.reasons


def test_paired_yaml_carries_coding_agent_execution_contract(tmp_path, monkeypatch):
    import yaml as _yaml

    monkeypatch.chdir(tmp_path)
    prepared = prepare_goal_prompt("Build a FastAPI receipts API with tests")
    assert prepared.task_list_path is not None
    data = _yaml.safe_load(prepared.task_list_path.read_text(encoding="utf-8"))

    contract = data.get("coding_agent_execution_contract")
    assert isinstance(contract, dict)
    assert contract["executor"] == "claude"
    assert contract["rule"]
    flag_names = [entry["name"] for entry in contract["required_flags"]]
    for flag in REQUIRED_CLAUDE_FLAGS:
        bare = flag.split(" ", 1)[0]
        assert bare in flag_names, f"missing flag {bare} in required_flags"
    assert contract["canonical_invocation"].startswith("claude ")
    assert contract["forbidden_alternatives"]


def test_yaml_validator_rejects_yaml_missing_contract(tmp_path, monkeypatch):
    import yaml as _yaml

    monkeypatch.chdir(tmp_path)
    prepared = prepare_goal_prompt("Build a FastAPI receipts API with tests")
    yaml_path = prepared.task_list_path
    data = _yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    data.pop("coding_agent_execution_contract", None)
    yaml_path.write_text(_yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    root = Path(__file__).resolve().parents[1]
    validator = root / "scripts" / "validate_task_list_yaml.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(yaml_path)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "coding_agent_execution_contract" in combined
