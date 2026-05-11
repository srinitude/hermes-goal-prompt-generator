# Executor catalog, fallbacks, and worktree contract

The skill ships a documented catalog of every popular coding-agent CLI it
knows how to drive. The installer chooses which one a generated goal targets;
the skill probes the installer's `PATH`, records what's installed, and bakes
the executor-specific flag set + worktree into both the Markdown contract and
the companion TDD YAML.

## Catalog (12 entries)

| Executor key | Binary | Docs |
| --- | --- | --- |
| `claude` (default) | `claude` | https://code.claude.com/docs |
| `codex` | `codex` | https://github.com/openai/codex |
| `opencode` | `opencode` | https://opencode.ai/docs |
| `gemini` | `gemini` | https://github.com/google-gemini/gemini-cli |
| `cursor` | `cursor-agent` (fallback: `cursor`) | https://docs.cursor.com/en/cli/overview |
| `aider` | `aider` | https://aider.chat/docs/usage.html |
| `pi` | `pi` | https://github.com/earendil-works/pi-coding-agent |
| `qwen` | `qwen` (fallback: `qwen-code`) | https://github.com/QwenLM/qwen-code |
| `goose` | `goose` | https://block.github.io/goose/ |
| `amp` | `amp` | https://ampcode.com/manual |
| `crush` | `crush` | https://github.com/charmbracelet/crush |
| `hermes` | `hermes` | https://hermes-agent.nousresearch.com/docs |

The catalog is the single source of truth for which CLIs are supported. It
lives in `src/goal_prompt_generator/executors.py` and is mirrored bit-for-bit
into `scripts/validate_task_list_yaml.py`'s `EXECUTOR_CATALOG_PROFILES` —
keep both in sync.

## Configuring the executor

Three knobs, evaluated in this order:

1. `--executor <catalog-key>` on the helper script
   (`scripts/generate_goal_prompt.py`).
2. `executor=<catalog-key>` keyword on `prepare_goal_prompt(...)` /
   `build_task_list(...)` / `write_task_list(...)`.
3. `GOAL_PROMPT_GENERATOR_EXECUTOR=<catalog-key>` environment variable.

If none is set, the generator probes the installer's `PATH` for every catalog
entry and picks the **first available** in catalog priority order. If nothing
is installed the contract falls back to `claude` and surfaces the missing
binary as a blocker in the generated YAML's `coding_agent_alternatives`
block.

## Per-executor required-flag set

Every catalog entry lists the *non-interactive* invocation flags that the
generated `canonical_invocation` MUST carry. The skill never invents a flag
that isn't documented by the CLI itself; flag sets are verified against the
upstream docs via `firecrawl map --limit 5000` + `firecrawl scrape` and pinned
in source.

| Executor | Required flags |
| --- | --- |
| `claude` | `--print`, `--add-dir`, `--agent`, `--allow-dangerously-skip-permissions`, `--dangerously-skip-permissions`, `--debug-file`, `--effort`, `--include-hook-events`, `--output-format`, `--include-partial-messages`, `--input-format`, `--json-schema`, `--mcp-config`, `--settings`, `--strict-mcp-config`, `--system-prompt-file`, `--tools`, `--verbose`, `--worktree` |
| `codex` | `--full-auto`, `--dangerously-bypass-approvals-and-sandbox`, `--reasoning-effort`, `--model` |
| `opencode` | `run`, `--model`, `--prompt` |
| `gemini` | `--prompt`, `--yolo`, `--model` |
| `cursor` | `--print`, `--force`, `--model` |
| `aider` | `--yes-always`, `--no-auto-commits`, `--message`, `--model` |
| `pi` | `--non-interactive`, `--prompt` |
| `qwen` | `--prompt`, `--yolo` |
| `goose` | `run`, `--no-session`, `--text` |
| `amp` | `--no-tui`, `--prompt` |
| `crush` | `--prompt`, `--yolo` |
| `hermes` | `--quiet`, `--no-skill-load`, `--prompt`, `--model`, `--provider`, `--reasoning-effort` |

## Worktree rule (every executor)

Every coding agent **must** root its worktree under the active Hermes
worktree's `repo_root`, never at an arbitrary parent or sibling checkout.
`repository_evidence(workdir)` returns:

```python
{
  "claude_worktree":     {"root": "<repo_root>/.claude/worktrees",   "directory_template": "<repo_root>/.claude/worktrees/<worktree-name>"},
  "executor_worktrees": {
    "claude":   {"root": "<repo_root>/.claude/worktrees",   "directory_template": "<repo_root>/.claude/worktrees/<worktree-name>"},
    "codex":    {"root": "<repo_root>/.codex/worktrees",    "directory_template": "<repo_root>/.codex/worktrees/<worktree-name>"},
    "opencode": {"root": "<repo_root>/.opencode/worktrees", "directory_template": "<repo_root>/.opencode/worktrees/<worktree-name>"},
    "gemini":   {"root": "<repo_root>/.gemini/worktrees",   "directory_template": "<repo_root>/.gemini/worktrees/<worktree-name>"},
    "cursor":   {"root": "<repo_root>/.cursor/worktrees",   "directory_template": "<repo_root>/.cursor/worktrees/<worktree-name>"},
    "aider":    {"root": "<repo_root>/.aider/worktrees",    "directory_template": "<repo_root>/.aider/worktrees/<worktree-name>"},
    "pi":       {"root": "<repo_root>/.pi/worktrees",       "directory_template": "<repo_root>/.pi/worktrees/<worktree-name>"},
    "qwen":     {"root": "<repo_root>/.qwen/worktrees",     "directory_template": "<repo_root>/.qwen/worktrees/<worktree-name>"},
    "goose":    {"root": "<repo_root>/.goose/worktrees",    "directory_template": "<repo_root>/.goose/worktrees/<worktree-name>"},
    "amp":      {"root": "<repo_root>/.amp/worktrees",      "directory_template": "<repo_root>/.amp/worktrees/<worktree-name>"},
    "crush":    {"root": "<repo_root>/.crush/worktrees",    "directory_template": "<repo_root>/.crush/worktrees/<worktree-name>"},
    "hermes":   {"root": "<repo_root>/.hermes/worktrees",   "directory_template": "<repo_root>/.hermes/worktrees/<worktree-name>"},
  }
}
```

Because `repo_root` is `git --show-toplevel`, when Hermes is itself running
from a `.worktrees/hermes-*` checkout every executor's worktree
automatically lands inside *that* Hermes worktree — not at the parent
checkout, not at a sibling.

The structural validator (`scripts/validate_task_list_yaml.py`) enforces:

- For `executor=claude`: `directory_template` MUST contain
  `.claude/worktrees/<worktree-name>` literally.
- For every other executor: `directory_template` MUST end with
  `<worktree-name>`; the dotdir component is executor-specific and is
  enforced via the catalog flag set rather than a hard-coded literal.

Both checks guarantee a downstream agent can substitute a real worktree name
and end up inside the active repo root.

## Runtime continuity invariant

Switching executors **never** weakens the GoalManager continuation contract.
Every executor profile inherits the same runtime rule that lives in
`agent_runtime_protocol.goal_manager_continuation_contract`:

- continue autonomously until all acceptance criteria validate or Hermes goal
  `max_turns` pauses the loop,
- do not ask the user for input, guidance, confirmation, or permission on
  non-final turns,
- end every non-final assistant response with
  `GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued` plus the next
  YAML task id,
- end the final validated response with
  `GOAL_RUNTIME_STATUS: COMPLETE — all acceptance criteria and validations
  satisfied`.

Each executor's `non_interactive_proof` field documents the specific flag
combination that disables interactive approvals; the canonical invocation
asserts the proof by carrying every required flag verbatim.

## Hermes-as-executor model selection

When the chosen executor is `hermes`, the contract additionally documents how
to pick the model + reasoning effort from what the installer has
authenticated:

- Inspect `~/.hermes/config.yaml` and authenticated providers via
  `hermes model`, which is powered by
  `hermes_cli/model_switch.list_authenticated_providers`.
- Pick the strongest available coding model from the curated lists in
  `hermes_cli/models.py` (`_PROVIDER_MODELS` / `OPENROUTER_MODELS`); fall back
  to the next tier when the preferred model is unauthenticated.
- Reasoning effort comes from `agent.reasoning_effort`
  (`hermes_constants.VALID_REASONING_EFFORTS =
  ('minimal','low','medium','high','xhigh')`); choose `high` for complex
  multi-phase work and `medium` for routine refactors.

This rule is embedded verbatim in
`coding_agent_alternatives.fallback_rules.model_selection_for_hermes` and in
the executor `rule` string for `executor=hermes`.

## YAML surface added by this feature

```yaml
coding_agent_alternatives:
  selected_executor: <one of the catalog keys>
  selection_source: explicit | env:GOAL_PROMPT_GENERATOR_EXECUTOR | auto:first-installed-in-catalog
  catalog:
    <executor>:
      display_name: ...
      binary: ...
      homepage: ...
      docs: ...
      required_flags: [{name, placeholder}, ...]
      worktree_directory_template: <repo-root>/.<executor>/worktrees/<worktree-name>
      non_interactive_proof: ...
      # only present for hermes:
      model_selection_rule: ...
  installed_clis:
    - cli: claude
      display_name: Claude Code
      binary: claude
      path: /Users/.../bin/claude
      version: 2.1.128 (Claude Code)
      available: true
      ...
  configuration_knobs:
    helper_flag: "--executor <catalog-key>"
    python_api_kwarg: "executor=<catalog-key>"
    environment_variable: GOAL_PROMPT_GENERATOR_EXECUTOR
    valid_catalog_keys: [aider, amp, claude, codex, crush, cursor, gemini, goose, hermes, opencode, pi, qwen]
  fallback_rules:
    fallback_chain: ...
    continuity_invariant: "Every executor MUST honor the GoalManager continuation contract..."
    model_selection_for_hermes: ...
```

And on the repository-context block:

```yaml
validation_evidence:
  repository_context:
    claude_worktree:    {root, directory_template, resolution_rule, ...}
    executor_worktrees: {claude, codex, opencode, gemini, cursor, aider, pi, qwen, goose, amp, crush, hermes}
```

## When to call `detect_installed_executors` directly

```python
from goal_prompt_generator import detect_installed_executors, resolve_executor_choice

installed = detect_installed_executors()  # cached after first call per process
selected = resolve_executor_choice(explicit="codex", installed=installed)
```

Catalog probing is bounded by a 1.5s per-binary `--version` timeout so a
hung CLI cannot stall generation. Results are cached at the module level for
the lifetime of the process.

## Pitfalls

1. **Drift between `executors.py` and `validate_task_list_yaml.py`**.
   Both files duplicate the catalog (the validator can't import from `src/`
   without dragging in PyYAML / repository introspection). When you add a new
   executor, edit both.
2. **Forgetting the per-binary fallback**.
   Some installers ship `cursor-agent` only when the desktop app is also
   present. The catalog supports `binary_fallback` for that. If you add a new
   entry whose CLI ships under two names, populate it.
3. **Picking an `--executor` the installer doesn't have**.
   `resolve_executor_choice` accepts the explicit value as-is and the
   generator emits a valid contract for it, but the `installed_clis` block
   will show `available: false`. Downstream consumers must surface that as a
   blocker (the installer can't actually run the contract) instead of
   silently proceeding.
4. **Loosening the worktree literal for `executor=claude`**.
   The Claude path keeps its strict `.claude/worktrees/<worktree-name>`
   literal substring check because the validator's substring match on the
   Markdown contract requires it. Only non-claude executors use the
   relaxed `<worktree-name>` ending check.
