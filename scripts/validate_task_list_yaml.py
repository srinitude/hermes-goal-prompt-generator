#!/usr/bin/env python3
"""Validate a coding-agent task-list YAML produced by `goal-prompt-generator`.

Usage:
    python3 validate_task_list_yaml.py <path-to-yaml>

Exits 0 with `OK: ...` on success, 1 with a list of problems on failure. The
checks here are the contract surface a coding agent relies on; do not weaken
them without updating `references/coding-agent-task-list-yaml.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - env-specific
    print(f"validate_task_list_yaml: PyYAML is required ({exc})", file=sys.stderr)
    raise SystemExit(2) from exc


REQUIRED_TASK_FIELDS = {
    "id",
    "title",
    "status",
    "dependencies",
    "validation_steps",
    "ci_commands",
    "styleguide_rules",
    "guardrails",
    "learnings",
    "gotchas",
    "context_files",
    "context_urls",
    "principle_ids",
}

PROHIBITED_TASK_GRAPH_FIELDS = {"prerequisites", "blocking_tasks"}

REQUIRED_TOP_LEVEL = {
    "metadata",
    "validation_evidence",
    "styleguide_rules",
    "guardrails",
    "ci_commands",
    "principles",
    "phases",
    "agent_runtime_protocol",
    "coding_agent_execution_contract",
}

LEGACY_RECONCILIATION_KEY = "contrary_evidence_already_collected"
RECONCILIATION_FINAL_STATES = {
    "all-claims-reconciled",
    "some-claims-downgraded",
    "some-claims-escalated-to-execution-time",
}
RECONCILIATION_CONFLICT_FIELDS = {
    "check_id", "evidence_target", "original_claim",
    "contrarian_observation", "severity", "resolution",
}

PHASE_ORDER = ("ANALYSIS", "BOOTSTRAP", "RED", "GREEN", "REFACTOR")

ALLOWED_STATUS = {"pending", "in_progress", "completed", "blocked", "cancelled"}

REQUIRED_CLAUDE_FLAGS = (
    "--print",
    "--add-dir",
    "--agent",
    "--allow-dangerously-skip-permissions",
    "--dangerously-skip-permissions",
    "--debug-file",
    "--effort",
    "--include-hook-events",
    "--output-format",
    "--include-partial-messages",
    "--input-format",
    "--json-schema",
    "--mcp-config",
    "--settings",
    "--strict-mcp-config",
    "--system-prompt-file",
    "--tools",
    "--verbose",
    "--worktree",
)

# Catalog of every popular coding-agent CLI the skill knows how to drive.
# Each value: (binary_name, required_flag_tuple).
# Keep this in sync with src/goal_prompt_generator/executors.py — if they
# drift, the structural validator and the generator disagree.
EXECUTOR_CATALOG_PROFILES: dict[str, dict[str, Any]] = {
    "claude": {"binary": "claude", "flags": REQUIRED_CLAUDE_FLAGS},
    "codex": {"binary": "codex", "flags": (
        "--full-auto", "--dangerously-bypass-approvals-and-sandbox",
        "--reasoning-effort", "--model",
    )},
    "opencode": {"binary": "opencode", "flags": ("run", "--model", "--prompt")},
    "gemini": {"binary": "gemini", "flags": ("--prompt", "--yolo", "--model")},
    "cursor": {"binary": "cursor-agent", "flags": ("--print", "--force", "--model")},
    "aider": {"binary": "aider", "flags": (
        "--yes-always", "--no-auto-commits", "--message", "--model",
    )},
    "pi": {"binary": "pi", "flags": ("--non-interactive", "--prompt")},
    "qwen": {"binary": "qwen", "flags": ("--prompt", "--yolo")},
    "goose": {"binary": "goose", "flags": ("run", "--no-session", "--text")},
    "amp": {"binary": "amp", "flags": ("--no-tui", "--prompt")},
    "crush": {"binary": "crush", "flags": ("--prompt", "--yolo")},
    "hermes": {"binary": "hermes", "flags": (
        "--quiet", "--no-skill-load", "--prompt",
        "--model", "--provider", "--reasoning-effort",
    )},
}


def _as_dict(value: Any, label: str, problems: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        problems.append(f"{label}: expected mapping, got {type(value).__name__}")
        return {}
    return value


def _as_list(value: Any, label: str, problems: list[str]) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        problems.append(f"{label}: expected list, got {type(value).__name__}")
        return []
    return value


def _phase_index(name: str) -> int:
    try:
        return PHASE_ORDER.index(name)
    except ValueError:
        return -1


def _uses_legacy_task_graph(data: dict[str, Any]) -> bool:
    """Detect already-sealed v1 task ledgers that made legacy fields immutable.

    Current generated YAMLs must use `dependencies` as the only task graph field.
    Some immutable ledgers produced before that tightening contain
    `prerequisites` / `blocking_tasks` and also list those fields under
    `agent_runtime_protocol.immutable_fields`. Execution agents are only allowed
    to mutate `status`, `learnings`, and `gotchas`, so the validator accepts that
    legacy shape when validating those historical sealed ledgers instead of
    forcing contract-breaking edits.

    Detection is intentionally narrow: only YAMLs that explicitly opted into the
    legacy shape by listing `prerequisites` / `blocking_tasks` under
    `agent_runtime_protocol.immutable_fields` are grandfathered. Per-task
    presence alone is not enough — that would let newly authored YAMLs sneak the
    legacy fields back in.
    """
    runtime = data.get("agent_runtime_protocol")
    if not isinstance(runtime, dict):
        return False
    immutable = runtime.get("immutable_fields")
    if not isinstance(immutable, list):
        return False
    names = {item for item in immutable if isinstance(item, str)}
    return bool(PROHIBITED_TASK_GRAPH_FIELDS & names)


def _check_reconciliation_required(
    data: dict[str, Any],
    evidence: dict[str, Any],
    fc_maps: dict[str, Any],
    osrc_fetched: dict[str, Any],
    problems: list[str],
) -> None:
    """Refuse YAMLs that claim Firecrawl/opensrc evidence but skip reconciliation.

    Compatibility shim: a non-empty validation_evidence.contrary_evidence_already_collected
    list is treated as legacy reconciliation evidence so we do not invalidate the
    immutable runtime ledger that already carries it instead of the newer key.
    """
    has_claims = bool(fc_maps) or bool(osrc_fetched)
    if not has_claims:
        return
    rec = data.get("validation_reconciliation")
    has_rec = isinstance(rec, dict) and len(rec) > 0
    legacy = evidence.get(LEGACY_RECONCILIATION_KEY)
    has_legacy = isinstance(legacy, list) and len(legacy) > 0
    if has_rec or has_legacy:
        return
    problems.append(
        "validation_reconciliation: required and non-empty when "
        "firecrawl.required_maps_present or opensrc.fetched is non-empty "
        f"(legacy validation_evidence.{LEGACY_RECONCILIATION_KEY} list also accepted)"
    )


def _check_reconciliation_shape(data: dict[str, Any], problems: list[str]) -> None:
    rec = data.get("validation_reconciliation")
    if rec is None:
        return
    rec = _as_dict(rec, "validation_reconciliation", problems)
    if not rec:
        problems.append("validation_reconciliation: must be non-empty")
        return
    if rec.get("final_state") not in RECONCILIATION_FINAL_STATES:
        problems.append("validation_reconciliation.final_state: invalid or missing")
    buckets = {k: _as_list(rec.get(k), f"validation_reconciliation.{k}", problems) for k in ("conflicts", "resolutions")}
    if buckets["resolutions"] != buckets["conflicts"]:
        problems.append("validation_reconciliation.resolutions: must preserve conflicts ordering")
    for bucket, items in buckets.items():
        for idx, item in enumerate(items):
            item = _as_dict(item, f"validation_reconciliation.{bucket}[{idx}]", problems)
            missing = RECONCILIATION_CONFLICT_FIELDS - set(item)
            if missing:
                problems.append(f"validation_reconciliation.{bucket}[{idx}]: missing {sorted(missing)}")


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"yaml parse error: {exc}"]

    problems: list[str] = []
    if not isinstance(data, dict):
        return [f"top-level: expected mapping, got {type(data).__name__}"]

    missing_top = REQUIRED_TOP_LEVEL - set(data)
    if missing_top:
        problems.append(f"top-level: missing keys {sorted(missing_top)}")

    cc_block = _as_dict(data.get("ci_commands"), "ci_commands", problems)
    sg_block = _as_dict(data.get("styleguide_rules"), "styleguide_rules", problems)
    gr_block = _as_dict(data.get("guardrails"), "guardrails", problems)
    pr_block = _as_dict(data.get("principles"), "principles", problems)
    runtime_block = _as_dict(data.get("agent_runtime_protocol"), "agent_runtime_protocol", problems)
    uses_legacy_task_graph = _uses_legacy_task_graph(data)
    raw_goal_runtime = runtime_block.get("goal_manager_continuation_contract")
    if raw_goal_runtime is None and uses_legacy_task_graph:
        goal_runtime: dict[str, Any] = {}
    else:
        goal_runtime = _as_dict(
            raw_goal_runtime,
            "agent_runtime_protocol.goal_manager_continuation_contract",
            problems,
        )
    if goal_runtime:
        required_runtime = (
            "runtime",
            "source_markdown_section",
            "contract",
            "continue_until",
            "non_final_response_marker",
            "final_response_marker",
            "human_input_policy",
            "judge_shape",
        )
        for key in required_runtime:
            value = goal_runtime.get(key)
            if not (isinstance(value, str) and value.strip()):
                problems.append(f"agent_runtime_protocol.goal_manager_continuation_contract.{key}: missing or empty")
        if goal_runtime.get("runtime") != "hermes /goal":
            problems.append("agent_runtime_protocol.goal_manager_continuation_contract.runtime: must be 'hermes /goal'")
        if "max_turns" not in str(goal_runtime.get("continue_until", "")):
            problems.append("agent_runtime_protocol.goal_manager_continuation_contract.continue_until: must mention max_turns")
        if "GOAL_RUNTIME_STATUS: CONTINUE" not in str(goal_runtime.get("non_final_response_marker", "")):
            problems.append("agent_runtime_protocol.goal_manager_continuation_contract.non_final_response_marker: must contain GOAL_RUNTIME_STATUS: CONTINUE")
        if "GOAL_RUNTIME_STATUS: COMPLETE" not in str(goal_runtime.get("final_response_marker", "")):
            problems.append("agent_runtime_protocol.goal_manager_continuation_contract.final_response_marker: must contain GOAL_RUNTIME_STATUS: COMPLETE")
        if "do not ask" not in str(goal_runtime.get("human_input_policy", "")).lower():
            problems.append("agent_runtime_protocol.goal_manager_continuation_contract.human_input_policy: must forbid asking the user")

    immutable_fields = _as_list(
        runtime_block.get("immutable_fields"),
        "agent_runtime_protocol.immutable_fields",
        problems,
    )
    immutable_field_names = {item for item in immutable_fields if isinstance(item, str)}
    legacy_immutable = sorted(PROHIBITED_TASK_GRAPH_FIELDS & immutable_field_names)
    if legacy_immutable and not uses_legacy_task_graph:
        problems.append(
            "agent_runtime_protocol.immutable_fields: legacy task graph fields are not allowed "
            f"{legacy_immutable}; use dependencies only"
        )

    cc_ids = set(cc_block)
    sg_ids = set(sg_block)
    gr_ids = set(gr_block)
    pr_ids = set(pr_block)

    phases = _as_list(data.get("phases"), "phases", problems)
    phase_names = [p.get("name") if isinstance(p, dict) else None for p in phases]
    declared_phases = [n for n in phase_names if n]
    if declared_phases != [n for n in PHASE_ORDER if n in declared_phases]:
        problems.append(
            f"phases: order must be a prefix-preserving subsequence of {list(PHASE_ORDER)}, got {declared_phases}"
        )

    task_ids: list[str] = []
    task_to_phase: dict[str, int] = {}
    principle_use: set[str] = set()
    red_task_ids: set[str] = set()
    green_task_ids: set[str] = set()

    for phase in phases:
        if not isinstance(phase, dict):
            problems.append(f"phase: expected mapping, got {type(phase).__name__}")
            continue
        name = phase.get("name")
        idx = _phase_index(name) if isinstance(name, str) else -1
        if idx < 0:
            problems.append(f"phase: unknown name {name!r}")
        if name == "RED":
            hard_gate = phase.get("hard_gate")
            if not (isinstance(hard_gate, str) and hard_gate.strip()):
                problems.append("phases.RED: missing or empty hard_gate")
        for task in _as_list(phase.get("tasks"), f"phase[{name}].tasks", problems):
            if not isinstance(task, dict):
                problems.append(f"phase[{name}].tasks: task must be mapping")
                continue
            tid = task.get("id")
            if not isinstance(tid, str) or not tid:
                problems.append(f"phase[{name}].tasks: task missing id")
                continue
            task_ids.append(tid)
            task_to_phase[tid] = idx
            missing = REQUIRED_TASK_FIELDS - set(task)
            if missing:
                problems.append(f"{tid}: missing fields {sorted(missing)}")
            legacy_graph = sorted(PROHIBITED_TASK_GRAPH_FIELDS & set(task))
            if legacy_graph and not uses_legacy_task_graph:
                problems.append(
                    f"{tid}: legacy task graph fields are not allowed {legacy_graph}; "
                    "model prerequisite checks as explicit tasks and infer reverse blockers from dependencies"
                )

            status = task.get("status")
            if status not in ALLOWED_STATUS:
                problems.append(f"{tid}: status {status!r} not in {sorted(ALLOWED_STATUS)}")

            for key, ref_set in (
                ("ci_commands", cc_ids),
                ("styleguide_rules", sg_ids),
                ("guardrails", gr_ids),
                ("principle_ids", pr_ids),
            ):
                for value in _as_list(task.get(key), f"{tid}.{key}", problems):
                    if value not in ref_set:
                        problems.append(f"{tid}: bad {key} ref {value!r}")
                    elif key == "principle_ids":
                        principle_use.add(value)

            for list_key in ("learnings", "gotchas", "context_files", "context_urls",
                             "dependencies", "validation_steps"):
                _as_list(task.get(list_key), f"{tid}.{list_key}", problems)

            if name == "RED":
                red_task_ids.add(tid)
            elif name == "GREEN":
                green_task_ids.add(tid)

    idset = set(task_ids)
    if len(idset) != len(task_ids):
        seen, dupes = set(), []
        for t in task_ids:
            if t in seen:
                dupes.append(t)
            seen.add(t)
        problems.append(f"task ids: duplicates {dupes}")

    for phase in phases:
        if not isinstance(phase, dict):
            continue
        name = phase.get("name")
        for task in _as_list(phase.get("tasks"), f"phase[{name}].tasks", []):
            if not isinstance(task, dict):
                continue
            tid = task.get("id")
            if not isinstance(tid, str):
                continue
            deps = _as_list(task.get("dependencies"), f"{tid}.dependencies", problems)
            for ref in deps:
                if not isinstance(ref, str):
                    continue
                if ref not in idset:
                    problems.append(f"{tid}: dangling dependency {ref!r}")
                    continue
                if ref in task_to_phase and tid in task_to_phase:
                    if task_to_phase[ref] > task_to_phase[tid]:
                        problems.append(
                            f"{tid}: dependency {ref!r} lives in a later phase (phase ordering invariant)"
                        )

    if green_task_ids and red_task_ids:
        for phase in phases:
            if not isinstance(phase, dict) or phase.get("name") != "GREEN":
                continue
            for task in _as_list(phase.get("tasks"), "GREEN.tasks", problems):
                if not isinstance(task, dict):
                    continue
                tid = task.get("id")
                deps = _as_list(task.get("dependencies"), "", [])
                covers_red = bool(deps) and any(ref in red_task_ids for ref in deps)
                if not covers_red:
                    problems.append(
                        f"{tid}: GREEN task must reference >=1 RED task in dependencies"
                    )

    unused_principles = pr_ids - principle_use
    if unused_principles:
        problems.append(
            f"principles: unused ids {sorted(unused_principles)} (every declared principle must appear in some task)"
        )

    evidence = _as_dict(data.get("validation_evidence"), "validation_evidence", problems)
    fc = _as_dict(evidence.get("firecrawl"), "validation_evidence.firecrawl", problems)
    fc_auth = fc.get("auth")
    fc_maps = _as_dict(
        fc.get("required_maps_present"),
        "validation_evidence.firecrawl.required_maps_present",
        problems,
    )
    if fc_auth == "authenticated":
        if not fc_maps:
            problems.append(
                "validation_evidence.firecrawl: auth=authenticated but required_maps_present is empty"
            )
        for tech, entry in fc_maps.items():
            entry = _as_dict(entry, f"firecrawl.required_maps_present[{tech}]", problems)
            uc = entry.get("url_count")
            if not (isinstance(uc, int) and uc > 0):
                problems.append(
                    f"firecrawl.required_maps_present[{tech}]: url_count must be a positive int"
                )
            cmd = entry.get("map_command", "")
            if "--limit 5000" not in str(cmd):
                problems.append(
                    f"firecrawl.required_maps_present[{tech}]: map_command must contain '--limit 5000'"
                )
            if entry.get("map_limit") != 5000:
                problems.append(
                    f"firecrawl.required_maps_present[{tech}]: map_limit must be 5000"
                )
    elif fc_auth not in {"unavailable", None}:
        problems.append(
            f"validation_evidence.firecrawl.auth: must be 'authenticated' or 'unavailable', got {fc_auth!r}"
        )

    osrc = _as_dict(evidence.get("opensrc"), "validation_evidence.opensrc", problems)
    osrc_cli = osrc.get("cli_version")
    osrc_fetched = _as_dict(
        osrc.get("fetched"),
        "validation_evidence.opensrc.fetched",
        problems,
    )
    if osrc_cli and osrc_cli != "unavailable":
        if not osrc_fetched:
            problems.append(
                "validation_evidence.opensrc: cli_version present but fetched is empty"
            )
        for repo, entry in osrc_fetched.items():
            entry = _as_dict(entry, f"opensrc.fetched[{repo}]", problems)
            kp = entry.get("key_paths")
            if not (isinstance(kp, list) and kp):
                problems.append(
                    f"opensrc.fetched[{repo}]: key_paths must be a non-empty list"
                )

    repo_ctx = _as_dict(
        evidence.get("repository_context"),
        "validation_evidence.repository_context",
        problems,
    )
    # repository_context is required for goal contracts produced by 1.6.0+,
    # but we accept its absence on legacy YAMLs (no plan_id rotation, no
    # workdir field on metadata) so the structural validator does not silently
    # invalidate already-shipped runtime ledgers. New writes ALWAYS set it.
    metadata = _as_dict(data.get("metadata"), "metadata", [])
    expects_repo_ctx = "workdir" in metadata or "repo_root" in metadata
    if expects_repo_ctx:
        for required in ("workdir", "repo_root", "key_paths", "claude_worktree"):
            if required not in repo_ctx:
                problems.append(
                    f"validation_evidence.repository_context: missing {required!r}"
                )
        key_paths = _as_list(
            repo_ctx.get("key_paths"),
            "validation_evidence.repository_context.key_paths",
            problems,
        )
        for idx, entry in enumerate(key_paths):
            if not (isinstance(entry, str) and entry.strip()):
                problems.append(
                    f"validation_evidence.repository_context.key_paths[{idx}]: must be a non-empty string"
                )
        claude_repo = _as_dict(
            repo_ctx.get("claude_worktree"),
            "validation_evidence.repository_context.claude_worktree",
            problems,
        )
        if claude_repo:
            if claude_repo.get("flag") != "--worktree":
                problems.append("validation_evidence.repository_context.claude_worktree.flag: must be '--worktree'")
            if claude_repo.get("short_flag") != "-w":
                problems.append("validation_evidence.repository_context.claude_worktree.short_flag: must be '-w'")
            template = claude_repo.get("directory_template")
            if not (isinstance(template, str) and ".claude/worktrees/<worktree-name>" in template):
                problems.append("validation_evidence.repository_context.claude_worktree.directory_template: must resolve to .claude/worktrees/<worktree-name>")

    _check_reconciliation_required(data, evidence, fc_maps, osrc_fetched, problems)
    _check_reconciliation_shape(data, problems)

    contract = _as_dict(
        data.get("coding_agent_execution_contract"),
        "coding_agent_execution_contract",
        problems,
    )
    if contract:
        executor = contract.get("executor")
        if executor not in EXECUTOR_CATALOG_PROFILES:
            valid = ", ".join(sorted(EXECUTOR_CATALOG_PROFILES))
            problems.append(
                f"coding_agent_execution_contract.executor: must be one of [{valid}], got {executor!r}"
            )
            # Skip the rest of the contract checks — they all reference the catalog.
            executor = None
        profile = EXECUTOR_CATALOG_PROFILES.get(executor or "")
        rule = contract.get("rule")
        if not (isinstance(rule, str) and rule.strip()):
            problems.append("coding_agent_execution_contract.rule: missing or empty")
        required_flags = _as_list(
            contract.get("required_flags"),
            "coding_agent_execution_contract.required_flags",
            problems,
        )
        flag_names: list[str] = []
        for entry in required_flags:
            entry = _as_dict(entry, "coding_agent_execution_contract.required_flags[*]", problems)
            name = entry.get("name") if entry else None
            placeholder = entry.get("placeholder") if entry else None
            # Catalogs for non-claude executors include bare subcommands (`run`)
            # alongside `--flag` entries. Treat any non-empty string as a valid
            # name; the substring-match below still enforces correctness against
            # the executor's profile.
            if not (isinstance(name, str) and name.strip()):
                problems.append(
                    f"coding_agent_execution_contract.required_flags[*].name: missing or empty"
                )
                continue
            flag_names.append(name)
            if not (isinstance(placeholder, str) and placeholder.strip()):
                problems.append(
                    f"coding_agent_execution_contract.required_flags[{name}].placeholder: missing or empty"
                )
        if profile:
            expected_flags = profile["flags"]
            missing_flags = [f for f in expected_flags if f not in flag_names]
            if missing_flags:
                problems.append(
                    f"coding_agent_execution_contract.required_flags: missing required flags {missing_flags}"
                )
        canonical = contract.get("canonical_invocation")
        if not (isinstance(canonical, str) and canonical.strip()):
            problems.append("coding_agent_execution_contract.canonical_invocation: missing or empty")
        elif profile:
            expected_binary = profile["binary"]
            if not canonical.lstrip().startswith(expected_binary + " ") and canonical.strip() != expected_binary:
                problems.append(
                    f"coding_agent_execution_contract.canonical_invocation: must start with '{expected_binary} '"
                )
            for flag in profile["flags"]:
                if flag not in canonical:
                    problems.append(
                        f"coding_agent_execution_contract.canonical_invocation: missing flag {flag}"
                    )
            legacy_rule_mentions_prompt = (
                uses_legacy_task_graph
                and "positional prompt argument" in str(contract.get("rule", ""))
            )
            if "<instructions-from-hermes-agent>" not in canonical and not legacy_rule_mentions_prompt:
                problems.append(
                    "coding_agent_execution_contract.canonical_invocation: missing positional prompt argument <instructions-from-hermes-agent>"
                )
        worktree = _as_dict(
            contract.get("worktree_directory"),
            "coding_agent_execution_contract.worktree_directory",
            problems,
        )
        if worktree:
            if worktree.get("flag") != "--worktree":
                problems.append("coding_agent_execution_contract.worktree_directory.flag: must be '--worktree'")
            if worktree.get("short_flag") != "-w":
                problems.append("coding_agent_execution_contract.worktree_directory.short_flag: must be '-w'")
            for key in ("root", "directory_template", "resolution_rule"):
                value = worktree.get(key)
                if not (isinstance(value, str) and value.strip()):
                    problems.append(f"coding_agent_execution_contract.worktree_directory.{key}: missing or empty")
            template = worktree.get("directory_template")
            if executor == "claude":
                if isinstance(template, str) and ".claude/worktrees/<worktree-name>" not in template:
                    problems.append("coding_agent_execution_contract.worktree_directory.directory_template: must resolve to .claude/worktrees/<worktree-name>")
            else:
                # Non-claude executors place worktrees under their own dotdir
                # (e.g. .codex/worktrees/, .hermes/worktrees/). The contract is
                # that the template ends with "<worktree-name>" so a downstream
                # agent can substitute the actual name; the dotdir component is
                # executor-specific and validated by the executor catalog
                # profile rather than by a hard-coded literal.
                if isinstance(template, str) and "<worktree-name>" not in template:
                    problems.append("coding_agent_execution_contract.worktree_directory.directory_template: must end with '<worktree-name>'")
        forbidden = _as_list(
            contract.get("forbidden_alternatives"),
            "coding_agent_execution_contract.forbidden_alternatives",
            problems,
        )
        if not forbidden:
            problems.append(
                "coding_agent_execution_contract.forbidden_alternatives: must list at least one forbidden alternative"
            )

    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_task_list_yaml.py <path-to-yaml>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"validate_task_list_yaml: file not found: {path}", file=sys.stderr)
        return 2
    problems = validate(path)
    if problems:
        for p in problems:
            print(f"FAIL: {p}", file=sys.stderr)
        return 1
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    task_count = sum(
        len((p or {}).get("tasks") or []) for p in (data.get("phases") or [])
    )
    principle_count = len((data.get("principles") or {}))
    print(f"OK: {task_count} tasks, {principle_count} principles, {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
