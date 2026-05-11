# Executing Generated TDD Goal Contracts

Use this when a user asks to execute an existing goal Markdown plus paired TDD YAML contract instead of generating a new prompt.

## Pattern observed

- Treat the Markdown goal as immutable contract evidence.
- Treat the YAML task list as runtime state; mutate only `status`, `learnings`, and `gotchas` unless the contract explicitly permits more.
- Preserve strict phase order: `ANALYSIS -> BOOTSTRAP -> RED -> GREEN -> REFACTOR`.
- For RED hard gates, do not make GREEN production edits until the kickoff and all RED tests are committed and observed failing for the intended reason.
- Use a headless executor exactly as the contract specifies when present. In this environment, Claude Code stream-json required a wrapped JSONL user message:
  `{"type":"user","message":{"role":"user","content":[{"type":"text","text":"..."}]}}`.
- When bare shell sessions lack Claude auth but fish has it, run the exact invocation through `/opt/homebrew/bin/fish -lc '...'`.
- Keep validation independent after the delegated executor completes: rerun task-list validation, pytest, sync/drift checks, git diff checks, and scoped git status from Hermes itself.
- If live-e2e gates fail closed due to missing external actors/credentials, record the exact fail-closed label and resume point in YAML gotchas/blockers; do not attempt live mutation past the failed gate.

## Finalization checklist

1. Verify every task status in all phases is `completed` or explicitly blocked by contract.
2. Validate the YAML with `scripts/validate_task_list_yaml.py`.
3. Re-run the contract's local CI commands after any commit, not only before it.
4. Commit only scoped implementation files; leave immutable goal Markdown and mutable runtime YAML uncommitted if the contract says they are runtime artifacts.
5. If the contract says "if pushing," do not push by default; report no GitHub checks invoked.