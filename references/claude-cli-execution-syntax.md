# Claude CLI execution syntax notes

Session signal: while executing a generated goal contract that required Claude Code handoff, the user corrected the agent with “default to the correct syntax and resume.” The practical fix was to use Claude Code's real prompt flag syntax (`-p` / `--print`) rather than inventing or persisting an invalid long form (`-p`) when launching `claude`.

## Rules for future generated-goal execution

- Probe the installed CLI before constructing the first execution command: `claude --version` and `claude --help` (or `claude -h`) are contract prerequisites, not optional niceties.
- For Claude Code 2.1.128 observed in this session, the prompt payload flag is `-p` or `--print`, not `--p`.
- Use structured IO flags exactly when communicating programmatically: `--output-format stream-json` and `--input-format stream-json`.
- If the generated Markdown/YAML contract names a flag form that conflicts with the installed CLI, treat the Markdown as the immutable goal contract but adapt the runtime command to the real CLI syntax and record the adaptation under the task's mutable `learnings`/`gotchas` fields. Do not make production-code edits until the RED hard gate is satisfied.
- Do not keep retrying an invalid CLI invocation after the first syntax failure. Re-read help, update the runtime command, and continue from the current TDD ledger state.
- If the installed `claude` process hangs or the full generated contract flag set blocks progress, and the user explicitly waives flag strictness (for example, “get it to work, don’t worry about flags for now”), treat that as a narrow execution-time waiver rather than a reason to abandon the generated goal. Record the waiver in the mutable task-list `learnings`/`gotchas`, keep the ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR order, honor the RED hard gate, and continue through the repository’s real command boundary (for Terminite, `MISE_LOCKED=1 mise run ...`). Do not rewrite the immutable Markdown contract just because runtime flags were waived.

## Why this belongs in the skill

The `goal-prompt-generator` output includes a downstream coding-agent execution contract. Future agents executing those generated contracts need to distinguish the persisted contract text from the installed `claude` binary's accepted syntax. The user expects the agent to default to the working syntax once discovered rather than asking again or repeating the invalid form.
