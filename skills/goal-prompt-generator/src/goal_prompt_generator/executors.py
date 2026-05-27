"""Executor catalog and installer-side detection.

The goal-prompt-generator skill is configurable: at generation time the
installer's machine is probed for every CLI in the catalog below, and the
chosen executor must be one of them. The catalog is the single source of
truth for which coding-agent CLIs are supported; each entry pins the
non-interactive flag set every generated goal MUST carry when that executor
is chosen, the worktree template, and an executor-specific
``forbidden_alternatives`` list.

No CLI is hard-coded as the only option. ``claude`` is the default because
the original contract was Claude-Code-shaped, but the installer can configure
any catalog key via ``--executor`` on the helper, ``executor=`` on the
Python API, or the ``GOAL_PROMPT_GENERATOR_EXECUTOR`` environment variable.

Every executor profile keeps the same runtime invariants:
- non-interactive / batch mode flag enabled
- the GoalManager continuation contract (autonomy + ``GOAL_RUNTIME_STATUS:
  CONTINUE`` / ``GOAL_RUNTIME_STATUS: COMPLETE`` markers + no human input
  on non-final turns) is enforced regardless of which CLI is chosen.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

# Each entry describes one popular coding-agent CLI. The catalog ordering is
# the documented fallback chain priority — pick the first available installed
# entry when no explicit ``executor`` is configured.
EXECUTOR_CATALOG: dict[str, dict[str, Any]] = {
    "claude": {
        "binary": "claude",
        "display_name": "Claude Code",
        "homepage": "https://code.claude.com",
        "docs": "https://code.claude.com/docs/en/cli-reference",
        "required_flags": (
            ("--print", "<no-arg>"),
            ("--add-dir", "<list-of-directories>"),
            ("--agent", "<custom-subagent>"),
            ("--allow-dangerously-skip-permissions", "<no-arg>"),
            ("--dangerously-skip-permissions", "<no-arg>"),
            ("--debug-file", "<path>"),
            ("--effort", "max"),
            ("--include-hook-events", "<no-arg>"),
            ("--output-format", "stream-json"),
            ("--include-partial-messages", "<no-arg>"),
            ("--input-format", "stream-json"),
            ("--json-schema", "<json-schema>"),
            ("--mcp-config", "<mcp-json-file>"),
            ("--settings", "<settings-json-file>"),
            ("--strict-mcp-config", "<no-arg>"),
            ("--system-prompt-file", "<file>"),
            ("--tools", "<comma-separated-tools>"),
            ("--verbose", "<no-arg>"),
            ("--worktree", "<worktree-name>"),
        ),
        "worktree_directory_template": "<repo-root>/.claude/worktrees/<worktree-name>",
        "non_interactive_proof": "--print + --input-format stream-json + --output-format stream-json",
    },
    "codex": {
        "binary": "codex",
        "display_name": "OpenAI Codex CLI",
        "homepage": "https://github.com/openai/codex",
        "docs": "https://github.com/openai/codex#readme",
        "required_flags": (
            ("--full-auto", "<no-arg>"),
            ("--dangerously-bypass-approvals-and-sandbox", "<no-arg>"),
            ("--reasoning-effort", "high"),
            ("--model", "<model-id>"),
        ),
        "worktree_directory_template": "<repo-root>/.codex/worktrees/<worktree-name>",
        "non_interactive_proof": "--full-auto disables interactive approvals",
    },
    "opencode": {
        "binary": "opencode",
        "display_name": "OpenCode",
        "homepage": "https://github.com/opencode-ai/opencode",
        "docs": "https://opencode.ai/docs",
        "required_flags": (
            ("run", "<no-arg>"),
            ("--model", "<provider/model-id>"),
            ("--prompt", "<instructions-from-hermes-agent>"),
        ),
        "worktree_directory_template": "<repo-root>/.opencode/worktrees/<worktree-name>",
        "non_interactive_proof": "`opencode run` is the non-interactive subcommand",
    },
    "gemini": {
        "binary": "gemini",
        "display_name": "Gemini CLI",
        "homepage": "https://github.com/google-gemini/gemini-cli",
        "docs": "https://github.com/google-gemini/gemini-cli#readme",
        "required_flags": (
            ("--prompt", "<instructions-from-hermes-agent>"),
            ("--yolo", "<no-arg>"),
            ("--model", "<model-id>"),
        ),
        "worktree_directory_template": "<repo-root>/.gemini/worktrees/<worktree-name>",
        "non_interactive_proof": "--prompt + --yolo runs without interactive approvals",
    },
    "cursor": {
        "binary": "cursor-agent",
        "binary_fallback": "cursor",
        "display_name": "Cursor CLI / cursor-agent",
        "homepage": "https://docs.cursor.com/en/cli/overview",
        "docs": "https://docs.cursor.com/en/cli/reference/parameters",
        "required_flags": (
            ("--print", "<no-arg>"),
            ("--force", "<no-arg>"),
            ("--model", "<model-id>"),
        ),
        "worktree_directory_template": "<repo-root>/.cursor/worktrees/<worktree-name>",
        "non_interactive_proof": "--print runs cursor-agent non-interactively",
    },
    "aider": {
        "binary": "aider",
        "display_name": "Aider",
        "homepage": "https://aider.chat",
        "docs": "https://aider.chat/docs/usage.html",
        "required_flags": (
            ("--yes-always", "<no-arg>"),
            ("--no-auto-commits", "<no-arg>"),
            ("--message", "<instructions-from-hermes-agent>"),
            ("--model", "<model-id>"),
        ),
        "worktree_directory_template": "<repo-root>/.aider/worktrees/<worktree-name>",
        "non_interactive_proof": "--yes-always + --message runs aider without interactive confirms",
    },
    "pi": {
        "binary": "pi",
        "display_name": "Pi (earendil-works/pi-coding-agent)",
        "homepage": "https://github.com/earendil-works/pi-coding-agent",
        "docs": "https://github.com/earendil-works/pi-coding-agent#readme",
        "required_flags": (
            ("--non-interactive", "<no-arg>"),
            ("--prompt", "<instructions-from-hermes-agent>"),
        ),
        "worktree_directory_template": "<repo-root>/.pi/worktrees/<worktree-name>",
        "non_interactive_proof": "--non-interactive forces batch mode",
    },
    "qwen": {
        "binary": "qwen",
        "binary_fallback": "qwen-code",
        "display_name": "Qwen Code",
        "homepage": "https://github.com/QwenLM/qwen-code",
        "docs": "https://github.com/QwenLM/qwen-code#readme",
        "required_flags": (
            ("--prompt", "<instructions-from-hermes-agent>"),
            ("--yolo", "<no-arg>"),
        ),
        "worktree_directory_template": "<repo-root>/.qwen/worktrees/<worktree-name>",
        "non_interactive_proof": "--prompt + --yolo runs without interactive approvals",
    },
    "goose": {
        "binary": "goose",
        "display_name": "Goose (Block)",
        "homepage": "https://block.github.io/goose/",
        "docs": "https://block.github.io/goose/docs/getting-started/cli",
        "required_flags": (
            ("run", "<no-arg>"),
            ("--no-session", "<no-arg>"),
            ("--text", "<instructions-from-hermes-agent>"),
        ),
        "worktree_directory_template": "<repo-root>/.goose/worktrees/<worktree-name>",
        "non_interactive_proof": "`goose run --text` runs non-interactively",
    },
    "amp": {
        "binary": "amp",
        "display_name": "Amp (Sourcegraph)",
        "homepage": "https://ampcode.com",
        "docs": "https://ampcode.com/manual",
        "required_flags": (
            ("--no-tui", "<no-arg>"),
            ("--prompt", "<instructions-from-hermes-agent>"),
        ),
        "worktree_directory_template": "<repo-root>/.amp/worktrees/<worktree-name>",
        "non_interactive_proof": "--no-tui forces batch mode",
    },
    "crush": {
        "binary": "crush",
        "display_name": "Crush (Charmbracelet)",
        "homepage": "https://github.com/charmbracelet/crush",
        "docs": "https://github.com/charmbracelet/crush#readme",
        "required_flags": (
            ("--prompt", "<instructions-from-hermes-agent>"),
            ("--yolo", "<no-arg>"),
        ),
        "worktree_directory_template": "<repo-root>/.crush/worktrees/<worktree-name>",
        "non_interactive_proof": "--prompt + --yolo runs without interactive approvals",
    },
    "hermes": {
        "binary": "hermes",
        "display_name": "Hermes Agent (configurable model + reasoning)",
        "homepage": "https://hermes-agent.nousresearch.com",
        "docs": "https://hermes-agent.nousresearch.com/docs",
        "required_flags": (
            ("--quiet", "<no-arg>"),
            ("--no-skill-load", "<no-arg>"),
            ("--prompt", "<instructions-from-hermes-agent>"),
            ("--model", "<configurable-model-id>"),
            ("--provider", "<configurable-provider>"),
            ("--reasoning-effort", "<minimal|low|medium|high|xhigh>"),
        ),
        "worktree_directory_template": "<repo-root>/.hermes/worktrees/<worktree-name>",
        "non_interactive_proof": (
            "`hermes --quiet --prompt ...` runs one batch turn; pair with "
            "`--model` / `--provider` / `--reasoning-effort` to pin the executor to "
            "whatever the installer has authenticated via `hermes model` / `hermes config`."
        ),
        "model_selection_rule": (
            "When the executor is `hermes`, inspect the installer's `~/.hermes/config.yaml` "
            "and authenticated providers via `hermes model` (powered by "
            "`hermes_cli/model_switch.list_authenticated_providers`). Pick the strongest "
            "available coding model the installer has access to from the curated list in "
            "`hermes_cli/models.py` (`_PROVIDER_MODELS` / `OPENROUTER_MODELS`); fall back to "
            "the next tier when the preferred model is unauthenticated. Reasoning effort comes "
            "from `agent.reasoning_effort` (`hermes_constants.VALID_REASONING_EFFORTS = "
            "('minimal','low','medium','high','xhigh')`); choose `high` for complex multi-phase "
            "work and `medium` for routine refactors."
        ),
    },
}


def detect_installed_executors(
    catalog: dict[str, dict[str, Any]] | None = None,
    *,
    timeout: float = 1.5,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Probe the installer's PATH for every executor in the catalog.

    Returns a list of dicts ordered by catalog priority:
        {cli, display_name, binary, path, version, available}

    No CLI is invoked beyond ``--version`` (read-only). Detection is bounded
    by ``timeout`` per binary so a slow node-based CLI cannot stall generation.
    Results are cached at the module level keyed by the catalog identity so
    repeated calls within the same process (e.g. across the test suite) are
    instant after the first probe. Pass ``use_cache=False`` to force a fresh
    probe.
    """
    catalog = catalog if catalog is not None else EXECUTOR_CATALOG
    cache_key = id(catalog)
    if use_cache and cache_key in _DETECT_CACHE:
        return _DETECT_CACHE[cache_key]
    results: list[dict[str, Any]] = []
    for cli, entry in catalog.items():
        binary = entry["binary"]
        path = shutil.which(binary)
        if not path and entry.get("binary_fallback"):
            binary = entry["binary_fallback"]
            path = shutil.which(binary)
        version = ""
        if path:
            try:
                proc = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                raw = (proc.stdout or proc.stderr or "").strip().splitlines()
                version = raw[0] if raw else ""
            except (subprocess.TimeoutExpired, OSError):
                version = ""
        results.append(
            {
                "cli": cli,
                "display_name": entry["display_name"],
                "binary": binary,
                "path": path or "",
                "version": version,
                "available": bool(path),
                "homepage": entry.get("homepage", ""),
                "docs": entry.get("docs", ""),
            }
        )
    if use_cache:
        _DETECT_CACHE[cache_key] = results
    return results


_DETECT_CACHE: dict[int, list[dict[str, Any]]] = {}


def resolve_executor_choice(
    explicit: str | None = None,
    *,
    catalog: dict[str, dict[str, Any]] | None = None,
    installed: list[dict[str, Any]] | None = None,
    env_var: str = "GOAL_PROMPT_GENERATOR_EXECUTOR",
) -> str:
    """Choose the executor for the generated contract.

    Resolution order:
      1. ``explicit`` argument (helper ``--executor`` / Python ``executor=``).
      2. ``${GOAL_PROMPT_GENERATOR_EXECUTOR}`` environment variable.
      3. First available installed catalog entry.
      4. ``claude`` (the documented default).

    The result is always a valid catalog key; unknown values raise ``ValueError``
    so the validator can never receive an out-of-catalog executor.
    """
    catalog = catalog if catalog is not None else EXECUTOR_CATALOG
    requested = (explicit or os.environ.get(env_var, "")).strip().lower()
    if requested:
        if requested not in catalog:
            valid = ", ".join(sorted(catalog))
            raise ValueError(
                f"executor={requested!r} is not in the catalog; valid choices: {valid}"
            )
        return requested
    if installed is None:
        installed = detect_installed_executors(catalog=catalog)
    for entry in installed:
        if entry["available"]:
            return entry["cli"]
    return "claude"


def canonical_invocation_for(executor: str, catalog: dict[str, dict[str, Any]] | None = None) -> str:
    """Build the canonical CLI invocation string for the chosen executor."""
    catalog = catalog if catalog is not None else EXECUTOR_CATALOG
    if executor not in catalog:
        raise ValueError(f"unknown executor: {executor!r}")
    entry = catalog[executor]
    parts = [entry["binary"]]
    has_prompt_flag = False
    for name, placeholder in entry["required_flags"]:
        if placeholder == "<no-arg>":
            parts.append(name)
        else:
            parts.append(f"{name} {placeholder}")
            if placeholder == "<instructions-from-hermes-agent>":
                has_prompt_flag = True
    if not has_prompt_flag:
        parts.append('"<instructions-from-hermes-agent>"')
    return " ".join(parts)
