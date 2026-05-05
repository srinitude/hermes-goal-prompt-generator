# Hermes Agent Source Integration

The repository root is a valid Hermes skill, but mandatory automatic preflight for raw built-in `/goal <text>` commands requires changes inside Hermes Agent itself.

Why: Hermes queues a new `/goal` prompt immediately as the first turn. If preflight runs only as a normal skill instruction, raw text can reach `GoalManager.set()` and the queue before it is optimized.

## Apply the patch

```bash
cd ~/.hermes/hermes-agent
git apply /path/to/goal-prompt-generator/patches/hermes-agent-goal-preflight.patch
```

Then run the focused Hermes validation commands from `references/implementation-validation-notes.md`.

## Entry points covered

- CLI: `HermesCLI._handle_goal_command` in `cli.py`.
- Gateway: `_handle_goal_command` in `gateway/run.py`.
- TUI: `command.dispatch` handler for `goal` in `tui_gateway/server.py`.

## Behavior contract

- `/goal status`, `pause`, `resume`, `clear`, `stop`, and `done` stay unchanged.
- New raw goals call `prepare_goal_prompt()` before `GoalManager.set()`.
- The optimized Markdown becomes `GoalState.goal`.
- The generated file path, source hash, title, and optimizer name are persisted as audit metadata.
- Preflight errors fail closed; raw prompts are not queued as fallback.
