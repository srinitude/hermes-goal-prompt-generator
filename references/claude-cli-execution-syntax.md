# Claude CLI execution syntax notes

Session signal: while executing a generated goal contract that required Claude Code handoff, the user corrected the agent with "default to the correct syntax and resume." The practical fix was to use Claude Code's real prompt flag syntax (`-p` / `--print`) rather than inventing or persisting an invalid long form (`--p`) when launching `claude`.

In skill version 1.6.1 the persisted contract was corrected to match the official Claude Code CLI reference (https://code.claude.com/docs/en/cli-reference, mapped via `firecrawl map --limit 5000 https://code.claude.com/docs` and scraped via `firecrawl scrape --format markdown --json https://code.claude.com/docs/en/cli-reference`) so generated goals no longer carry the invalid `--p` literal in the first place. Two flags changed shape:

| Pre-1.6.1 contract literal             | Real CLI shape                                         | Why it was wrong                                                                                                                                                                          |
| -------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--p <instructions-from-hermes-agent>` | `claude --print "<instructions>"` (or `-p`)            | The prompt payload is a positional argument, not the value of `--print`/`-p`. The literal `--p` is rejected with `error: unknown option '--p'`.                                            |
| `--strict-mcp-config <mcp-json-file>`  | `--strict-mcp-config` (boolean) + `--mcp-config <file>` | `--strict-mcp-config` takes no arg — it constrains MCP loading to whatever `--mcp-config` points at. Both flags are required when fully sandboxing MCP; the previous form merged the two. |

## Rules for future generated-goal execution

- Probe the installed CLI before constructing the first execution command: `claude --version` and `claude --help` (or `claude -h`) are contract prerequisites, not optional niceties.
- The official prompt-mode flag is `--print` (long form, boolean) or `-p` (short form, boolean). The prompt itself is the positional argument: `claude --print "<instructions>"`.
- Use structured IO flags exactly when communicating programmatically: `--output-format stream-json` and `--input-format stream-json`.
- When sandboxing MCP, pass both `--mcp-config <mcp-json-file>` (JSON file with MCP server definitions) and the boolean `--strict-mcp-config` (which disables every other MCP source). They are separate flags — never collapse them into one.
- If a stale generated Markdown/YAML contract still names `--p` or `--strict-mcp-config <file>`, treat the Markdown as the immutable goal contract but adapt the runtime command to the real CLI syntax (`--print` and the `--mcp-config`/`--strict-mcp-config` pair). Record the adaptation under the task's mutable `learnings`/`gotchas` fields. Do not make production-code edits until the RED hard gate is satisfied.
- Do not keep retrying an invalid CLI invocation after the first syntax failure. Re-read help, update the runtime command, and continue from the current TDD ledger state.
- If the installed `claude` process hangs or the full generated contract flag set blocks progress, and the user explicitly waives flag strictness (for example, "get it to work, don't worry about flags for now"), treat that as a narrow execution-time waiver rather than a reason to abandon the generated goal. Record the waiver in the mutable task-list `learnings`/`gotchas`, keep the ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR order, honor the RED hard gate, and continue through the repository's real command boundary (for Terminite, `MISE_LOCKED=1 mise run ...`). Do not rewrite the immutable Markdown contract just because runtime flags were waived.

## Why this belongs in the skill

The `goal-prompt-generator` output includes a downstream coding-agent execution contract. Future agents executing those generated contracts need to distinguish the persisted contract text from the installed `claude` binary's accepted syntax. The user expects the agent to default to the working syntax once discovered rather than asking again or repeating the invalid form. After 1.6.1, freshly generated contracts already match the working syntax — the adaptation rule above only applies to legacy contracts on disk.
