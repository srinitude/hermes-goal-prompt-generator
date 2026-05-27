# Standalone Repo Release Packaging for goal-prompt-generator

Use this when promoting the in-Hermes skill implementation to the public standalone repo at `https://github.com/srinitude/hermes-goal-prompt-generator`.

## Trigger

- User asks to publish, push, release, or sync `goal-prompt-generator` outside `~/.hermes/skills/...`.
- A contract/schema bump touched generator source, validators, tests, templates, references, examples, or changelog.

## Proven workflow

1. Work from the skill source directory, but do **not** push directly from a dirty `~/.hermes` tree.
2. Clone the standalone repo into a clean temp directory, e.g. `/tmp/hermes-goal-prompt-generator-push`.
3. Use `rsync` with an explicit include/exclude list to copy only package files that belong in the public repo. Avoid leaking local skill caches, runtime generated goal prompts, private notes, or unrelated Hermes artifacts.
4. Run local validation in the clean clone before committing:
   - `python3 scripts/validate_skill.py`
   - `python3 -m pytest tests -q`
   - `git diff --check`
   - static secret/security scan over added/changed files
5. For schema/contract version bumps, verify every coupled artifact changed together:
   - `src/goal_prompt_generator/constants.py`
   - `pyproject.toml`
   - validators under `scripts/` and/or `src/goal_prompt_generator/validation.py`
   - tests
   - `SKILL.md`
   - `templates/optimized-goal-template.md`
   - regenerated examples
   - `CHANGELOG.md`
6. Commit from the clean clone, push `main`, then verify remote state and checks:
   - `git rev-parse HEAD`
   - `git ls-remote origin main`
   - `gh run list --branch main --limit 5`
   - wait until the relevant workflow completes successfully.

## Source-of-truth rule (NON-NEGOTIABLE)

The local skill at `~/.hermes/skills/software-development/goal-prompt-generator/` is the **only** source of truth. The standalone repo is a downstream mirror.

- Any code fix, README change, or validator correction discovered while preparing a release MUST be applied to the local skill FIRST, then re-synced into the clean clone via `rsync`. Never patch the clone alone — the local skill will silently regress on the next release pass.
- After applying a fix locally, run `python3 scripts/validate_skill.py` + `python3 -m pytest tests -q` in the LOCAL skill dir before re-running rsync.
- If the user says any variant of "use local skill as source of truth" or "ensure repo uses local X as source", treat that as confirmation that you may have been editing the wrong copy — re-anchor immediately, re-sync, and verify the change is present in both places.

## Non-execution affirmation rule

When release-packaging the `goal-prompt-generator` skill, the user has interjected `"Ensure that goal is not executed"` mid-task. The skill's non-execution guardrail forbids invoking `/goal`, generating goal prompts, or executing the printed handoff line — but that guardrail can look ambiguous during release work because the skill is "loaded" via the skill-invocation header.

- When the user issues this interjection, explicitly acknowledge in one short line that `/goal` is not being invoked, no goal prompt is being generated, no handoff line is being executed, and the current operation is purely Git/GitHub release packaging.
- Do not pause for additional confirmation; resume the release work immediately after the affirmation.
- Pre-emptively state the same affirmation in the final summary so the user does not need to ask.

## Re-release / re-squash pattern

When the user asks to update a file (typically README/CHANGELOG) and re-squash + re-tag + re-release on top of an already-pushed `v0.1.0` (or equivalent):

1. Edit the local skill first.
2. **Start from a fresh clone** (`rm -rf` the temp dir, clone again) — never reuse a previous clone, because the previous run's `git checkout --orphan` state leaks.
3. Re-sync local → fresh clone via the same explicit `rsync --exclude` list.
4. Re-run validators in the clean clone.
5. Delete the existing GitHub release FIRST (`gh release delete <tag> --yes`), then delete the remote tag (`git push --delete origin <tag>`), then force-push `main`, then push the new tag, then `gh release create` again. Doing it in the other order leaves the release pointing at a dangling tag for a few seconds and can confuse downstream consumers.
6. Use `--force-with-lease=main:<expected-remote-sha>` rather than bare `--force` so an unexpected concurrent push aborts the operation.
7. Verify post-push: remote `main` SHA equals local HEAD, remote tag resolves to local HEAD, `gh api repos/<owner>/<repo>/commits --jq 'length'` returns `1`, `gh release view` returns the new release, `gh run list --branch main --limit 3` shows CI success for the new commit.

### Multiple re-release cycles in one session

When the user iterates (edit local skill → re-release; edit again → re-release; etc.) inside a single session:

- Each cycle MUST start with `rm -rf` of the temp clone dir, not a `git pull` or `git reset`. Reusing the previous orphan-branch state corrupts the staging area silently.
- Track the previous remote SHA across cycles so `--force-with-lease=main:<previous-sha>` keeps rejecting drift. After each successful push, the previous SHA is whatever `git ls-remote origin main` returned at the start of the new cycle — capture it before deleting the local clone.
- The `<expected-remote-sha>` for `--force-with-lease` should match what was on origin at clone time, not your previous local HEAD. If `gh release delete` raced with a concurrent CI run, recheck `git ls-remote origin main` before the force push.
- After 2+ cycles in a session, audit the local skill's `pyproject.toml` `version` and `goal_prompt_generator_version` constants — they should not have drifted accidentally across cycles, since the public tag stays at `v0.1.0` while the bundled skill semver is independent.

## Firecrawl during release-research runs

The standalone release packaging often pairs with a user-requested research pass (Firecrawl maps + scrapes to validate documentation claims). The Firecrawl 1.16 CLI has known auth quirks (see `references/firecrawl-cli-1-16-quirks.md`); a few release-specific reminders:

- Do NOT background `firecrawl map ... > out.json &` in this terminal harness. Background shells lose `FIRECRAWL_API_KEY` and the JSON file silently fills with the interactive auth banner ("Enter choice [1/2]:") instead of valid map output. Symptom: the file is exactly ~493 bytes and starts with `🔥 firecrawl cli v1.16.0`. Run maps foreground sequentially instead.
- Re-probe with `python3 scripts/probe_firecrawl_reachability.py` whenever Firecrawl output looks suspicious. The probe exits 0 only when a real map call returns a populated `data.links` array — use it as a binary gate before claiming the research evidence is valid.
- The `--limit 5000` argument is mandatory for every release-prep map call. Validators expect that exact limit recorded under `validation_evidence.firecrawl.required_maps_present[*].map_limit`.

## Validator regression pitfall (caught during v0.1.0 prep)

`scripts/validate_task_list_yaml.py`'s `_uses_legacy_task_graph()` previously detected legacy mode via two signals: (a) `prerequisites`/`blocking_tasks` listed under `agent_runtime_protocol.immutable_fields`, OR (b) per-task presence of those fields. Signal (b) is too permissive — it lets a newly authored YAML inject the legacy fields and skip rejection, because their presence alone trips the grandfather escape hatch. The test `test_yaml_validator_rejects_legacy_prerequisites_and_blocking_tasks` exists specifically to catch this; if it goes red, narrow detection to signal (a) only.

Diff that restored the test:

```python
def _uses_legacy_task_graph(data):
    runtime = data.get("agent_runtime_protocol")
    if not isinstance(runtime, dict):
        return False
    immutable = runtime.get("immutable_fields")
    if not isinstance(immutable, list):
        return False
    names = {item for item in immutable if isinstance(item, str)}
    return bool(PROHIBITED_TASK_GRAPH_FIELDS & names)
```

Always run `python3 -m pytest tests -q` against the LOCAL skill before rsyncing — the local skill is the source of truth, and the clone's tests passing while local fails means you patched the wrong copy.

## Research-evidence directory must be gitignored / excluded

When the release prep includes user-requested research (Firecrawl maps, `firecrawl scrape`, `opensrc` fetches), put the artifacts in `research/` and add `--exclude='research/'` to the `rsync` invocation. Otherwise:

- `git add -A` after `git checkout --orphan` will silently commit `research/*.json`, `research/*.err`, and `research/RESEARCH_SUMMARY.md` (observed: 81-file commit instead of the expected 73).
- The release ships network responses that don't belong in the package.

Audit `git ls-tree -r HEAD --name-only | wc -l` against the expected file count before pushing.

## Session-specific lessons from v1.7.0

- The v1.7.0 release commit was `614a4b02b4c15c51aa0b0eae2bc2297ef326224b`.
- `prerequisites` and `blocking_tasks` were removed from the YAML schema; `dependencies` is the single task graph field.
- Validator enforcement must reject legacy graph fields instead of silently shimming them.
- Every GREEN task must depend on at least one RED task.
- The handoff and runtime contract must include `GOAL_RUNTIME_STATUS: CONTINUE` for non-final turns and `GOAL_RUNTIME_STATUS: COMPLETE` only after validation.
- `canonical_invocation` must end with quoted positional `"<instructions-from-hermes-agent>"`; `--print` enables non-interactive mode but does not take the prompt as its flag value.
- Do not claim release completion until remote `origin/main` equals local `HEAD` and GitHub Actions are green.
