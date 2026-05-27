# Skill-authoring goal prompts (deliverable is itself an agentskills.io SKILL.md package)

Use this reference when the user's prompt asks the generator to produce a goal whose **deliverable is a coding-agent-agnostic agent skill** (a `SKILL.md` + optional `references/`, `scripts/`, `templates/`, `assets/`, conforming to https://agentskills.io/specification). Real example: "create a coding-agent-agnostic agent skill named `design-with-pencil`". This is a recurring class — encode it once.

## Distinguishing signals

- The deliverable is a directory shaped like `<skill-name>/SKILL.md` + supporting dirs.
- The user names a methodology repo (e.g. `srinitude/design-craft`), a CLI/SDK to wrap (e.g. Pencil CLI, OpenHue), and a spec URL (agentskills.io, anthropic guide PDF, llms.txt).
- The skill must be agent-agnostic: no Claude-/Cursor-/Windsurf-/Replit-/IDE-specific behavior, no model-provider-specific syntax.
- The user demands exactly one deterministic workflow path through the skill.

## Required research (front-load before the helper runs)

1. **`firecrawl map --limit 5000 --json --pretty -o research/url-maps/<tech>.json`** for every doc root the user cites:
   - The wrapped tool's official docs root (e.g. `https://docs.pencil.dev/`).
   - The agentskills.io site (`https://agentskills.io`).
   - Each map file's `data.links` is a list of strings or `{url, title, description}` objects depending on doc shape — defensively check `isinstance(link, str)` before using it as a URL.
2. **`firecrawl scrape <page> --format markdown --json -o research/scrapes/<page>.json`** for the most important pages (per `firecrawl-cli-1-16-quirks.md` §3a-pre — always `-o`, never piped to stdin):
   - The wrapped tool's CLI reference page (full command surface, every flag, every subcommand, every env var, every supported MCP tool, every example invocation).
   - `https://agentskills.io/specification` — the authoritative frontmatter contract (name ≤64 chars, description ≤1024 chars, optional `license`/`compatibility`/`metadata`/`allowed-tools`, optional `scripts/` `references/` `assets/` dirs, progressive disclosure).
   - `https://agentskills.io/skill-creation/best-practices` — start from real expertise, design coherent units, moderate detail, progressive disclosure, plan-validate-execute, bundle reusable scripts.
   - `https://agentskills.io/skill-creation/optimizing-descriptions` — how skill triggering works, trigger eval queries, should/should-not split.
   - `https://agentskills.io/skill-creation/quickstart` — minimal directory shape (`.agents/skills/<name>/SKILL.md`).
   - `https://agentskills.io/skill-creation/using-scripts` — design scripts for agentic use (no interactive prompts, `--help` docs, helpful error messages, structured output, version-pinned `uvx`/`npx`/`bunx`).
3. **`opensrc fetch <org>/<repo>`** for any methodology repo the user names. Read its `SKILL.md` (if it ships one), its `README.md`, its `references/` directory, and its `scripts/` directory deeply enough to enumerate:
   - The methodology's pipeline / phases / structure (e.g. Design Craft's THINK→RESEARCH→SHAPE→BUILD→VERIFY→ITERATE→SHIP).
   - The reference catalog and what each reference governs.
   - Naming conventions, design primitives, component hierarchy guidance, validation practices, anti-patterns.
   - Any bundled scripts, schemas, templates that the authored skill should leverage or analogously bundle.
4. **Anthropic skill-building PDF** (`https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf`) — `firecrawl scrape ... --format markdown --json -o ...` works on the PDF URL; otherwise extract via `firecrawl agent --schema-file ... --urls ...` per SKILL.md step 11.

Persist every research artifact under `~/.hermes/goal-prompts/research/{url-maps,scrapes}/` so the YAML's `validation_evidence.firecrawl.required_maps_present[*]` and `.evidence[]` can cite real on-disk paths with real link counts.

## Pre-helper prompt construction (file-fed, not heredoc)

Per SKILL.md pitfall #16, write the full source prompt to `/tmp/<project>_prompt.txt` first, then call:

```bash
python3 ~/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py \
  --workdir <abs-path-to-target-repo-or-fresh-dir> \
  --json "$(cat /tmp/<project>_prompt.txt)"
```

The prompt body MUST enumerate:

- **Hard constraints** as numbered, enforceable rules (e.g. "exactly one deterministic design path", "PENCIL_CLI_KEY required, never logged", "Tokens → Atoms → Molecules → Organisms → Templates → Screens in strict order", "Design Craft used operationally in every phase").
- **Distinguishable skill outputs** — every file the deliverable contains, listed with its purpose:
  - `<skill>/SKILL.md` with frontmatter that lists the canonical name regex, ≤1024-char description requirements, license, compatibility, metadata.
  - `<skill>/references/<topic>.md` files — session-specific or condensed-knowledge supplements.
  - `<skill>/templates/<name>.<ext>` — starter files for copy-and-modify.
  - `<skill>/scripts/<name>.<ext>` — re-runnable verifications (preflight checks, validators, deterministic probes).
  - `<skill>/assets/<name>.<ext>` — JSON schemas, brand kits, etc.
  - `<skill>/tests/` + `<skill>/tests/fixtures/` — RED-first failing tests with canonical fixtures.
  - `<skill>/CHECKLIST.md`, `<skill>/README.md`, `<skill>/LICENSE`, `<skill>/mise.toml`.
- **Acceptance criteria** that exercise the agentskills.io frontmatter contract specifically (name regex, description length, body section order), the wrapped tool's command surface fidelity, the methodology's coverage per phase, the no-secrets grep, the agent-agnostic grep, and the trigger eval should/should-not split.
- **Tests required** — one RED test per acceptance criterion, written before any implementation. Use deterministic fixtures (canonical surface lists, methodology reference lists, frontmatter contract JSON, section-order list, positive/negative schema fixtures, screenshot manifests).
- **Local CI/CD** — `mise.toml` with `setup`/`lint`/`test`/`check` tasks; `mise run check` must be green before any commit.
- **Domain: software-development** — guarantees the helper detects `domain: "software-development"` + `domain_confidence: "high"` and emits the full constraints + cleanup + engineering-principles sections (verify in the frontmatter after generation).

## Fixtures the authored skill should ship (and the YAML should require)

These recur across every skill-authoring goal. Encode them in the prompt and the YAML so RED tests can assert deterministically:

- `tests/fixtures/frontmatter-contract.json` — locks the name regex, description min/max length and required substrings, license, compatibility, metadata.
- `tests/fixtures/<tool>-cli-surface.txt` — every documented subcommand/flag/env var/MCP tool/path, one canonical token per line, sourced from the tool's official CLI page with a `# source: <url>` header.
- `tests/fixtures/<methodology>-references.txt` — every methodology reference file the authored SKILL.md cites, with a `# source: <url>` header.
- `tests/fixtures/skill-md-section-order.txt` — locked SKILL.md body section order.
- `tests/fixtures/should-trigger.txt` + `tests/fixtures/should-not-trigger.txt` — ≥8 prompts each per `optimizing-descriptions` best practices.
- `tests/fixtures/state-inventory-positive.json` + `tests/fixtures/state-inventory-negative.json` (if the authored skill validates structured user inputs).
- `tests/fixtures/manifest-pass.json` / `manifest-warn.json` / `manifest-fail.json` (if the authored skill produces a validation report).

## YAML phase shape (rebuild programmatically per `programmatic-yaml-rebuild.md`)

A skill-authoring goal needs ~35–45 tasks, NOT the helper's canned 7. Use the programmatic rebuild pattern:

- **ANALYSIS (5–7)** — A01 verify research artifacts on disk; A02 extract canonical CLI surface fixture from the tool's scrape; A03 map methodology → SKILL phases fixture from the methodology's opensrc-fetched SKILL.md; A04 trigger/anti-trigger fixtures; A05 frontmatter contract fixture; A06 SKILL.md section-order fixture.
- **BOOTSTRAP (2–3)** — repo scaffold + mise task runner; fixtures into the scaffold; CI wired (`mise run check` expected to be red until R-tests exist).
- **RED (10–14)** — R00 hard-gate kickoff (commit all failing test skeletons together, observed failing for the right reason), then one RED test per acceptance criterion: frontmatter contract, section order, CLI surface fidelity, methodology coverage, preflight script exit-code matrix, any domain-specific scripts (contrast.py, run_validation.py, state-inventory validator), trigger eval, no-secrets grep, agent-agnostic grep.
- **GREEN (12–18)** — G01 implement the SKILL.md frontmatter + section-order validator and the SKILL.md body just deep enough to pass R01/R02; G02..G06 fill SKILL.md phases one at a time (each phase cites its methodology reference operationally, not by name only); G07..G15 implement each preflight/validator/runtime script, fixture-by-fixture, marking each RED test green as it lands; G(last) author README + LICENSE + install table with manual paths for `.agents/skills/`, `.claude/skills/`, `.cursor/skills/`.
- **REFACTOR (2)** — X01 ruthless final-diff cleanup; X02 engineering-rubric replay across P1..P18.

### Required shared blocks

- `styleguide_rules`: file-size (≤200 LOC), construct-size (≤30 LOC), nesting (≤3), tests-first, no-secrets, doc-citations (every tool token traces back to the canonical surface fixture), agent-agnostic, methodology-operational (every phase section MUST cite its methodology reference AND state the operational check it contributes — citation alone is forbidden), deterministic, screenshot/real-output-required if applicable.
- `guardrails`: no-execution (never run the goal Markdown or handoff line during this run), continuation contract, RED hard-gate, tool-only (e.g. `pencil_only`, `openhue_only`), system-first ordering (e.g. `design_system_first`), methodology-every-phase, research-only-tools (research-time tools like Firecrawl/opensrc must NOT be required at the AUTHORED SKILL's runtime unless explicitly cited as optional), no-secret-leak, no-runtime-invocation in tests, ruthless cleanup.
- `ci_commands`: `CC_MISE_SETUP`/`LINT`/`TEST`/`CHECK`, `CC_VALIDATE_SKILL_MD`, `CC_VALIDATE_FRONTMATTER`, `CC_CHECK_<TOOL>_CLI`, `CC_RUN_VALIDATION`, `CC_GREP_NO_SECRETS`, `CC_GREP_CLI_SURFACE`, `CC_GREP_<METHODOLOGY>_COVERAGE`, `CC_TRIGGER_EVAL`, `CC_SCHEMA_VALIDATE`/`CC_SCHEMA_REJECT`, `CC_AGENT_AGNOSTIC`, `CC_GIT_STATUS_CLEAN`, plus `CC_VALIDATE_GOAL` and `CC_VALIDATE_TASKS` that re-run the upstream `validate_optimized_markdown` and `validate_task_list_yaml.py` against the running goal artifacts.

## Verification checklist before printing the handoff

- [ ] Helper emitted `domain: "software-development"` and `domain_confidence: "high"`.
- [ ] YAML task count is ≥30 after programmatic rebuild; ANALYSIS / BOOTSTRAP / RED / GREEN / REFACTOR all populated.
- [ ] Every GREEN task has at least one direct R* in `dependencies` (validator enforces; pitfall #5 of `programmatic-yaml-rebuild.md`).
- [ ] All 18 engineering principles are referenced somewhere (or trimmed per `programmatic-yaml-rebuild.md` pitfall #9).
- [ ] `validation_evidence.firecrawl.required_maps_present` records every documented research-target with real `url_count` integers; `validation_evidence.firecrawl.evidence[]` cites the scraped pages by absolute path.
- [ ] `validation_evidence.opensrc.fetched[<org>/<repo>].key_paths[]` cites the methodology repo's `SKILL.md`, `README.md`, and the specific `references/*.md` the YAML's task list references.
- [ ] `validation_reconciliation.final_state` is `all-claims-reconciled` (or honestly `some-claims-downgraded` / `some-claims-escalated-to-execution-time` if any research tool wasn't usable).
- [ ] Both validators return OK before printing the handoff `/goal` line. Print the handoff once; do NOT execute it.

## Anti-patterns specific to skill-authoring goals

1. **Letting the helper emit the canned 7-task scaffold and stopping.** A skill-authoring deliverable with 15+ files and 8+ test categories cannot be executed from a 7-task plan. Rebuild programmatically.
2. **Inlining the wrapped CLI's surface in prose.** The surface MUST live in a fixture file the RED test asserts against; prose drifts.
3. **Citing the methodology only as a reference in SKILL.md.** The user's brief almost always says "must be used in every step, not merely cited" — encode `S8_methodology_operational` as a styleguide rule and `G6_methodology_every_phase` as a guardrail.
4. **Adding host-agent-specific install instructions inside SKILL.md body.** Per `agentskills.io` the SKILL.md is host-agent-agnostic. Host-agent install paths belong in `README.md`'s table (`.agents/skills/`, `.claude/skills/`, `.cursor/skills/`, `~/.computer/skills/`, `.gemini/skills/`).
5. **Forgetting the no-secrets test has to detect *implementation drift*, not just current cleanliness.** Add a synthetic-leak control fixture under `tests/fixtures/_synthetic_leak.txt` AND make the production-tree grep use `--exclude-dir=tests/fixtures` so the test would fail if a real leak appeared in a non-fixture file.
6. **Treating the authored skill's `references/` as a full mirror of upstream docs.** Per the curator/SKILL-update guidance: references hold *condensed* knowledge banks and session-specific detail, not full doc mirrors. Keep them concise and task-shaped.
