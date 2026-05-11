# Mandatory final step: derive the coding-agent-updatable TDD task list YAML from the validated goal prompt

This is the **mandatory final step** of `goal-prompt-generator` (skill version `1.1.0`+). After the optimized goal prompt Markdown passes validation, the generator must derive a paired ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR TDD task list YAML, validate it structurally, and validate its research/source claims with Firecrawl and `opensrc`.

The YAML is the **runtime state** any coding agent reads and mutates through its building process. The Markdown goal prompt is the **immutable contract**. Do not regenerate the goal. Do not execute it. Just produce the YAML and validate it.

---

## When this applies

This step runs **on every successful generation** when the domain is software-development or classification is uncertain. It is no longer gated on a separate user request; the goal Markdown alone is an incomplete artifact.

It still applies when the user asks to:

- "combine these and turn it into a task list YAML"
- "make a YAML the coding agent can update through its building process"
- "ANALYSIS / BOOTSTRAP / RED / GREEN / REFACTOR task list"
- "each task needs dependencies, blockers, validation steps, ci/cd, styleguide, guardrails, learnings, gotchas, context files/urls, status"

Anti-triggers:

- Domain is unambiguously non-software (e.g. a creative-writing prompt with no code surface). The optimized Markdown still saves; the YAML step is skipped and noted in the report.
- User wants the plan *executed* — this skill only produces and validates the YAML.

---

## Required top-level YAML shape

```yaml
metadata:                # plan id, version, source goal markdown path + hash, hard invariants
validation_evidence:     # PROOF that any tool you claim was used was authenticated/cached
                         # firecrawl: cli_version, auth, url_maps_root,
                         #   required_maps_present[<tech>]: { file, url_count, map_command, map_limit: 5000 }
                         #   evidence[]: scrape/crawl/search/extract citations
                         # opensrc: cli_version, cache_root,
                         #   fetched[<repo>]: { key_paths[], pinned_version, divergences[] }
                         # authoritative_reference_urls: grouped by technology
styleguide_rules:        # S1..Sn keyed rules, referenced by id from each task
guardrails:              # G1..Gn keyed rules, referenced by id from each task
ci_commands:             # CC_* keyed shell commands, referenced by id from each task
principles:              # P1..P18 — one entry per software engineering core principle in scope
phases:                  # ordered: ANALYSIS, BOOTSTRAP, RED, GREEN, REFACTOR; each has tasks: []
agent_runtime_protocol:  # status_transitions, mutable_fields, immutable_fields, resume_protocol, goal_manager_continuation_contract
coding_agent_execution_contract:  # MANDATORY — see "Coding Agent Execution Contract" below
```

The **shared rule blocks** (`styleguide_rules`, `guardrails`, `ci_commands`, `principles`) are the trick that keeps the file compact. Tasks reference them by id (`S1_file_size`, `G3_no_silent_fallback`, `CC_test_unit`, `P10_boundary_validation`) instead of repeating prose. This makes patches surgical and lets the validator catch dangling references.

---

## Required per-task fields (all 15 MUST be present on every task)

The user's prompt enumerated these explicitly. All are required:

```yaml
- id: <UNIQUE_TASK_ID>           # e.g. A01, B03, R12, G07, X02
  title: "<one-line human-readable>"
  status: pending                # pending | in_progress | completed | blocked | cancelled
  dependencies: [...]            # sole task graph edge: task ids that must complete first; prerequisite gates are explicit tasks and reverse blockers are inferred
  validation_steps:              # ordered, observable, user-facing — include non-final GOAL_RUNTIME_STATUS: CONTINUE marker discipline
    - "<step 1>"
    - "<step 2>"
  ci_commands: [CC_*, ...]       # references into top-level ci_commands
  styleguide_rules: [S*, ...]    # references into top-level styleguide_rules
  guardrails: [G*, ...]          # references into top-level guardrails
  learnings: []                  # MUTABLE — agent appends as it discovers facts
  gotchas: []                    # MUTABLE — agent appends pitfalls and rewind notes
  context_files: [...]           # files the agent should read for context
  context_urls: [...]            # authoritative documentation URLs (sourced from Firecrawl maps)
  principle_ids: [P*, ...]       # which engineering principles the task validates
```

Three of those fields (`status`, `learnings`, `gotchas`) are explicitly mutable; everything else is contract. Document this in the `agent_runtime_protocol` block at the bottom of the YAML so a future session knows what it may overwrite.

`agent_runtime_protocol.goal_manager_continuation_contract` is mandatory for `/goal`-ready artifacts. It must include runtime `hermes /goal`, the source Markdown section, the literal continuation contract, `continue_until` mentioning `max_turns`, both response markers (`GOAL_RUNTIME_STATUS: CONTINUE` and `GOAL_RUNTIME_STATUS: COMPLETE`), `human_input_policy` forbidding user asks on non-final turns, and `judge_shape` warning not to say the overall goal is complete/blocked/waiting for input before final validation.

`dependencies` is the only task graph field for new generated ledgers. Prerequisite gate conditions (for example "Firecrawl auth verified" or "Bun >= 1.1.30 installed") MUST be modeled as explicit ANALYSIS or BOOTSTRAP tasks, and downstream work references those task ids in `dependencies`. Do not emit `prerequisites`; do not emit `blocking_tasks` because reverse blockers are inferred from dependent tasks. The validator intentionally has a narrow compatibility path for already-sealed immutable ledgers that contain legacy `prerequisites` / `blocking_tasks` and list them under `agent_runtime_protocol.immutable_fields`; execution agents may not rewrite those immutable fields, so the validator accepts that legacy shape while still rejecting it for new artifacts.

---

## Phase shape: ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR

Use these five phases, in this order. The mapping from the goal Markdown's `## Execution Plan` is:

| Goal Markdown phase | YAML phase  | Purpose |
|---------------------|-------------|---------|
| (new — sourced from `## Research and Source Validation Requirements`) | `ANALYSIS`  | Source-reality report, test manifest, doc validation, source inspection, contract gap map. **No production edits.** |
| `Phase 0: BOOTSTRAP` | `BOOTSTRAP` | Local CI/CD, lockfiles, principle bootstrap records, evidence directory shape, eval seeds. Exit gate: validation runs cleanly (even if every test still fails). |
| `Phase 1: RED`       | `RED`       | Every unit/integration/e2e test enumerated in the manifest is committed and observed failing for the right reason. **Hard gate: no production code edits permitted before R00 plus all RED tasks are committed.** Encode this `hard_gate` as a string field on the phase block. |
| `Phase 2: GREEN`     | `GREEN`     | Smallest production code per RED suite, in dependency order. Each GREEN task references ≥1 specific RED task in `dependencies`. |
| `Phase 3: REFACTOR`  | `REFACTOR`  | Dedupe, demote dead code/strings, principle rerun, security paranoid pass, minimal-diff audit. |

Encode `hard_gate` like this on the RED phase block:

```yaml
- name: RED
  hard_gate: >
    No production code edits are permitted before R00 (kickoff) is completed and every RED
    task is committed and observed failing for the documented reason. Any attempt to edit
    production code while a RED task is still pending or in_progress must abort and resume
    the failing RED task instead.
  tasks:
    - id: R00
      title: "RED kickoff: enumerate test manifest from spec"
      ...
```

The `agent_runtime_protocol` section should explicitly say: "Never restart RED phase if all RED tests are already committed and observed failing."

---

## Firecrawl `map --limit 5000` validation flow

For every technology referenced in the validated goal prompt spec — frameworks, runtimes, providers, CLIs, SDKs, vendor APIs — execute this flow and record the evidence in `validation_evidence.firecrawl`.

### 1. Probe readiness

```bash
FIRECRAWL_NO_TELEMETRY=1 firecrawl --version
FIRECRAWL_NO_TELEMETRY=1 firecrawl --status
```

Firecrawl may exit `0` while printing an authentication/setup banner ("Welcome! To get started, authenticate..."). Treat that as **not usable** for source validation. Do not claim mapping succeeded; record the requirement as execution-time validation only and label any alternate discovery as preliminary.

### 2. Map every official documentation root with `--limit 5000`

```bash
firecrawl map --limit 5000 --json --pretty https://<official-docs-root> \
  --output <execution-dir>/research/url-maps/<tech>.json
```

The `--limit 5000` is a hard requirement from the user's prompt. Lower limits silently truncate the URL surface and break downstream `context_urls` validation.

**`--json --pretty` is also required.** Firecrawl 1.16.0's default `map` output is a newline-delimited plain-text URL list (the file is *not* JSON and `json.load()` throws `JSONDecodeError: Expecting value: line 1 column 1`). Without the JSON flags the structural validator's `url_count` check cannot read the file and the agent ends up either fabricating counts or recording zero. Always pass both flags.

**Verify each map has real content before recording it.** Some doc roots return only the seed URL (1 link) because the page is a leaf, dynamic JSON, or behind a docc renderer. Examples observed in practice:

| Bad root (returns 1 link) | Good root (returns 90+ links) |
|---|---|
| `https://huggingface.co/docs/transformers/model_doc/qwen3_vl` | `https://huggingface.co/docs/transformers` |
| `https://developer.apple.com/documentation/applicationservices/accessibility_constants` | `https://developer.apple.com/documentation/accessibility` |

The fix: map a higher-level root, then cite the deep-link in `validation_evidence.firecrawl.evidence[]` via `firecrawl scrape <deep-url>`. After every `map` run, immediately count links:

```bash
python3 -c "import json; d=json.load(open('research/url-maps/<tech>.json')); ll=d.get('data',{}).get('links') or d.get('links') or []; print(f'{len(ll)} links')"
```

If `len(ll) < 5`, re-map with a higher-level root before treating the file as evidence.

### 3. Record each map in `validation_evidence.firecrawl.required_maps_present`

Read each cached map's `data.links` length and write it into the YAML:

```yaml
validation_evidence:
  firecrawl:
    cli_version: "1.x.y"
    auth: authenticated   # or: unavailable
    url_maps_root: "research/url-maps"
    required_maps_present:
      bun:
        file: "research/url-maps/bun.json"
        url_count: 1842
        map_command: "firecrawl map --limit 5000 https://bun.sh/docs"
        map_limit: 5000
      hono:
        file: "research/url-maps/hono.json"
        url_count: 612
        map_command: "firecrawl map --limit 5000 https://hono.dev/docs"
        map_limit: 5000
      ...
```

The `url_count` is your evidence that the map actually contains data, not just an auth-prompt error masquerading as success. A non-positive `url_count` must be treated as an unavailability marker.

### 4. Use the rest of the Firecrawl toolset on URLs surfaced by the maps

Maps alone are not enough. Use the rest of the Firecrawl CLI surface to validate the YAML's `context_urls` and `validation_evidence.authoritative_reference_urls`:

```bash
firecrawl scrape   <url>                # validate page exists, capture canonical content
firecrawl crawl    <url> --depth 2      # validate sub-tree of related docs
firecrawl search   "<query>" --site <tech-docs-root>
firecrawl extract  <url> --schema <schema>  # pull structured facts (versions, endpoints)
```

Cite each tool invocation under `validation_evidence.firecrawl.evidence[]`:

```yaml
validation_evidence:
  firecrawl:
    evidence:
      - tool: scrape
        url: "https://bun.sh/docs/runtime/typescript"
        captured_at: "2026-05-06T03:18:00Z"
        cited_in_tasks: [A03, B02, G05]
      - tool: extract
        url: "https://hono.dev/docs/api/hono"
        schema: "endpoint-listing"
        captured_at: "2026-05-06T03:19:00Z"
        cited_in_tasks: [A04, R07]
```

### 5. Validation honesty rules

- Do not claim a Firecrawl map "ran during this generation" if you only verified the cache. Phrase it as "verified the cache covers the required URLs" and instruct a downstream task to refresh maps older than N days.
- Every `context_urls` entry on every task SHOULD appear in some `required_maps_present[<tech>]` map's link list — that is what makes the URL "authoritative" rather than user-typed.
- If Firecrawl was unavailable, set `validation_evidence.firecrawl.auth: unavailable`, leave `required_maps_present` empty (or `null`), and add an A* ANALYSIS task such as `A03: Verify Firecrawl authentication and map availability`, then make tasks that need Firecrawl depend on `A03` and include `validation_steps: ["firecrawl --status reports authenticated", ...]`.

---

## `opensrc` source-validation flow

For every technology in the spec that has an open-source repository, execute this flow and record the evidence in `validation_evidence.opensrc`.

### 1. Probe readiness

```bash
opensrc --version
opensrc list      # smoke test that fetched repos are usable
```

If `opensrc` is unavailable, set `validation_evidence.opensrc.cli_version: unavailable` and add an ANALYSIS task to install/auth it before any source claim is finalized.

### 2. Fetch each open-source dependency

```bash
opensrc path  <org>/<repo>            # writable cache path
opensrc fetch <org>/<repo>            # materialize source
opensrc fetch <org>/<repo>@<version>  # pin to the version your spec depends on
```

### 3. Cite specific source paths under `validation_evidence.opensrc.fetched`

For every API, version, file path, or behavioral claim the YAML makes about that technology, cite the exact `<repo>/<file>` (and line range when reasonable):

```yaml
validation_evidence:
  opensrc:
    cli_version: "0.x.y"
    cache_root: "~/.opensrc/cache"
    fetched:
      honojs/hono:
        pinned_version: "4.6.3"
        key_paths:
          - "src/hono.ts:1-120"          # cited by A04, R07
          - "src/router/reg-exp-router/router.ts"
          - "package.json"               # version + exports cross-check
        divergences: []                  # main vs pinned tarball mismatches, if any
      oven-sh/bun:
        pinned_version: "1.1.34"
        key_paths:
          - "src/bun.js/api/server.zig"
          - "packages/bun-types/index.d.ts"
        divergences:
          - field: "Bun.serve options.idleTimeout"
            note: "main introduces field absent in 1.1.34; pin to 1.1.34 spec"
```

### 4. Cross-check version pins

The repo's `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` is the source of truth. If `main` diverges from a pinned tarball, record the mismatch under `divergences[]` and update the YAML to match the pinned version.

### 5. Honesty rules

- Cite paths, not just repo URLs. `https://github.com/honojs/hono` is not a citation; `honojs/hono/src/hono.ts:1-120` is.
- A `key_paths` entry must actually exist after `opensrc fetch`. Never invent paths.
- If a claim is impossible to source-validate (e.g. the technology is closed-source), document it under `validation_evidence.firecrawl.evidence[]` instead, and add an ANALYSIS task that turns the closed-source claim into a black-box behavioral test.

---

## Structural validator (run BEFORE handing the file back)

After writing the YAML, always run:

```bash
python3 ~/.hermes/skills/software-development/goal-prompt-generator/scripts/validate_task_list_yaml.py <path-to-yaml>
```

The validator catches the failure mode where one CI/styleguide/guardrail/principle/dependency ID is misspelled or never declared. It enforces:

- every per-task field is present,
- every `ci_commands` / `styleguide_rules` / `guardrails` / `principle_ids` reference resolves to a declared id,
- every `dependencies` reference resolves to an existing task id,
- **legacy graph-field ban**: no new task contains `prerequisites` or `blocking_tasks`; model gates as explicit tasks and infer reverse blockers from dependents. Already-sealed immutable ledgers that list those fields under `agent_runtime_protocol.immutable_fields` are accepted through a compatibility path because execution agents may not rewrite immutable fields,
- **GREEN → RED traceability**: every GREEN task references ≥1 RED task in `dependencies` (transitive coverage through another GREEN dep is acceptable but flagged),
- **principle coverage**: every declared principle id appears in at least one task's `principle_ids`,
- **phase ordering invariant**: no task in phase N has a dependency on a task in phase N+1 or later,
- the RED phase carries a non-empty `hard_gate` field,
- `validation_evidence.firecrawl.required_maps_present[*].url_count` is a positive integer when `auth: authenticated`; absent / zero / `null` when `auth: unavailable`,
- every `firecrawl map` `map_command` recorded in evidence contains the literal `--limit 5000`,
- `validation_evidence.opensrc.fetched[*].key_paths` is a non-empty list when `cli_version` is not `unavailable`,
- `agent_runtime_protocol.goal_manager_continuation_contract` exists and carries the `/goal` continuation markers, `max_turns` policy, and no-user-input policy for new v1.7.0+ task lists. Already-sealed immutable legacy ledgers may omit this block only when their executor contract rule itself contains the positional prompt argument / continuation language needed for safe execution.

If the validator exits non-zero, fix the YAML and re-run. Do not return the YAML to the user with structural errors.

---

## Common pitfalls

1. **Forgetting the space after `:`** when writing `key:"value"` instead of `key: "value"`. PyYAML's scanner reports it as `could not find expected ':'` two lines later. Fix with `perl -i -pe 's/^(\s*[A-Za-z][A-Za-z0-9_]*):"/\1: "/' <file>.yaml` and re-parse.
2. **Repeating styleguide rules and CI commands inline on every task.** Don't. Use the shared-block + reference-by-id pattern; it's why those top-level blocks exist.
3. **Skipping `learnings: []` / `gotchas: []`** because they're empty at generation time. The empty arrays are the contract surface — they tell the coding agent it's allowed to append there.
4. **Putting orchestration logic into `validation_steps`.** Validation steps describe observable user-facing checks ("server health endpoint returns 200", "memory query for project A returns no project B items"). They are NOT instructions for how the agent should implement the work.
5. **Letting the test manifest drift from the YAML.** When the source goal lists product states (e.g. 90 of them), the RED phase must enumerate tests that cover all of them. Generate the manifest as an explicit ANALYSIS task whose output gates the RED phase.
6. **Claiming Firecrawl/opensrc validated something they didn't.** See "Firecrawl validation flow" and "opensrc validation flow" above. Firecrawl can exit 0 while printing a setup prompt; treat that as failure. `opensrc` fetched at `main` may diverge from the pinned tarball version — cross-check `package.json` before adopting an API.
7. **Using `firecrawl map` without `--limit 5000`.** Hard requirement. Lower limits silently truncate the URL surface and break `context_urls` validation. The `map_command` recorded in `validation_evidence` must contain the literal `--limit 5000`.
8. **Letting GREEN tasks edit production code before RED is committed.** Encode a `hard_gate` field on the RED phase block with explicit text refusing GREEN edits, and make every GREEN task depend directly on the relevant RED task ids. The `agent_runtime_protocol` section should reiterate that `dependencies` is the only graph edge; reverse blockers are inferred.
9. **Naming the YAML after a session artifact.** `<project>-<intent>-tdd-tasks.yaml` is correct — it's the project name, not the session number. `task-list-2026-05-06.yaml` or `session-output.yaml` is wrong.
10. **Citing repo URLs instead of source paths under `opensrc.fetched`.** A citation is `<repo>/<file>:<line>`, not `https://github.com/<org>/<repo>`. URLs go in `firecrawl.evidence[]`; source paths go in `opensrc.fetched[].key_paths[]`.
11. **Treating the YAML as optional once the Markdown saved.** It is not. Skill version `1.1.0`+ requires both artifacts. A run that produces only the Markdown is incomplete and must be flagged in the report.

---

## Coding Agent Execution Contract (MANDATORY top-level block)

Skill version `1.6.1`+ requires every generated YAML to carry a `coding_agent_execution_contract` top-level block. The block pins the implementation pathway: every code/test/config/doc change a downstream agent makes while executing this plan must originate from a `claude` CLI invocation that carries the full required flag set.

The flag inventory below is the authoritative set, cross-checked against the official Claude Code CLI reference at https://code.claude.com/docs/en/cli-reference (mapped via `firecrawl map --limit 5000 https://code.claude.com/docs`, scraped via `firecrawl scrape --format markdown --json https://code.claude.com/docs/en/cli-reference`). Note: `--print` is the long form of the prompt-mode flag (short `-p`) and is a **boolean** — the prompt itself is the `claude` positional argument, not the value of `--print`. `--strict-mcp-config` is also a **boolean** that locks MCP loading to whatever `--mcp-config <file>` points at, so both flags are required when fully sandboxing MCP.

### Required shape

```yaml
coding_agent_execution_contract:
  executor: "claude"
  rule: >
    All implementation work that satisfies this goal MUST be performed by invoking the
    `claude` CLI (Claude Code) with the full required flag set documented below. The
    Hermes Agent instructions for this goal are passed verbatim as the `claude`
    positional prompt argument (quoted), with `--print` enabling non-interactive SDK
    mode; every other flag is mandatory and must be populated with a concrete, validated
    value before launch. Do not substitute, omit, or rename any flag, and do not
    implement requirements through any other mechanism.
  required_flags:
    - { name: "--print",                              placeholder: "<no-arg>" }
    - { name: "--add-dir",                            placeholder: "<list-of-directories>" }
    - { name: "--agent",                              placeholder: "<custom-subagent>" }
    - { name: "--allow-dangerously-skip-permissions", placeholder: "<no-arg>" }
    - { name: "--dangerously-skip-permissions",       placeholder: "<no-arg>" }
    - { name: "--debug-file",                         placeholder: "<path>" }
    - { name: "--effort",                             placeholder: "max" }
    - { name: "--include-hook-events",                placeholder: "<no-arg>" }
    - { name: "--output-format",                      placeholder: "stream-json" }
    - { name: "--include-partial-messages",           placeholder: "<no-arg>" }
    - { name: "--input-format",                       placeholder: "stream-json" }
    - { name: "--json-schema",                        placeholder: "<json-schema>" }
    - { name: "--mcp-config",                         placeholder: "<mcp-json-file>" }
    - { name: "--settings",                           placeholder: "<settings-json-file>" }
    - { name: "--strict-mcp-config",                  placeholder: "<no-arg>" }
    - { name: "--system-prompt-file",                 placeholder: "<file>" }
    - { name: "--tools",                              placeholder: "<comma-separated-tools>" }
    - { name: "--verbose",                            placeholder: "<no-arg>" }
    - { name: "--worktree",                           placeholder: "<worktree-name>" }
  canonical_invocation: >
    claude --print
    --add-dir <list-of-directories>
    --agent <custom-subagent>
    --allow-dangerously-skip-permissions
    --dangerously-skip-permissions
    --debug-file <path>
    --effort max
    --include-hook-events
    --output-format stream-json
    --include-partial-messages
    --input-format stream-json
    --json-schema <json-schema>
    --mcp-config <mcp-json-file>
    --settings <settings-json-file>
    --strict-mcp-config
    --system-prompt-file <file>
    --tools <comma-separated-tools>
    --verbose
    --worktree <worktree-name>
    "<instructions-from-hermes-agent>"
  worktree_directory:
    flag: "--worktree"
    short_flag: "-w"
    root: "<repo_root>/.claude/worktrees"
    directory_template: "<repo_root>/.claude/worktrees/<worktree-name>"
    resolution_rule: "Resolve the --worktree/-w name under the active repository root recorded in validation_evidence.repository_context; if Hermes is running from .worktrees/hermes-*, keep the Claude worktree inside that current Hermes worktree."
  forbidden_alternatives:
    - "Implementing changes through any tool other than `claude` (no inline shell scripts, no other CLIs, no editor sessions, no manual file edits)."
    - "Omitting, renaming, aliasing, or substituting any flag in the required set."
    - "Paraphrasing the flag set — the exact spelling above is the contract."
```

### Validator enforcement

`scripts/validate_task_list_yaml.py` enforces all of:

- `executor` must equal `"claude"`.
- `rule` must be a non-empty string.
- `required_flags` must contain an entry whose `name` is each of the 19 flags listed above; every entry must carry a non-empty `placeholder` string (use `"<no-arg>"` for boolean flags such as `--print`, `--strict-mcp-config`, `--include-hook-events`, `--include-partial-messages`, `--allow-dangerously-skip-permissions`, `--dangerously-skip-permissions`, and `--verbose`).
- `canonical_invocation` must be non-empty, must start with `claude `, must mention every flag in the required set as a literal substring, and must include the quoted positional prompt placeholder `"<instructions-from-hermes-agent>"` after the flags.
- `forbidden_alternatives` must be a non-empty list.
- **`worktree_directory` block is REQUIRED** (the validator dereferences `contract.get("worktree_directory")` into `_as_dict(...)` and treats `None` as a failure: `expected mapping, got NoneType`). When present, it must satisfy: `flag == "--worktree"`, `short_flag == "-w"`, non-empty string `root` / `directory_template` / `resolution_rule`, AND `directory_template` must contain the literal substring `.claude/worktrees/<worktree-name>`. Canonical shape:

  ```yaml
  worktree_directory:
    flag: "--worktree"
    short_flag: "-w"
    root: ".claude/worktrees"
    directory_template: ".claude/worktrees/<worktree-name>"
    resolution_rule: >
      Resolve <worktree-name> against metadata.plan_id (e.g. 'flora-skill-creation') so each
      goal run lands in its own worktree at .claude/worktrees/<plan-id>/, isolated from siblings.
  ```

Run the validator immediately after writing the YAML; missing or malformed contract entries fail the file at generation time, not at agent runtime.

### `validation_reconciliation` quirks the validator enforces (and the docs don't always make obvious)

- `final_state` must be one of `all-claims-reconciled`, `some-claims-downgraded`, `some-claims-escalated-to-execution-time`. Any other literal fails.
- **`resolutions` must `==`-equal `conflicts` literally** — not "preserve ordering" as a softer word might suggest. The validator does a Python `!=` comparison: `if buckets["resolutions"] != buckets["conflicts"]: problems.append("resolutions: must preserve conflicts ordering")`. That means each `resolutions[i]` dict must have the exact same key set AND same values as `conflicts[i]`. Building `resolutions[i]` with a different shape (e.g. `{check_id, action, applied_to}`) fails. The cleanest pattern is `data["validation_reconciliation"]["resolutions"] = [dict(c) for c in conflicts]`, then add any semantic extras (`action`, `applied_to`) to BOTH lists symmetrically — never to only one side.
- Each entry (in either bucket) must carry the full conflict-field set: `check_id`, `evidence_target`, `original_claim`, `contrarian_observation`, `severity`, `resolution`. Missing any one fails with `validation_reconciliation.<bucket>[i]: missing [...]`.
Run the validator immediately after writing the YAML; missing or malformed contract entries fail the file at generation time, not at agent runtime.

---

## Output filename convention

Use a stable, project-shaped filename: `<project>-<intent>-tdd-tasks.yaml` (e.g. `terminite-real-implementation-tdd-tasks.yaml`). Save next to the source goal Markdown file so future sessions can find it without `grep`. Do NOT add numeric suffixes unless a collision actually occurs.
