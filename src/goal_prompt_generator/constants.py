from __future__ import annotations

VERSION = "1.0.0"

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

REQUIRED_SECTIONS = [
    "Goal", "Original Intent", "Domain", "Assumptions", "Non-Execution Guardrail",
    "`/goal` Preflight Requirement", "Autonomous Execution Requirement",
    "Research and Source Validation Requirements", "Scope", "Execution Plan",
    "Acceptance Criteria", "Validation Commands", "Completion Definition",
    "Failure Conditions", "Final Output Requirements",
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
