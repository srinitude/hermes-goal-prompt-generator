# Validator audit + TDD execution notes

Use this reference when executing or repairing a generated goal-prompt-generator audit task list, especially one that treats the Markdown goal as immutable and the paired YAML as mutable runtime state.

## Sequence that worked

1. Load the immutable Markdown contract and paired task-list YAML first. Treat only per-task `status`, `learnings`, and `gotchas` as mutable.
2. Before GREEN edits, ensure RED evidence is committed and captures the documented failure reason. Do not reinterpret this as optional if the YAML has a RED `hard_gate`.
3. During REFACTOR/final cleanup, run the checks both before and after staging:
   - `git diff --check`
   - `git diff --cached --check`
   - full pytest suite
   - `python3 scripts/validate_skill.py <skill-dir>`
   - `python3 scripts/validate_task_list_yaml.py <task-list.yaml>`
   - Markdown validator import for the immutable goal file
4. Remove in-repository bootstrap virtualenvs before commit. If the repo does not declare pytest/PyYAML as runtime deps and system `python3` lacks them, create a throwaway venv under `/tmp`, run the final suite from there, then delete it.
5. Generate final evidence reports under `audit/reports/` only after whitespace/cleanup passes, because trimming audit transcripts or final report regeneration can invalidate earlier `git diff --check` receipts.
6. Stage everything, run `git diff --cached --check`, then make one squashed audit commit.
7. After the code/audit commit, update only the external runtime YAML fields (`status`, `learnings`, `gotchas`) if that YAML is outside the repo. Validate it again.

## Final cleanup scanner

A useful lightweight scanner for changed Python files checks:

- no changed Python file over 200 LOC,
- no changed function/class/test construct over 30 LOC,
- AST branch nesting depth <= 3,
- no untracked `.venv*` entries in the repo.

Save the JSON result in `audit/reports/style-scan.txt` or `audit/reports/final-diff-cleanup.txt` and rerun after splitting oversized modules.

## Evidence gotchas

- `git diff --check` ignores staged content once the worktree is clean; always run `git diff --cached --check` before committing newly-added audit transcripts.
- Run the staged whitespace check **after** generating the final evidence reports. The reports themselves can introduce failures: Python `csv.DictWriter` defaults to CRLF line endings that `git diff --check` reports as trailing whitespace, and inline `python3 -c` command transcripts can leave a trailing space after `-c`. Normalize generated CSV/report files (`\r\n` -> `\n`, strip line-end whitespace) before the final `git add -A && git diff --cached --check`.
- Pytest failure transcripts often contain trailing spaces; if committed as audit evidence, trim trailing whitespace across changed text files before `git diff --cached --check`.
- A literal `/goal ` grep can legitimately match the immutable task-list contract itself. Do not mutate immutable YAML validation prose to satisfy the grep; instead remove accidental runtime handoff lines from mutable audit artifacts and record the immutable-contract false positives in `gotchas`.
- Firecrawl `--status` may exit 0 while unauthenticated; if it says `Not authenticated`, leave map evidence empty/unpromoted and record execution-time validation rather than claiming Firecrawl maps were refreshed. If the user says they reloaded environment variables, still verify the active backend process sees `FIRECRAWL_API_KEY`; remote/Daytona terminals may not inherit the host reload or even have `hermes config env-path` available.

## Recovery: orphaned RED commit, GREEN never landed

If a prior audit run left the YAML showing every task `completed` but `git
log` shows no GREEN reconciliation commit (only the RED kickoff is referenced
by `audit/contradiction-evidence.md`), do not trust the YAML. Re-run pytest
in a clean `/tmp` venv: 28+ failures with `--p` vs `--print` and `tests/test_validator_*_red.py`
errors mean the GREEN diff never hit a branch and the contradiction-evidence
SHA is dangling. Treat the existing `audit/` artifacts as analysis output,
re-execute every GREEN reconciliation in source against the existing RED
tests, run pytest again, then squash-commit. Reference resolved-commit lines
in `contradiction-evidence.md` should say "the squashed audit commit" rather
than a literal SHA so amend cycles do not invalidate self-references.

When `mcp_patch` reports a 1-byte trailing-newline verifier flake on an audit
file, reread the file before retrying — the change usually landed despite
the verifier failure. Switch to a single `mcp_execute_code` rewrite pass for
multi-file changes; that side-steps the flake entirely and gives explicit
per-anchor MISSING reporting.

## Recovery: cron `git pull --ff-only` reverts the audit commit between turns

When the skill repo is mirrored to a Hermes-managed remote (e.g.
`srinitude/hermes-goal-prompt-generator`), a background cron can fast-forward
the local `main` branch back to the remote tip *between agent turns*. This
silently drops any local-only audit commit and reverts every tracked file in
the worktree. Untracked `audit/` artifacts survive because they are outside
any branch.

Diagnostic signals (any one is enough):

- `git rev-parse HEAD` returned commit X at the end of last turn but commit Y
  (which is older) at the start of this turn.
- Pytest passed at the end of last turn but reports the EXACT same RED
  failures (`--p` vs `--print`, fenced-code substring leaks, missing
  `shared_blocks`) at the start of this turn.
- `git status --short` shows every tracked file the audit touched as
  modified again, even though no edits were made between turns.

Recovery sequence:

```bash
git reflog | head -20                  # find the dangling audit SHA, often
                                       # listed as "HEAD@{1}: commit (amend)"
git stash push -u -m "in-progress"     # keep any new evidence files
git reset --hard <dangling-sha>        # restore the audit tree
git stash pop                          # reapply new evidence
# resolve any conflicts on contract files by keeping the audit-commit version:
git checkout --ours <conflicted-files>
git reset HEAD && git checkout -- .    # clean up partial stage state
# only the truly-new evidence files should remain as untracked
git add -A
git commit --amend --no-edit
```

Stabilization rules (do these BEFORE walking away from the next pytest):

- Push the audit branch to the remote once the audit is complete; subsequent
  pulls become no-ops and cannot revert HEAD.
- In `audit/contradiction-evidence.md` and any YAML `learnings[]` strings,
  reference "the squashed audit commit" rather than literal short SHAs.
  Every `git commit --amend` rotates the SHA, so self-referential SHAs need
  another amend, which rotates again, ad infinitum.
- After amending, run `git rev-parse --short HEAD` and treat that as the
  authoritative SHA for the chat reply only — never persist it inside the
  commit's own files.

## Executor-contract blocker: unsupported mandatory flags

When an audit/goal contract requires all repository edits to originate from a specific coding executor invocation, verify the live CLI before writing even “small” doc/spec files. Claude Code currently may expose `-p, --print` while rejecting the contract literal `--p` with `error: unknown option '--p'`. If the immutable Markdown/YAML contract requires `--p` and forbids substitutions, stop at the earliest task that would write repo state, mark it `blocked` in the external YAML, and record the exact autonomous resume point (install/wrap a CLI that accepts the required flag, or amend/regenerate the immutable contract). Do not enter BOOTSTRAP/RED, do not create RED scaffolds, and do not hand-edit tests/docs as a workaround; that would satisfy the task while violating the execution contract.

## Commit verification pattern

After the squashed audit commit, run a read-only verification pass before replying:

1. `git status --short` is empty.
2. `git log -1 --oneline` shows the intended single audit commit.
3. Full pytest still passes from the temporary `/tmp` venv (or the project runner), then remove that venv.
4. `scripts/validate_skill.py`, `scripts/validate_task_list_yaml.py <external-yaml>`, and the inline Markdown validator all pass.
5. Parse the external task-list YAML and confirm every task status is `completed` when the contract has finished. Do not commit the external YAML unless it lives inside the repo; it is runtime state and only `status`, `learnings`, and `gotchas` are mutable.
