---
name: goal-prompt-generator
description: >
  Generate isolated optimized Markdown goal prompts plus a paired ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR TDD task list YAML that any coding agent can dynamically update through its building process. Use when a user asks to enhance, structure, validate, or save a goal prompt without executing it. Do NOT use as an automatic `/goal` preflight, slash-command interceptor, goal-loop hook, or to execute the generated goal or its task list; this skill only produces and validates the standalone prompt file and its companion task list YAML.
version: 1.3.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [goal, prompt-optimization, isolated-generation, tdd]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, test-driven-development]
---

# Goal Prompt Generator

## Overview

`goal-prompt-generator` converts one raw user request into two paired artifacts plus one printed handoff line:

1. one isolated, optimized Markdown goal prompt file (the contract),
2. one ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR TDD task list YAML file (the runtime state any coding agent dynamically updates through its building process), and
3. one printed `/goal ...` handoff prompt that names both generated files and describes the deterministic work needed to execute them.

The generator preserves the user's original intent, adds deterministic metadata, detects the domain, resolves ambiguity with explicit assumptions, injects autonomy, software-development constraints, software-specific final-diff cleanup requirements, and software engineering core principles/rubric when required, validates the Markdown contract, derives the companion task list YAML from the validated spec, validates the YAML structurally, and validates the YAML's research/source claims using Firecrawl `map --limit 5000` plus the rest of the Firecrawl toolset on each official documentation source for every technology in the spec, and using `opensrc` on every technology with an open-source repository.

This skill is **not** a `/goal` command hook. It must not be wired into Hermes Agent's built-in `/goal` command, persistent goal loop, gateway command routing, or TUI command dispatch. The generator runs only when explicitly invoked as a skill, script, or standalone CLI.

## When to Use

**Trigger conditions** — load this skill when:
- The user asks to generate, enhance, optimize, refine, validate, or save a standalone goal prompt.
- The user provides rough goal text and wants a structured Markdown prompt file for later use.
- The user mentions `goal-prompt-generator`, isolated goal prompt generation, optimized goal files, or source prompt hashes.
- An existing generated goal Markdown file must be validated or reused without executing the underlying goal.

**Anti-triggers** — do NOT use this skill when:
- The user wants the generated goal executed immediately.
- The user invokes Hermes Agent's built-in `/goal` command directly and expects normal `/goal` behavior.
- The request is to intercept, reroute, or automatically preprocess `/goal` commands.
- The task is general planning that does not require a saved Markdown goal prompt file.

## Non-Execution Rule

Never execute the task described by the input prompt while using this skill. Only perform these operations:

1. Enhance and structure the prompt.
2. Detect the domain.
3. Inject required constraints.
4. Generate metadata.
5. Format Markdown.
6. Validate generated Markdown.
7. Choose a safe filename.
8. Save the Markdown file.
9. Derive the companion ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR TDD task list YAML from the validated spec.
10. Run the structural validator on the YAML.
11. Run Firecrawl `map --limit 5000` on the official documentation source of every technology referenced in the spec, then use the rest of the Firecrawl toolset (`scrape`, `crawl`, `search`, `extract`) on the mapped URLs to validate the YAML's `context_urls`, `validation_evidence`, and per-task contracts.
12. For every technology in the spec that has an open-source repository, run the `opensrc` CLI to fetch the repo and cross-check the YAML's API/version/path claims against actual source code.
13. Save the YAML file next to the Markdown file.
14. Report both paths and both validation results.
15. Print the final handoff `/goal` prompt that names both generated files and the deterministic work required to execute them, in the exact format defined under `## Mandatory Final Step: Print Handoff /goal Prompt`.

Step 11 and step 12 must be probed for readiness before claiming success. If Firecrawl is unauthenticated or `opensrc` is unavailable, do not claim the YAML was tool-validated; record the requirement as an execution-time validation requirement and label any fallback discovery honestly. See `references/research-tool-readiness.md`.

## Isolation Boundary

The generator is intentionally isolated from Hermes Agent's `/goal` workflow.

- Do not modify `cli.py`, `gateway/run.py`, `tui_gateway/server.py`, `hermes_cli/goals.py`, or equivalent command handlers to call this generator automatically.
- Do not make raw `/goal` text run through this skill by default.
- Do not add fail-closed `/goal` routing, queue interception, or goal-state metadata writes for this skill.
- If a user wants to use the generated prompt with `/goal`, they must explicitly pass the saved Markdown file or paste its contents themselves.

For the full isolation contract, read `references/isolation-contract.md`.

## Standalone Helper

Use the helper script for explicit generation:

```bash
python ~/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py \
  --json "Build a FastAPI API with tests"
```

The script writes the optimized Markdown file and paired TDD task list YAML to the current working directory by default, then prints the generated paths, status, title, source hash, validation status, and final `/goal` handoff prompt.

**The helper is a generator, not an in-place validator.** Use `--input-file <path-to-file>.md` only when you explicitly want the helper to reuse an existing valid generated Markdown file or regenerate a new optimized file from an invalid/incomplete file's contents. Positional arguments are always treated as raw prompt text, never as filesystem paths. To validate an existing generated file in place without creating or reusing output files, do NOT pipe it through the helper — import the validator directly:

```bash
python3 -c "
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.home() / '.hermes/skills/software-development/goal-prompt-generator/src'))
from goal_prompt_generator.validation import validate_optimized_markdown
text = pathlib.Path('<path-to-file>.md').read_text()
r = validate_optimized_markdown(text)
print('valid:', r.valid, 'reasons:', r.reasons)
"
```

See `references/revalidating-existing-files.md` for the full recipe and the list of substring-matched boilerplate paragraphs that must NOT be soft-wrapped across newlines. See `references/research-tool-readiness.md` for handling requested Firecrawl/source-validation requirements without falsely claiming unavailable tooling was used. See `references/runtime-server-goal-edits.md` for adding concrete runtime/server contracts such as Mastra on Bun with Hono to an existing generated goal prompt. See `references/real-implementation-goal-prompts.md` when the user needs a generated goal that turns scaffold/template/descriptor-only work into real source-level implementation with exhaustive TDD gates. See `references/paradox-resolving-goal-prompts.md` when the user's request contains two apparently-contradictory constraints (e.g. "ship X from the start" + "X stays gitignored") that must both hold; the reference covers the deterministic-regeneration-from-in-tree-templates pattern, the Markdown additions, and the YAML `agent_runtime_protocol.paradox_invariant_check` protocol.

See `references/coding-agent-task-list-yaml.md` for the mandatory final step: turning the validated goal prompt spec into a single coding-agent-updatable YAML task list (ANALYSIS / BOOTSTRAP / RED / GREEN / REFACTOR shape, with per-task dependencies, blocking_tasks, validation_steps, prerequisites, ci_commands, styleguide_rules, guardrails, learnings, gotchas, context_files, context_urls, principle_ids, and status). That reference covers the schema, shared-rule-block pattern, the Firecrawl `map --limit 5000` + Firecrawl-toolset URL-validation flow, the `opensrc` source-validation flow, validation honesty, and the structural validator script (`scripts/validate_task_list_yaml.py`).

See `references/firecrawl-cli-1-16-quirks.md` for the concrete CLI quirks (map vs scrape JSON shape, `--format` singular, background-shell auth-loss, leaf-root detection, end-to-end working pattern) observed during real generator runs.

## Required Metadata Contract

Every optimized Markdown file must begin with this frontmatter shape:

```yaml
---
generated_by: goal-prompt-generator
goal_prompt_generator_version: "1.3.0"
optimized_for: hermes-agent-goal
optimization_status: optimized
source_prompt_hash: "stable-sha256-hash-of-original-prompt"
generated_at: "ISO-8601 timestamp"
domain: "detected-domain"
domain_confidence: "high-or-moderate-or-low"
---
```

A prompt counts as already generated by this skill only when all of these are true:

- Metadata exists.
- `generated_by` equals `goal-prompt-generator`.
- `optimized_for` equals `hermes-agent-goal`.
- `optimization_status` equals `optimized`.
- `source_prompt_hash` is present and non-empty.
- All required Markdown sections are present.
- The autonomy requirement is present.
- The non-execution guardrail is present.
- The isolated generation boundary is present.
- Acceptance criteria and validation requirements are present.
- Software-development constraints are present when the domain is software development or uncertain.
- The software-development cleanup requirement is present when the domain is software development.
- The software engineering core principles and condensed engineering rubric are present when the domain is software development.
- The Coding Agent Execution Contract section is present and lists every required `claude` CLI flag verbatim.

If any check fails, treat the input as not valid generated output and regenerate it only when the user explicitly asks this skill or helper to do so.

## Required Markdown Sections

Generated files must contain these sections in order:

1. `# Generated Goal Title`
2. `## Goal`
3. `## Original Intent`
4. `## Domain`
5. `## Assumptions`
6. `## Non-Execution Guardrail`
7. `## Isolated Generation Boundary`
8. `## Autonomous Execution Requirement`
9. `## Research and Source Validation Requirements`
10. `## Scope`
11. `## Execution Plan`
12. `### Phase 0: BOOTSTRAP`
13. `### Phase 1: RED`
14. `### Phase 2: GREEN`
15. `### Phase 3: REFACTOR`
16. `## Software Development Constraints` when required
17. `## Software Engineering Core Principles` when the domain is software development
18. `## Acceptance Criteria`
19. `## Validation Commands`
20. `## Completion Definition`
21. `## Failure Conditions`
22. `## Final Output Requirements`
23. `## Coding Agent Execution Contract`

## Domain Detection

Classify as `software-development` if the prompt involves writing, modifying, reviewing, testing, deploying, refactoring, or debugging code; building apps, plugins, APIs, CLIs, SDKs, packages, automation, infrastructure, CI/CD, model integrations, or developer tools; inspecting repositories, commits, PRs, issues, source files, package manifests, build tools, deployment configs, or runtime behavior; or using implementation technologies such as Git, GitHub, Docker, Railway, Vercel, AWS, Bun, Node, TypeScript, Swift, Python, Mastra, Next.js, React, Effect, OpenRouter, fal.ai, Stripe, Better Auth, or comparable systems.

If classification is uncertain, choose the stricter path and include software-development constraints.

## Software-Development Constraints

When the detected domain is software development, or when domain classification is uncertain, include these constraints exactly enough to be enforceable:

```text
Ensure you always follow these rules:
- 200 LOC maximum per file.
- 30 LOC maximum per coding-language construct type, including functions, classes, interfaces, protocols, methods, components, hooks, services, schemas, tests, and comparable constructs.
- Maximum nesting depth of 3.
- For tests, nesting depth is measured relative to the test declaration.
- Local CI/CD must be configured and runnable before tests are written.
- Tests must be written before implementation code.
- Tests must focus on user-facing behavior, contracts, APIs, interfaces, workflows, and observable outcomes.
- Never test implementation details.
- Never write tests merely for the sake of increasing coverage.
- No TODOs, mocks, stubs, placeholders, fake behavior, fake services, simulated functionality, or incomplete implementations.
- Use only real tests, real behavior, real services, real functionality, real data flows, and real verification paths.
- Always operate with a BOOTSTRAP / RED / GREEN / REFACTOR TDD-first mindset.
```

## Software-Development Cleanup Requirement

When the detected domain is `software-development`, append this paragraph under `## Software Development Constraints` after the existing rules. Do not add it to clear non-software prompts, and do not use it to execute the generated goal during optimization.

```text
At the end of the goal execution, perform a ruthless cleanup pass over the final diff. Remove every code change, file change, configuration change, dependency change, test change, documentation change, or generated artifact that is unrelated, incidental, speculative, exploratory, redundant, or extraneous to the successful completion of the approved goal. The final submitted change set must contain only the minimum necessary changes required to satisfy the goal and its validation criteria. If the goal is executed within a brownfield codebase, preserve the repository’s existing intent, architecture, conventions, abstractions, naming patterns, style, behavior, public contracts, tests, workflows, and integration assumptions unless the approved goal explicitly requires changing them. Before marking the goal complete, verify that the final change set does not introduce regressions, does not conflict with the surrounding repository context, does not degrade existing behavior, and does not leave behind temporary implementation scaffolding, abandoned experiments, dead code, unused dependencies, unused exports, debug logs, placeholder logic, TODOs, mocks, stubs, or broad refactors that are not required by the goal. If a change was made during execution but is not necessary for the final validated solution, revert it before completion.
```

## Software Engineering Core Principles

When the detected domain is `software-development`, append this section after the software-development cleanup requirement. Do not add it to clear non-software prompts, and do not use it to execute the generated goal during optimization.

### Core Principles

1. **Treat programs as descriptions before execution** — Separate what work should happen from when and how it is executed. Design workflows, jobs, request handlers, and automation steps as explicit execution plans run through one well-defined execution boundary that owns cancellation, retries, logging, cleanup, dependency wiring, and failure reporting.
2. **Make expected failure part of the domain model** — Distinguish expected errors from unexpected defects. Model recoverable failures explicitly: validation failure, auth failure, payment declined, rate limited, and missing resource.
3. **Separate recoverable failures from defects** — Defects should terminate the operation and flow into diagnostics, not business recovery logic. Classify failures as user-correctable, retryable, compensatable, or defect; defects should fail fast with rich diagnostic context.
4. **Preserve failure causes, not just messages** — Errors should carry structured cause data: category, operation, retryability, input metadata, dependency name, correlation ID, and causal chain. Never reduce failures to `Error("something went wrong")`.
5. **Design every resource with a lifecycle** — Every resource needs an owner, scope, acquisition path, cleanup path, and failure behavior. Apply this to DB pools, browser sessions, temp files, locks, subprocesses, feature flags, queues, websocket connections, and test fixtures.
6. **Make cancellation and interruption first-class** — Long-running work must be cancellable. Request handlers, background jobs, CLI commands, AI agent loops, uploads, streams, and test runs should respond to cancellation and release resources deterministically.
7. **Use structured concurrency instead of ad hoc async work** — Parent operations should own child operations. When the parent is canceled, times out, or fails, children should be canceled or joined according to an explicit policy. Avoid untracked background tasks.
8. **Push dependencies to the boundary** — Business logic should depend on interfaces and capabilities, not concrete clients. Wire real implementations at the app boundary and test implementations at the test boundary.
9. **Keep service interfaces clean; move construction complexity elsewhere** — Service APIs should express business capabilities, not bootstrapping details. Assemble configuration, credentials, telemetry clients, connection pools, and dependency graphs outside the core interface.
10. **Validate and transform data at boundaries** — Parse external data once at the boundary, then operate internally on validated domain data. Apply this to HTTP requests, environment variables, webhooks, database rows, queue messages, LLM outputs, and config files.
11. **Treat configuration as typed, validated, and redacted** — Configuration should be parsed, validated, documented, and redacted before use. Missing or malformed config should fail startup, not appear as runtime mystery behavior.
12. **Build timeout and retry policy into external calls** — Every external call should have an explicit timeout, retry policy, backoff policy, idempotency strategy, and failure classification. No network call should wait indefinitely.
13. **Optimize based on measurement, not intuition** — Instrument before optimizing. Use latency histograms, error rates, queue depth, memory, CPU, flamegraphs, and business-level success metrics to find real bottlenecks.
14. **Make observability part of execution, not an afterthought** — Every meaningful operation should emit structured telemetry: request ID, user or tenant when safe, operation name, duration, outcome, failure cause, dependency calls, retry count, and cancellation reason.
15. **Cache deliberately, with invalidation semantics** — Cache expensive or remote computations only when you can define the key, freshness rule, invalidation rule, error behavior, and concurrency behavior.
16. **Serialize shared-state updates when consistency matters** — Shared mutable state should have a coordination mechanism: lock, transaction, queue, actor, compare-and-swap, database constraint, or single-writer policy.
17. **Compose small units into larger workflows** — Implement small, testable, composable units with explicit inputs, outputs, failures, dependencies, and lifecycle. Compose them into workflows rather than creating large imperative procedures.
18. **Keep provider-specific details behind stable application contracts** — Isolate vendor APIs behind internal contracts. Apply this to LLMs, payments, email, auth, storage, observability, search, browser automation, and deployment providers.

### Condensed Engineering Rubric

Use this as a checklist:

1. Can every operation state its success type, expected failures, dependencies, and side effects?
2. Are recoverable errors modeled separately from defects?
3. Are failure causes preserved with enough structure for diagnosis?
4. Does every resource have deterministic cleanup?
5. Are all long-running operations cancellable?
6. Are concurrent tasks owned by a parent scope or durable supervisor?
7. Are dependencies injected at the boundary rather than imported everywhere?
8. Is all external data validated and transformed before internal use?
9. Is configuration validated, redacted, and failed fast?
10. Does every external call have timeout, retry, and idempotency policy?
11. Is telemetry emitted as structured logs, metrics, and traces?
12. Are caches explicit about keys, TTL, invalidation, and consistency?
13. Are shared-state updates coordinated?
14. Are provider integrations hidden behind stable contracts?
15. Are optimizations driven by measurements?

### Bottom Line

Engineer software as explicit, typed, observable, cancellable, resource-safe workflows with clear failure semantics and boundary-driven dependency management.

## Coding Agent Execution Contract

Always include this section as the final `##`-level section of the generated Markdown, regardless of domain. The section pins the implementation pathway: every code/test/config/doc change a downstream agent makes while executing this goal must originate from a `claude` CLI invocation that carries the full required flag set. The literal substring `CLAUDE_CLI_EXECUTION_CONTRACT` from `goal_prompt_generator.constants` (single physical line, no soft wrap) and every flag listed below MUST appear verbatim in the rendered Markdown:

```text
All implementation work that satisfies this goal MUST be performed by invoking the `claude` CLI (Claude Code) with the full required flag set: `--p <instructions-from-hermes-agent>`, `--add-dir <list-of-directories>`, `--agent <custom-subagent>`, `--allow-dangerously-skip-permissions`, `--dangerously-skip-permissions`, `--debug-file <path>`, `--effort max`, `--include-hook-events`, `--output-format stream-json`, `--include-partial-messages`, `--input-format stream-json`, `--json-schema <json-schema>`, `--settings <settings-json-file>`, `--strict-mcp-config <mcp-json-file>`, `--system-prompt-file <file>`, `--tools <comma-separated-tools>`, `--verbose`, and `--worktree <worktree-name>`. The Hermes Agent instructions for this goal are passed verbatim as the `--p` payload; every other flag is mandatory and must be populated with a concrete, validated value before launch. Do not substitute, omit, or rename any flag in this set, and do not implement the requirements through any other mechanism (no inline shell scripts, no other CLIs, no editor sessions, no manual file edits) — every change to the repository must originate from a `claude` invocation that carries the full flag set above.
```

The companion task list YAML MUST also carry a top-level `coding_agent_execution_contract` block with `executor: claude`, every required flag enumerated under `required_flags[*]` with a non-empty `placeholder` (use `"<no-arg>"` for boolean flags), a `canonical_invocation` string starting with `claude ` and mentioning every required flag, and a non-empty `forbidden_alternatives` list. `scripts/validate_task_list_yaml.py` enforces all of that. See `references/coding-agent-task-list-yaml.md` for the canonical YAML shape.

## Autonomy Requirement

Always include this requirement, regardless of domain:

```text
Ensure that you can operate everything autonomously without human intervention or a human in the loop, except where credentials, external approvals, legal authorization, payment authorization, or explicit safety constraints make human action mandatory. When human action is truly unavoidable, clearly document the blocker, the required human action, and the exact point at which autonomous execution can resume.
```

## Output File Rules

- Save the file in the same directory where the skill or helper was explicitly executed.
- Use lowercase, hyphen-separated words.
- Use `.md` extension.
- Remove unsafe filesystem characters.
- Keep names concise but descriptive.
- Avoid generic names such as `prompt.md`, `enhanced.md`, and `output.md`.
- Append numeric suffixes such as `-2`, `-3`, or `-4` on collision.
- Reuse a valid generated file when the input points to one.
- Regenerate invalid or incomplete generated files into a new safe filename only during explicit generator use.

## Coding Agent Task List YAML

After the optimized Markdown file passes validation, the generator MUST derive a paired ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR TDD task list YAML and validate it. This is not optional and is not gated on a separate user request — completing the skill means producing both files.

The YAML is the runtime state any coding agent dynamically updates through its building process; the Markdown is the immutable contract.

### Required top-level YAML shape

```yaml
metadata:                # plan id, version, source goal markdown path + hash, hard invariants
validation_evidence:     # PROOF that any tool you claim was used was authenticated/cached
                         # firecrawl: cli_version, auth, url_maps_root, required_maps_present
                         #   (each entry: file path + url_count + map_command + map_limit: 5000)
                         # opensrc: cli_version, cache_root, fetched repos with key_paths
                         # authoritative_reference_urls: grouped by technology
styleguide_rules:        # S1..Sn keyed rules, referenced by id from each task
guardrails:              # G1..Gn keyed rules, referenced by id from each task
ci_commands:             # CC_* keyed shell commands, referenced by id from each task
principles:              # P1..P18 — one entry per software engineering core principle in scope
phases:                  # ordered: ANALYSIS, BOOTSTRAP, RED, GREEN, REFACTOR; each has tasks: []
agent_runtime_protocol:  # status_transitions, mutable_fields, immutable_fields, resume_protocol
```

### Required per-task fields (all MUST be present on every task)

```yaml
- id: <UNIQUE_TASK_ID>           # e.g. A01, B03, R12, G07, X02
  title: "<one-line human-readable>"
  status: pending                # pending | in_progress | completed | blocked | cancelled
  prerequisites: [...]           # gate descriptions or task ids that must clear before start
  dependencies: [...]            # task ids that must complete first
  blocking_tasks: [...]          # task ids this one blocks
  validation_steps: [...]        # ordered, observable, user-facing — never implementation details
  ci_commands: [CC_*, ...]       # references into top-level ci_commands
  styleguide_rules: [S*, ...]    # references into top-level styleguide_rules
  guardrails: [G*, ...]          # references into top-level guardrails
  learnings: []                  # MUTABLE — agent appends as it discovers facts
  gotchas: []                    # MUTABLE — agent appends pitfalls and rewind notes
  context_files: [...]           # files the agent should read for context
  context_urls: [...]            # authoritative documentation URLs (sourced from Firecrawl maps)
  principle_ids: [P*, ...]       # which engineering principles the task validates
```

`status`, `learnings`, and `gotchas` are mutable; everything else is contract.

### Phase order (strict)

`ANALYSIS` → `BOOTSTRAP` → `RED` → `GREEN` → `REFACTOR`. RED carries a `hard_gate` string forbidding production-code edits before the kickoff RED task plus all RED tests are committed and observed failing for the right reason.

### Firecrawl `map --limit 5000` validation flow

For every technology referenced in the validated spec (frameworks, runtimes, providers, CLIs, SDKs, vendor APIs):

1. Identify the official documentation root URL.
2. Run `firecrawl --status` to confirm authentication. Treat a `0`-exit auth/setup banner as **not usable** and record the requirement as execution-time validation only.
3. If authenticated, run `firecrawl map --limit 5000 <official-docs-root>` and persist the JSON output to `<execution-dir>/research/url-maps/<tech>.json`.
4. Read each map file's `data.links` length and write it into `validation_evidence.firecrawl.required_maps_present[<tech>].url_count` along with the `file`, `map_command`, and `map_limit: 5000`.
5. Use the rest of the Firecrawl toolset (`scrape`, `crawl`, `search`, `extract`) on URLs surfaced by those maps to validate every `context_urls` entry the YAML emits and every `validation_evidence.authoritative_reference_urls` claim. Cite scraped/extracted evidence in `validation_evidence.firecrawl.evidence[]`.
6. Never claim a Firecrawl tool was used when only the cache was inspected; phrase that as "verified the cache covers the required URLs" and add a refresh task to the YAML.

### `opensrc` source-validation flow

For every technology in the spec that has an open-source repository:

1. Run `opensrc --version` (or equivalent) to confirm availability.
2. Run `opensrc path <org>/<repo>` (or `opensrc fetch <org>/<repo>`) to materialize the source.
3. For every API, version, file path, or behavioral claim the YAML makes about that technology, cite the exact `<repo>/<file>:<line>` (or path) under `validation_evidence.opensrc.fetched[<repo>].key_paths[]`.
4. Cross-check the repo's `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` against any version pin the YAML asserts. If `main` diverges from a pinned tarball, record that under `validation_evidence.opensrc.divergences[]` and update the YAML to match the pinned version.
5. If `opensrc` is unavailable, record the requirement as execution-time validation only and label discovery honestly.

### Structural validator (run BEFORE handing the YAML back)

Always run `scripts/validate_task_list_yaml.py <path-to-yaml>`. It enforces:

- every per-task field is present,
- every `ci_commands` / `styleguide_rules` / `guardrails` / `principle_ids` reference resolves to a declared id,
- every `dependencies` / `blocking_tasks` reference resolves to an existing task id,
- every GREEN task has at least one RED task in `dependencies` ∪ `prerequisites`,
- every declared principle id appears in at least one task's `principle_ids`,
- no task in phase N depends on a task in phase N+1 or later,
- the RED phase carries a `hard_gate` field,
- `validation_evidence.firecrawl.required_maps_present[*].url_count` is a positive integer when authenticated; absent or zero when unauthenticated.

### Output filename convention

Use `<project>-<intent>-tdd-tasks.yaml`, saved in the same directory as the goal Markdown file. Do NOT add numeric suffixes unless a real collision occurs. Never use session-shaped names like `task-list-2026-05-06.yaml` or `session-output.yaml`.

## Mandatory Final Step: Print Handoff `/goal` Prompt

After the optimized Markdown file and the companion task list YAML both exist and pass validation, the generator MUST print one final line — the deterministic handoff prompt that any downstream coding agent can paste into Hermes `/goal` to start execution. This step runs after the YAML is validated and is the very last thing the skill emits before reporting completion.

### Required output format

Print exactly one line, in this shape:

```text
/goal <deterministic-work-description-that-references-every-generated-file-by-absolute-path>
```

The bracketed payload MUST:

- describe the deterministic work needed to execute the spec end-to-end,
- name every generated artifact by absolute path — the goal Markdown file AND the companion `<project>-<intent>-tdd-tasks.yaml` file (and any additional spec/TDD YAMLs the run produced),
- instruct the receiving agent to read the goal Markdown as the immutable contract and the task list YAML as the mutable runtime state,
- instruct the receiving agent to walk phases in strict order ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR, honoring the RED `hard_gate`,
- instruct the receiving agent to update only the mutable per-task fields (`status`, `learnings`, `gotchas`) and to leave every other field as contract,
- preserve the autonomy, non-execution-of-other-work, and ruthless-final-diff-cleanup requirements from the goal Markdown.

### Canonical template

```text
/goal Execute the goal contract at <ABS_PATH_TO_GOAL_MD> by walking the paired TDD task list at <ABS_PATH_TO_TASKS_YAML> in strict ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR order. Treat the Markdown file as the immutable contract and the YAML as the runtime state; mutate only `status`, `learnings`, and `gotchas` per task. Honor the RED phase `hard_gate` (no GREEN production-code edits before the R00 kickoff and all RED tests are committed and observed failing for the right reason). Use every `ci_commands`, `styleguide_rules`, `guardrails`, `validation_steps`, `context_files`, `principle_ids`, and `context_urls` reference verbatim. Operate autonomously per the goal's autonomy requirement, do not execute work outside the contract, and finish with the ruthless final-diff cleanup pass defined in the goal Markdown.
```

Substitute the absolute paths and, when more than two artifacts exist (for example multiple companion YAMLs), enumerate them all in the bracketed payload.

### Rules

- Print this line to stdout (or echo it in the chat reply) AFTER the file paths and validation results have already been reported.
- Print exactly one line beginning with `/goal ` — no Markdown code fences, no leading bullet, no trailing commentary on the same line.
- Do NOT execute the printed `/goal` line. Printing it is the entire step. The user or a downstream orchestrator decides when to invoke it.
- Do NOT alter the goal Markdown or the task list YAML to add this handoff line; it is a runtime emission of the skill, not a persisted artifact.

## Validation Checklist

Before considering this skill's output complete:

- [ ] The optimized Markdown file exists in the execution directory.
- [ ] The Markdown file starts with the required metadata block.
- [ ] `source_prompt_hash` is non-empty and stable for the original prompt.
- [ ] All required Markdown sections are present.
- [ ] The non-execution guardrail is present.
- [ ] The isolated generation boundary is present.
- [ ] The autonomy requirement is present.
- [ ] Software-development constraints appear for software or uncertain prompts.
- [ ] The software-development cleanup requirement appears for software-development prompts.
- [ ] The software engineering core principles and rubric appear for software-development prompts.
- [ ] Non-software prompts omit software-development constraints, cleanup language, and software engineering principles when the domain is clear.
- [ ] The Markdown filename is safe, lowercase, hyphen-separated, concise, and collision-resistant.
- [ ] The generated prompt's requested task has not been executed during optimization.
- [ ] Hermes `/goal` has not been invoked, intercepted, or modified by the generation process.
- [ ] Shareable-repo packaging, if updated, contains no automatic `/goal` source-integration patch or handler-routing docs unless explicitly requested.
- [ ] The companion task list YAML file exists next to the Markdown file with the `<project>-<intent>-tdd-tasks.yaml` shape.
- [ ] The YAML contains `metadata`, `validation_evidence`, `styleguide_rules`, `guardrails`, `ci_commands`, `principles`, `phases`, and `agent_runtime_protocol` top-level blocks.
- [ ] The YAML's `phases` are ordered ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR.
- [ ] The RED phase carries a `hard_gate` field forbidding GREEN production edits before R00 and all RED tests are committed.
- [ ] Every per-task field listed in `## Mandatory Final Step` is present on every task.
- [ ] `scripts/validate_task_list_yaml.py` returns OK on the YAML.
- [ ] `validation_evidence.firecrawl` records `cli_version`, `auth`, `url_maps_root`, and `required_maps_present[<tech>].url_count` for every technology in the spec — or honestly records the tool as unavailable.
- [ ] Every `firecrawl map` claim used `--limit 5000` and the limit is recorded.
- [ ] Other Firecrawl tools (`scrape`, `crawl`, `search`, `extract`) were used on URLs surfaced by the maps to validate `context_urls` and `validation_evidence.authoritative_reference_urls`, with cited evidence.
- [ ] `validation_evidence.opensrc` records `cli_version`, `cache_root`, and per-repo `key_paths` for every open-source technology in the spec — or honestly records the tool as unavailable.
- [ ] If a required research/tooling source (Firecrawl, opensrc) was unavailable, the YAML preserves the requirement as an execution-time acceptance condition and labels alternate discovery honestly.
- [ ] After both files exist and pass validation, the skill printed exactly one final handoff line beginning with `/goal ` that names every generated artifact by absolute path and describes the deterministic work required to execute the spec.
- [ ] The handoff `/goal` line was not executed by this skill and was not persisted into either generated artifact.
- [ ] The generated Markdown carries a `## Coding Agent Execution Contract` section that mentions every required `claude` CLI flag (`--p`, `--add-dir`, `--agent`, `--allow-dangerously-skip-permissions`, `--dangerously-skip-permissions`, `--debug-file`, `--effort max`, `--include-hook-events`, `--output-format stream-json`, `--include-partial-messages`, `--input-format stream-json`, `--json-schema`, `--settings`, `--strict-mcp-config`, `--system-prompt-file`, `--tools`, `--verbose`, `--worktree`) verbatim.
- [ ] The companion task list YAML carries a `coding_agent_execution_contract` top-level block whose `executor` is `claude`, whose `required_flags` enumerates each of the 18 required flags with a non-empty `placeholder`, whose `canonical_invocation` starts with `claude ` and contains every required flag, and whose `forbidden_alternatives` is a non-empty list.

## Common Pitfalls

1. **Regenerating when the user asks for a small in-place requirement edit.** If the input is an existing valid generated goal file and the user asks to add, tighten, or adjust one requirement, patch that file in place instead of regenerating a new prompt. Search for duplicated sections such as the top-level goal body and preserved `Original Intent`, apply the same semantic edit to both when present, then run the in-place validator.
2. **Executing the generated goal while optimizing it.** This violates the core guardrail. Only save and validate the prompt.
3. **Treating the generator as `/goal` middleware.** This refactored skill is isolated and must not run automatically inside `/goal`.
4. **Trusting partial metadata.** Missing sections or missing constraints make the file invalid even if frontmatter exists.
5. **Skipping software constraints on uncertain prompts.** Uncertainty must use the stricter software-development path.
6. **Skipping cleanup on software-development prompts.** Classified software-development prompts must include the ruthless final-diff cleanup paragraph, while clear non-software prompts must not be polluted with it.
7. **Skipping software engineering core principles on software-development prompts.** Classified software-development prompts must include the core principles, condensed rubric, and bottom-line workflow summary, while clear non-software prompts must not be polluted with them.
8. **Overwriting unrelated files.** Use collision-resistant filenames and only write generated Markdown/YAML targets.
9. **Letting stale `/goal` preflight requirements leak back in.** Earlier versions of this skill included automatic `/goal` preflight/source-integration behavior, but the current contract is explicit isolated generation only. If updating the skill or shareable repo, remove stale `patches/`, `hermes-agent-source-integration` docs, `hermes-goal-integration` references, goal handler edits, and tests that expect automatic routing unless the user explicitly changes scope again.
10. **Soft-wrapping boilerplate paragraphs when hand-editing.** The validator checks the autonomy / non-execution / isolation / software-constraints / cleanup / software engineering principles text as literal substrings. Keep each boilerplate paragraph on a single physical line; break only with blank-line paragraph separators.
11. **Using `generate_goal_prompt.py` when you only need in-place validation.** The helper is a generator. Use `--input-file` only for explicit reuse/regeneration from an existing Markdown file; positional arguments are raw prompt text. Use the inline `validate_optimized_markdown` import shown in the *Standalone Helper* section when you want validation only.
12. **Claiming required research tooling was used when it was unavailable.** Probe Firecrawl and opensrc readiness before writing evidence phrasing. If a required tool is unavailable during prompt editing, label fallback discovery as preliminary and preserve tool validation as an execution-time acceptance condition.
13. **Using broad `replace_all` anchors while patching generated prompts.** Generic anchors such as closing code fences or `---` separators can match dozens of locations and duplicate an inserted requirement throughout the file. Patch against a unique heading/sentence, then search for the inserted phrase count and remove accidental duplicates before running the validator.
14. **Skipping the YAML final step.** The skill is incomplete until the companion `<project>-<intent>-tdd-tasks.yaml` exists, passes `scripts/validate_task_list_yaml.py`, and has its `validation_evidence` block populated. Producing only the Markdown is a partial run.
15. **Using `firecrawl map` without `--limit 5000` and `--json --pretty`.** Both are required. `--limit 5000` is the user's hard requirement. `--json --pretty` is required because Firecrawl 1.16.0's default `map` output is a plain-text URL list, not JSON.
16. **Claiming Firecrawl tools were used when only `firecrawl --status` succeeded.** `--status` proves auth, not that any map/scrape/extract actually ran. Cite real map files with `data.links` length and real `scrape`/`extract` outputs in `validation_evidence`.
17. **Claiming `opensrc` validated something when only the README was skimmed.** `opensrc` claims must cite specific files and lines when reasonable. For every API/version assertion the YAML makes, record source paths under `validation_evidence.opensrc.fetched[<repo>].key_paths[]`.
18. **Letting GREEN tasks edit production code before the RED kickoff is committed.** Encode a `hard_gate` field on the RED phase block with explicit refusal text and seed an R00 kickoff task whose `blocking_tasks` lists every GREEN task. Reiterate the rule in `agent_runtime_protocol`.
19. **Forgetting the space after `:` in YAML.** Writing `key:"value"` instead of `key: "value"` makes PyYAML's scanner fail two lines later with `could not find expected ':'`. Run the structural validator immediately after writing the file.
20. **Skipping the final handoff `/goal` print.** The skill is incomplete until it prints exactly one line beginning with `/goal ` that names every generated file by absolute path and describes the deterministic work to execute them.
21. **Executing the printed handoff `/goal` line.** Printing it is the entire step. Never run it during this skill, never wire it into Hermes `/goal` automatically, and never persist it into the goal Markdown or the task list YAML.
22. **Running Firecrawl in a background terminal session that loses `FIRECRAWL_API_KEY`.** Some terminal/MCP backgrounding paths spawn the child process without the parent's exported environment. Re-run banner-shaped files and explicitly carry the key into background invocations when needed.
23. **Assuming `firecrawl scrape --format markdown --json` nests output under `data.markdown`.** Firecrawl 1.16.0 returns scrape JSON at the top level: `{"markdown": "...", "metadata": {...}}`. Map output is nested as `{"success": true, "data": {"links": [...]}}`.
24. **Treating an apparently-contradictory user requirement as one to silently relax.** Honor both constraints literally and resolve the paradox via deterministic regeneration from in-tree templates; see `references/paradox-resolving-goal-prompts.md`.
25. **Soft-wrapping the Coding Agent Execution Contract paragraph or omitting any of the 18 required `claude` flags.** The validator (`validate_optimized_markdown`) substring-matches the `CLAUDE_CLI_EXECUTION_CONTRACT` constant and each individual flag (`--p`, `--add-dir`, `--agent`, `--allow-dangerously-skip-permissions`, `--dangerously-skip-permissions`, `--debug-file`, `--effort max`, `--include-hook-events`, `--output-format stream-json`, `--include-partial-messages`, `--input-format stream-json`, `--json-schema`, `--settings`, `--strict-mcp-config`, `--system-prompt-file`, `--tools`, `--verbose`, `--worktree`). Wrapping the paragraph at ~80 cols silently invalidates the file with `claude CLI execution contract missing` or `required claude CLI flag missing: <flag>`. Keep the boilerplate paragraph on a single physical line and reproduce every flag exactly as listed. The companion YAML `coding_agent_execution_contract` block must mirror the same set under `required_flags[*].name`, and the `canonical_invocation` string must contain every flag. Do not substitute, rename, or re-order to make the diff "look cleaner" — the validator will reject it.
