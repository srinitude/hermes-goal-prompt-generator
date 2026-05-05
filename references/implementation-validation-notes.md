# Implementation and Validation Notes

Use these notes when maintaining the canonical Hermes `/goal` preflight integration.

## Integration must happen before goal persistence

Hermes queues a new `/goal <text>` immediately as the first goal turn. Preflight therefore must run before `GoalManager.set()` and before queueing. A normal skill-only or plugin-only approach is insufficient for the built-in command path because raw text can otherwise reach the persistent goal loop first.

Patch every built-in new-goal entrypoint, not just the CLI:

- `cli.py` — interactive CLI command handler.
- `gateway/run.py` — messaging gateway command handler.
- `tui_gateway/server.py` — TUI `command.dispatch` goal handler.

Keep `/goal` controls unchanged: empty/status, pause, resume, clear, stop, and done.

## Store optimized markdown as the canonical goal

`GoalState.goal` should contain the optimized Markdown, because the existing continuation and judge loop already reads `state.goal`. Store extra audit metadata alongside it:

- `goal_file`
- `goal_source_hash`
- `goal_title`
- `optimized_by`

Use `goal_title` or `goal_file` in status output so `/goal status`, pause, and resume messages do not dump the full optimized Markdown.

## Validate more than frontmatter presence

A prompt is optimized only if the metadata and body contract are complete. Validate:

- `generated_by`
- `goal_prompt_generator_version`
- `optimized_for`
- `optimization_status`
- non-empty `source_prompt_hash`
- `generated_at`
- `domain`
- valid `domain_confidence`
- all required Markdown sections
- autonomy requirement
- non-execution guardrail
- acceptance and validation sections
- software-development constraints when domain is software or uncertain

Partial frontmatter should be regenerated, not trusted.

## Test isolation pitfall

TUI and gateway tests that invoke real preflight can write `*-goal.md` files to the process cwd. In pytest fixtures, set both `HERMES_HOME` and `monkeypatch.chdir(tmp_path)` so generated prompt files do not pollute the repository root.

If repository-root artifacts appear after tests, remove only generated `*-goal*.md` files that were produced by the preflight tests; do not delete unrelated Markdown.

## Local validation commands

The project test wrapper may try to install `pytest-split` and fail when the venv has no `pip`. Use direct pytest for this focused validation:

```bash
cd ~/.hermes/hermes-agent
/Users/kiren/.hermes/hermes-agent/venv/bin/python -m py_compile \
  hermes_cli/goal_prompt_generator.py \
  hermes_cli/goals.py \
  cli.py \
  gateway/run.py \
  tui_gateway/server.py

/Users/kiren/.hermes/hermes-agent/venv/bin/python -m pytest \
  tests/hermes_cli/test_goal_prompt_generator.py \
  tests/hermes_cli/test_goal_preflight_integration.py \
  tests/hermes_cli/test_goals.py \
  tests/tui_gateway/test_goal_command.py \
  tests/gateway/test_goal_preflight_command.py \
  tests/gateway/test_goal_verdict_send.py \
  -q -o 'addopts='
```

Also smoke-test the standalone skill script from a temporary directory so file-writing behavior is verified without executing the generated goal.
