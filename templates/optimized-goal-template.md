---
generated_by: goal-prompt-generator
goal_prompt_generator_version: "1.0.0"
optimized_for: hermes-agent-goal
optimization_status: optimized
source_prompt_hash: "stable-sha256-hash-of-original-prompt"
generated_at: "ISO-8601 timestamp"
domain: "detected-domain"
domain_confidence: "high-or-moderate-or-low"
---

# Generated Goal Title

## Goal

Clear statement of the transformed user goal.

## Original Intent

Brief summary of the user's original prompt and what must be preserved.

## Domain

Detected domain and confidence level.

## Assumptions

Explicit assumptions used to resolve ambiguity.

## Non-Execution Guardrail

Do not execute this prompt while generating it. Only enhance, structure, validate, and save it.

## `/goal` Preflight Requirement

If this prompt is passed to Hermes Agent's `/goal` workflow and is not already optimized by `goal-prompt-generator`, run `goal-prompt-generator` first, save the optimized Markdown goal file, validate the optimized file, and only then run `/goal` using the optimized file as input.

If this prompt already contains valid `goal-prompt-generator` metadata and all required sections, do not re-optimize it unnecessarily. Validate it and proceed with `/goal`.

## Autonomous Execution Requirement

Ensure that you can operate everything autonomously without human intervention or a human in the loop, except where credentials, external approvals, legal authorization, payment authorization, or explicit safety constraints make human action mandatory. When human action is truly unavoidable, clearly document the blocker, the required human action, and the exact point at which autonomous execution can resume.

## Research and Source Validation Requirements

List documentation, repositories, URLs, files, APIs, or external sources the downstream agent must inspect before implementation.

## Scope

### In Scope

What the goal includes.

### Out of Scope

What the goal excludes.

## Execution Plan

### Phase 0: BOOTSTRAP

Setup, documentation review, repo inspection, environment validation, local CI/CD setup, and preconditions.

### Phase 1: RED

Failing tests, failing checks, acceptance criteria, and expected failure evidence.

### Phase 2: GREEN

Minimal implementation required to satisfy tests and acceptance criteria.

### Phase 3: REFACTOR

Hardening, simplification, deduplication, quality gates, performance checks, and final verification.

## Software Development Constraints

Include this section only when the detected domain is software development or classification is uncertain.

## Acceptance Criteria

Concrete, testable, user-facing criteria.

## Validation Commands

Commands or checks the downstream agent must run.

## Completion Definition

Exact definition of done.

## Failure Conditions

Conditions that mean the goal is incomplete or invalid.

## Final Output Requirements

Files, artifacts, reports, or summaries the downstream agent must produce.
