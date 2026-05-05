# Local Validation Checklist

Use these checks after editing the isolated generator implementation.

```bash
cd /Users/kiren/.hermes/hermes-agent/goal-prompt-generator
/Users/kiren/.hermes/hermes-agent/venv/bin/python -m py_compile   src/goal_prompt_generator/*.py scripts/*.py
/Users/kiren/.hermes/hermes-agent/venv/bin/python -m pytest tests -q -o 'addopts='
/Users/kiren/.hermes/hermes-agent/venv/bin/python scripts/validate_skill.py
```

Standalone skill script smoke test:

```bash
cd /tmp
python ~/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py   --json "Build a FastAPI API with tests"
```

Expected behavior:

- The script prints JSON containing `valid: true`.
- A concise lowercase hyphenated `*-goal.md` file appears in the current directory.
- The generated file starts with `generated_by: goal-prompt-generator` metadata.
- The generated file contains `## Non-Execution Guardrail`, `## Isolated Generation Boundary`, and `## Autonomous Execution Requirement`.
- Software prompts contain `## Software Development Constraints`.
- Software prompts contain the ruthless final-diff cleanup requirement.
- Software prompts contain `## Software Engineering Core Principles` with the condensed engineering rubric.
- Clear non-software prompts do not contain software cleanup language or software engineering principles.
- The script does not execute the generated goal.
- Hermes `/goal` is not invoked, intercepted, or modified.
