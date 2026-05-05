# Contributing

Thanks for improving `goal-prompt-generator`.

## Quality bar

- Keep the generator deterministic and inspectable.
- Preserve the non-execution guardrail.
- Keep source files small and focused.
- Do not add automatic Hermes `/goal` routing or command interception.
- Use `mise` tasks where possible.

## Local checks

```bash
mise run quality
```

Direct equivalent:

```bash
python -m py_compile src/goal_prompt_generator/*.py scripts/*.py
python -m pytest tests -q -o 'addopts='
python scripts/validate_skill.py
```

## Release checklist

1. Update `VERSION` in `src/goal_prompt_generator/constants.py` if behavior changes.
2. Update `pyproject.toml` version.
3. Regenerate `examples/fastapi-api-tests-goal.md` if the Markdown contract changes.
4. Refresh `MANIFEST.md`.
5. Confirm no cache files or generated root-level goal files are committed.
