---
name: goal-prompt-generator
description: >
  Generate isolated optimized Markdown files for individual Hermes goal prompts. Use when a user asks to enhance, structure, validate, or save a goal prompt without executing it. Do NOT use as an automatic `/goal` preflight, slash-command interceptor, goal-loop hook, or to execute the generated goal; this skill only produces and validates standalone prompt files.
version: 1.0.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [goal, prompt-optimization, isolated-generation, tdd]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, test-driven-development]
---

# Goal Prompt Generator

## Overview

`goal-prompt-generator` converts one raw user request into one isolated, optimized Markdown goal prompt file. It preserves the user's original intent, adds deterministic metadata, detects the domain, resolves ambiguity with explicit assumptions, injects autonomy, software-development constraints, software-specific final-diff cleanup requirements, and software engineering core principles/rubric when required, validates the Markdown contract, and saves the result in the execution directory.

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
9. Report the path and validation result.

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

The script writes the optimized Markdown file to the current working directory by default and prints the generated path, status, title, source hash, and validation status.

**The positional `prompt` argument is treated as raw prompt text, not as a path.** Passing an existing `.md` path to "re-validate" it will hash that path string and emit a junk regenerated file with a long `generated-by-…-goal.md` filename. To validate an existing generated file in place, do NOT pipe it through the helper — import the validator directly:

```bash
python3 -c "
import sys, pathlib
sys.path.insert(0, '/Users/kiren/.hermes/skills/software-development/goal-prompt-generator/src')
from goal_prompt_generator.validation import validate_optimized_markdown
text = pathlib.Path('<path-to-file>.md').read_text()
r = validate_optimized_markdown(text)
print('valid:', r.valid, 'reasons:', r.reasons)
"
```

See `references/revalidating-existing-files.md` for the full recipe and the list of substring-matched boilerplate paragraphs that must NOT be soft-wrapped across newlines.

## Required Metadata Contract

Every optimized Markdown file must begin with this frontmatter shape:

```yaml
---
generated_by: goal-prompt-generator
goal_prompt_generator_version: "1.0.1"
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

## Validation Checklist

Before considering this skill's output complete:

- [ ] The optimized file exists in the execution directory.
- [ ] The file starts with the required metadata block.
- [ ] `source_prompt_hash` is non-empty and stable for the original prompt.
- [ ] All required sections are present.
- [ ] The non-execution guardrail is present.
- [ ] The isolated generation boundary is present.
- [ ] The autonomy requirement is present.
- [ ] Software-development constraints appear for software or uncertain prompts.
- [ ] The software-development cleanup requirement appears for software-development prompts.
- [ ] The software engineering core principles and rubric appear for software-development prompts.
- [ ] Non-software prompts omit software-development constraints, cleanup language, and software engineering principles when the domain is clear.
- [ ] The filename is safe, lowercase, hyphen-separated, concise, and collision-resistant.
- [ ] The generated prompt's requested task has not been executed during optimization.
- [ ] Hermes `/goal` has not been invoked, intercepted, or modified by the generation process.
- [ ] Shareable-repo packaging, if updated, contains no automatic `/goal` source-integration patch or handler-routing docs unless explicitly requested.

## Common Pitfalls

1. **Executing the generated goal while optimizing it.** This violates the core guardrail. Only save and validate the prompt.
2. **Treating the generator as `/goal` middleware.** This refactored skill is isolated and must not run automatically inside `/goal`.
3. **Trusting partial metadata.** Missing sections or missing constraints make the file invalid even if frontmatter exists.
4. **Skipping software constraints on uncertain prompts.** Uncertainty must use the stricter software-development path.
5. **Skipping cleanup on software-development prompts.** Classified software-development prompts must include the ruthless final-diff cleanup paragraph, while clear non-software prompts must not be polluted with it.
6. **Skipping software engineering core principles on software-development prompts.** Classified software-development prompts must include the core principles, condensed rubric, and bottom-line workflow summary, while clear non-software prompts must not be polluted with them.
7. **Overwriting unrelated files.** Use collision-resistant filenames and only write the generated Markdown target.
8. **Letting stale `/goal` preflight requirements leak back in.** Earlier versions of this skill included automatic `/goal` preflight/source-integration behavior, but the current contract is explicit isolated generation only. If updating the skill or shareable repo, remove stale `patches/`, `hermes-agent-source-integration` docs, `hermes-goal-integration` references, `prepare_goal_prompt` modules, goal handler edits, and tests that expect automatic routing unless the user explicitly changes scope again.
9. **Soft-wrapping the autonomy / non-execution / isolation / software-constraints / cleanup / software engineering principles boilerplate across newlines when hand-editing a generated file.** The validator (`validate_optimized_markdown`) checks these as literal substrings against the rendered Markdown. Wrapping the autonomy paragraph at ~80 cols silently invalidates an otherwise-correct file with `reasons=['autonomy requirement missing']`. Keep each boilerplate paragraph on a single physical line — the literal strings live in `goal_prompt_generator.validation` (`AUTONOMY`, plus the constants used by `validate_optimized_markdown`, including `SOFTWARE_CLEANUP_REQUIREMENT` and `SOFTWARE_ENGINEERING_PRINCIPLES`); reproduce them verbatim and only break with a blank-line paragraph break, never a mid-paragraph newline.
10. **Passing a `.md` path to `generate_goal_prompt.py` to re-validate it.** The positional argument is hashed as raw prompt text, producing a junk regenerated file. Use the inline `validate_optimized_markdown` import shown in the *Standalone Helper* section, or call `scripts/validate_skill.py` if it covers the path you need.
