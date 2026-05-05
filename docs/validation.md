# Validation

## Standalone repository

```bash
mise run quality
```

Direct commands:

```bash
uv run pytest -q
uv run python scripts/validate_skill.py
python scripts/generate_goal_prompt.py --json "Build a FastAPI API with tests"
```

## Hermes Agent integration

After applying `patches/hermes-agent-goal-preflight.patch` to a Hermes Agent checkout, run the focused Hermes tests documented in `references/implementation-validation-notes.md`.
