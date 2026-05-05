# goal-prompt-generator

[![Quality](https://github.com/srinitude/hermes-goal-prompt-generator/actions/workflows/quality.yml/badge.svg)](https://github.com/srinitude/hermes-goal-prompt-generator/actions/workflows/quality.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Hermes Agent skill and CLI for turning one raw goal prompt into one isolated, optimized, reusable Markdown goal file without executing the requested goal.**

`goal-prompt-generator` preserves user intent, detects the prompt domain, injects autonomy, TDD constraints, software-specific final-diff cleanup, and software engineering core principles/rubric when appropriate, writes a validated Markdown file, and can validate or reuse existing generated files. It is intentionally **not** a Hermes `/goal` preflight hook and does not modify or intercept Hermes Agent's built-in `/goal` command.

---

## What you get

- A complete Hermes Agent skill at repository root: [`SKILL.md`](SKILL.md).
- Linked skill references, templates, and scripts in [`references/`](references), [`templates/`](templates), and [`scripts/`](scripts).
- A standalone Python package in [`src/goal_prompt_generator`](src/goal_prompt_generator).
- A CLI command: `goal-prompt-generator`.
- Tests that verify metadata, domain detection, non-execution guardrails, isolated generation boundaries, software-specific cleanup injection, software engineering principles/rubric injection, file writing, reuse detection, regeneration, copy equivalence, and filename collision behavior.

---

## What this does not do

- It does **not** run automatically inside `/goal`.
- It does **not** patch `cli.py`, `gateway/run.py`, `tui_gateway/server.py`, or `hermes_cli/goals.py`.
- It does **not** queue generated prompts into the persistent goal loop.
- It does **not** execute the generated goal.

If you want to execute a generated prompt later, intentionally pass the saved Markdown file or its contents to your chosen workflow yourself.

---

## Quick install as a Hermes skill

Clone the repository and symlink it into Hermes' local skill directory:

```bash
git clone https://github.com/srinitude/hermes-goal-prompt-generator.git
cd hermes-goal-prompt-generator

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
goal_prompt_generator_version: "1.0.1"
optimized_for: hermes-agent-goal
optimization_status: optimized
source_prompt_hash: "stable-sha256-hash-of-original-prompt"
generated_at: "ISO-8601 timestamp"
domain: "detected-domain"
domain_confidence: "high-or-moderate-or-low"
---
```

The body includes: goal, original intent, domain, assumptions, non-execution guardrail, isolated generation boundary, autonomous execution requirement, research requirements, scope, BOOTSTRAP / RED / GREEN / REFACTOR phases, acceptance criteria, validation commands, completion definition, failure conditions, and final output requirements.

Software-development prompts include strict TDD and implementation constraints, a ruthless final-diff cleanup requirement, and a software engineering core principles/rubric section. Uncertain prompts retain the existing strict software-development constraints; clear non-software prompts omit software-specific cleanup and software engineering principles language.

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
└── .github/workflows/quality.yml
```

---

## Safety model

`goal-prompt-generator` never performs the task described by the input prompt. It only enhances, structures, validates, and saves a Markdown goal file. It is explicit-use tooling only, not automatic `/goal` middleware.

---

## License

MIT. See [`LICENSE`](LICENSE).
