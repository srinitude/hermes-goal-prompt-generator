from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

import yaml

from .constants import CLAUDE_CLI_EXECUTION_CONTRACT, CLAUDE_CLI_REQUIRED_FLAGS
from .contrarian_validation import ContrarianValidator
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
    return " ".join(parts)


def coding_agent_execution_contract_block() -> dict[str, Any]:
    return {
        "executor": "claude",
        "rule": CLAUDE_CLI_EXECUTION_CONTRACT,
        "required_flags": [
            {"name": name, "placeholder": placeholder}
            for name, placeholder in CLAUDE_CLI_REQUIRED_FLAGS
        ],
        "canonical_invocation": claude_cli_canonical_invocation(),
        "forbidden_alternatives": [
            "Implementing changes through any tool other than `claude` (no inline shell scripts, no other CLIs, no editor sessions, no manual file edits).",
            "Omitting, renaming, aliasing, or substituting any flag in the required set.",
            "Paraphrasing the flag set — the exact spelling above is the contract.",
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


def task(tid: str, title: str, deps: list[str], blocks: list[str], principles: list[str]) -> dict[str, Any]:
    return {
        "id": tid,
        "title": title,
        "status": "pending",
        "prerequisites": [] if tid.startswith(("A", "B")) else deps,
        "dependencies": deps,
        "blocking_tasks": blocks,
        "validation_steps": [
            "Run the referenced ci_commands exactly and record observable outcomes.",
            "Append only durable discoveries to learnings and gotchas.",
        ],
        "ci_commands": ["CC_VALIDATE_GOAL", "CC_VALIDATE_TASKS"],
        "styleguide_rules": ["S1", "S2", "S3", "S4"],
        "guardrails": ["G1", "G2", "G3", "G4"],
        "learnings": [],
        "gotchas": [],
        "context_files": [],
        "context_urls": [],
        "principle_ids": principles,
    }


def _validation_reconciliation(goal_path: Path, yaml_dict: dict[str, Any]) -> dict[str, Any]:
    """Replay contrarian re-verification offline against the freshly built YAML.

    Runs only filesystem/dict checks (no network): principles, topology, hard_gate,
    coding-agent execution contract, and a replay of cached Firecrawl map entries
    when their on-disk JSON is reachable. The result becomes the YAML's top-level
    ``validation_reconciliation`` block so optimistic claims cannot land silently.
    """
    md = goal_path.read_text(encoding="utf-8") if goal_path.exists() else ""
    validator = ContrarianValidator()
    validator.recheck_principle_coverage(yaml_dict)
    validator.recheck_phase_dependency_topology(yaml_dict)
    validator.recheck_hard_gate_text(yaml_dict)
    validator.recheck_coding_agent_execution_contract(md, yaml_dict)
    firecrawl = (yaml_dict.get("validation_evidence") or {}).get("firecrawl") or {}
    for tech, entry in (firecrawl.get("required_maps_present") or {}).items():
        data = entry or {}
        validator.recheck_firecrawl_map(tech, data.get("file", ""), data.get("url_count", -1))
    opensrc = (yaml_dict.get("validation_evidence") or {}).get("opensrc") or {}
    for slug, entry in (opensrc.get("fetched") or {}).items():
        for key_path in ((entry or {}).get("key_paths") or []):
            validator.recheck_opensrc_path_exists(slug, key_path, "")
    return validator.reconcile().to_dict()


def build_task_list(goal_path: Path, task_path: Path, source_hash: str, title: str) -> dict[str, Any]:
    all_principles = list(PRINCIPLES)
    tasks = {
        "ANALYSIS": [task("A01", "Read the immutable goal contract and derive execution context", [], ["B01"], all_principles[:4]),
                     task("A02", "Identify required docs, source repositories, and validation evidence", ["A01"], ["B01"], all_principles[4:8])],
        "BOOTSTRAP": [task("B01", "Establish local gates and baseline repository state", ["A01", "A02"], ["R00"], all_principles[8:12])],
        "RED": [task("R00", "Commit RED kickoff before production edits", ["B01"], ["G01"], all_principles[12:15]),
                task("R01", "Write failing user-facing contract tests and observe the right failure", ["R00"], ["G01"], all_principles[15:])],
        "GREEN": [task("G01", "Implement the minimum real solution that satisfies RED evidence", ["R00", "R01"], ["X01"], all_principles)],
        "REFACTOR": [task("X01", "Run ruthless final-diff cleanup and full validation", ["G01"], [], all_principles)],
    }
    goal = str(goal_path.resolve())
    yaml_file = str(task_path.resolve())
    validator = str((Path(__file__).resolve().parents[2] / "scripts" / "validate_task_list_yaml.py").resolve())
    quoted_goal = shlex.quote(goal)
    quoted_yaml = shlex.quote(yaml_file)
    quoted_validator = shlex.quote(validator)
    data = {
        "metadata": {
            "plan_id": task_path.stem,
            "version": "1.0.0",
            "source_goal_markdown_path": goal,
            "source_prompt_hash": source_hash,
            "hard_invariants": ["Markdown contract is immutable", "Only task status, learnings, and gotchas are mutable"],
        },
        "validation_evidence": research_evidence(task_path.parent),
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
            "G4": "Stop and record blockers when credentials, approvals, or safety constraints are required.",
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
            "immutable_fields": ["id", "title", "prerequisites", "dependencies", "blocking_tasks", "validation_steps", "ci_commands", "styleguide_rules", "guardrails", "context_files", "context_urls", "principle_ids"],
            "resume_protocol": "Read the Markdown contract first, then continue from the first pending YAML task in phase order.",
            "handoff_goal_markdown": goal,
            "handoff_task_list_yaml": yaml_file,
        },
        "coding_agent_execution_contract": coding_agent_execution_contract_block(),
    }
    for phase in data["phases"]:
        for item in phase["tasks"]:
            item["context_files"] = [goal, yaml_file]
    data["validation_reconciliation"] = _validation_reconciliation(goal_path, data)
    return data


def write_task_list(goal_path: Path, source_hash: str, title: str) -> Path:
    path = task_list_path(goal_path)
    data = build_task_list(goal_path, path, source_hash, title)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def handoff_prompt(goal_path: Path, task_path: Path) -> str:
    return "/goal Execute the goal contract at " + str(goal_path.resolve()) + " by walking the paired TDD task list at " + str(task_path.resolve()) + " in strict ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR order. Treat the Markdown file as the immutable contract and the YAML as the runtime state; mutate only `status`, `learnings`, and `gotchas` per task. Honor the RED phase `hard_gate` (no GREEN production-code edits before the R00 kickoff and all RED tests are committed and observed failing for the right reason). Use every `ci_commands`, `styleguide_rules`, `guardrails`, `validation_steps`, `context_files`, `principle_ids`, and `context_urls` reference verbatim. Operate autonomously per the goal's autonomy requirement, do not execute work outside the contract, and finish with the ruthless final-diff cleanup pass defined in the goal Markdown."
