# Implementation and Validation Notes

Use these notes when maintaining isolated goal prompt generation.

## Scope boundary

The canonical implementation lives in `src/goal_prompt_generator/` and the explicit helper script is `scripts/generate_goal_prompt.py`. These files generate and validate paired Markdown goal contracts and ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR task-list YAML files.

Do not add source-level Hermes `/goal` integration to this repository. The generator must not be called automatically from CLI, gateway, TUI, or persistent goal-loop handlers.

## Validate more than frontmatter presence

A prompt is valid generated output only if the metadata and body contract are complete. Validate:

- `generated_by`
- `goal_prompt_generator_version`
- `optimized_for`
- `optimization_status`
- non-empty `source_prompt_hash`
- `generated_at`
- `domain`
- valid `domain_confidence`
- all required Markdown sections
- isolated generation boundary
- autonomy requirement
- non-execution guardrail
- acceptance and validation sections
- software-development constraints when domain is software or uncertain
- software-development cleanup requirement when domain is software-development
- software engineering core principles and rubric when domain is software-development

Partial frontmatter should be regenerated only during explicit generator use.

## Task-list YAML validation

A generated YAML file is valid only if `scripts/validate_task_list_yaml.py` accepts it. The YAML must include ordered ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR phases, a RED `hard_gate`, resolvable command/style/guardrail/principle references, and mutable runtime fields limited to task `status`, `learnings`, and `gotchas`.

## Test isolation pitfall

Tests and smoke runs can write `*-goal.md` and `*-tdd-tasks.yaml` files to the process cwd. Run tests in temporary directories where possible, and remove only generated root-level artifacts if they appear.

## Local validation commands

```bash
cd <skill-root>
python3 -m py_compile src/goal_prompt_generator/*.py scripts/*.py
python3 scripts/validate_skill.py
tmp=$(mktemp -d)
python3 scripts/generate_goal_prompt.py --dir "$tmp" "Build a FastAPI API with tests"
python3 scripts/validate_task_list_yaml.py "$tmp"/*-tdd-tasks.yaml
```

Also smoke-test the script from a temporary directory so file-writing behavior is verified without executing the generated goal.
