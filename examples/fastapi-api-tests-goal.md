---
generated_by: goal-prompt-generator
goal_prompt_generator_version: "1.0.0"
optimized_for: hermes-agent-goal
optimization_status: optimized
source_prompt_hash: "dc30a04b515cecf114e140aef47eddc08b5b48012bb27f56523152ab8641bbf7"
generated_at: "2026-01-01T00:00:00+00:00"
domain: "software-development"
domain_confidence: "high"
---


# Fastapi API tests Goal

## Goal

Complete the user's requested outcome in a concrete, verifiable way: Build a FastAPI API with tests

## Original Intent

Preserve this original request without executing it during optimization:

> Build a FastAPI API with tests

## Domain

Detected domain: `software-development`. Confidence: `high`.

## Assumptions

- Use the active workspace unless a path or repository is specified.
- Make reasonable assumptions where details are missing and document them before acting.
- Preserve the user's intent over incidental wording.

## Non-Execution Guardrail

Do not execute this prompt while generating it. Only enhance, structure, validate, and save it.

## `/goal` Preflight Requirement

If this prompt is passed to Hermes Agent's `/goal` workflow and is not already optimized by `goal-prompt-generator`, run `goal-prompt-generator` first, save the optimized Markdown goal file, validate the optimized file, and only then run `/goal` using the optimized file as input.

If this prompt already contains valid `goal-prompt-generator` metadata and all required sections, do not re-optimize it unnecessarily. Validate it and proceed with `/goal`.

## Autonomous Execution Requirement

Ensure that you can operate everything autonomously without human intervention or a human in the loop, except where credentials, external approvals, legal authorization, payment authorization, or explicit safety constraints make human action mandatory. When human action is truly unavoidable, clearly document the blocker, the required human action, and the exact point at which autonomous execution can resume.

## Research and Source Validation Requirements

- Inspect authoritative documentation, repositories, files, APIs, and runtime behavior relevant to the task before implementation.
- Do not rely on assumptions when documentation or source code provides authoritative behavior.

## Scope

### In Scope

- Deliver the requested outcome with explicit assumptions, ordered work, and verifiable results.

### Out of Scope

- Unrelated enhancements, speculative rewrites, and actions requiring unavailable credentials or approvals.

## Execution Plan

### Phase 0: BOOTSTRAP

Validate context, prerequisites, source materials, environment, and local quality gates before making changes.

### Phase 1: RED

Define failing checks or acceptance evidence that prove the requested outcome is not yet satisfied.

### Phase 2: GREEN

Make the smallest complete change or action set needed to satisfy the checks and user-facing requirements.

### Phase 3: REFACTOR

Simplify, remove duplication, harden edge cases, and rerun validation without broadening scope.

## Software Development Constraints

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

## Acceptance Criteria

- The final result satisfies the original user intent.
- All assumptions, blockers, and trade-offs are documented.
- User-facing behavior and observable outcomes are validated.

## Validation Commands

- Run the relevant local checks, tests, linters, builds, or source inspections for this domain.
- Record exact commands and outcomes in the final response.

## Completion Definition

Done means the requested outcome is complete, validated, and summarized with generated or modified artifacts listed explicitly.

## Failure Conditions

- Required credentials, approvals, legal authorization, payment authorization, or safety constraints are unavailable.
- Validation fails or cannot be run.
- The result cannot be verified against the acceptance criteria.

## Final Output Requirements

- Provide a concise completion summary.
- List files, artifacts, commands, validation results, blockers, and the next autonomous resume point if blocked.
