# Repository Context Exploration (1.6.0)

Generated goal prompts and their paired TDD task list YAMLs run against a real
codebase. Before 1.6.0 the generator only validated documentation (Firecrawl)
and open-source dependencies (`opensrc`); it never looked at the repository the
user was actually invoking the skill against. That left the downstream coding
agent to re-discover obvious things — `AGENTS.md`, the manifest, the lockfile,
the CI config, the head SHA — every time, and made it easy for hallucinated
file paths to land in `context_files`.

The 1.6.0 generator introduces a **Repository Context** snapshot that runs as
part of every generation and gets baked into both artifacts.

## What gets captured

`repository_evidence(workdir)` (in `goal_prompt_generator.repository`) returns a
stable, stdlib-only snapshot of the workdir:

| Field | Description |
|---|---|
| `workdir` | Absolute path that was inspected (defaults to cwd). |
| `repo_root` | Output of `git rev-parse --show-toplevel`, or `workdir` when not a git repo. |
| `is_git_repo` | True only when `git rev-parse --show-toplevel` returns a path. |
| `vcs.head_sha` / `branch` / `remote_url` / `dirty` | Bounded `git` reads (timeouts capped). |
| `manifests` | Detected from a curated list (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Dockerfile`, `Makefile`, `mise.toml`, …). |
| `lockfiles` | `uv.lock`, `pnpm-lock.yaml`, `Cargo.lock`, `go.sum`, etc. |
| `agent_context_files` | `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules`, `.github/copilot-instructions.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`, `DESIGN.md`, `README.md`. |
| `agent_context_excerpts` | First 800 chars of up to 3 detected agent-context files. |
| `ci_paths` | `.github/workflows`, `.gitlab-ci.yml`, `.circleci/config.yml`, `Jenkinsfile`, etc. |
| `top_level_entries` | Up to 40 sorted top-level files/dirs (ignored dirs like `node_modules` and `.venv` filtered). |
| `primary_languages` | File counts by language across the worktree (capped at 4000 files for huge monorepos). |
| `key_paths` | Curated absolute-path list of the highest-signal files for a coding agent: agent-context first, then manifests, lockfiles, CI configs, an existing `.claude/worktrees` directory when present, then canonical source dirs (`src/`, `lib/`, `app/`, `internal/`, `cmd/`, `pkg/`, `packages/`, `apps/`, `tests/`). Capped at 24 entries. |
| `claude_worktree` | Claude Code worktree metadata derived from the active repo root: `flag: --worktree`, `short_flag: -w`, `root: <repo_root>/.claude/worktrees`, `directory_template: <repo_root>/.claude/worktrees/<worktree-name>`, `exists`, `existing_worktrees`, and the rule that this directory stays inside the current Hermes `.worktrees/hermes-*` checkout when Hermes itself is running from one. |

Everything is best-effort: if `git` is missing the `vcs` block reports empty
strings; if the workdir has no recognized files the `primary_languages` list
is `[]`.

## Where the snapshot lands

1. The generated Markdown gets a new top-level `## Repository Context` section
   immediately after `## Research and Source Validation Requirements`. The
   section lists the workdir, repo root, branch, head SHA, Claude Code `--worktree`/`-w` directory resolution (`<repo_root>/.claude/worktrees/<worktree-name>`), top-level layout,
   manifests/lockfiles/CI/agent-context files, and the curated key paths as
   absolute backtick-quoted paths so the contract is unambiguous.
2. The paired YAML's `validation_evidence.repository_context` carries the full
   snapshot dict.
3. Each task's `context_files` is seeded with the goal Markdown path, the
   YAML path, **and every entry of `key_paths`**. That's the contract: the
   downstream coding agent reads those files before producing a diff.
4. `metadata.workdir` and `metadata.repo_root` are written so the structural
   validator can require the `repository_context` block.
5. `agent_runtime_protocol.handoff_workdir` carries the workdir for any
   orchestrator that hydrates a fresh terminal session.
6. `agent_runtime_protocol.claude_worktree_root`, `claude_worktree_directory_template`, and `claude_worktree_resolution` carry the exact directory rule that downstream launchers must apply when filling the required `--worktree` flag.
7. `coding_agent_execution_contract.worktree_directory` mirrors the same root/template/rule next to the required flag list so the structural validator can fail YAMLs that omit the Claude worktree directory contract.

## How to drive it

The CLI exposes the new flag:

```bash
python ~/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py \
  --workdir /Users/kiren/projects/myapp \
  --json "Add an OAuth callback handler with tests"
```

When `--workdir` is omitted the cwd is used. The Python API takes the same
keyword:

```python
from goal_prompt_generator import prepare_goal_prompt

prepared = prepare_goal_prompt(
    "Add an OAuth callback handler with tests",
    workdir="/Users/kiren/projects/myapp",
)
```

`build_optimized_markdown(prompt, workdir=...)` and
`write_task_list(goal_path, source_hash, title, workdir=...)` accept the same
keyword. You can also pre-compute the dict once and pass it to both via the
`repository=` keyword to avoid re-inspecting the same tree twice.

## Contrarian re-verification

`ContrarianValidator.recheck_repository_key_path(workdir, key_path)` runs
during the offline reconciliation pass. Any key path that no longer exists on
disk surfaces as a `Conflict(check_id="repository_key_path", severity="warn",
resolution="downgraded_to_attempted")` in `validation_reconciliation`. That
keeps optimistic claims from silently shipping when the workdir was retargeted
between generation and execution.

## Structural validator

`scripts/validate_task_list_yaml.py` requires the `repository_context` block
whenever `metadata.workdir` or `metadata.repo_root` is present (i.e. on every
1.6.0+ YAML). Required sub-keys: `workdir`, `repo_root`, `key_paths`, and `claude_worktree`. Empty
`key_paths` lists are accepted (small workdirs may legitimately have nothing
to surface), but every entry must be a non-empty string. `coding_agent_execution_contract.worktree_directory` must also carry `flag: --worktree`, `short_flag: -w`, a non-empty `root`, and a `directory_template` ending in `.claude/worktrees/<worktree-name>`. Older YAMLs without
the metadata fields are exempt so we don't break already-shipped runtime
ledgers.

## Honesty rules

- Do not synthesize plausible-looking files into `key_paths` if the workdir
  doesn't actually have them. The curated list is built from on-disk
  existence checks; if the snapshot is sparse, the snapshot is sparse — the
  goal contract should reflect that and the BOOTSTRAP/ANALYSIS tasks should
  carry an explicit "discover canonical layout" step.
- If `git` is unavailable, the `vcs` block reports empty strings; do not
  fabricate a head SHA or branch.
- Subdirectory invocation: when the user runs the generator from `src/api/`
  inside a larger monorepo, `repo_root` is still the top of the git tree but
  `workdir` is the subdir. Both go into the contract so the agent knows which
  subset of the repo is in scope.
