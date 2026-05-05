# Implementation and Validation Notes

Use these notes when maintaining isolated goal prompt generation.

## Scope boundary

The canonical implementation lives in `src/goal_prompt_generator/` and the explicit helper script is `scripts/generate_goal_prompt.py`. These files generate and validate Markdown prompt files only.

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

## Test isolation pitfall

Tests and smoke runs can write `*-goal.md` files to the process cwd. Run tests in temporary directories where possible, and remove only generated root-level `*-goal*.md` artifacts if they appear.

## Local validation commands

```bash
cd /Users/kiren/.hermes/hermes-agent/goal-prompt-generator
/Users/kiren/.hermes/hermes-agent/venv/bin/python -m py_compile   src/goal_prompt_generator/*.py scripts/*.py
/Users/kiren/.hermes/hermes-agent/venv/bin/python -m pytest tests -q -o 'addopts='
/Users/kiren/.hermes/hermes-agent/venv/bin/python scripts/validate_skill.py
```

Also smoke-test the script from a temporary directory so file-writing behavior is verified without executing the generated goal.
