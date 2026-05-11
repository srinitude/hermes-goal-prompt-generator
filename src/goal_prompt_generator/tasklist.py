from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

import yaml

from .constants import CLAUDE_CLI_EXECUTION_CONTRACT, CLAUDE_CLI_REQUIRED_FLAGS, GOAL_RUNTIME_CONTINUATION_CONTRACT
from .contrarian_validation import ContrarianValidator
from .executors import (
    EXECUTOR_CATALOG,
    canonical_invocation_for,
    detect_installed_executors,
    resolve_executor_choice,
)
from .repository import repository_evidence
from .research import research_evidence

PHASES = ("ANALYSIS", "BOOTSTRAP", "RED", "GREEN", "REFACTOR")
PRINCIPLES = {
    "P1": "Treat programs as descriptions before execution.",
    "P2": "Make expected failure part of the domain model.",
    "P3": "Separate recoverable failures from defects.",
    "P4": "Preserve failure causes, not just messages.",
    "P5": "Design every resource with a lifecycle.",
    "P6": "Make cancellation and interruption first-class.",
    "P7": "Use structured concurrency instead of ad hoc async work.",
    "P8": "Push dependencies to the boundary.",
    "P9": "Keep service interfaces clean; move construction complexity elsewhere.",
    "P10": "Validate and transform data at boundaries.",
    "P11": "Treat configuration as typed, validated, and redacted.",
    "P12": "Build timeout and retry policy into external calls.",
    "P13": "Optimize based on measurement, not intuition.",
    "P14": "Make observability part of execution, not an afterthought.",
    "P15": "Cache deliberately, with invalidation semantics.",
    "P16": "Serialize shared-state updates when consistency matters.",
    "P17": "Compose small units into larger workflows.",
    "P18": "Keep provider-specific details behind stable application contracts.",
}


def claude_cli_canonical_invocation() -> str:
    parts = ["claude"]
    for name, placeholder in CLAUDE_CLI_REQUIRED_FLAGS:
        parts.append(name if placeholder == "<no-arg>" else f"{name} {placeholder}")
    parts.append('"<instructions-from-hermes-agent>"')
    return " ".join(parts)


def coding_agent_execution_contract_block(
    claude_worktree: dict[str, Any] | None = None,
    executor: str = "claude",
    executor_worktrees: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    worktree = claude_worktree or {}
    executor_worktrees = executor_worktrees or {}
    if executor == "claude":
        # Legacy / default path: keep the Claude-Code-shaped contract bit-for-bit so
        # already-generated YAMLs and the structural validator's substring match keep
        # passing.
        return {
            "executor": "claude",
            "rule": CLAUDE_CLI_EXECUTION_CONTRACT,
            "required_flags": [
                {"name": name, "placeholder": placeholder}
                for name, placeholder in CLAUDE_CLI_REQUIRED_FLAGS
            ],
            "canonical_invocation": claude_cli_canonical_invocation(),
            "worktree_directory": {
                "flag": worktree.get("flag") or "--worktree",
                "short_flag": worktree.get("short_flag") or "-w",
                "root": worktree.get("root") or "<repo-root>/.claude/worktrees",
                "directory_template": worktree.get("directory_template") or "<repo-root>/.claude/worktrees/<worktree-name>",
                "resolution_rule": worktree.get("resolution_rule") or "Resolve the --worktree/-w name under the active repository root before launching Claude Code.",
            },
            "forbidden_alternatives": [
                "Implementing changes through any tool other than `claude` (no inline shell scripts, no other CLIs, no editor sessions, no manual file edits).",
                "Omitting, renaming, aliasing, or substituting any flag in the required set.",
                "Paraphrasing the flag set — the exact spelling above is the contract.",
            ],
        }
    # Non-claude executor: pull contract shape from the catalog. The worktree
    # directory_template comes from the executor_worktrees evidence (which
    # resolves under the active Hermes worktree's repo_root), guaranteeing every
    # CLI roots its worktree inside the active Hermes .worktrees/hermes-*
    # checkout — not at an arbitrary parent.
    if executor not in EXECUTOR_CATALOG:
        raise ValueError(f"unknown executor: {executor!r}; not in catalog")
    entry = EXECUTOR_CATALOG[executor]
    binary = entry["binary"]
    catalog_template = entry.get("worktree_directory_template", f"<repo-root>/.{executor}/worktrees/<worktree-name>")
    resolved = executor_worktrees.get(executor) or {}
    template = resolved.get("directory_template") or catalog_template
    root_dir = resolved.get("root") or f"<repo-root>/.{executor}/worktrees"
    resolution_rule = resolved.get("resolution_rule") or (
        f"Resolve the --worktree/-w name under the active repository root before launching {entry['display_name']}."
    )
    flag_list = [
        {"name": name, "placeholder": placeholder}
        for name, placeholder in entry["required_flags"]
    ]
    canonical = canonical_invocation_for(executor)
    rule = (
        f"All implementation work that satisfies this goal MUST be performed by invoking the "
        f"`{binary}` CLI ({entry['display_name']}) with the full required flag set "
        f"({', '.join('`' + f['name'] + '`' for f in flag_list)}). The Hermes Agent "
        f"instructions for this goal are passed as the CLI's prompt argument; every flag is "
        f"mandatory and must be populated with a concrete, validated value before launch. "
        f"Non-interactive proof: {entry['non_interactive_proof']}. Worktree directory resolves "
        f"to {template} inside the active Hermes worktree (repo_root recorded in Repository "
        f"Context). Do not substitute, omit, or rename any flag, and do not implement the "
        f"requirements through any other mechanism (no other CLIs, no editor sessions, no "
        f"manual file edits) — every change to the repository must originate from a `{binary}` "
        f"invocation that carries the full flag set above."
    )
    if executor == "hermes" and entry.get("model_selection_rule"):
        rule += " " + entry["model_selection_rule"]
    return {
        "executor": executor,
        "rule": rule,
        "required_flags": flag_list,
        "canonical_invocation": canonical,
        "worktree_directory": {
            "flag": "--worktree",
            "short_flag": "-w",
            "root": root_dir,
            "directory_template": template,
            "resolution_rule": resolution_rule,
        },
        "forbidden_alternatives": [
            f"Implementing changes through any tool other than `{binary}` (no inline shell scripts, no other CLIs, no editor sessions, no manual file edits).",
            "Omitting, renaming, aliasing, or substituting any flag in the required set.",
            "Paraphrasing the flag set — the exact spelling above is the contract.",
            "Placing the executor's worktree outside the active Hermes worktree (the worktree directory MUST resolve under the active repo_root from Repository Context).",
        ],
    }


def task_list_path(goal_path: Path) -> Path:
    name = goal_path.name.removesuffix("-goal.md")
    candidate = goal_path.with_name(f"{name}-tdd-tasks.yaml")
    if not candidate.exists():
        return candidate
    for idx in range(2, 1000):
        numbered = goal_path.with_name(f"{name}-tdd-tasks-{idx}.yaml")
        if not numbered.exists():
            return numbered
    raise FileExistsError(f"too many task-list filename collisions for {candidate.name}")


def task(tid: str, title: str, deps: list[str], principles: list[str]) -> dict[str, Any]:
    return {
        "id": tid,
        "title": title,
        "status": "pending",
        "dependencies": deps,
        "validation_steps": [
            "Run the referenced ci_commands exactly and record observable outcomes.",
            "Append only durable discoveries to learnings and gotchas.",
            "If this is not the final validated task, end the assistant response with `GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued` and name the next task id.",
        ],
        "ci_commands": ["CC_VALIDATE_GOAL", "CC_VALIDATE_TASKS"],
        "styleguide_rules": ["S1", "S2", "S3", "S4"],
        "guardrails": ["G1", "G2", "G3", "G4", "G5"],
        "learnings": [],
        "gotchas": [],
        "context_files": [],
        "context_urls": [],
        "principle_ids": principles,
    }


def _validation_reconciliation(goal_path: Path, yaml_dict: dict[str, Any]) -> dict[str, Any]:
    """Replay contrarian re-verification offline against the freshly built YAML.

    Runs only filesystem/dict checks (no network): principles, topology, hard_gate,
    coding-agent execution contract, repository key-path existence, and a replay of
    cached Firecrawl map entries when their on-disk JSON is reachable. The result
    becomes the YAML's top-level ``validation_reconciliation`` block so optimistic
    claims cannot land silently.
    """
    md = goal_path.read_text(encoding="utf-8") if goal_path.exists() else ""
    validator = ContrarianValidator()
    validator.recheck_principle_coverage(yaml_dict)
    validator.recheck_phase_dependency_topology(yaml_dict)
    validator.recheck_hard_gate_text(yaml_dict)
    validator.recheck_coding_agent_execution_contract(md, yaml_dict)
    repo = (yaml_dict.get("validation_evidence") or {}).get("repository_context") or {}
    for key_path in (repo.get("key_paths") or []):
        validator.recheck_repository_key_path(repo.get("workdir", ""), key_path)
    firecrawl = (yaml_dict.get("validation_evidence") or {}).get("firecrawl") or {}
    for tech, entry in (firecrawl.get("required_maps_present") or {}).items():
        data = entry or {}
        validator.recheck_firecrawl_map(tech, data.get("file", ""), data.get("url_count", -1))
    opensrc = (yaml_dict.get("validation_evidence") or {}).get("opensrc") or {}
    for slug, entry in (opensrc.get("fetched") or {}).items():
        for key_path in ((entry or {}).get("key_paths") or []):
            validator.recheck_opensrc_path_exists(slug, key_path, "")
    return validator.reconcile().to_dict()


def build_task_list(
    goal_path: Path,
    task_path: Path,
    source_hash: str,
    title: str,
    workdir: str | Path | None = None,
    repository: dict[str, Any] | None = None,
    executor: str | None = None,
) -> dict[str, Any]:
    all_principles = list(PRINCIPLES)
    tasks = {
        "ANALYSIS": [task("A01", "Read the immutable goal contract and derive execution context", [], all_principles[:4]),
                     task("A02", "Identify required docs, source repositories, and validation evidence", ["A01"], all_principles[4:8])],
        "BOOTSTRAP": [task("B01", "Establish local gates and baseline repository state", ["A01", "A02"], all_principles[8:12])],
        "RED": [task("R00", "Commit RED kickoff before production edits", ["B01"], all_principles[12:15]),
                task("R01", "Write failing user-facing contract tests and observe the right failure", ["R00"], all_principles[15:])],
        "GREEN": [task("G01", "Implement the minimum real solution that satisfies RED evidence", ["R00", "R01"], all_principles)],
        "REFACTOR": [task("X01", "Run ruthless final-diff cleanup and full validation", ["G01"], all_principles)],
    }
    goal = str(goal_path.resolve())
    yaml_file = str(task_path.resolve())
    validator = str((Path(__file__).resolve().parents[2] / "scripts" / "validate_task_list_yaml.py").resolve())
    quoted_goal = shlex.quote(goal)
    quoted_yaml = shlex.quote(yaml_file)
    quoted_validator = shlex.quote(validator)
    repo_evidence = repository if repository is not None else repository_evidence(workdir)
    repo_key_paths = list(repo_evidence.get("key_paths") or [])
    claude_worktree = repo_evidence.get("claude_worktree") or {}
    executor_worktrees = repo_evidence.get("executor_worktrees") or {}
    installed_clis = detect_installed_executors()
    resolved_executor = resolve_executor_choice(explicit=executor, installed=installed_clis)
    catalog_view = {
        cli: {
            "display_name": entry["display_name"],
            "binary": entry["binary"],
            "homepage": entry.get("homepage", ""),
            "docs": entry.get("docs", ""),
            "required_flags": [
                {"name": name, "placeholder": placeholder}
                for name, placeholder in entry["required_flags"]
            ],
            "worktree_directory_template": entry.get("worktree_directory_template", ""),
            "non_interactive_proof": entry.get("non_interactive_proof", ""),
            **({"model_selection_rule": entry["model_selection_rule"]} if entry.get("model_selection_rule") else {}),
        }
        for cli, entry in EXECUTOR_CATALOG.items()
    }
    data = {
        "metadata": {
            "plan_id": task_path.stem,
            "version": "1.0.0",
            "source_goal_markdown_path": goal,
            "source_prompt_hash": source_hash,
            "workdir": repo_evidence.get("workdir", ""),
            "repo_root": repo_evidence.get("repo_root", ""),
            "hard_invariants": [
                "Markdown contract is immutable",
                "Only task status, learnings, and gotchas are mutable",
                "Repository key paths must exist before any edit and must be re-verified at execution time",
                "Claude Code --worktree/-w directory must resolve under the active Hermes worktree repo root at .claude/worktrees/<worktree-name>",
                "Hermes /goal execution must continue autonomously until all acceptance criteria validate or the external goal max_turns budget pauses the loop",
                "Non-final assistant responses must end with GOAL_RUNTIME_STATUS: CONTINUE and a next YAML task id",
            ],
        },
        "validation_evidence": {
            **research_evidence(task_path.parent),
            "repository_context": repo_evidence,
        },
        "styleguide_rules": {
            "S1": "Keep files and constructs small, focused, and readable.",
            "S2": "Tests validate user-facing behavior, not implementation details.",
            "S3": "No TODOs, mocks, stubs, placeholders, or fake behavior.",
            "S4": "Preserve existing repository conventions unless the contract requires change.",
        },
        "guardrails": {
            "G1": "Do not execute work outside the goal contract.",
            "G2": "Do not mutate immutable YAML fields.",
            "G3": "Do not make GREEN production edits before the RED hard gate clears.",
            "G4": "Record non-bypassable credential, approval, legal, payment, or safety constraints in learnings/gotchas without asking the user unless every autonomous path is exhausted.",
            "G5": "For Hermes /goal execution, keep going autonomously on non-final turns and end with GOAL_RUNTIME_STATUS: CONTINUE plus the next YAML task id.",
        },
        "ci_commands": {
            "CC_VALIDATE_GOAL": f"test -f {quoted_goal}",
            "CC_VALIDATE_TASKS": f"python3 {quoted_validator} {quoted_yaml}",
        },
        "principles": PRINCIPLES,
        "phases": [{"name": name, **({"hard_gate": "No GREEN production-code edits before R00 and all RED tests are committed and observed failing for the right reason."} if name == "RED" else {}), "tasks": phase_tasks} for name, phase_tasks in tasks.items()],
        "agent_runtime_protocol": {
            "phase_order": list(PHASES),
            "mutable_fields": ["status", "learnings", "gotchas"],
            "immutable_fields": ["id", "title", "dependencies", "validation_steps", "ci_commands", "styleguide_rules", "guardrails", "context_files", "context_urls", "principle_ids"],
            "dependency_graph_semantics": "dependencies is the only task graph edge; model prerequisite gate checks as explicit tasks and infer reverse blockers from dependent tasks.",
            "resume_protocol": "Read the Markdown contract first, then continue from the first pending YAML task in phase order.",
            "handoff_goal_markdown": goal,
            "handoff_task_list_yaml": yaml_file,
            "handoff_workdir": repo_evidence.get("workdir", ""),
            "claude_worktree_root": claude_worktree.get("root", ""),
            "claude_worktree_directory_template": claude_worktree.get("directory_template", ""),
            "claude_worktree_resolution": claude_worktree.get("resolution_rule", ""),
            "goal_manager_continuation_contract": {
                "runtime": "hermes /goal",
                "source_markdown_section": "## Goal Runtime Continuation Contract",
                "contract": GOAL_RUNTIME_CONTINUATION_CONTRACT,
                "continue_until": "all acceptance criteria validate or Hermes goal max_turns pauses the loop",
                "non_final_response_marker": "GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued",
                "final_response_marker": "GOAL_RUNTIME_STATUS: COMPLETE — all acceptance criteria and validations satisfied",
                "human_input_policy": "do not ask the user; choose autonomous fallbacks and update YAML learnings/gotchas",
                "judge_shape": "Avoid saying the overall goal is complete, blocked, unachievable, waiting for input, or needing human action on non-final turns.",
            },
        },
        "coding_agent_execution_contract": coding_agent_execution_contract_block(claude_worktree, executor=resolved_executor, executor_worktrees=executor_worktrees),
        "coding_agent_alternatives": {
            "selected_executor": resolved_executor,
            "selection_source": (
                "explicit" if executor
                else "env:GOAL_PROMPT_GENERATOR_EXECUTOR" if "GOAL_PROMPT_GENERATOR_EXECUTOR" in __import__("os").environ
                else "auto:first-installed-in-catalog"
            ),
            "catalog": catalog_view,
            "installed_clis": installed_clis,
            "configuration_knobs": {
                "helper_flag": "--executor <catalog-key>",
                "python_api_kwarg": "executor=<catalog-key>",
                "environment_variable": "GOAL_PROMPT_GENERATOR_EXECUTOR",
                "valid_catalog_keys": sorted(EXECUTOR_CATALOG.keys()),
            },
            "fallback_rules": {
                "fallback_chain": "Try the explicitly configured executor; if unavailable, fall back to the first available installed CLI in catalog priority order; if none, default to `claude` and surface a blocker.",
                "continuity_invariant": "Every executor MUST honor the GoalManager continuation contract (autonomy, GOAL_RUNTIME_STATUS: CONTINUE/COMPLETE markers, no human input on non-final turns). Switching executors does not weaken the contract.",
                "model_selection_for_hermes": EXECUTOR_CATALOG.get("hermes", {}).get("model_selection_rule", ""),
            },
        },
    }
    for phase in data["phases"]:
        for item in phase["tasks"]:
            item["context_files"] = [goal, yaml_file, *repo_key_paths]
    data["validation_reconciliation"] = _validation_reconciliation(goal_path, data)
    return data


def write_task_list(
    goal_path: Path,
    source_hash: str,
    title: str,
    workdir: str | Path | None = None,
    repository: dict[str, Any] | None = None,
    executor: str | None = None,
) -> Path:
    path = task_list_path(goal_path)
    data = build_task_list(goal_path, path, source_hash, title, workdir=workdir, repository=repository, executor=executor)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def handoff_prompt(goal_path: Path, task_path: Path) -> str:
    goal = str(goal_path.resolve())
    tasks = str(task_path.resolve())
    return (
        "/goal Execute the goal contract at "
        + goal
        + " by walking the paired TDD task list at "
        + tasks
        + " in strict ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR order. "
        + "This is a Hermes /goal runtime: continue autonomously until all acceptance criteria validate or Hermes goal max_turns pauses the loop. "
        + "Do not ask the user for input, guidance, confirmation, or permission on non-final turns; choose safe autonomous fallbacks and update only YAML `status`, `learnings`, and `gotchas`. "
        + "End every non-final response with `GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued` and the next YAML task id; use `GOAL_RUNTIME_STATUS: COMPLETE — all acceptance criteria and validations satisfied` only after the full contract validates. "
        + "Treat the Markdown file as the immutable contract and the YAML as the runtime state. Honor the RED phase `hard_gate` (no GREEN production-code edits before the R00 kickoff and all RED tests are committed and observed failing for the right reason). "
        + "Use every `dependencies`, `ci_commands`, `styleguide_rules`, `guardrails`, `validation_steps`, `context_files`, `principle_ids`, and `context_urls` reference verbatim. Operate autonomously per the goal's autonomy requirement, do not execute work outside the contract, and finish with the ruthless final-diff cleanup pass defined in the goal Markdown."
    )
