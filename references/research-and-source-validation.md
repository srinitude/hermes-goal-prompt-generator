# Research and Source Validation Notes

This skill was created after validating Hermes Agent documentation and source behavior.

## Documentation validated with Firecrawl

- `firecrawl map https://hermes-agent.nousresearch.com/docs --limit 5000` was used to map the docs.
- `https://hermes-agent.nousresearch.com/docs/user-guide/features/goals` was scraped and queried.
- Additional docs inspected included skills system, creating skills, plugins, hooks, CLI commands, and slash commands.

Key `/goal` documentation findings:

- `/goal <description>` starts a persistent goal.
- `/goal` and `/goal status` display current goal status.
- `/goal pause`, `/goal resume`, and `/goal clear` control existing goals.
- Goal execution persists across turns until complete, paused, cleared, or the budget is exhausted.
- A judge evaluates after turns and malformed judge output fails open by continuing rather than marking done.

## Source validated with opensrc

The source was inspected via `opensrc path NousResearch/hermes-agent` after `opensrc path gh:NousResearch/hermes-agent` returned a 405 from the resolver.

Files inspected:

- `hermes_cli/goals.py` for `GoalState`, `GoalManager`, persistence, status, and continuation prompts.
- `cli.py` for CLI `/goal` handling and first-turn queueing.
- `gateway/run.py` for gateway `/goal` handling and enqueue behavior.
- `tui_gateway/server.py` for TUI `/goal` dispatch behavior.
- `agent/skill_commands.py` for Hermes skill command loading conventions.
- `hermes_cli/plugins.py` for plugin hooks and why direct `/goal` integration is safer than a generic hook for this preflight.

Implementation conclusion:

- `/goal` queues a new goal immediately as the next user turn, so mandatory preflight must run before `GoalManager.set()` and before queueing.
- A skill document alone cannot guarantee preflight routing for built-in `/goal`; the CLI, gateway, and TUI handlers must call the optimizer directly.
- `GoalState.goal` remains the canonical prompt consumed by the existing goal loop; after preflight it stores optimized Markdown, not raw text.
- Audit fields store generated file path, source prompt hash, generated title, and optimizer name.
