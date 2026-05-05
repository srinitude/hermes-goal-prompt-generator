# goal-prompt-generator

[![Quality](https://github.com/srinitude/hermes-goal-prompt-generator/actions/workflows/quality.yml/badge.svg)](https://github.com/srinitude/hermes-goal-prompt-generator/actions/workflows/quality.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Hermes Agent skill and CLI for turning raw `/goal` prompts into optimized, reusable Markdown goal files without executing the requested goal during generation.**

`goal-prompt-generator` is designed as a preflight optimizer for [Hermes Agent](https://github.com/NousResearch/hermes-agent). It preserves user intent, detects the prompt domain, injects autonomy and TDD constraints when appropriate, writes a validated Markdown file, and lets Hermes reuse already-optimized goal files safely.

---

## What you get

- A complete Hermes Agent skill at repository root: [`SKILL.md`](SKILL.md).
- Linked skill references, templates, and scripts in [`references/`](references), [`templates/`](templates), and [`scripts/`](scripts).
- A standalone Python package in [`src/goal_prompt_generator`](src/goal_prompt_generator).
- A CLI command: `goal-prompt-generator`.
- Tests that verify metadata, domain detection, non-execution guardrails, file writing, reuse detection, regeneration, and filename collision behavior.
- A Hermes Agent source integration patch in [`patches/hermes-agent-goal-preflight.patch`](patches/hermes-agent-goal-preflight.patch) for mandatory built-in `/goal` preflight routing.

---

## Quick install as a Hermes skill

Clone the repository and symlink it into Hermes' local skill directory:

```bash
git clone https://github.com/srinitude/hermes-goal-prompt-generator.git
cd goal-prompt-generator

mkdir -p ~/.hermes/skills/software-development
ln -sfn "$(pwd)" ~/.hermes/skills/software-development/goal-prompt-generator

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

No API keys are required. The generator is deterministic Python and does not call an LLM.

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
python scripts/generate_goal_prompt.py --json "Write a heartfelt poem about the ocean at sunrise"
```

Output is a `*-goal.md` file in the current directory. The generated goal is **not executed**.

---

## Generated file contract

Every generated Markdown file starts with machine-readable metadata:

```yaml
---
generated_by: goal-prompt-generator
goal_prompt_generator_version: "1.0.0"
optimized_for: hermes-agent-goal
optimization_status: optimized
source_prompt_hash: "stable-sha256-hash-of-original-prompt"
generated_at: "ISO-8601 timestamp"
domain: "detected-domain"
domain_confidence: "high-or-moderate-or-low"
---
```

The body includes the required `/goal` structure: goal, original intent, domain, assumptions, non-execution guardrail, `/goal` preflight requirement, autonomous execution requirement, research requirements, scope, BOOTSTRAP / RED / GREEN / REFACTOR phases, acceptance criteria, validation commands, completion definition, failure conditions, and final output requirements.

Software-development or uncertain prompts also include strict TDD and implementation constraints.

---

## Hermes `/goal` preflight integration

The skill itself can generate optimized files, but making raw built-in `/goal <text>` commands preflight automatically requires Hermes Agent source integration because Hermes queues new goals immediately.

Apply the included patch to a Hermes Agent checkout:

```bash
cd ~/.hermes/hermes-agent
git apply /path/to/goal-prompt-generator/patches/hermes-agent-goal-preflight.patch
```

The patch wires preflight into:

- `cli.py`
- `gateway/run.py`
- `tui_gateway/server.py`
- `hermes_cli/goals.py`
- `hermes_cli/goal_prompt_generator.py`

Read [`docs/hermes-agent-source-integration.md`](docs/hermes-agent-source-integration.md) before applying the patch.

---

## Validation

```bash
mise run quality
```

Equivalent direct commands:

```bash
uv run pytest -q
uv run python scripts/validate_skill.py
python scripts/generate_goal_prompt.py --json "Build a FastAPI API with tests"
```

Expected result: tests pass, skill packaging validates, and the smoke command writes a valid `fastapi-api-tests-goal.md` file without executing that goal.

---

## Repository layout

```text
.
├── SKILL.md
├── README.md
├── LICENSE
├── pyproject.toml
├── mise.toml
├── references/
├── templates/
├── scripts/
├── src/goal_prompt_generator/
├── tests/
├── docs/
├── examples/
├── patches/
└── .github/workflows/quality.yml
```

---

## Safety model

`goal-prompt-generator` never performs the task described by the input prompt. It only enhances, structures, validates, and saves a Markdown goal file. Downstream execution happens only if you explicitly pass the generated Markdown to Hermes Agent's `/goal` workflow.

---

## License

MIT. See [`LICENSE`](LICENSE).
