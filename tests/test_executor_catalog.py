"""Tests for the executor catalog, fallbacks, and per-executor worktree rule."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from goal_prompt_generator import (
    EXECUTOR_CATALOG,
    canonical_invocation_for,
    detect_installed_executors,
    prepare_goal_prompt,
    resolve_executor_choice,
)
from goal_prompt_generator.repository import repository_evidence


PROMPT = "Build a FastAPI receipts API with TDD tests"


def _run_validator(yaml_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_task_list_yaml.py"), str(yaml_path)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )


def test_catalog_has_all_documented_executors() -> None:
    expected = {
        "claude", "codex", "opencode", "gemini", "cursor", "aider",
        "pi", "qwen", "goose", "amp", "crush", "hermes",
    }
    assert set(EXECUTOR_CATALOG.keys()) == expected, (
        "executor catalog must include every documented popular coding-agent CLI"
    )


def test_resolve_executor_choice_rejects_unknown() -> None:
    with pytest.raises(ValueError) as exc:
        resolve_executor_choice(explicit="nonexistent-cli")
    assert "valid choices" in str(exc.value)


def test_resolve_executor_choice_respects_environment_variable(monkeypatch) -> None:
    monkeypatch.setenv("GOAL_PROMPT_GENERATOR_EXECUTOR", "codex")
    monkeypatch.delenv("__force_no_explicit__", raising=False)
    selected = resolve_executor_choice()
    assert selected == "codex"


def test_resolve_executor_choice_falls_back_to_claude_when_nothing_installed() -> None:
    empty = [
        {"cli": cli, "available": False, "binary": entry["binary"],
         "display_name": entry["display_name"], "path": "", "version": "",
         "homepage": entry.get("homepage", ""), "docs": entry.get("docs", "")}
        for cli, entry in EXECUTOR_CATALOG.items()
    ]
    selected = resolve_executor_choice(installed=empty)
    assert selected == "claude"


def test_detect_installed_executors_returns_one_entry_per_catalog_key() -> None:
    installed = detect_installed_executors(use_cache=False, timeout=0.5)
    assert {c["cli"] for c in installed} == set(EXECUTOR_CATALOG.keys())
    for entry in installed:
        assert "available" in entry
        assert "binary" in entry
        assert "path" in entry
        assert isinstance(entry["available"], bool)


def test_canonical_invocation_starts_with_executor_binary() -> None:
    for executor, entry in EXECUTOR_CATALOG.items():
        canonical = canonical_invocation_for(executor)
        assert canonical.startswith(entry["binary"] + " "), (
            f"canonical invocation for {executor} must start with binary {entry['binary']!r}"
        )
        for name, _placeholder in entry["required_flags"]:
            assert name in canonical, (
                f"canonical invocation for {executor} must mention every required flag: missing {name}"
            )


def test_repository_evidence_emits_executor_worktrees_under_repo_root() -> None:
    workdir = ROOT
    evidence = repository_evidence(workdir)
    assert "executor_worktrees" in evidence
    repo_root = Path(evidence["repo_root"])
    for cli, entry in EXECUTOR_CATALOG.items():
        wt = evidence["executor_worktrees"][cli]
        template = Path(wt["directory_template"])
        # The template must live inside the active repo root.
        try:
            template.relative_to(repo_root)
        except ValueError:
            pytest.fail(
                f"executor_worktrees[{cli}].directory_template {template} "
                f"escapes repo_root {repo_root} — every executor MUST root its "
                f"worktree under the active Hermes worktree."
            )
        assert template.name == "<worktree-name>", (
            f"executor_worktrees[{cli}].directory_template must end with <worktree-name>"
        )


def test_generated_yaml_for_each_catalog_executor_validates(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GOAL_PROMPT_GENERATOR_EXECUTOR", raising=False)
    for executor in EXECUTOR_CATALOG:
        out = tmp_path / executor
        out.mkdir()
        prepared = prepare_goal_prompt(
            PROMPT,
            execution_dir=out,
            executor=executor,
        )
        assert prepared.validation.valid, prepared.validation.reasons
        result = _run_validator(prepared.task_list_path)
        assert result.returncode == 0, (
            f"executor={executor}: validator failed\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        data = yaml.safe_load(prepared.task_list_path.read_text(encoding="utf-8"))
        contract = data["coding_agent_execution_contract"]
        assert contract["executor"] == executor
        canonical = contract["canonical_invocation"]
        binary = EXECUTOR_CATALOG[executor]["binary"]
        assert canonical.lstrip().startswith(binary + " ")
        for flag, _ in EXECUTOR_CATALOG[executor]["required_flags"]:
            assert flag in canonical, (
                f"executor={executor}: canonical invocation missing flag {flag}"
            )


def test_yaml_carries_coding_agent_alternatives_block(tmp_path) -> None:
    prepared = prepare_goal_prompt(PROMPT, execution_dir=tmp_path, executor="codex")
    data = yaml.safe_load(prepared.task_list_path.read_text(encoding="utf-8"))
    alt = data["coding_agent_alternatives"]
    assert alt["selected_executor"] == "codex"
    assert alt["selection_source"] == "explicit"
    assert set(alt["configuration_knobs"]["valid_catalog_keys"]) == set(EXECUTOR_CATALOG.keys())
    assert {c["cli"] for c in alt["installed_clis"]} == set(EXECUTOR_CATALOG.keys())
    assert "GoalManager continuation contract" in alt["fallback_rules"]["continuity_invariant"]


def test_yaml_worktree_directory_lands_inside_repo_root_for_every_executor(tmp_path) -> None:
    for executor in EXECUTOR_CATALOG:
        out = tmp_path / executor
        out.mkdir()
        prepared = prepare_goal_prompt(PROMPT, execution_dir=out, executor=executor, workdir=ROOT)
        data = yaml.safe_load(prepared.task_list_path.read_text(encoding="utf-8"))
        repo_root = data["validation_evidence"]["repository_context"]["repo_root"]
        template = data["coding_agent_execution_contract"]["worktree_directory"]["directory_template"]
        assert template.startswith(repo_root), (
            f"executor={executor}: worktree {template} must live under repo_root {repo_root}"
        )
        assert template.endswith("<worktree-name>"), (
            f"executor={executor}: worktree template must end with <worktree-name>"
        )


def test_continuation_contract_preserved_across_executors(tmp_path) -> None:
    """Switching executors must NEVER weaken the GoalManager continuation contract."""
    for executor in EXECUTOR_CATALOG:
        out = tmp_path / executor
        out.mkdir()
        prepared = prepare_goal_prompt(PROMPT, execution_dir=out, executor=executor)
        data = yaml.safe_load(prepared.task_list_path.read_text(encoding="utf-8"))
        contract = data["agent_runtime_protocol"]["goal_manager_continuation_contract"]
        assert contract["non_final_response_marker"] == "GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued"
        assert contract["final_response_marker"] == "GOAL_RUNTIME_STATUS: COMPLETE — all acceptance criteria and validations satisfied"
        assert "do not ask the user" in contract["human_input_policy"]


def test_validator_rejects_unknown_executor(tmp_path) -> None:
    prepared = prepare_goal_prompt(PROMPT, execution_dir=tmp_path, executor="claude")
    data = yaml.safe_load(prepared.task_list_path.read_text(encoding="utf-8"))
    data["coding_agent_execution_contract"]["executor"] = "made-up-cli"
    prepared.task_list_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = _run_validator(prepared.task_list_path)
    assert result.returncode != 0
    combined = (result.stdout + result.stderr).lower()
    assert "must be one of" in combined or "executor" in combined
