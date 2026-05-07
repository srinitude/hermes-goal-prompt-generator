# Changelog

## 1.6.0 - Deep repository/codebase context exploration

- Adds `goal_prompt_generator.repository.repository_evidence(workdir)` — a stdlib-only snapshot of the invoking workdir: VCS state (head SHA, branch, remote, dirty flag), manifests, lockfiles, agent-context files (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules`, `.github/copilot-instructions.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`, `DESIGN.md`, `README.md`), CI configs, primary-language breakdown, top-level layout, Claude Code `--worktree`/`-w` directory resolution (`<repo_root>/.claude/worktrees/<worktree-name>`), and a curated absolute-path key-path list.
- Adds a new top-level `## Repository Context` section to every generated Markdown goal prompt; legacy 1.3.0–1.5.0 contracts on disk are still accepted by the validator without that section.
- Adds `validation_evidence.repository_context` to every paired YAML, plus `metadata.workdir`/`metadata.repo_root`, `agent_runtime_protocol.handoff_workdir`, `agent_runtime_protocol.claude_worktree_*`, and `coding_agent_execution_contract.worktree_directory`. Every task's `context_files` is seeded with the curated repository key paths so the downstream coding agent reads them before producing a diff.
- Plumbs `workdir` through `prepare_goal_prompt(prompt, workdir=...)`, `build_optimized_markdown(prompt, workdir=...)`, `write_task_list(..., workdir=...)`, and `build_task_list(..., workdir=...)`. Adds a new `--workdir <path>` flag to the helper CLI; default remains the cwd.
- Adds `ContrarianValidator.recheck_repository_key_path(workdir, key_path)` so the offline reconciliation pass downgrades vanished key paths to `downgraded_to_attempted` in `validation_reconciliation`.
- `scripts/validate_task_list_yaml.py` now requires the `repository_context` block whenever `metadata.workdir`/`metadata.repo_root` is set, including the `claude_worktree` block; older YAMLs without those fields remain accepted.
- Adds `references/repository-context-exploration.md` and a new pitfall (#42) covering the workdir-snapshot honesty rules.
- Bumps `VERSION` to `1.6.0` and adds `1.5.0` to `LEGACY_GENERATOR_VERSIONS`.
- Adds `tests/test_repository_evidence.py` (10 tests covering repository introspection, Claude worktree directory evidence, Markdown rendering, YAML wiring, structural validation, and legacy-version compatibility).

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
