---
name: goal-prompt-generator
description: >
  Generate isolated optimized Markdown goal prompts plus a paired ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR TDD task list YAML that any coding agent can dynamically update through its building process. Use when a user asks to enhance, structure, validate, or save a goal prompt without executing it. Do NOT use as an automatic `/goal` preflight, slash-command interceptor, goal-loop hook, or to execute the generated goal or its task list; this skill only produces and validates the standalone prompt file and its companion task list YAML.
version: 0.1.0
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
3. one printed `/goal ...` handoff prompt — **a paste-target only** — that names both generated files and front-loads the Hermes GoalManager continuation discipline needed to keep `/goal` running autonomously until completion or `max_turns`.

Both output files are written under `~/.hermes/goal-prompts/` by default (created on first use). Override the destination with `--dir <path>` (helper) or `execution_dir=<path>` (Python API). The skill never falls back to the current working directory and never invokes `/goal` itself.

The generator preserves the user's original intent, adds deterministic metadata, detects the domain, resolves ambiguity with explicit assumptions, injects autonomy, a Hermes `/goal` runtime continuation contract, software-development constraints, software-specific final-diff cleanup requirements, and software engineering core principles/rubric when required, validates the Markdown contract, derives the companion task list YAML from the validated spec, validates the YAML structurally, deeply explores the invoking repository/codebase context (the workdir, the git state, manifests, lockfiles, agent-context files like `AGENTS.md`/`CLAUDE.md`, CI config, primary languages, top-level layout, and a curated key-path list seeded into every task's `context_files`), validates the YAML's research/source claims using Firecrawl `map --limit 5000` plus the rest of the Firecrawl toolset on each official documentation source for every technology in the spec, and uses `opensrc` on every technology with an open-source repository.

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

Never execute the task described by the input prompt while using this skill. Never instantiate, dispatch, run, or otherwise call `/goal` or any equivalent goal-runner from inside this skill, the helper script, or any code path that produces the prompt artifacts. Even when the skill prints the handoff `/goal …` line at the end (Mandatory Final Step), that line is a **paste-target only** for the user or a downstream orchestrator — the generator MUST NOT submit it, echo it back through `/goal`, route it through Hermes Agent's command bus, or feed it into any LLM/agent loop. Only perform these operations:

1. Enhance and structure the prompt.
2. Detect the domain.
3. Inject required constraints, including the GoalManager-aware continuation discipline that prevents premature `/goal` completion, user-input pauses, and bad non-final judge signals.
4. Generate metadata.
5. Format Markdown.
6. Validate generated Markdown.
7. Choose a safe filename.
8. Save the Markdown file.
9. Derive the companion ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR TDD task list YAML from the validated spec.
10. Run the structural validator on the YAML.
10.5. Deeply explore the invoking repository/codebase context. Probe the workdir (default: cwd; override with `--workdir <path>` on the helper or `workdir=<path>` on the Python API), capture the git state (head SHA, branch, remote, dirty flag), surface manifests/lockfiles/CI configs/agent-context files (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules`, `.github/copilot-instructions.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`, `DESIGN.md`, `README.md`), compute the primary-language breakdown, emit a curated absolute-path key-path list seeded into every task's `context_files`, and derive the Claude Code `--worktree` / `-w` directory rule as `<repo_root>/.claude/worktrees/<worktree-name>` inside the active Hermes worktree. Persist the snapshot into the goal Markdown's `## Repository Context` section, into the YAML's `validation_evidence.repository_context` block, into `agent_runtime_protocol.claude_worktree_*`, into `coding_agent_execution_contract.worktree_directory`, and into every task's `context_files`. See `references/repository-context-exploration.md`.
11. Run Firecrawl `map --limit 5000` on the official documentation source of every technology referenced in the spec, then use the rest of the Firecrawl toolset (`scrape`, `crawl`, `search`, structured-extraction via `firecrawl agent`) on the mapped URLs to validate the YAML's `context_urls`, `validation_evidence`, and per-task contracts. The Firecrawl 1.16.0 CLI exposes no top-level extract subcommand; route schema-driven extraction through `firecrawl agent --schema-file … --urls …`.
11.5. Run the contrarian re-verification pass on every claim emitted by step 11 and step 12, then write `validation_reconciliation` into the YAML. The pass invokes `ContrarianValidator` (see `references/contrarian-validation.md` and `src/goal_prompt_generator/contrarian_validation.py`) and persists a top-level `validation_reconciliation: {conflicts, resolutions, final_state}` block whose `final_state` is one of `all-claims-reconciled`, `some-claims-downgraded`, or `some-claims-escalated-to-execution-time`.
12. For every technology in the spec that has an open-source repository, run the `opensrc` CLI to fetch the repo and cross-check the YAML's API/version/path claims against actual source code.
13. Save the YAML file next to the Markdown file.
14. Report both paths and both validation results.
15. Print the final handoff `/goal` prompt that names both generated files, front-loads the non-final `GOAL_RUNTIME_STATUS: CONTINUE` response contract, forbids asking the user for input during execution, and describes the deterministic work required to execute them, in the exact format defined under `## Mandatory Final Step: Print Handoff /goal Prompt`.

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
  --workdir /path/to/project \
  --json "Build a FastAPI API with tests"
```

The script writes the optimized Markdown file and paired TDD task list YAML to `~/.hermes/goal-prompts/` by default (the directory is created on first use), then prints the generated paths, status, title, source hash, validation status, and final `/goal` handoff prompt as a paste-target. To override the destination, pass `--dir <path>`. To inspect a specific repository instead of the cwd, pass `--workdir <path>`. The helper never runs `/goal`; printing the handoff line is the entire final step.

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

See `references/revalidating-existing-files.md` for the full recipe and the list of substring-matched boilerplate paragraphs that must NOT be soft-wrapped across newlines. See `references/repository-context-exploration.md` for the deep workdir-introspection contract: what gets captured, how `--workdir` / `workdir=` plumbs through `prepare_goal_prompt`, `build_optimized_markdown`, and `write_task_list`, where the snapshot lands in the Markdown/YAML, and the contrarian-recheck rule for vanished key paths. See `references/research-tool-readiness.md` for handling requested Firecrawl/source-validation requirements without falsely claiming unavailable tooling was used. See `references/runtime-server-goal-edits.md` for adding concrete runtime/server contracts such as Mastra on Bun with Hono to an existing generated goal prompt. See `references/real-implementation-goal-prompts.md` when the user needs a generated goal that turns scaffold/template/descriptor-only work into real source-level implementation with exhaustive TDD gates. See `references/skill-authoring-goal-prompts.md` when the user's prompt asks the generator to produce a goal whose **deliverable is itself a coding-agent-agnostic agentskills.io SKILL.md package** (e.g. `design-with-pencil`, `openhue-room-control`, any "create a skill that wraps tool X with methodology Y"); it covers the front-loaded Firecrawl maps/scrapes + opensrc methodology pull, the file-fed prompt construction, the canonical 35–45-task ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR shape, the required fixtures (`frontmatter-contract.json`, `<tool>-cli-surface.txt`, `<methodology>-references.txt`, `skill-md-section-order.txt`, should-/should-not-trigger lists), and the agent-agnosticity / no-secrets / methodology-every-phase invariants. See `references/cross-platform-port-goals.md` when the user asks to convert / port / rebuild an existing app from one framework or runtime into a native or first-class app in another (web → native iOS/macOS/Android, Electron/Flutter → native, etc.) — it covers the pre-helper bundle-introspection probes (`rg` over minified JS for THREE/R3F/primitive/material/light/camera class names), the file-fed-prompt pattern that fixes `domain: uncertain` misclassification, the ~40-task ANALYSIS/BOOTSTRAP/RED/GREEN/REFACTOR shape with a vision-parity GREEN sweep, and the platform-MCP-preferred CI annotation rule. See `references/paradox-resolving-goal-prompts.md` when the user's request contains two apparently-contradictory constraints (e.g. "ship X from the start" + "X stays gitignored") that must both hold; the reference covers the deterministic-regeneration-from-in-tree-templates pattern, the Markdown additions, and the YAML `agent_runtime_protocol.paradox_invariant_check` protocol.

See `references/coding-agent-task-list-yaml.md` for the mandatory final step: turning the validated goal prompt spec into a single coding-agent-updatable YAML task list (ANALYSIS / BOOTSTRAP / RED / GREEN / REFACTOR shape, with a single per-task `dependencies` graph field plus validation_steps, ci_commands, styleguide_rules, guardrails, learnings, gotchas, context_files, context_urls, principle_ids, and status). That reference covers the schema, shared-rule-block pattern, the Firecrawl `map --limit 5000` + Firecrawl-toolset URL-validation flow, the `opensrc` source-validation flow, validation honesty, and the structural validator script (`scripts/validate_task_list_yaml.py`).

See `references/programmatic-yaml-rebuild.md` for the build-YAML-from-a-Python-dict + bulk-Markdown-augmentation-via-single-`mcp_execute_code`-pass workflow used when the helper baseline is structurally valid but semantically thin (short user prompt, large implied scope, 30–50+ tasks needed) — and for the `mcp_patch` post-write-verifier 1-byte-trailing-newline flake workaround.

See `references/per-provider-parity-goals.md` when the goal is parity-shaped — "make plugin/library X compete with every other plugin/library in the same category Y" (memory providers, model providers, terminal backends, vector stores, gateway adapters, scorers). The reference covers the canonical phase shape (ANALYSIS competitor inventory → BOOTSTRAP parity-matrix harness → RED one-test-per-dimension → GREEN aggregator + observability + telemetry → REFACTOR sync-and-observe-one-real-session), the dimensions to probe, and the latency-contract block that has to land in A05 to make "hot-path zero-blocking-IO" enforceable.

See `scripts/validate_source_claims.py` for a deterministic, dependency-free verifier that pre-flights opensrc repo caches, cited file paths, host reachability (TCP and TLS separately, so selective L7 firewall RST is detectable), Firecrawl usability, and helper presence BEFORE the generator writes any artifact. Use it on every run that names ≥1 opensrc repo and ≥1 cited path; fabrication is the most expensive failure mode for a generated goal.

See `scripts/probe_firecrawl_reachability.py` for the deterministic Firecrawl L7-RST probe that distinguishes the four reachability modes (CLI absent / env-var unparsed / banner-authenticated-but-API-blocked / truly authenticated) and exits 0 only when a real `firecrawl map ... --limit 5000 --json --pretty` returns a populated `data.links` array. `_firecrawl_auth()` in `src/goal_prompt_generator/research.py` should agree with this probe; run the probe before generating a goal prompt YAML to confirm the right `auth:` value will land.

See `references/retarget-existing-goal-runtime.md` when the user asks to update an existing generated goal and paired YAML to make a different machine/environment (for example Daytona) the real source/runtime location without executing the goal.

See `references/third-party-oss-pr-goals.md` when the goal's deliverable is a pull request into a third-party open-source repository (e.g. `warpdotdev/warp`, `mastra-ai/mastra`, `vercel/next.js`) — not the user's own project. The reference covers (a) the pre-helper probes for the upstream PR template / CONTRIBUTING / workflows / real file-size distribution / recent reviewer activity, (b) the `### Project-Specific Overrides (<org>/<repo>)` subsection that must be appended UNDER the canonical Software-Development Constraints block (never replacing it), (c) the scoping nuance — file-size cap follows upstream practice, 30-LOC construct cap and depth-3 nesting cap apply to NEWLY CREATED constructs/blocks only, existing ones are preserved — and the matching `metadata.hard_invariants` literals (`file_loc_policy: follow_<upstream>_practice`, `construct_loc_max_new_only: 30`, `nesting_depth_max_new_only: 3`), (d) the required `validation_reconciliation` conflict entries when generic caps are scoped down (`final_state: some-claims-downgraded`, `resolutions == conflicts`), and (e) the canonical phase shape that ends in `G14` (watch checks → fix → rebase → push → re-watch loop), `G15` (respond to review-bot feedback in-place), and `X03` (final acceptance: every check green + branch fast-forward-only + no unresolved review threads).

See `references/validator-audit-tdd-execution.md` when executing a generated validator-audit task list end-to-end; it covers RED evidence commits, final staged cleanup checks, audit transcript whitespace/CSV normalization, Firecrawl env-reload verification in remote backends, temporary venv handling, post-commit verification, and mutable-runtime-YAML-only updates.

See `references/claude-cli-execution-syntax.md` when executing a generated goal through Claude Code; it records the user-corrected runtime rule to probe the installed `claude` CLI and use the real prompt flag syntax (`--print` long form, `-p` short — the prompt is a positional argument, NOT the value of `--print`) plus `--output-format stream-json` / `--input-format stream-json` for structured IO instead of repeating an invalid invocation.

See `references/executing-generated-tdd-contracts.md` when the user asks to execute an already-generated immutable goal Markdown plus mutable TDD YAML contract. It captures the safe execution pattern from a full ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR run: mutate only `status` / `learnings` / `gotchas`, preserve the RED hard gate, use wrapped stream-json JSONL input for Claude Code, rerun validations independently after delegated execution, keep runtime goal artifacts out of commits when the contract says so, and record live-e2e fail-closed labels as blockers instead of mutating past them.

See `references/opensrc-cache-bust-and-refetch.md` when the user asks to bust, wipe, refresh, or rebuild the entire `opensrc` cache before a generation pass; it covers the save-inventory-first → `opensrc clean` → parallel xargs `-P 6` refetch → OK/FAIL classification pattern, the transient-vs-permanent failure modes (git pack-tmp race vs npm yank), and the rule for staging two parallel jobs (refresh-originals + fetch-new-repos) with separate logs.

See `references/auditing-cli-flag-inventory.md` for the 4-step audit playbook (probe live binary → `firecrawl map --limit 5000 <docs-root>` → `firecrawl scrape --format markdown --json <cli-reference>` → diff against the persisted `CLAUDE_CLI_REQUIRED_FLAGS` tuple) that catches contract-rot like the 1.6.1 fix (invalid `--p`, collapsed `--strict-mcp-config <file>`). Run it proactively before every contract version bump and reactively whenever a user reports `error: unknown option '--X'` from a generated handoff. The reference also enumerates every file that must be touched in a single contract-fix PR (constants → validators → tests → SKILL.md → template → references → CHANGELOG → regenerated example) and the live-binary smoke test that proves the new canonical invocation parses.

See `references/standalone-repo-release-packaging.md` when publishing or syncing the skill implementation to the standalone public repo; it records the clean-temp-clone + explicit `rsync` packaging workflow, coupled version-bump files, v1.7.0 schema/runtime-contract lessons, the source-of-truth-is-local-skill rule, the non-execution-affirmation interjection pattern, the re-squash / re-tag / re-release ordering (delete release → delete remote tag → force-push main → push tag → recreate release), the `research/` exclusion rule, the `_uses_legacy_task_graph()` regression pitfall, and the requirement to verify remote `origin/main` plus GitHub Actions before reporting release completion.

See `references/firecrawl-cli-1-16-quirks.md` for the concrete CLI quirks (map vs scrape JSON shape, `--format` singular, background-shell auth-loss, leaf-root detection, missing `extract`, crawl timeout honesty, handoff drift fixes, and end-to-end working pattern) observed during real generator runs. See `references/dns-blocked-research-tools.md` when provider websites or research tools fail due local DNS/resolver behavior; it contains the non-mutating DNS matrix and validation-honesty wording for Firecrawl/opensrc failures. See `references/remote-backend-helper-unavailable.md` when Hermes terminal execution is in Daytona or another remote backend and the host-side skill helper path shown in the prompt is not mounted into the backend; it documents the fallback workflow using `skill_view()` support-file content, local validators, honest research-tool evidence, and the same final handoff contract.

## Required Metadata Contract

Every optimized Markdown file must begin with this frontmatter shape:

```yaml
---
generated_by: goal-prompt-generator
goal_prompt_generator_version: "0.1.0"
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
9. `## Goal Runtime Continuation Contract`
10. `## Research and Source Validation Requirements`
11. `## Repository Context`
12. `## Scope`
13. `## Execution Plan`
14. `### Phase 0: BOOTSTRAP`
15. `### Phase 1: RED`
16. `### Phase 2: GREEN`
17. `### Phase 3: REFACTOR`
18. `## Software Development Constraints` when required
19. `## Software Engineering Core Principles` when the domain is software development
20. `## Acceptance Criteria`
21. `## Validation Commands`
22. `## Completion Definition`
23. `## Failure Conditions`
24. `## Final Output Requirements`
25. `## Coding Agent Execution Contract`

The Coding Agent Execution Contract section pins the executor. By default the executor is Claude Code (the contract literal `CLAUDE_CLI_EXECUTION_CONTRACT` lists every required `claude` flag), but the installer can target any executor in the catalog by passing `--executor <key>` to the helper, `executor=<key>` to `prepare_goal_prompt(...)`, or setting `GOAL_PROMPT_GENERATOR_EXECUTOR`. The catalog covers 12 popular coding-agent CLIs: `claude`, `codex`, `opencode`, `gemini`, `cursor`, `aider`, `pi`, `qwen`, `goose`, `amp`, `crush`, and `hermes` (Hermes Agent itself running with a configurable model + reasoning effort). Every catalog entry pins the non-interactive flag set every generated goal MUST carry when that executor is chosen, and every executor's worktree directory MUST resolve under the active Hermes worktree's `repo_root` — `<repo_root>/.<executor>/worktrees/<worktree-name>`. The GoalManager continuation contract (autonomy, `GOAL_RUNTIME_STATUS: CONTINUE`/`COMPLETE` markers, no human input on non-final turns) is preserved regardless of which executor is chosen. See `references/executor-fallbacks-and-model-selection.md` for the full catalog, flag sets, worktree contract, and Hermes-as-executor model-selection rule. See `references/tool-fallback-alternatives.md` for valid fallback alternatives to Firecrawl and `opensrc` when those tools are unavailable on the installer's machine.

## Domain Detection

Classify as `software-development` if the prompt involves writing, modifying, reviewing, testing, deploying, refactoring, or debugging code; building apps, plugins, APIs, CLIs, SDKs, packages, automation, infrastructure, CI/CD, model integrations, or developer tools; inspecting repositories, commits, PRs, issues, source files, package manifests, build tools, deployment configs, or runtime behavior; or using implementation technologies such as Git, GitHub, Docker, Railway, Vercel, AWS, Bun, Node, TypeScript, Swift, Python, Mastra, Hermes Agent, Daytona, devcontainers, Codespaces, MCP, Next.js, React, Effect, OpenRouter, fal.ai, Stripe, Better Auth, or comparable systems.

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
All implementation work that satisfies this goal MUST be performed by invoking the `claude` CLI (Claude Code) with the full required flag set: `--print`, `--add-dir <list-of-directories>`, `--agent <custom-subagent>`, `--allow-dangerously-skip-permissions`, `--dangerously-skip-permissions`, `--debug-file <path>`, `--effort max`, `--include-hook-events`, `--output-format stream-json`, `--include-partial-messages`, `--input-format stream-json`, `--json-schema <json-schema>`, `--mcp-config <mcp-json-file>`, `--settings <settings-json-file>`, `--strict-mcp-config`, `--system-prompt-file <file>`, `--tools <comma-separated-tools>`, `--verbose`, and `--worktree <worktree-name>`. The Hermes Agent instructions for this goal are passed verbatim as the `claude` positional prompt argument (quoted), with `--print` enabling non-interactive SDK mode; every other flag is mandatory and must be populated with a concrete, validated value before launch. When populating `--worktree <worktree-name>`, resolve the filesystem directory as `<active-repo-root>/.claude/worktrees/<worktree-name>` inside the current Hermes worktree recorded in Repository Context; do not place Claude worktrees under a parent checkout or outside the active Hermes worktree. Do not substitute, omit, or rename any flag in this set, and do not implement the requirements through any other mechanism (no inline shell scripts, no other CLIs, no editor sessions, no manual file edits) — every change to the repository must originate from a `claude` invocation that carries the full flag set above.
```

The companion task list YAML MUST also carry a top-level `coding_agent_execution_contract` block with `executor: claude`, every required flag enumerated under `required_flags[*]` with a non-empty `placeholder` (use `"<no-arg>"` for boolean flags), a `canonical_invocation` string starting with `claude `, mentioning every required flag, and ending with a quoted positional `"<instructions-from-hermes-agent>"` argument, a `worktree_directory` block that maps `--worktree` / `-w` to `<repo_root>/.claude/worktrees/<worktree-name>` inside the active Hermes worktree, and a non-empty `forbidden_alternatives` list. `scripts/validate_task_list_yaml.py` enforces all of that. See `references/coding-agent-task-list-yaml.md` for the canonical YAML shape.

## Autonomy Requirement

Always include this requirement, regardless of domain:

```text
Ensure that you can operate everything autonomously without human intervention or a human in the loop, except where credentials, external approvals, legal authorization, payment authorization, or explicit safety constraints make human action mandatory. When human action is truly unavoidable, clearly document the blocker, the required human action, and the exact point at which autonomous execution can resume.
```

## Goal Runtime Continuation Contract

Always include this section immediately after `## Autonomous Execution Requirement`, regardless of domain. It exists because Hermes `/goal` judges the latest assistant final response after every turn and will stop when the response looks complete, blocked, or waiting for user input. The generated goal must make non-final responses judge-friendly for continuation. Keep this paragraph as one physical line so validators can substring-match it:

```text
When this contract is executed through Hermes `/goal`, shape every intermediate assistant final response so the GoalManager judge has an unambiguous reason to continue: continue autonomously until all acceptance criteria validate or Hermes goal max_turns pauses the loop; do not ask the user for input, guidance, confirmation, or permission; do not state that the overall goal is complete, blocked, unachievable, waiting for input, or needing human action unless every acceptance criterion and validation requirement is satisfied or a non-bypassable legal, payment, credential, or safety requirement prevents every remaining autonomous path. For every non-final turn, end the response with `GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued` and name the next YAML task id. For the final validated turn only, end with `GOAL_RUNTIME_STATUS: COMPLETE — all acceptance criteria and validations satisfied`. If a task encounters friction, record it in the YAML task's mutable `learnings` or `gotchas`, choose the safest remaining autonomous alternative, and keep working rather than pausing for human input.
```

The companion YAML MUST mirror this under `agent_runtime_protocol.goal_manager_continuation_contract` and every task MUST reference the continuation guardrail. The final handoff `/goal` line MUST front-load the same runtime rule before detailed task-list instructions, because `GoalManager.judge_goal()` truncates the stored goal text before sending it to the auxiliary judge.

## Output File Rules

- Save every generated artifact (the Markdown goal prompt and the paired TDD task list YAML) under `~/.hermes/goal-prompts/`. Create that directory on first use.
- Only override the destination when the caller explicitly passes `--dir <path>` to the helper, or `execution_dir=<path>` to `prepare_goal_prompt`. The skill itself never falls back to the current working directory.
- Use lowercase, hyphen-separated words.
- Use `.md` extension for the goal prompt and `.yaml` for the paired task list.
- Remove unsafe filesystem characters.
- Keep names concise but descriptive.
- Avoid generic names such as `prompt.md`, `enhanced.md`, and `output.md`.
- Append numeric suffixes such as `-2`, `-3`, or `-4` on collision.
- Reuse a valid generated file when the input points to one.
- Regenerate invalid or incomplete generated files into a new safe filename only during explicit generator use.

## Repository Context Exploration

Every generation pass runs against a real codebase: the workdir (default cwd, overridable with `--workdir <path>` on the helper or `workdir=<path>` on `prepare_goal_prompt` / `build_optimized_markdown` / `write_task_list`). Before the goal Markdown is sealed and the YAML is written, the generator deeply explores that workdir and threads the result through both artifacts.

### What gets captured

`goal_prompt_generator.repository.repository_evidence(workdir)` returns:

- `workdir` and `repo_root` (resolved absolute paths; `repo_root` is `git rev-parse --show-toplevel` when available).
- `is_git_repo` plus a `vcs` block with `head_sha`, `branch`, `remote_url`, and `dirty`.
- `manifests` (`pyproject.toml`, `setup.py`, `requirements.txt`, `package.json`, `deno.json`, `bun.lock`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`, `pom.xml`, `build.gradle*`, `Package.swift`, `mix.exs`, `pubspec.yaml`, `Dockerfile`, `compose.yaml`, `Makefile`, `justfile`, `mise.toml`, `.tool-versions`, `Procfile`).
- `lockfiles` (`uv.lock`, `poetry.lock`, `Pipfile.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `bun.lockb`, `Cargo.lock`, `go.sum`, `Gemfile.lock`, `composer.lock`, `mix.lock`, `pubspec.lock`).
- `agent_context_files` and `agent_context_excerpts` (first 800 chars of up to 3 of: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules`, `.github/copilot-instructions.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`, `DESIGN.md`, `README.md`).
- `ci_paths` (`.github/workflows`, `.gitlab-ci.yml`, `.circleci/config.yml`, `Jenkinsfile`, `azure-pipelines.yml`, `.buildkite`, `.travis.yml`).
- `top_level_entries` (up to 40, ignored dirs filtered).
- `primary_languages` (top 5 by file count, capped at 4000 files for huge monorepos).
- `key_paths` (up to 24 absolute paths in priority order: agent-context first, then manifests, lockfiles, CI configs, an existing `.claude/worktrees` directory when present, then canonical source dirs `src/`, `lib/`, `app/`, `internal/`, `cmd/`, `pkg/`, `packages/`, `apps/`, `tests/`).
- `claude_worktree` (Claude Code `--worktree` / `-w` metadata derived from the active repo root: `root: <repo_root>/.claude/worktrees`, `directory_template: <repo_root>/.claude/worktrees/<worktree-name>`, `exists`, `existing_worktrees`, and the rule that this directory stays inside the current Hermes `.worktrees/hermes-*` checkout when Hermes itself is already running from one).

### Where it lands

- The Markdown gets a top-level `## Repository Context` section with the workdir, repo root, git state, Claude Code worktree directory resolution, top-level layout, manifests/lockfiles/CI config/agent-context-file lists, and the curated key paths as backtick-quoted absolute paths.
- The YAML's `validation_evidence.repository_context` carries the full snapshot dict, including `claude_worktree`.
- `metadata.workdir` and `metadata.repo_root` are written so the structural validator can require the block.
- `agent_runtime_protocol.handoff_workdir`, `agent_runtime_protocol.claude_worktree_root`, `agent_runtime_protocol.claude_worktree_directory_template`, and `agent_runtime_protocol.claude_worktree_resolution` are set so any orchestrator that hydrates a fresh terminal session knows where to land and how to fill the required `--worktree` flag.
- `coding_agent_execution_contract.worktree_directory` mirrors the `--worktree` / `-w` directory contract beside the required flag list.
- Every task's `context_files` is seeded with the goal Markdown path, the YAML path, and **every entry in `key_paths`** — so the downstream coding agent reads them before producing a diff.

### Honesty rules

- Do not synthesize key paths that don't exist. The list is built from on-disk presence checks only; small or sparse workdirs produce small `key_paths` lists, and that is correct behavior.
- If `git` is unavailable, the `vcs` block is empty strings; do not fabricate a head SHA or branch.
- The contrarian re-verification pass (`ContrarianValidator.recheck_repository_key_path`) re-checks every promised key path on disk and downgrades any vanished entry to `downgraded_to_attempted` in `validation_reconciliation`. Treat that as a real signal: investigate before assuming the contract is still accurate.
- Subdirectory invocations (e.g. running from `src/api/` inside a monorepo) are valid: `repo_root` stays at the git top while `workdir` records the subdir. Both go into the contract.

See `references/repository-context-exploration.md` for the full reference.

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
agent_runtime_protocol:  # status_transitions, mutable_fields, immutable_fields, resume_protocol, goal_manager_continuation_contract
```

### Required per-task fields (all MUST be present on every task)

```yaml
- id: <UNIQUE_TASK_ID>           # e.g. A01, B03, R12, G07, X02
  title: "<one-line human-readable>"
  status: pending                # pending | in_progress | completed | blocked | cancelled
  dependencies: [...]            # sole task graph edge: task ids that must complete first; prerequisite gates are explicit tasks and reverse blockers are inferred
  validation_steps: [...]        # ordered, observable, user-facing — include non-final GOAL_RUNTIME_STATUS: CONTINUE marker discipline
  ci_commands: [CC_*, ...]       # references into top-level ci_commands
  styleguide_rules: [S*, ...]    # references into top-level styleguide_rules
  guardrails: [G*, ...]          # references into top-level guardrails
  learnings: []                  # MUTABLE — agent appends as it discovers facts
  gotchas: []                    # MUTABLE — agent appends pitfalls and rewind notes
  context_files: [...]           # files the agent should read for context
  context_urls: [...]            # authoritative documentation URLs (sourced from Firecrawl maps)
  principle_ids: [P*, ...]       # which engineering principles the task validates
```

`status`, `learnings`, and `gotchas` are mutable; everything else is contract. Every task's `validation_steps` and `guardrails` must preserve the GoalManager runtime rule: on non-final `/goal` turns, do not ask the user for input and end with `GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued` plus the next YAML task id.

### Phase order (strict)

`ANALYSIS` → `BOOTSTRAP` → `RED` → `GREEN` → `REFACTOR`. RED carries a `hard_gate` string forbidding production-code edits before the kickoff RED task plus all RED tests are committed and observed failing for the right reason.

### Firecrawl `map --limit 5000` validation flow

For every technology referenced in the validated spec (frameworks, runtimes, providers, CLIs, SDKs, vendor APIs):

1. Identify the official documentation root URL.
2. Run `firecrawl --status` to confirm authentication. Treat a `0`-exit auth/setup banner as **not usable** and record the requirement as execution-time validation only.
3. If authenticated, run `firecrawl map --limit 5000 <official-docs-root>` and persist the JSON output to `<output-dir>/research/url-maps/<tech>.json` (where `<output-dir>` is `~/.hermes/goal-prompts/` unless overridden by `--dir`).
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
- every `dependencies` reference resolves to an existing task id,
- every GREEN task has at least one RED task in `dependencies`,
- legacy task graph fields (`prerequisites`, `blocking_tasks`) are absent because prerequisite gates are explicit tasks and reverse blockers are inferred from dependent tasks,
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
- preserve the autonomy, non-execution-of-other-work, GoalManager continuation, and ruthless-final-diff-cleanup requirements from the goal Markdown,
- front-load the `/goal`-specific rule that non-final turns must continue autonomously, must not ask the user for input, and must end with `GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued` plus the next YAML task id.

### Canonical template

```text
/goal Execute the goal contract at <ABS_PATH_TO_GOAL_MD> by walking the paired TDD task list at <ABS_PATH_TO_TASKS_YAML> in strict ANALYSIS → BOOTSTRAP → RED → GREEN → REFACTOR order. This is a Hermes /goal runtime: continue autonomously until all acceptance criteria validate or Hermes goal max_turns pauses the loop. Do not ask the user for input, guidance, confirmation, or permission on non-final turns; choose safe autonomous fallbacks and update only YAML `status`, `learnings`, and `gotchas`. End every non-final response with `GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued` and the next YAML task id; use `GOAL_RUNTIME_STATUS: COMPLETE — all acceptance criteria and validations satisfied` only after the full contract validates. Treat the Markdown file as the immutable contract and the YAML as the runtime state. Honor the RED phase `hard_gate` (no GREEN production-code edits before the R00 kickoff and all RED tests are committed and observed failing for the right reason). Use every `dependencies`, `ci_commands`, `styleguide_rules`, `guardrails`, `validation_steps`, `context_files`, `principle_ids`, and `context_urls` reference verbatim. Operate autonomously per the goal's autonomy requirement, do not execute work outside the contract, and finish with the ruthless final-diff cleanup pass defined in the goal Markdown.
```

Substitute the absolute paths and, when more than two artifacts exist (for example multiple companion YAMLs), enumerate them all in the bracketed payload.

### Rules

- Print this line to stdout (or echo it in the chat reply) AFTER the file paths and validation results have already been reported.
- Print exactly one line beginning with `/goal ` — no Markdown code fences, no leading bullet, no trailing commentary on the same line.
- Do NOT execute the printed `/goal` line. Printing it is the entire step. **The skill, the helper script, and any code path that produces the artifacts MUST NEVER instantiate `/goal`, dispatch a goal run, push the line back into Hermes Agent's command bus, or otherwise act on the handoff.** Only the user (or a downstream orchestrator the user has explicitly chosen) decides when, where, and whether to invoke it.
- Treat the handoff as a paste-target. The line is also returned in the JSON payload's `handoff_prompt` field for tooling that wants to display it; consumers of that field MUST display it, not run it.
- Do NOT alter the goal Markdown or the task list YAML to add this handoff line; it is a runtime emission of the skill, not a persisted artifact.

## Validation Checklist

Before considering this skill's output complete:

- [ ] The optimized Markdown file exists in `~/.hermes/goal-prompts/` (or the explicit `--dir` override) and not in the current working directory.
- [ ] The Markdown file starts with the required metadata block.
- [ ] `source_prompt_hash` is non-empty and stable for the original prompt.
- [ ] All required Markdown sections are present.
- [ ] The generated Markdown carries a `## Repository Context` section with the workdir, repo root, git state (when available), Claude Code `--worktree` / `-w` directory resolution, manifests/lockfiles/CI/agent-context-file lists, and absolute-path curated key paths — built from on-disk introspection of the invoking workdir, never fabricated.
- [ ] The companion YAML carries a non-empty `validation_evidence.repository_context` block whose `workdir`, `repo_root`, `key_paths`, and `claude_worktree` are present, and whose snapshot matches the on-disk reality at generation time. `metadata.workdir`, `metadata.repo_root`, `agent_runtime_protocol.handoff_workdir`, `agent_runtime_protocol.claude_worktree_root`, `agent_runtime_protocol.claude_worktree_directory_template`, and `agent_runtime_protocol.claude_worktree_resolution` are populated.
- [ ] Every task's `context_files` includes the goal Markdown, the YAML, and every entry of `validation_evidence.repository_context.key_paths`.
- [ ] The non-execution guardrail is present.
- [ ] The isolated generation boundary is present.
- [ ] The autonomy requirement is present.
- [ ] The `## Goal Runtime Continuation Contract` section is present, contains the exact `GOAL_RUNTIME_STATUS: CONTINUE` and `GOAL_RUNTIME_STATUS: COMPLETE` markers, forbids asking the user for input on non-final `/goal` turns, and says to continue autonomously until all acceptance criteria validate or Hermes goal `max_turns` pauses the loop.
- [ ] Software-development constraints appear for software or uncertain prompts.
- [ ] The software-development cleanup requirement appears for software-development prompts.
- [ ] The software engineering core principles and rubric appear for software-development prompts.
- [ ] Non-software prompts omit software-development constraints, cleanup language, and software engineering principles when the domain is clear.
- [ ] The Markdown filename is safe, lowercase, hyphen-separated, concise, and collision-resistant.
- [ ] The generated prompt's requested task has not been executed during optimization.
- [ ] Hermes `/goal` has not been invoked, dispatched, instantiated, intercepted, or modified by the generation process. Neither the skill nor the helper script ran the printed handoff line.
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
- [ ] After both files exist and pass validation, the skill printed exactly one final handoff line beginning with `/goal ` that names every generated artifact by absolute path, describes the deterministic work required to execute the spec, front-loads the GoalManager continuation contract, forbids asking the user for input on non-final turns, and includes both `GOAL_RUNTIME_STATUS` markers.
- [ ] The handoff `/goal` line was not executed by this skill and was not persisted into either generated artifact.
- [ ] The generated Markdown carries a `## Coding Agent Execution Contract` section that mentions every required `claude` CLI flag (`--print`, `--add-dir`, `--agent`, `--allow-dangerously-skip-permissions`, `--dangerously-skip-permissions`, `--debug-file`, `--effort max`, `--include-hook-events`, `--output-format stream-json`, `--include-partial-messages`, `--input-format stream-json`, `--json-schema`, `--mcp-config`, `--settings`, `--strict-mcp-config`, `--system-prompt-file`, `--tools`, `--verbose`, `--worktree`) verbatim.
- [ ] The companion task list YAML carries a `coding_agent_execution_contract` top-level block whose `executor` is `claude`, whose `required_flags` enumerates each of the 19 required flags with a non-empty `placeholder` (use `"<no-arg>"` for boolean flags), whose `canonical_invocation` starts with `claude `, contains every required flag, and ends with a quoted positional `"<instructions-from-hermes-agent>"` argument, whose `worktree_directory` maps `--worktree` / `-w` to `.claude/worktrees/<worktree-name>` inside the active Hermes worktree, and whose `forbidden_alternatives` is a non-empty list.
- [ ] The companion task list YAML carries `agent_runtime_protocol.goal_manager_continuation_contract` with runtime `hermes /goal`, `continue_until`, `non_final_response_marker`, `final_response_marker`, `human_input_policy`, and `judge_shape`; every task references the continuation guardrail.
- [ ] The companion task list YAML carries a non-empty top-level `validation_reconciliation` block (the contrarian re-verification reconciliation block) emitted by the step 11.5 pass; the block contains `conflicts`, `resolutions`, and `final_state` keys.
- [ ] `validation_reconciliation.final_state` is set to one of the three allowed values: `all-claims-reconciled`, `some-claims-downgraded`, or `some-claims-escalated-to-execution-time`. No other literal is accepted.
- [ ] The contrarian re-verification artifact / evidence list is cited: every `Conflict` entry under `validation_reconciliation.conflicts[]` carries a non-empty `check_id`, `evidence_target`, `original_claim`, `contrarian_observation`, `severity`, and `resolution`, and the `resolutions[]` array preserves the same ordering for end-to-end traceability into the YAML's `validation_evidence` and into `learnings[]`.

## Common Pitfalls

1. **Regenerating when the user asks for a small in-place requirement edit.** If the input is an existing valid generated goal file and the user asks to add, tighten, or adjust one requirement, patch that file in place instead of regenerating a new prompt. Search for duplicated sections such as the top-level goal body and preserved `Original Intent`, apply the same semantic edit to both when present, then run the in-place validator.
2. **Executing the generated goal while optimizing it.** This violates the core guardrail. Only save and validate the prompt. **Never call `/goal`, instantiate a goal run, or push the printed handoff line through Hermes Agent's command bus from inside the skill or helper.** The generator's job ends after writing the Markdown + YAML files and printing the paste-target line; if you find yourself about to invoke `/goal` during the same skill turn, stop.
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
16. **Feeding the helper a heredoc via `--json @-` or letting a thin one-line prompt slip through.** The helper tokenizes argv and classifies the domain by keyword density, so `@-` becomes the entire prompt (domain = uncertain, confidence = low, title = "Optimized goal Goal", `## Software Engineering Core Principles` section omitted). Always (a) write the full prompt to `/tmp/<project>_prompt.txt` first, (b) feed it as `--json "$(cat /tmp/<project>_prompt.txt)"`, and (c) verify the resulting frontmatter has `domain: "software-development"` + `confidence: "high"` and the title is project-shaped before proceeding. Also always pass `--workdir <abs-path-to-source-folder>` when the helper runs from a different cwd, otherwise `repository_context` snapshots the cwd rather than the actual source folder. See `references/cross-platform-port-goals.md` for the full file-fed-prompt + bundle-introspection workflow.
17. **Claiming Firecrawl tools were used when only `firecrawl --status` succeeded.** `--status` proves auth, not that any map/scrape/extract actually ran. Cite real map files with `data.links` length and real `scrape`/`extract` outputs in `validation_evidence`.
18. **Claiming `opensrc` validated something when only the README was skimmed.** `opensrc` claims must cite specific files and lines when reasonable. For every API/version assertion the YAML makes, record source paths under `validation_evidence.opensrc.fetched[<repo>].key_paths[]`.
19. **Letting GREEN tasks edit production code before the RED kickoff is committed.** Encode a `hard_gate` field on the RED phase block with explicit refusal text and make every GREEN task depend directly on the relevant RED task ids (at minimum R00/R01 for the baseline). Reverse blockers are inferred from `dependencies`; do not emit `blocking_tasks`.
20. **Forgetting the space after `:` in YAML.** Writing `key:"value"` instead of `key: "value"` makes PyYAML's scanner fail two lines later with `could not find expected ':'`. Run the structural validator immediately after writing the file.
21. **Skipping the final handoff `/goal` print.** The skill is incomplete until it prints exactly one line beginning with `/goal ` that names every generated file by absolute path and describes the deterministic work to execute them.
22. **Executing the printed handoff `/goal` line.** Printing it is the entire step. Never run it during this skill, never wire it into Hermes `/goal` automatically, never persist it into the goal Markdown or the task list YAML, never feed it into another agent loop, and never substitute the line as the next prompt to the active conversation. If a downstream consumer (Telegram bot, orchestrator, gateway) needs to display the line, it MUST surface it as text for the user — not as a command to run.
23. **Letting the generated goal tell `/goal` it is done, blocked, or waiting for input before the contract is truly complete.** Hermes `GoalManager` judges only the latest assistant response against the stored goal; a response that says the overall goal is complete, blocked, unachievable, or waiting for user input can stop the loop early. Generated artifacts MUST include the Goal Runtime Continuation Contract, put it near the top of the Markdown and handoff line, carry it in `agent_runtime_protocol.goal_manager_continuation_contract`, and require every non-final response to end with `GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued` plus the next YAML task id. Record friction in YAML `learnings` / `gotchas`, choose the safest autonomous fallback, and continue until validation succeeds or Hermes itself pauses at `max_turns`.

24. **Letting the canonical Software-Development Constraints paragraph apply absolutely when the goal targets a brownfield third-party repo whose own style violates it.** The canonical paragraph (`200 LOC maximum per file`, `30 LOC maximum per coding-language construct type`, `Maximum nesting depth of 3`) is correct as a default — and the Markdown validator substring-matches it, so it must remain in the generated file verbatim. But when the workdir is someone else's OSS repo (Warp, Mastra, Next.js, etc.) whose existing files routinely run 1k-27k LOC, enforcing the cap forces the downstream agent into one of two contract violations: (a) split existing files into new <200-LOC files, breaking the "avoid creating new files or folders unless absolutely necessary" rule, or (b) refactor existing 50-200-LOC constructs down to 30 LOC, breaking the minimal-diff invariant and "do not degrade existing behavior" rule. The fix is NOT to delete the canonical paragraph (the validator will fail) but to APPEND a `### Project-Specific Overrides (<org>/<repo>)` subsection underneath that (i) explicitly states "follow upstream practice on file size, do not split existing files solely to satisfy a cap", (ii) scopes the 30-LOC construct cap to "NEWLY CREATED constructs only" with existing constructs preserved, (iii) scopes the depth-3 nesting cap to "NEWLY CREATED blocks only", and to mirror the scoping in the YAML via `metadata.hard_invariants` (`file_loc_policy: follow_<upstream>_practice`, `construct_loc_max_new_only: 30`, `construct_loc_max_existing_policy: unchanged_follow_<upstream>`, `nesting_depth_max_new_only: 3`, `nesting_depth_max_existing_policy: unchanged_follow_<upstream>`), via `styleguide_rules` keys that telegraph the scoping (`S1_file_size_follow_<upstream>`, `S2_construct_size` with "NEWLY CREATED" in the body, `S3_nesting_depth` with "NEWLY CREATED" in the body), and via `validation_reconciliation` conflict entries with `resolution: some-claims-downgraded` and matching top-level `final_state: some-claims-downgraded`. See `references/third-party-oss-pr-goals.md` for the full Markdown + YAML template and the pre-helper probes that surface the real upstream LOC distribution.

For the archived long-form operational gotchas (Firecrawl environment loss, Firecrawl 1.16 quirks, opensrc evidence, validator edge cases, remote-backend helper absence, patch verifier flakes, and execution-audit recovery), read `references/common-pitfalls-archive.md`.
