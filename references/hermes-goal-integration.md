# Hermes `/goal` Integration Contract

The mandatory preflight must be implemented at every built-in `/goal` entrypoint that can start a new goal.

## Entry points

- CLI: `HermesCLI._handle_goal_command` in `cli.py`.
- Gateway: `_handle_goal_command` in `gateway/run.py`.
- TUI: `command.dispatch` handler for `goal` in `tui_gateway/server.py`.

## Routing sequence

1. Parse the `/goal` argument.
2. Preserve subcommands: empty/status, pause, resume, clear, stop, done.
3. For new goal text, call `prepare_goal_prompt(arg)`.
4. If preflight succeeds, call `GoalManager.set(prepared.goal_text, ...)` with audit metadata.
5. Queue or send `state.goal`, which is now optimized Markdown.
6. Show the user `prepared.file_path` and `prepared.status`.
7. If preflight fails, return an error and do not queue the raw prompt.

## Audit metadata

`GoalState` includes:

- `goal_file`
- `goal_source_hash`
- `goal_title`
- `optimized_by`

Status output should use `goal_title` or `goal_file` to avoid dumping full optimized Markdown.

## Loop prevention

`validate_optimized_markdown` treats a file as optimized only if metadata and required sections are complete. Valid optimized Markdown is reused; invalid or incomplete Markdown is regenerated. This prevents infinite re-optimization loops while still rejecting partial metadata.
