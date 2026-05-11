# Paradox-resolving goal prompts

Use this reference when the user issues two constraints that look mutually exclusive but must both hold. The job of the goal prompt is NOT to negotiate the constraints away — it is to encode the deterministic architectural pattern that satisfies both literally.

## When this applies

The signal is usually a phrase like "it's paradoxical but make it work", "I know this seems contradictory", "do both anyway", or two requirements separated by "AND" that one of them seems to forbid the other. Real instances include:

- Generated artifacts that must "ship from the start" but stay gitignored (e.g. `.terminite/`, `.next/`, `.venv/`, generated SDK clients, `node_modules`, `dist/`, captured snapshots).
- Configuration that must "always be present" but must never be committed (e.g. `.env`, secrets bundles, signed certificates).
- Caches that must "exist on first use" but must never be in version control (e.g. `~/.cache/<app>`, build caches, model weights).
- Reproducible environments that must "match exactly" across machines but must never be committed verbatim (e.g. lock files derived from manifests, IDE workspaces, devcontainer overlays).

The unifying shape: a derived/runtime artifact that must be (a) deterministically reproducible, (b) immediately available after a single non-interactive command, and (c) never tracked.

## Resolution pattern: deterministic regeneration from in-tree templates

The architecture has six load-bearing pieces. Every paradox-resolving goal prompt MUST encode all six explicitly:

1. **In-tree source-of-truth templates.** Commit the template payloads (TypeScript modules, Jinja2 files, JSON descriptors, whatever the runtime is) under a stable source path. The templates are tracked; their renderings are not.
2. **A single deterministic non-interactive bootstrap command.** Name the exact command (e.g. `mise run terminite:bootstrap`, `bun run bootstrap`, `make .terminite/`). It MUST be byte-stable: same inputs → same output bytes, with no environment-dependent randomness, no UUIDs, no timestamps, no locale-sensitive sort orders. If randomness is unavoidable (e.g. project IDs), seed it from a content hash so re-runs produce identical bytes.
3. **An automatic trigger wired to a lifecycle event.** The bootstrap MUST run automatically on the lifecycle event the user expects ("from the very start" usually means right after `<package-manager> install`). Name the exact hook (`postinstall` script in `package.json`, `pip install -e .` setup hook, `mise install`-time hook, Cargo build script). The standalone command and the lifecycle hook MUST produce identical output.
4. **Idempotence as a hard invariant.** Re-running the bootstrap on an already-correct tree MUST produce zero diff. Encode this as a contract test that fails CI if a second run changes any byte.
5. **The exclusion invariant.** `.gitignore` (or equivalent) MUST contain exactly one entry for the artifact and that entry MUST never be removed or duplicated by the bootstrap. Encode `git ls-files | grep '^<artifact>/'` returning empty as a CI-enforced invariant.
6. **An invariant-check protocol that runs after every task.** The companion task list YAML's `agent_runtime_protocol` MUST include a `paradox_invariant_check` field that the agent reasserts after every status transition. Without this, the paradox tends to drift mid-execution.

## Required additions to the goal Markdown

When a paradox is detected, the standard required-sections list still applies, but reinforce these sections:

- **`## Goal`** — open with "Resolve the apparent paradox by..." so the resolution architecture is the headline, not an afterthought.
- **`## Original Intent`** — quote both halves verbatim. Add a sentence: "The downstream agent MUST honor both halves together; resolve the paradox, do not silently relax either constraint."
- **`## Assumptions`** — explicitly enumerate the six load-bearing pieces above as assumptions about how the resolution will work.
- **`## Scope > In Scope`** — list the bootstrap pipeline, the automatic trigger, the idempotence contract, the exclusion invariant, AND the invariant-check protocol as separate scope items.
- **`## Scope > Out of Scope`** — explicitly list "committing the artifact to git" and "removing the exclusion entry" as out of scope. The agent will be tempted to "fix" the paradox by relaxing one side; pre-empting that here is cheap insurance.
- **`## Acceptance Criteria`** — add four criteria mirroring the invariants: (a) fresh-clone produces full tree via one command, (b) re-run is byte-stable, (c) artifact stays excluded after every step, (d) no path under the artifact is ever tracked or staged.
- **`## Validation Commands`** — name the exact commands the receiving agent runs to prove each invariant: `git ls-files | grep '^<prefix>/'`, `git check-ignore -v <prefix>/<file>`, `git status --porcelain`, the bootstrap command twice in a row, `diff` between the two runs.
- **`## Failure Conditions`** — explicitly list "artifact becomes tracked", "exclusion entry is removed or duplicated", and "second run produces non-zero diff" as failure conditions.

## Required additions to the companion TDD task list YAML

The YAML carries the load between sessions. Reinforce these blocks:

- **`metadata.hard_invariants[]`** — include the exclusion invariant ("`.gitignore` contains exactly one entry for X"), the no-tracking invariant ("`git ls-files` reports zero `X/*` paths"), the idempotence invariant ("re-running bootstrap is byte-stable"), and the bootstrap-command invariant ("a single non-interactive command reproduces the tree").
- **`guardrails`** — declare a dedicated paradox guardrail (e.g. `G1_paradox_invariant`) that every ANALYSIS, BOOTSTRAP, RED, GREEN, and REFACTOR task references in its `guardrails` list. Co-declare `G_idempotence` and `G_no_interactive` so the bootstrap design has them in scope from the start.
- **RED phase** — author one test per invariant (`tests/<artifact>-from-scratch.test.ts`, `tests/<artifact>-idempotence.test.ts`, `tests/<artifact>-postinstall.test.ts`, `tests/gitignore-invariant.test.ts`, `tests/hygiene-<artifact>.test.ts`). Each test MUST be committed and observed failing for the right reason before any GREEN production change. The RED phase `hard_gate` MUST forbid GREEN edits before all five RED tests are committed.
- **GREEN phase** — order tasks: (G1) split/promote in-tree templates → (G2) implement the bootstrap orchestrator with structured `BootstrapResult` → (G3) wire the standalone task → (G4) wire the automatic trigger → (G5) refactor any pre-existing init/codegen path to delegate to the new orchestrator → (G6) extend the hygiene check → (G7) document the paradox in README.
- **REFACTOR phase** — include a "ruthless final-diff cleanup" task that re-asserts every invariant on the final diff and fails if any is violated.
- **`agent_runtime_protocol.paradox_invariant_check`** — write the exact verification recipe as a string. The agent reasserts it after every status transition. Example shape:

  ```yaml
  agent_runtime_protocol:
    paradox_invariant_check: >
      After every status transition, the agent MUST verify:
      (1) `.gitignore` contains exactly one line equal to `<prefix>/`;
      (2) `git ls-files` reports zero `<prefix>/*` paths;
      (3) `git status --porcelain` reports zero `<prefix>/*` paths as staged.
      Any violation aborts the current task and resumes invariant repair.
  ```

## Worked example: `.terminite/` (May 2026)

User said: "Update the repo to have all .terminite files and directories generated from the very start. .terminite should still remain in .gitignore, it's paradoxical but make it work."

The resolved architecture:

- In-tree templates: `src/terminite/templates.ts`, `src/terminite/mise-template.ts`, `src/terminite/templates/<area>.ts` (split when >200 LOC).
- Single deterministic command: `mise run terminite:bootstrap` → runs `bun src/terminite/bootstrap.ts` → writes the full `.terminite/` tree from the in-tree templates.
- Automatic trigger: `package.json` `scripts.postinstall = "bun src/terminite/bootstrap.ts"` so any `bun install` produces the tree.
- Idempotence: `BootstrapResult` includes `alreadyPresent: boolean`; existing-equal files are not rewritten; second run produces zero diff.
- Exclusion invariant: existing `ensureGitignore` in `src/terminite/preflight.ts` already enforces "exactly one `.terminite/` entry, never duplicated, never removed".
- Invariant check after every task: `paradox_invariant_check` block in `agent_runtime_protocol`.

Generated artifacts: `update-repo-have-all-terminite-goal.md` (paradox resolution in `## Goal`, six pieces in `## Assumptions`, mirror failures in `## Failure Conditions`) + `terminite-bootstrap-paradox-tdd-tasks.yaml` (G1_paradox_invariant referenced by every task; six RED tests; ANALYSIS task A05 dedicated to architecting the resolution).

## Anti-patterns

- **"Just commit it"** — relaxes the exclusion side. Do not propose this. The user's "make it work" means honor both.
- **"Just don't ignore it"** — same anti-pattern, opposite direction.
- **"Generate it lazily on first use"** — fails the "from the very start" requirement when the user expects clone-then-go.
- **"Use a symlink to a system path"** — non-portable, breaks reproducibility, hides the artifact from co-located tooling.
- **Encoding the paradox in prose only** — without the `paradox_invariant_check` protocol in the YAML, mid-execution agents drift. The invariant check MUST be a structured field the agent reads programmatically.
- **Letting GREEN tasks touch `.gitignore`** — the only legitimate `.gitignore` writes happen in BOOTSTRAP/RED-supporting infrastructure and via the existing repo-preflight idempotent `ensureGitignore` path. Never write a GREEN task whose primary change is a `.gitignore` edit.

## Cross-references

- See `references/coding-agent-task-list-yaml.md` for the YAML schema and the `agent_runtime_protocol` block.
- See `references/research-tool-readiness.md` when the paradox involves vendor-specific lifecycle semantics (e.g. Bun postinstall, mise hooks, Cargo build scripts) that must be source-validated via opensrc + Firecrawl before the bootstrap design lands.
