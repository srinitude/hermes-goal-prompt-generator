# Local Validation Checklist

Use these checks after editing the canonical implementation.

```bash
cd ~/.hermes/hermes-agent
/Users/kiren/.hermes/hermes-agent/venv/bin/python -m pytest \
  tests/hermes_cli/test_goal_prompt_generator.py \
  tests/hermes_cli/test_goal_preflight_integration.py \
  tests/hermes_cli/test_goals.py \
  tests/tui_gateway/test_goal_command.py \
  -q -o 'addopts='
```

Standalone skill script smoke test:

```bash
cd /tmp
python ~/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py \
  --json "Build a FastAPI API with tests"
```

Expected behavior:

- The script prints JSON containing `valid: true`.
- A concise lowercase hyphenated `*-goal.md` file appears in the current directory.
- The generated file starts with `generated_by: goal-prompt-generator` metadata.
- The generated file contains `## Non-Execution Guardrail` and `## Autonomous Execution Requirement`.
- Software prompts contain `## Software Development Constraints`.
- The script does not execute the generated goal.
