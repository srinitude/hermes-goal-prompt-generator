# goal-prompt-generator

[![skills.sh](https://skills.sh/b/srinitude/hermes-goal-prompt-generator)](https://skills.sh/s/srinitude/hermes-goal-prompt-generator)
[![Quality](https://github.com/srinitude/hermes-goal-prompt-generator/actions/workflows/quality.yml/badge.svg)](https://github.com/srinitude/hermes-goal-prompt-generator/actions/workflows/quality.yml)
[![Release](https://img.shields.io/github/v/release/srinitude/hermes-goal-prompt-generator?include_prereleases&sort=semver)](https://github.com/srinitude/hermes-goal-prompt-generator/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Hermes Agent skill and CLI that turns one raw goal prompt into two paired artifacts — an isolated, optimized Markdown goal contract and a paired ANALYSIS / BOOTSTRAP / RED / GREEN / REFACTOR TDD task-list YAML — plus one printed `/goal …` handoff line, without ever executing the requested goal.**

`goal-prompt-generator` preserves the user's original intent, adds deterministic metadata, detects the domain, resolves ambiguity with explicit assumptions, injects autonomy, Hermes `/goal` runtime continuation discipline, software-development constraints, software engineering core principles, repository-context introspection, Firecrawl + `opensrc` research/source validation, and a contrarian re-verification pass — then writes both files, runs structural validators, and prints a handoff `/goal` line as a **paste-target only**.

It is intentionally **not** a Hermes `/goal` preflight hook, slash-command interceptor, or goal-loop middleware. It never modifies or intercepts Hermes Agent's built-in `/goal` command, and it never runs the generated contract.

---

## What you get

- A complete Hermes Agent skill package in [`skills/goal-prompt-generator/`](skills/goal-prompt-generator).
- Linked skill references, templates, and scripts in [`skills/goal-prompt-generator/references/`](skills/goal-prompt-generator/references), [`skills/goal-prompt-generator/templates/`](skills/goal-prompt-generator/templates), and [`skills/goal-prompt-generator/scripts/`](skills/goal-prompt-generator/scripts) — including playbooks for the **12-executor coding-agent catalog**, **fallback alternatives for Firecrawl/opensrc/Claude Code when they are unavailable**, cross-platform port goals, third-party OSS PR goals, paradox-resolving goals, real-implementation goals, per-provider parity goals, skill-authoring goals, retargeting an existing goal's runtime, contrarian validation, repository-context exploration, the Claude CLI execution syntax, the Firecrawl 1.16 CLI quirks, and the standalone-repo release packaging workflow.
- A standalone Python package in [`skills/goal-prompt-generator/src/goal_prompt_generator`](skills/goal-prompt-generator/src/goal_prompt_generator).
- A CLI command: `goal-prompt-generator` (entry point in `pyproject.toml`).
- Standalone validator scripts in [`skills/goal-prompt-generator/scripts/`](skills/goal-prompt-generator/scripts):
  - `validate_skill.py` — skill packaging validator.
  - `validate_task_list_yaml.py` — structural validator for the companion TDD task-list YAML (catalog-aware: enforces every executor's required-flag set).
  - `validate_source_claims.py` — deterministic pre-flight verifier for opensrc repo caches, cited file paths, host reachability, Firecrawl usability, and helper presence.
  - `probe_firecrawl_reachability.py` — L7-RST probe that distinguishes the four Firecrawl reachability modes.
  - `run_contrarian_validation.py` — entry point for the contrarian re-verification pass.
- A test suite covering metadata, domain detection, non-execution guardrails, isolated generation boundaries, software-specific cleanup, software engineering principles, repository-context evidence, research-tool evidence, source-claim verification, contrarian validation, **the 12-executor catalog with per-executor worktree rules and continuation-contract preservation**, file writing, reuse detection, regeneration, copy equivalence, and filename collision behavior. 91 tests total.

---

## What this does not do

- It does **not** run automatically inside `/goal`.
- It does **not** patch `cli.py`, `gateway/run.py`, `tui_gateway/server.py`, or `hermes_cli/goals.py`.
- It does **not** queue generated prompts into the persistent goal loop.
- It does **not** execute the generated goal.
- It does **not** execute the printed handoff `/goal …` line — that line is a paste-target only.

If you want to execute a generated prompt later, intentionally pass the saved Markdown file (or its absolute path together with the companion YAML) to your chosen workflow yourself.

---

## Quick install as a Hermes skill

```bash
git clone https://github.com/srinitude/hermes-goal-prompt-generator.git
cd hermes-goal-prompt-generator

mkdir -p ~/.hermes/skills/software-development
ln -sfn "$(pwd)/skills/goal-prompt-generator" ~/.hermes/skills/software-development/goal-prompt-generator

hermes skills list | grep goal-prompt-generator
```

Then start a fresh Hermes session and load it explicitly when needed:

```bash
hermes -s goal-prompt-generator
```

Or inside Hermes:

```text
/skill goal-prompt-generator
```

> Restart Hermes or use `/reset` after installing so the skill loader sees the new skill.

---

## Standalone CLI usage

The generator is deterministic Python and does not call an LLM. Firecrawl and `opensrc` are only invoked when the goal references technologies whose docs/source the generator must validate, and only when those CLIs are present and authenticated.

Using `mise`:

```bash
mise run setup
mise run smoke
```

Using `uv` directly:

```bash
uv run --with-editable . goal-prompt-generator --json "Build a FastAPI API with tests"
```

Using the repository script without installing the package:

```bash
python skills/goal-prompt-generator/scripts/generate_goal_prompt.py --json "Build a FastAPI API with tests"
```

### Pick the coding-agent CLI (executor)

The generated contract pins which coding-agent CLI executes the work. By default the executor is **Claude Code** (`claude`), but the generator probes your machine for every catalog entry and you can target any of them:

```bash
# Use the default (Claude Code) — same as omitting --executor
python skills/goal-prompt-generator/scripts/generate_goal_prompt.py --json "Build a FastAPI API with tests"

# Target OpenAI Codex
python skills/goal-prompt-generator/scripts/generate_goal_prompt.py --executor codex --json "..."

# Target Hermes Agent itself with a configurable model + reasoning effort
python skills/goal-prompt-generator/scripts/generate_goal_prompt.py --executor hermes --json "..."

# Or set the environment variable
export GOAL_PROMPT_GENERATOR_EXECUTOR=opencode
python skills/goal-prompt-generator/scripts/generate_goal_prompt.py --json "..."
```

The full 12-entry catalog: `claude`, `codex`, `opencode`, `gemini`, `cursor`, `aider`, `pi`, `qwen`, `goose`, `amp`, `crush`, `hermes`. See [`skills/goal-prompt-generator/references/executor-fallbacks-and-model-selection.md`](skills/goal-prompt-generator/references/executor-fallbacks-and-model-selection.md) for the per-executor required-flag set and the Hermes-as-executor model-selection rule.

### Output

Output is written to `~/.hermes/goal-prompts/` by default (created on first use):

- `<project>-<intent>-goal.md` — the immutable Markdown contract.
- `<project>-<intent>-tdd-tasks.yaml` — the mutable companion TDD task list YAML.

The skill also prints exactly one final line beginning with `/goal …` that names every generated artifact by absolute path, front-loads the `GOAL_RUNTIME_STATUS: CONTINUE` continuation contract, and describes the deterministic work required to execute the spec. **That printed line is not run** — it is a paste-target for the user or a downstream orchestrator.

Override the output directory with `--dir <path>` (helper) or `execution_dir=<path>` (Python API). Point the generator at a different repository with `--workdir <path>`.

---

## The 12-executor catalog

| Executor key (`--executor <key>`) | Binary | Required flags pinned in the generated contract |
| --- | --- | --- |
| `claude` (default) | `claude` | `--print`, `--add-dir`, `--agent`, `--allow-dangerously-skip-permissions`, `--dangerously-skip-permissions`, `--debug-file`, `--effort`, `--include-hook-events`, `--output-format stream-json`, `--include-partial-messages`, `--input-format stream-json`, `--json-schema`, `--mcp-config`, `--settings`, `--strict-mcp-config`, `--system-prompt-file`, `--tools`, `--verbose`, `--worktree` |
| `codex` | `codex` | `--full-auto`, `--dangerously-bypass-approvals-and-sandbox`, `--reasoning-effort`, `--model` |
| `opencode` | `opencode` | `run`, `--model`, `--prompt` |
| `gemini` | `gemini` | `--prompt`, `--yolo`, `--model` |
| `cursor` | `cursor-agent` (fallback: `cursor`) | `--print`, `--force`, `--model` |
| `aider` | `aider` | `--yes-always`, `--no-auto-commits`, `--message`, `--model` |
| `pi` | `pi` | `--non-interactive`, `--prompt` |
| `qwen` | `qwen` (fallback: `qwen-code`) | `--prompt`, `--yolo` |
| `goose` | `goose` | `run`, `--no-session`, `--text` |
| `amp` | `amp` | `--no-tui`, `--prompt` |
| `crush` | `crush` | `--prompt`, `--yolo` |
| `hermes` | `hermes` | `--quiet`, `--no-skill-load`, `--prompt`, `--model`, `--provider`, `--reasoning-effort` |

Resolution order (in `prepare_goal_prompt`):

1. `--executor <key>` on the helper.
2. `executor=<key>` keyword on the Python API.
3. `GOAL_PROMPT_GENERATOR_EXECUTOR=<key>` environment variable.
4. **First available installed CLI** in catalog priority order.
5. Fallback to `claude` and surface the missing binary as a blocker.

The YAML's `coding_agent_alternatives` block always carries the full catalog plus an `installed_clis` snapshot of what the generator probed on your machine (binary path, version, `available: true|false`).

### Every coding-agent CLI roots its worktree inside the active Hermes worktree

Every catalog entry's `worktree_directory.directory_template` resolves to `<repo_root>/.<executor>/worktrees/<worktree-name>` — and `repo_root` is `git --show-toplevel`, so when Hermes is itself running from a `.worktrees/hermes-*` checkout every executor's worktree lands inside *that* Hermes worktree:

```text
<hermes-worktree>/
├── .claude/worktrees/<name>/      ← claude
├── .codex/worktrees/<name>/       ← codex
├── .opencode/worktrees/<name>/    ← opencode
├── .gemini/worktrees/<name>/      ← gemini
├── .cursor/worktrees/<name>/      ← cursor
├── .aider/worktrees/<name>/       ← aider
├── .pi/worktrees/<name>/          ← pi
├── .qwen/worktrees/<name>/        ← qwen
├── .goose/worktrees/<name>/       ← goose
├── .amp/worktrees/<name>/         ← amp
├── .crush/worktrees/<name>/       ← crush
└── .hermes/worktrees/<name>/      ← hermes (configurable model + reasoning)
```

The structural validator enforces this for every executor, with the strict literal `.claude/worktrees/<worktree-name>` check kept for the Claude path (substring-matched by the Markdown validator) and a relaxed `<worktree-name>` ending check for the rest.

### Continuity invariant

Switching executors **never** weakens the GoalManager continuation contract. Every executor profile inherits the same runtime rule in `agent_runtime_protocol.goal_manager_continuation_contract`:

- continue autonomously until all acceptance criteria validate or Hermes goal `max_turns` pauses the loop,
- do not ask the user for input, guidance, confirmation, or permission on non-final turns,
- end every non-final response with `GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued` plus the next YAML task id,
- end the final validated response with `GOAL_RUNTIME_STATUS: COMPLETE — all acceptance criteria and validations satisfied`.

---

## Fallback alternatives when Firecrawl or `opensrc` are unavailable

The skill's contract requires Firecrawl maps + scrapes and `opensrc` source-grounded validation when the goal references real technologies. When those tools are unavailable on your machine, the skill degrades **honestly** — the YAML's `validation_evidence` records the requirement as an execution-time validation requirement instead of falsely claiming the tool was used.

See [`skills/goal-prompt-generator/references/tool-fallback-alternatives.md`](skills/goal-prompt-generator/references/tool-fallback-alternatives.md) for the full matrix:

| Mode | What the skill does |
| --- | --- |
| Firecrawl authenticated + reachable | Runs `firecrawl map --limit 5000` per technology, scrapes cited URLs, records `url_count` + cached map file. |
| Firecrawl unauthenticated / cache-only / L7 RST | Records the requirement as execution-time validation. Documents alternatives: `wget --recursive`, `curl <sitemap.xml>`, `markdown-crawler`, Browser MCP, or targeted `web_search` + `web_extract`. |
| `opensrc` available | Fetches every referenced repo, cites `<repo>/<file>:<line>` in `validation_evidence.opensrc.fetched[*].key_paths`. |
| `opensrc` unavailable | Records the requirement as execution-time validation. Documents alternatives: `gh repo clone`, `git clone --depth 1`, `npm view ... repository.url`, `pip download --no-deps`, `cargo vendor`, or `web_extract https://github.com/<org>/<repo>/blob/<ref>/<path>`. |

In every fallback case the **non-execution guardrail** and the **GoalManager continuation contract** are preserved — only the research/source surface degrades.

---

## Generated artifact contract

### Markdown frontmatter

```yaml
---
generated_by: goal-prompt-generator
goal_prompt_generator_version: "0.1.0"
optimized_for: hermes-agent-goal
optimization_status: optimized
source_prompt_hash: "stable-sha256-hash-of-original-prompt"
generated_at: "ISO-8601 timestamp"
domain: "detected-domain"
domain_confidence: "high-or-moderate-or-low"
---
```

### Markdown sections (in order)

`Generated Goal Title` → `Goal` → `Original Intent` → `Domain` → `Assumptions` → `Non-Execution Guardrail` → `Isolated Generation Boundary` → `Autonomous Execution Requirement` → `Goal Runtime Continuation Contract` → `Research and Source Validation Requirements` → `Repository Context` → `Scope` → `Execution Plan` (`Phase 0: BOOTSTRAP` → `Phase 1: RED` → `Phase 2: GREEN` → `Phase 3: REFACTOR`) → `Software Development Constraints` (when software-development or uncertain) → `Software Engineering Core Principles` (when software-development) → `Acceptance Criteria` → `Validation Commands` → `Completion Definition` → `Failure Conditions` → `Final Output Requirements` → `Coding Agent Execution Contract`.

### Companion TDD task list YAML

```yaml
metadata:                # plan id, version, source goal markdown path + hash, hard invariants
validation_evidence:     # Firecrawl maps, opensrc fetches, authoritative reference URLs, repository_context (with claude_worktree + executor_worktrees)
validation_reconciliation: # contrarian-re-verification result
styleguide_rules:        # S1..Sn keyed rules
guardrails:              # G1..Gn keyed rules
ci_commands:             # CC_* keyed shell commands
principles:              # P1..P18 — software engineering core principles
phases:                  # ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR (RED carries hard_gate)
agent_runtime_protocol:  # status_transitions, mutable_fields, immutable_fields, resume_protocol, goal_manager_continuation_contract
coding_agent_execution_contract:    # executor + required_flags + canonical_invocation + worktree_directory + forbidden_alternatives
coding_agent_alternatives:          # catalog + installed_clis + configuration_knobs + fallback_rules
```

`status`, `learnings`, and `gotchas` are mutable. Everything else is contract. `phases` order is strict, every GREEN task depends on at least one RED task, the RED phase carries a `hard_gate` forbidding GREEN production-code edits before R00 + all RED tests are committed and observed failing for the right reason.

---

## Validation

```bash
mise run quality
```

Equivalent direct commands:

```bash
uv run pytest -q                                       # 91 tests pass
uv run python skills/goal-prompt-generator/scripts/validate_skill.py                # skill packaging validator
python skills/goal-prompt-generator/scripts/generate_goal_prompt.py --json "..."    # end-to-end smoke
python skills/goal-prompt-generator/scripts/validate_task_list_yaml.py <yaml-path>  # structural YAML validator
```

---

## Repository layout

```text
.
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
├── MANIFEST.md
├── pyproject.toml
├── mise.toml
├── skills/
│   └── goal-prompt-generator/
│       ├── SKILL.md
│       ├── references/         # playbooks, contracts, pitfalls archive, executor catalog, tool fallbacks
│       ├── templates/          # optimized-goal-template.md
│       ├── scripts/            # CLI scripts + validators + probes
│       └── src/goal_prompt_generator/    # executors.py, repository.py, tasklist.py, validation.py, …
├── tests/              # 91 tests covering every contract surface
├── docs/
├── examples/
└── .github/workflows/quality.yml
```

---

## Safety model

`goal-prompt-generator` never performs the task described by the input prompt. It only:

1. enhances and structures the prompt,
2. detects the domain,
3. injects required constraints and the GoalManager continuation contract,
4. generates metadata,
5. formats and validates the Markdown,
6. introspects the invoking repository/codebase,
7. probes the installer's `PATH` for the 12 catalog coding-agent CLIs and records what's installed,
8. resolves which executor to pin in the contract (explicit `--executor` > env var > first available installed),
9. runs Firecrawl maps/scrapes and `opensrc` fetches when those tools are present and authenticated (degrades honestly otherwise),
10. runs the contrarian re-verification pass,
11. writes both files,
12. runs the structural validator (catalog-aware: enforces the chosen executor's required flag set + that every executor's worktree resolves inside the active Hermes worktree),
13. prints the handoff `/goal …` line as a **paste-target only**.

It is explicit-use tooling only, not automatic `/goal` middleware. The skill, the helper script, and every code path that produces the artifacts MUST NEVER instantiate `/goal`, dispatch a goal run, push the printed handoff line back into Hermes Agent's command bus, or otherwise act on the handoff line.

---

## Versioning

The Python package's internal version (`goal_prompt_generator_version` in generated frontmatter, `pyproject.toml`) and the GitHub repository's release tag move together. The current release is **`v0.1.0`** (initial public release); the bundled skill semver is **`0.1.0`**.

---

## License

MIT. See [`LICENSE`](LICENSE).
