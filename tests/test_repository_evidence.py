from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from goal_prompt_generator import (
    build_optimized_markdown,
    prepare_goal_prompt,
    repository_evidence,
    validate_optimized_markdown,
    workdir_path,
)
from goal_prompt_generator.constants import VERSION


def subprocess_env_with_current_path() -> dict[str, str]:
    env = os.environ.copy()
    current = [entry for entry in sys.path if entry]
    inherited = env.get("PYTHONPATH")
    if inherited:
        current.append(inherited)
    env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(current))
    return env


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Create a fake repo with manifests, lockfiles, agent-context files, and a CI file."""
    repo = tmp_path / "fakerepo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# Agents instructions\nFollow our existing conventions.\n", encoding="utf-8")
    (repo / "package.json").write_text('{"name": "fake", "version": "0.1.0"}\n', encoding="utf-8")
    (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '6.0'\n", encoding="utf-8")
    (repo / ".github").mkdir()
    (repo / ".github" / "workflows").mkdir()
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (repo / ".claude" / "worktrees" / "existing-agent").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "src" / "main.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "main.test.ts").write_text("import { x } from '../src/main';\n", encoding="utf-8")
    if subprocess.run(["which", "git"], capture_output=True).returncode == 0:
        _git(["init", "-q"], repo)
        _git(["config", "user.email", "test@example.com"], repo)
        _git(["config", "user.name", "Test"], repo)
        _git(["add", "-A"], repo)
        env = os.environ.copy()
        subprocess.run(["git", "commit", "-qm", "init"], cwd=str(repo), check=True, env=env, capture_output=True)
    return repo


def test_repository_evidence_returns_stable_keys(tmp_path: Path) -> None:
    evidence = repository_evidence(tmp_path)
    for key in (
        "workdir", "repo_root", "is_git_repo", "vcs", "manifests", "lockfiles",
        "agent_context_files", "agent_context_excerpts", "ci_paths",
        "top_level_entries", "primary_languages", "key_paths",
    ):
        assert key in evidence, f"missing key: {key}"


def test_repository_evidence_finds_canonical_files(fake_repo: Path) -> None:
    evidence = repository_evidence(fake_repo)
    assert "AGENTS.md" in evidence["agent_context_files"]
    assert "package.json" in evidence["manifests"]
    assert "pnpm-lock.yaml" in evidence["lockfiles"]
    assert any(p == ".github/workflows" for p in evidence["ci_paths"])
    assert any(entry.endswith("/AGENTS.md") for entry in evidence["key_paths"])
    assert any(entry.endswith("/package.json") for entry in evidence["key_paths"])
    excerpts = evidence["agent_context_excerpts"]
    assert "AGENTS.md" in excerpts
    assert excerpts["AGENTS.md"].startswith("# Agents instructions")


def test_repository_evidence_records_git_state(fake_repo: Path) -> None:
    if subprocess.run(["which", "git"], capture_output=True).returncode != 0:
        pytest.skip("git not available")
    evidence = repository_evidence(fake_repo)
    assert evidence["is_git_repo"] is True
    assert evidence["vcs"]["head_sha"]
    assert evidence["vcs"]["branch"]
    assert evidence["vcs"]["dirty"] is False


def test_repository_evidence_languages_count_top_level(fake_repo: Path) -> None:
    evidence = repository_evidence(fake_repo)
    languages = {entry["language"]: entry["file_count"] for entry in evidence["primary_languages"]}
    assert languages.get("TypeScript", 0) >= 2


def test_workdir_path_defaults_to_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert workdir_path(None) == tmp_path.resolve()
    nested = tmp_path / "nested"
    nested.mkdir()
    assert workdir_path(nested) == nested.resolve()


def test_repository_evidence_records_claude_worktree_directory(fake_repo: Path) -> None:
    evidence = repository_evidence(fake_repo)
    claude = evidence["claude_worktree"]

    root = fake_repo / ".claude" / "worktrees"
    assert claude["flag"] == "--worktree"
    assert claude["short_flag"] == "-w"
    assert claude["root"] == str(root)
    assert claude["directory_template"] == str(root / "<worktree-name>")
    assert claude["exists"] is True
    assert claude["existing_worktrees"] == ["existing-agent"]
    assert any(p.endswith("/.claude/worktrees") for p in evidence["key_paths"])


def test_build_optimized_markdown_includes_repository_section(fake_repo: Path) -> None:
    text = build_optimized_markdown("Add tests for the existing TS module", workdir=fake_repo)
    assert "## Repository Context" in text
    assert str(fake_repo) in text
    assert "AGENTS.md" in text
    assert "package.json" in text
    assert "branch:" in text
    assert "### Claude Code worktree directory" in text
    assert "--worktree` / `-w`" in text
    assert str(fake_repo / ".claude" / "worktrees" / "<worktree-name>") in text
    # Backwards-compat: validator still accepts the file
    assert validate_optimized_markdown(text).valid is True


def test_prepare_goal_prompt_writes_repository_context_into_yaml(
    tmp_path: Path, fake_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    prepared = prepare_goal_prompt(
        "Add a TypeScript greet helper with tests",
        workdir=fake_repo,
    )
    assert "## Repository Context" in prepared.goal_text
    assert prepared.task_list_path is not None
    data = yaml.safe_load(prepared.task_list_path.read_text(encoding="utf-8"))
    rc = data["validation_evidence"]["repository_context"]
    assert rc["workdir"] == str(fake_repo)
    assert rc["repo_root"] == str(fake_repo)
    assert any(p.endswith("/AGENTS.md") for p in rc["key_paths"])
    # Per-task context_files MUST include the repository key paths so the
    # downstream coding agent reads them before editing.
    a01 = data["phases"][0]["tasks"][0]
    assert any(p.endswith("/AGENTS.md") for p in a01["context_files"])
    assert any(p.endswith("/package.json") for p in a01["context_files"])
    # Metadata carries workdir + repo_root for the structural validator
    assert data["metadata"]["workdir"] == str(fake_repo)
    assert data["metadata"]["repo_root"] == str(fake_repo)
    assert data["agent_runtime_protocol"]["handoff_workdir"] == str(fake_repo)
    claude = rc["claude_worktree"]
    assert claude["directory_template"] == str(fake_repo / ".claude" / "worktrees" / "<worktree-name>")
    assert data["agent_runtime_protocol"]["claude_worktree_directory_template"] == claude["directory_template"]
    contract = data["coding_agent_execution_contract"]
    assert contract["worktree_directory"]["root"] == str(fake_repo / ".claude" / "worktrees")
    assert contract["worktree_directory"]["flag"] == "--worktree"
    assert any(p.endswith("/.claude/worktrees") for p in a01["context_files"])


def test_repository_validator_rejects_yaml_with_missing_key_paths(
    tmp_path: Path, fake_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    prepared = prepare_goal_prompt(
        "Add a TypeScript greet helper with tests",
        workdir=fake_repo,
    )
    yaml_path = prepared.task_list_path
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    data["validation_evidence"]["repository_context"]["key_paths"] = []
    yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    root = Path(__file__).resolve().parents[1]
    validator = root / "scripts" / "validate_task_list_yaml.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(yaml_path)],
        capture_output=True, text=True,
        env=subprocess_env_with_current_path(),
    )
    # Empty key_paths list is allowed (it's still a list); but missing the
    # field entirely must fail.
    assert result.returncode == 0  # empty list is acceptable
    del data["validation_evidence"]["repository_context"]["key_paths"]
    yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result2 = subprocess.run(
        [sys.executable, str(validator), str(yaml_path)],
        capture_output=True, text=True,
        env=subprocess_env_with_current_path(),
    )
    assert result2.returncode != 0
    combined = result2.stdout + result2.stderr
    assert "key_paths" in combined

    data["validation_evidence"]["repository_context"]["key_paths"] = []
    data["validation_evidence"]["repository_context"].pop("claude_worktree", None)
    yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result3 = subprocess.run(
        [sys.executable, str(validator), str(yaml_path)],
        capture_output=True, text=True,
        env=subprocess_env_with_current_path(),
    )
    assert result3.returncode != 0
    combined3 = result3.stdout + result3.stderr
    assert "claude_worktree" in combined3


def test_markdown_without_repository_context_section_fails_at_current_version(tmp_path: Path) -> None:
    """At the current VERSION the Repository Context section is mandatory.
    Legacy version support is fully removed, so a contract that lacks the
    section MUST fail validation regardless of any prior on-disk shape."""
    text = build_optimized_markdown("Refactor a Python package with tests")
    start = text.index("## Repository Context")
    end = text.index("## ", start + 1)
    stripped = text[:start] + text[end:]
    result = validate_optimized_markdown(stripped)
    assert result.valid is False
    assert any("Repository Context" in reason for reason in result.reasons)
