# Third-party OSS PR goals

Use this reference when the user asks for a generated goal whose deliverable is a **pull request into a third-party open-source repository** (e.g. `warpdotdev/warp`, `mastra-ai/mastra`, `vercel/next.js`) — not their own project. The PR must satisfy that repo's own contributor rules, pass every one of its GitHub Actions checks, and stay continuously rebased on its default branch while the run is in flight.

## Trigger signals

- User asks for a "PR to <org>/<repo>" or "implementation PR for <upstream-repo>".
- Goal text references upstream issues, an upstream PR template, or a maintainer handle.
- Workdir is a clone of someone else's repo (e.g. `~/dev/hermes-warp` → `warpdotdev/warp`) rather than the user's project.
- User says "follow the repo's practices" or "match the repo's style" — that's a flag that the generic Software-Development Constraints need to be **scoped**, not deleted.

## Pre-helper probes

Run these in the workdir BEFORE calling the helper, and persist findings into the YAML's `validation_evidence` / Markdown's `## Repository Context`:

1. **Confirm fork vs upstream:** `git remote -v` — verify the workdir is the upstream repo (or a fork that tracks it). Record the canonical upstream URL.
2. **Capture the PR template:** `head -80 .github/pull_request_template.md` (or `PULL_REQUEST_TEMPLATE.md`). Extract every required section (Description, Linked Issue, Testing, Screenshots, Agent Mode toggle if any, CHANGELOG-* suffixes).
3. **Capture contributor rules:** `head -120 CONTRIBUTING.md`. Note readiness labels (e.g. `ready-to-spec`, `ready-to-implement`), automated-review agents (e.g. Warp's Oz), SME-review automation, manual-test expectations.
4. **List all workflows:** `ls .github/workflows/` — these are the checks the PR must satisfy.
5. **Capture local CI gates:** look for `./script/presubmit`, `./script/run`, `cargo nextest`, `pnpm test`, etc. Mirror them in the YAML's `ci_commands` block.
6. **Sample real file sizes in the touched modules:** `find <touched-dir> -name '*.<ext>' -exec wc -l {} + | sort -rn | head -10`. The repo's actual size practice matters more than the generic 200-LOC default.
7. **Find the most-recent PRs merged by the user the goal asks to tag** (e.g. `@harryalbert`): `gh search prs --author <user> --repo <org>/<repo> --state merged --limit 30`. Reviewer expectations are a hard signal.

## Required Markdown additions (beyond the standard scaffold)

Add these under `## Software Development Constraints` (after the canonical paragraph, NOT replacing it — the validator substring-matches the canonical text) as a `### Project-Specific Overrides (<org>/<repo>)` subsection:

- **File size: follow upstream practice, not the generic cap.** Cite the sampled LOC distribution from probe #6. When the choice is "split into a new <200 LOC file" vs "grow an existing 1k-LOC file", the OSS-no-new-files constraint takes precedence — grow the existing file. Make this explicit; do not let a downstream agent infer it.
- **30-LOC construct cap and 3-deep nesting cap apply to NEWLY CREATED constructs/blocks only.** Existing constructs and blocks that are merely extended with a new match-arm, an additional parameter, or an inline edit are NOT refactored as part of this PR. Refactoring upstream's existing code to fit the cap violates the minimal-diff invariant and won't pass review. Phrase this as "Each NEWLY CREATED Rust/TS/Go construct in this PR …" — the "NEWLY CREATED" wording is the disambiguator.
- **No new dependencies.** Cargo.lock / package-lock.json / go.sum / pnpm-lock.yaml diff must show zero new entries.
- **No upstream-endorsed plugin / install flow** if the goal explicitly forbids one (e.g. "Warp does not own a Hermes plugin").
- **PR template + workflow.** Quote the exact required sections. Tag the user the goal names. Reference the issues the goal names. Honor readiness labels.
- **Stay continuously rebased on upstream default.** Every commit/push/recheck cycle runs `git fetch origin <default> && git rebase origin/<default>` first. If the rebase fails, resolve conflicts and rerun local CI before re-pushing.
- **Stay continuously synced with any companion upstream** (e.g. if the PR depends on another OSS project's `main`, fetch it on every cross-check).
- **Every GitHub Actions check on the PR must succeed** before completion. Enumerate the workflows from probe #4. Use `gh pr checks --watch` and loop fix → rebase → push → re-watch.
- **Automated-review agents are non-bypassable.** Address every comment from upstream's review bot (Oz, dependabot, codecov, etc.) in-place; do not merge over an unresolved thread.

## Required YAML additions

### `metadata.hard_invariants`

Replace the generic numeric caps with policy literals:

```yaml
metadata:
  hard_invariants:
    no_new_dependencies: true
    no_new_files_unless_necessary: true
    preserve_existing_behavior: true
    all_github_checks_must_pass: true
    pr_must_stay_in_sync_with_origin_master: true   # or origin/main, etc.
    pr_must_stay_in_sync_with_<companion_upstream>: true
    construct_loc_max_new_only: 30
    construct_loc_max_existing_policy: unchanged_follow_<upstream>
    nesting_depth_max_new_only: 3
    nesting_depth_max_existing_policy: unchanged_follow_<upstream>
    file_loc_policy: follow_<upstream>_practice
    pr_references_issues: ["#<id1>", "#<id2>"]
    pr_tags_user: "@<reviewer>"
```

### `styleguide_rules`

Use names that telegraph the scoping. Examples that worked end-to-end:

- `S1_file_size_follow_<upstream>` — body: "File size follows <upstream>'s own practice; do NOT split an existing module into a new file solely to satisfy a line cap when the upstream rule forbids new files."
- `S2_construct_size` — body: "Each NEWLY CREATED <lang> construct stays under 30 LOC. Existing constructs that are merely extended are NOT refactored as part of this PR."
- `S3_nesting_depth` — body: "Each NEWLY CREATED block keeps nesting depth ≤ 3. Existing deeper blocks that are merely edited or extended are NOT flattened."
- `S5_no_new_deps` — Cargo.toml / package.json / go.mod diff must be empty for new entries.
- `S6_no_new_files` — prefer growing existing files; when in doubt grow, don't split.
- `S7_match_arm_parity` (or equivalent for the language) — place the new variant beside the analogue variant for diff legibility.
- `S10_no_endorsement` — when the goal forbids endorsing a third-party plugin/product.

### `guardrails`

Add the OSS-PR-specific guardrails alongside the standard set:

- `G6_keep_pr_in_sync_with_origin_master` (or default branch name).
- `G7_keep_pr_in_sync_with_<companion_upstream>` when a companion upstream is in play.
- `G8_all_github_checks_pass`.
- `G9_pr_template_completed`.
- `G10_issue_workflow_honored`.
- `G13_<review_agent>_acknowledged` (Oz, dependabot, codeowner, etc.).

### `ci_commands`

Mandatory entries:

- `CC_GIT_SYNC_<DEFAULT>`: `git fetch origin <default> && git rebase origin/<default>`.
- `CC_GIT_<COMPANION>_SYNC` when a companion upstream is in play.
- Local CI mirrors of every workflow you cannot dispatch from the workdir: `cargo fmt`, `cargo clippy`, `cargo nextest run --workspace --locked --exclude <…>`, `cargo test --doc`, `./script/presubmit`, etc.
- `CC_GH_CHECKS_WATCH`: `gh pr checks --watch`.
- `CC_GH_PR_CREATE`, `CC_GH_PR_EDIT_BODY`, `CC_PR_BODY_LINT` (one-liner that asserts the required sections appear).
- `CC_GIT_DIFF_CARGO` (or the lockfile equivalent for the language) to enforce the no-new-deps invariant.
- `CC_GH_<REVIEWER>_ACTIVITY` to inspect recent merges by the reviewer the goal asks to tag.

### `validation_reconciliation`

When you scope a generic constraint (200 LOC cap, 30 LOC cap, depth 3), emit an explicit conflict entry:

```yaml
validation_reconciliation:
  conflicts:
    - check_id: VR07
      evidence_target: styleguide_rules.S1_file_size_follow_<upstream>
      original_claim: Each file edited or added stays under 200 logical lines.
      contrarian_observation: <upstream>'s neighboring sources routinely run far above 200 LOC (cite real LOC counts from the workdir). Constraint forbids new files; resolved by replacing the cap with follow-upstream-practice.
      severity: warning
      resolution: some-claims-downgraded
  resolutions: []  # validator requires this to be a deep copy of conflicts
  final_state: some-claims-downgraded
```

Per pitfall #10 in `programmatic-yaml-rebuild.md`: `resolutions == conflicts` exactly. `final_state` becomes `some-claims-downgraded` (not `all-claims-reconciled`) when any constraint was scoped down.

### Phase shape

ANALYSIS heavy on inventory tasks (A00 workdir+git baseline; A01 inventory parity surface via `rg`; A02 read upstream PR conversation + reviewer's recent merges; A03 map upstream-docs surface to feature contract; A04 sync companion upstream + map its surface; A05 audit CI workflows + PR template + CONTRIBUTING; A06 audit lockfile for no-new-deps; A07 reify feature → code-site matrix). BOOTSTRAP includes a dedicated "populate PR body scaffold" task (B02) and a "stake out gap sites without editing" task (B03). RED carries the standard hard_gate; one RED task per capability dimension; one RED task per cross-cutting invariant (`R<n>` lockfile-and-LOC audit, `R<m>` regression-of-existing-behavior). GREEN ends with **`G12` rebase + push, `G13` open PR, `G14` watch checks until green looping fix→rebase→push→re-watch, `G15` respond to review-bot feedback**. REFACTOR ends with **`X03` final acceptance: every check green, branch fast-forward-only, no unresolved review threads**.

## Pitfalls

1. **Stripping the canonical Software-Development Constraints paragraph.** The Markdown validator substring-matches it. Add a `### Project-Specific Overrides (<org>/<repo>)` subsection AFTER the canonical block; don't try to replace the boilerplate. Preserve every line of the canonical paragraph including "Always operate with a BOOTSTRAP / RED / GREEN / REFACTOR TDD-first mindset." as the anchor for your insertion.
2. **Enforcing the 200-LOC cap against a 1k-27k-LOC neighbor.** Probe real file sizes in the touched module before you let the cap survive into the YAML. The fix is to swap `S1_file_size` for `S1_file_size_follow_<upstream>` with the cited LOC distribution baked into the rule's body.
3. **Letting the 30-LOC construct cap and depth-3 nesting cap apply to existing code.** The phrase "NEWLY CREATED" is what disambiguates. Without it, a strict reading forces a downstream agent to refactor upstream constructs that span 50-200 LOC, which violates the minimal-diff and no-degradation invariants and won't pass review. Mirror the scoping in the YAML's `hard_invariants` (`construct_loc_max_new_only: 30`, `construct_loc_max_existing_policy: unchanged_follow_<upstream>`).
4. **Claiming Firecrawl was authenticated when the helper backgrounded the CLI in a non-interactive shell.** Confirmed flake: `firecrawl --status` in a foreground fish session reports authenticated, but the same command backgrounded via `mcp_terminal` `background=true` writes an "Enter choice [1/2]:" prompt to the `.json` file because stdin isn't a TTY. Always re-run the map under `/opt/homebrew/bin/fish -lc '…'` foreground if a backgrounded map produced a 493-byte ANSI file. Pitfall #15 (Firecrawl `--limit 5000 --json --pretty` required) still applies; this is the orthogonal "auth banner ate the JSON" failure mode.
5. **Forgetting that the goal handoff line is paste-target only.** The skill prints `/goal …` once at the end; never feed it back into Hermes during the same skill turn — even for "verification". The artifacts pass when the validators say they pass, not when the goal runs.
6. **Treating the conversation's mid-flight constraint corrections as throwaway.** When the user says "this constraint should be scoped to X" mid-generation, that's a real signal — encode it in both the YAML (`hard_invariants` + `styleguide_rules` keys with explicit-scope names) and the Markdown (`### Project-Specific Overrides`). Don't just patch the live run; the skill should know how to do it next time.
7. **Listing every required GitHub Actions workflow but no loop to watch them.** The PR is not done when it's opened. Encode `G14` (`watch checks → fix → rebase → push → re-watch`) and `G15` (`respond to review-bot feedback in-place`) as explicit task IDs whose dependencies block REFACTOR. Without these, a downstream agent will mark the PR opened and call the goal complete.
8. **`validation_reconciliation.final_state` left at `all-claims-reconciled` when constraints were downgraded.** Per the contrarian validator: if any conflict carries `resolution: some-claims-downgraded`, the top-level `final_state` MUST match. Mismatch fails the structural validator. Three correction signals in one session (file size, construct size, nesting depth) → three `VR0n` conflicts + `final_state: some-claims-downgraded`.

## Working size, observed end-to-end

- 7-task helper baseline (canned scaffold) → 48-task hand-built YAML covering the full ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR contract: ~5 minutes to author from a Python dict + ~3 validator round-trips. See `programmatic-yaml-rebuild.md` for the Python-dict pattern.
- Markdown stays at ~58 KB after bulk augmentation (Scope + Execution Plan + 22 Acceptance Criteria + Validation Commands + Completion Definition + Failure Conditions + Final Output + Project-Specific Overrides). Substring-validator passes on the first augmentation when the canonical boilerplate is preserved untouched.
