---
name: goal-prompt-generator
description: >
  Generate optimized Markdown goal files for Hermes Agent `/goal` prompts and mandatory `/goal` preflight routing. Use when a user asks to enhance, optimize, validate, save, or reuse a goal prompt, or when raw `/goal` text must be converted before execution. Do NOT use to execute the generated goal; this skill only structures, validates, and saves the prompt.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [goal, prompt-optimization, slash-commands, preflight, tdd]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, test-driven-development]
---

# Goal Prompt Generator

## Overview

`goal-prompt-generator` converts a raw user request into a Hermes Agent `/goal`-ready Markdown file. It preserves the user's original intent, adds deterministic metadata, resolves ambiguity with explicit assumptions, splits the work into BOOTSTRAP / RED / GREEN / REFACTOR phases, and saves the optimized prompt in the current execution directory.

The skill is also the mandatory preflight contract for `/goal`: raw `/goal` text must not be handed directly to the persistent goal loop. It must first be optimized into Markdown, validated, saved, and then used as the canonical `/goal` input.

## When to Use

**Trigger conditions** — load this skill when:
- The user asks to generate, enhance, optimize, refine, preflight, or save a Hermes `/goal` prompt.
- The user provides raw `/goal` text or asks to make a prompt suitable for Hermes Agent's persistent goal workflow.
- A `/goal` command or equivalent goal-execution request receives unoptimized text.
- An existing optimized goal Markdown file must be validated before reuse.
- The user mentions `goal-prompt-generator`, `/goal preflight`, optimized goal files, or source prompt hashes.

**Anti-triggers** — do NOT use this skill when:
- The user wants the actual generated goal executed immediately.
- The task is normal planning without Hermes `/goal` execution or optimized Markdown output.
- The prompt already contains valid `goal-prompt-generator` metadata and all required sections, except for validation before reuse.

## Non-Execution Rule

Never execute the task described by the input prompt while using this skill. Only perform these operations:

1. Enhance and structure the prompt.
2. Detect the domain.
3. Inject required constraints.
4. Generate metadata.
5. Format Markdown.
6. Validate optimized Markdown.
7. Choose a safe filename.
8. Save the Markdown file.
9. Report the path and validation result.

## Canonical Implementation

The Hermes Agent source integration is implemented in `hermes_cli.goal_prompt_generator` and wired into the CLI, gateway, and TUI `/goal` entrypoints before `GoalManager.set()` receives the prompt.

Use the helper script in this skill for standalone generation:

```bash
python ~/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py "Build a FastAPI API with tests"
```

The script writes the optimized Markdown file to the current working directory by default and prints the generated path, status, title, source hash, and validation status.

For maintenance gotchas, entrypoint coverage, validation commands, and test-isolation pitfalls, read `references/implementation-validation-notes.md`.

## Required Metadata Contract

Every optimized Markdown file must begin with this frontmatter shape:

```yaml
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
```

A prompt counts as already optimized only when all of these are true:

- Metadata exists.
- `generated_by` equals `goal-prompt-generator`.
- `optimized_for` equals `hermes-agent-goal`.
- `optimization_status` equals `optimized`.
- `source_prompt_hash` is present and non-empty.
- All required Markdown sections are present.
- The autonomy requirement is present.
- The non-execution guardrail is present.
- Acceptance criteria and validation requirements are present.
- Software-development constraints are present when the domain is software development or uncertain.

If any check fails, treat the input as unoptimized and regenerate it before `/goal` proceeds.

## Required Markdown Sections

Generated files must contain these sections in order:

1. `# Generated Goal Title`
2. `## Goal`
3. `## Original Intent`
4. `## Domain`
5. `## Assumptions`
6. `## Non-Execution Guardrail`
7. `## /goal Preflight Requirement`
8. `## Autonomous Execution Requirement`
9. `## Research and Source Validation Requirements`
10. `## Scope`
11. `## Execution Plan`
12. `### Phase 0: BOOTSTRAP`
13. `### Phase 1: RED`
14. `### Phase 2: GREEN`
15. `### Phase 3: REFACTOR`
16. `## Software Development Constraints` when required
17. `## Acceptance Criteria`
18. `## Validation Commands`
19. `## Completion Definition`
20. `## Failure Conditions`
21. `## Final Output Requirements`

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

## Autonomy Requirement

Always include this requirement, regardless of domain:

```text
Ensure that you can operate everything autonomously without human intervention or a human in the loop, except where credentials, external approvals, legal authorization, payment authorization, or explicit safety constraints make human action mandatory. When human action is truly unavoidable, clearly document the blocker, the required human action, and the exact point at which autonomous execution can resume.
```

## Output File Rules

- Save the file in the same directory where the skill or preflight was executed.
- Use lowercase, hyphen-separated words.
- Use `.md` extension.
- Remove unsafe filesystem characters.
- Keep names concise but descriptive.
- Avoid generic names such as `prompt.md`, `enhanced.md`, and `output.md`.
- Append numeric suffixes such as `-2`, `-3`, or `-4` on collision.
- Reuse a valid optimized file when the input points to one.
- Regenerate invalid or incomplete optimized files into a new safe filename.

## `/goal` Preflight Workflow

When `/goal` receives input:

1. Parse `/goal` subcommands first. Preserve `status`, `pause`, `resume`, `clear`, `stop`, and `done` behavior.
2. For new goal text, run `goal-prompt-generator` before `GoalManager.set()`.
3. If the input is a valid optimized Markdown file, reuse it without unnecessary regeneration.
4. If the input is raw text or invalid optimized Markdown, generate a new optimized Markdown file.
5. Validate the generated file.
6. Store audit metadata on goal state: optimized file path, source prompt hash, generated title, and optimizer name.
7. Queue only the optimized Markdown text as the first goal turn.
8. Show the user which optimized file was generated or reused.
9. Fail closed if preflight fails; never fall back to executing the raw prompt.
10. Prevent loops by treating valid metadata plus required sections as already optimized.

## Validation Checklist

Before considering this skill's output complete:

- [ ] The optimized file exists in the execution directory.
- [ ] The file starts with the required metadata block.
- [ ] `source_prompt_hash` is non-empty and stable for the original prompt.
- [ ] All required sections are present.
- [ ] The non-execution guardrail is present.
- [ ] The autonomy requirement is present.
- [ ] Software-development constraints appear for software or uncertain prompts.
- [ ] Non-software prompts omit software-development constraints when the domain is clear.
- [ ] The filename is safe, lowercase, hyphen-separated, concise, and collision-resistant.
- [ ] The generated prompt is suitable to pass directly to `/goal`.
- [ ] The generated prompt's requested task has not been executed during optimization.

## Common Pitfalls

1. **Executing the generated goal while optimizing it.** This violates the core guardrail. Only save and validate the prompt.
2. **Passing raw `/goal` text directly into the goal loop.** Always run preflight first for new goals.
3. **Trusting partial metadata.** Missing sections or missing constraints make the file invalid even if frontmatter exists.
4. **Skipping software constraints on uncertain prompts.** Uncertainty must use the stricter software-development path.
5. **Overwriting unrelated files.** Use collision-resistant filenames and only write the generated Markdown target.
6. **Dumping large optimized Markdown in status output.** Use title or file path for status labels; keep full Markdown as the queued goal text.
