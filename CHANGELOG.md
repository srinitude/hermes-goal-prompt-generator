# Changelog

## 1.4.0 - Contrarian validation + reconciliation

- Adds `ContrarianValidator`, `Conflict`, and `Reconciliation` for falsification-first rechecks of Firecrawl, opensrc, principle coverage, phase topology, hard gates, helper paths, and coding-agent execution contracts.
- Emits `validation_reconciliation` into generated task-list YAMLs and validates the reconciliation block shape.
- Adds standalone `scripts/run_contrarian_validation.py` plus source-claim verifier probes.

## 1.3.0 - Coding Agent Execution Contract + paired TDD task list YAML

- Adds a mandatory `## Coding Agent Execution Contract` section to every generated Markdown goal prompt. The section pins the implementation pathway: every code/test/config/doc change made while executing the goal must originate from a `claude` CLI invocation that carries the full required flag set (`--p`, `--add-dir`, `--agent`, `--allow-dangerously-skip-permissions`, `--dangerously-skip-permissions`, `--debug-file`, `--effort max`, `--include-hook-events`, `--output-format stream-json`, `--include-partial-messages`, `--input-format stream-json`, `--json-schema`, `--settings`, `--strict-mcp-config`, `--system-prompt-file`, `--tools`, `--verbose`, `--worktree`).
- Generates a paired ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR TDD task list YAML on every successful goal generation. The YAML is the runtime state any coding agent dynamically updates; the Markdown is the immutable contract. New `tasklist` module exposes `build_task_list`, `write_task_list`, `task_list_path`, and `handoff_prompt`.
- CLI now writes both files, validates the YAML structurally, and prints the deterministic `/goal` handoff line.
- Adds `scripts/validate_task_list_yaml.py` enforcing: per-task field presence; ci/styleguide/guardrail/principle/dependency reference resolution; GREEN→RED traceability; phase-ordering invariant; RED phase `hard_gate`; Firecrawl `map --limit 5000` evidence shape; `opensrc` source citations; and the new `coding_agent_execution_contract` top-level block (executor, rule, required_flags, canonical_invocation, forbidden_alternatives).
- Adds Firecrawl `map --limit 5000` + Firecrawl-toolset URL-validation flow and the `opensrc` source-validation flow.
- Adds new references: `coding-agent-task-list-yaml.md`, `extending-the-mandatory-contract.md`, `firecrawl-cli-1-16-quirks.md`, `paradox-resolving-goal-prompts.md`, `real-implementation-goal-prompts.md`, `research-tool-readiness.md`, `runtime-server-goal-edits.md`.
- Adds a software-development-only final diff cleanup requirement to generated prompts.
- Adds a software-development-only software engineering core principles/rubric section.
- Validates that software-development prompts include the cleanup requirement and core principles/rubric while clear non-software prompts omit them.
- Adds regression coverage for built-in/shareable output equivalence.
- API change: `prepare_goal_prompt(prompt, ..., allow_existing_path=False)` now requires `allow_existing_path=True` to treat a path-shaped input as an existing `.md` file. Default behavior treats the input as raw prompt text. The CLI has a new `--input-file <path>` flag for the path-input case.
- Bumps `VERSION` (and the frontmatter `goal_prompt_generator_version` value validators accept) from `1.0.1` to `1.3.0`.

## 1.0.1 - Isolated generation refactor

- Refocuses `goal-prompt-generator` on explicit, isolated Markdown goal prompt generation.
- Removes packaged Hermes `/goal` preflight/source-integration patch content.
- Adds an isolated generation boundary section to generated Markdown.
- Updates validation to reject generated files that lack the isolation boundary.
- Clarifies that Hermes Agent's built-in `/goal` command is not intercepted or modified.

## 1.0.0 - Initial release

- Added Hermes Agent skill content, linked references/templates/scripts, standalone Python package, CLI, tests, examples, and CI workflow.
