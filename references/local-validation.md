# Local Validation Checklist

Use these checks after editing the isolated generator implementation.

```bash
cd <skill-root>
python3 -m py_compile src/goal_prompt_generator/*.py scripts/*.py
python3 scripts/validate_skill.py
```

Standalone skill script smoke test:

```bash
tmp=$(mktemp -d)
python ~/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py \
  --dir "$tmp" "Build a FastAPI API with tests"
python ~/.hermes/skills/software-development/goal-prompt-generator/scripts/validate_task_list_yaml.py \
  "$tmp"/*-tdd-tasks.yaml
```

Expected behavior:

- The script prints `Validation: valid` and `Task list validation: valid`.
- A concise lowercase hyphenated `*-goal.md` file appears in the output directory.
- A paired `*-tdd-tasks.yaml` file appears next to the Markdown file.
- The generated Markdown starts with `generated_by: goal-prompt-generator` metadata.
- The generated Markdown contains `## Non-Execution Guardrail`, `## Isolated Generation Boundary`, and `## Autonomous Execution Requirement`.
- Software prompts contain `## Software Development Constraints`.
- Software prompts contain the ruthless final-diff cleanup requirement.
- Software prompts contain `## Software Engineering Core Principles` with the condensed engineering rubric.
- Clear non-software prompts do not contain software cleanup language or software engineering principles.
- The generated YAML passes `scripts/validate_task_list_yaml.py`.
- The final printed line begins with `/goal `.
- The script does not execute the generated goal.
- Hermes `/goal` is not invoked, intercepted, or modified.
