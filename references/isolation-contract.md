# Isolation Contract

`goal-prompt-generator` is explicit-use tooling. It generates one Markdown prompt file for one individual goal and then stops.

## Current behavior that was removed

Earlier versions described the generator as mandatory `/goal` preflight middleware. That behavior is no longer part of this skill or repository.

Remove or reject all of the following patterns:

- Calling `prepare_goal_prompt()` from Hermes Agent `/goal` command handlers.
- Patching `cli.py`, `gateway/run.py`, `tui_gateway/server.py`, or `hermes_cli/goals.py` for generator routing.
- Writing optimizer metadata into `GoalState`.
- Queueing generated Markdown automatically as the first persistent goal turn.
- Treating raw `/goal` text as invalid unless first processed by this generator.

## Expected behavior

- The user explicitly invokes the skill, script, or standalone CLI.
- The generator writes a validated Markdown goal prompt file in the selected directory.
- The generator reports the file path, title, source hash, status, and validation result.
- The generated goal is not executed.
- Hermes Agent's built-in `/goal` command remains independent and unchanged.
