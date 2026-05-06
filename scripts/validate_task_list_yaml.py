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
    "prerequisites",
    "dependencies",
    "blocking_tasks",
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

PHASE_ORDER = ("ANALYSIS", "BOOTSTRAP", "RED", "GREEN", "REFACTOR")

ALLOWED_STATUS = {"pending", "in_progress", "completed", "blocked", "cancelled"}

REQUIRED_CLAUDE_FLAGS = (
    "--p",
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
    "--settings",
    "--strict-mcp-config",
    "--system-prompt-file",
    "--tools",
    "--verbose",
    "--worktree",
)


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
                             "prerequisites", "dependencies", "blocking_tasks",
                             "validation_steps"):
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
            blocks = _as_list(task.get("blocking_tasks"), f"{tid}.blocking_tasks", problems)
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
            for ref in blocks:
                if not isinstance(ref, str):
                    continue
                if ref not in idset:
                    problems.append(f"{tid}: dangling blocking_tasks ref {ref!r}")
                    continue
                if ref in task_to_phase and tid in task_to_phase:
                    if task_to_phase[ref] < task_to_phase[tid]:
                        problems.append(
                            f"{tid}: blocking_tasks ref {ref!r} lives in an earlier phase (a task cannot block work that has already happened)"
                        )

    if green_task_ids and red_task_ids:
        for phase in phases:
            if not isinstance(phase, dict) or phase.get("name") != "GREEN":
                continue
            for task in _as_list(phase.get("tasks"), "GREEN.tasks", problems):
                if not isinstance(task, dict):
                    continue
                tid = task.get("id")
                covers_red = bool(
                    set(_as_list(task.get("dependencies"), "", []))
                    | set(_as_list(task.get("prerequisites"), "", []))
                ) and any(
                    ref in red_task_ids
                    for ref in (
                        _as_list(task.get("dependencies"), "", [])
                        + _as_list(task.get("prerequisites"), "", [])
                    )
                )
                if not covers_red:
                    problems.append(
                        f"{tid}: GREEN task must reference >=1 RED task in dependencies or prerequisites"
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

    contract = _as_dict(
        data.get("coding_agent_execution_contract"),
        "coding_agent_execution_contract",
        problems,
    )
    if contract:
        executor = contract.get("executor")
        if executor != "claude":
            problems.append(
                f"coding_agent_execution_contract.executor: must be 'claude', got {executor!r}"
            )
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
            if not (isinstance(name, str) and name.startswith("--")):
                problems.append(
                    f"coding_agent_execution_contract.required_flags[*].name: must start with '--', got {name!r}"
                )
                continue
            flag_names.append(name)
            if not (isinstance(placeholder, str) and placeholder.strip()):
                problems.append(
                    f"coding_agent_execution_contract.required_flags[{name}].placeholder: missing or empty"
                )
        missing_flags = [f for f in REQUIRED_CLAUDE_FLAGS if f not in flag_names]
        if missing_flags:
            problems.append(
                f"coding_agent_execution_contract.required_flags: missing required flags {missing_flags}"
            )
        canonical = contract.get("canonical_invocation")
        if not (isinstance(canonical, str) and canonical.strip()):
            problems.append("coding_agent_execution_contract.canonical_invocation: missing or empty")
        else:
            if not canonical.lstrip().startswith("claude "):
                problems.append(
                    "coding_agent_execution_contract.canonical_invocation: must start with 'claude '"
                )
            for flag in REQUIRED_CLAUDE_FLAGS:
                if flag not in canonical:
                    problems.append(
                        f"coding_agent_execution_contract.canonical_invocation: missing flag {flag}"
                    )
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
