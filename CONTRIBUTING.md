# Contributing

Thanks for improving `goal-prompt-generator`.

## Development workflow

Use `mise` as the user-facing task runner:

```bash
mise run setup
mise run quality
```

If you do not use `mise`, run the underlying commands directly:

```bash
uv sync --extra dev
uv run pytest -q
uv run python scripts/validate_skill.py
```

## Requirements

- Keep the generator deterministic.
- Do not add network calls or LLM calls to prompt generation.
- Do not execute the generated goal during generation.
- Preserve the metadata contract in `SKILL.md` and tests.
- Add tests before changing behavior.

## Release checklist

1. Update `VERSION` in `src/goal_prompt_generator/core.py` if behavior changes.
2. Update `SKILL.md` frontmatter version when appropriate.
3. Run `mise run quality`.
4. Smoke-test `scripts/generate_goal_prompt.py` in a temporary directory.
5. Confirm no generated `*-goal.md` files are committed accidentally.
