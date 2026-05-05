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

Expected behavior:

- tests pass,
- skill packaging validates,
- the smoke command writes a valid isolated `fastapi-api-tests-goal.md` file,
- no generated goal is executed,
- Hermes `/goal` is not invoked or modified.
