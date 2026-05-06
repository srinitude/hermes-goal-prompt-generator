from __future__ import annotations

VERSION = "1.3.0"

AUTONOMY = (
    "Ensure that you can operate everything autonomously without human intervention or a human in the loop, "
    "except where credentials, external approvals, legal authorization, payment authorization, or explicit safety "
    "constraints make human action mandatory. When human action is truly unavoidable, clearly document the blocker, "
    "the required human action, and the exact point at which autonomous execution can resume."
)

SOFTWARE_CONSTRAINTS = """Ensure you always follow these rules:
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
- Always operate with a BOOTSTRAP / RED / GREEN / REFACTOR TDD-first mindset."""

SOFTWARE_CLEANUP_REQUIREMENT = (
    "At the end of the goal execution, perform a ruthless cleanup pass over the final diff. "
    "Remove every code change, file change, configuration change, dependency change, test change, "
    "documentation change, or generated artifact that is unrelated, incidental, speculative, exploratory, "
    "redundant, or extraneous to the successful completion of the approved goal. The final submitted change "
    "set must contain only the minimum necessary changes required to satisfy the goal and its validation "
    "criteria. If the goal is executed within a brownfield codebase, preserve the repository’s existing intent, "
    "architecture, conventions, abstractions, naming patterns, style, behavior, public contracts, tests, workflows, "
    "and integration assumptions unless the approved goal explicitly requires changing them. Before marking the "
    "goal complete, verify that the final change set does not introduce regressions, does not conflict with the "
    "surrounding repository context, does not degrade existing behavior, and does not leave behind temporary "
    "implementation scaffolding, abandoned experiments, dead code, unused dependencies, unused exports, debug "
    "logs, placeholder logic, TODOs, mocks, stubs, or broad refactors that are not required by the goal. If a "
    "change was made during execution but is not necessary for the final validated solution, revert it before "
    "completion."
)

SOFTWARE_ENGINEERING_PRINCIPLES = """## Software Engineering Core Principles

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

Engineer software as explicit, typed, observable, cancellable, resource-safe workflows with clear failure semantics and boundary-driven dependency management."""

CLAUDE_CLI_EXECUTION_CONTRACT = (
    "All implementation work that satisfies this goal MUST be performed by invoking the `claude` CLI (Claude Code) "
    "with the full required flag set: `--p <instructions-from-hermes-agent>`, `--add-dir <list-of-directories>`, "
    "`--agent <custom-subagent>`, `--allow-dangerously-skip-permissions`, `--dangerously-skip-permissions`, "
    "`--debug-file <path>`, `--effort max`, `--include-hook-events`, `--output-format stream-json`, "
    "`--include-partial-messages`, `--input-format stream-json`, `--json-schema <json-schema>`, "
    "`--settings <settings-json-file>`, `--strict-mcp-config <mcp-json-file>`, `--system-prompt-file <file>`, "
    "`--tools <comma-separated-tools>`, `--verbose`, and `--worktree <worktree-name>`. "
    "The Hermes Agent instructions for this goal are passed verbatim as the `--p` payload; "
    "every other flag is mandatory and must be populated with a concrete, validated value before launch. "
    "Do not substitute, omit, or rename any flag in this set, and do not implement the requirements through any "
    "other mechanism (no inline shell scripts, no other CLIs, no editor sessions, no manual file edits) — "
    "every change to the repository must originate from a `claude` invocation that carries the full flag set above."
)

CLAUDE_CLI_REQUIRED_FLAGS = (
    ("--p", "<instructions-from-hermes-agent>"),
    ("--add-dir", "<list-of-directories>"),
    ("--agent", "<custom-subagent>"),
    ("--allow-dangerously-skip-permissions", "<no-arg>"),
    ("--dangerously-skip-permissions", "<no-arg>"),
    ("--debug-file", "<path>"),
    ("--effort", "max"),
    ("--include-hook-events", "<no-arg>"),
    ("--output-format", "stream-json"),
    ("--include-partial-messages", "<no-arg>"),
    ("--input-format", "stream-json"),
    ("--json-schema", "<json-schema>"),
    ("--settings", "<settings-json-file>"),
    ("--strict-mcp-config", "<mcp-json-file>"),
    ("--system-prompt-file", "<file>"),
    ("--tools", "<comma-separated-tools>"),
    ("--verbose", "<no-arg>"),
    ("--worktree", "<worktree-name>"),
)

REQUIRED_SECTIONS = [
    "Goal", "Original Intent", "Domain", "Assumptions", "Non-Execution Guardrail",
    "Isolated Generation Boundary", "Autonomous Execution Requirement",
    "Research and Source Validation Requirements", "Scope", "Execution Plan",
    "Acceptance Criteria", "Validation Commands", "Completion Definition",
    "Failure Conditions", "Final Output Requirements", "Coding Agent Execution Contract",
]

SOFTWARE_TERMS = set(
    "code coding test tests deploy refactor debug api cli sdk plugin package backend frontend database "
    "schema automation infrastructure ci cd github git docker railway vercel aws bun node typescript swift "
    "python mastra nextjs next.js react effect openrouter fal stripe auth repository source commit pr issue "
    "runtime app application workflow integration model fastapi".split()
)

DOMAIN_TERMS = {
    "creative-writing": set("write poem story essay song lyric creative narrative character ocean sunrise".split()),
    "research": set("research analyze literature paper papers summarize sources study market compare investigate".split()),
    "data-analysis": set("data csv spreadsheet chart statistics metric dataset visualization analysis".split()),
    "business-operations": set("strategy plan proposal customer sales marketing operations process policy".split()),
}

STOP = set(
    "a an the and or to for with of in on at from this that these those it is are be by into about build "
    "create make implement add develop generate produce".split()
)
