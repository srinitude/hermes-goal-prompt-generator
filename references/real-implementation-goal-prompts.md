# Real Implementation Goal Prompts

Use this reference when a user asks for a generated goal prompt that turns an existing scaffold, contract layer, template generator, or descriptor-only project into a real implementation.

## Trigger signals

- User says the prior result was not the real implementation.
- Repository contains string templates or descriptors that mention real APIs (`createWorkflow`, `Agent`, `Hono`, `Bun.serve`, `MastraServer`) but runtime behavior is absent.
- User asks for BOOTSTRAP / RED / GREEN / REFACTOR and forbids production code before tests.
- User wants every product state enumerated in unit, integration, and end-to-end tests.

## Required prompt additions

Add sections beyond the standard generated goal scaffold:

1. **Real Implementation Mandate** — explicitly forbid string-template scaffolds masquerading as runtime behavior.
2. **Authoritative Source Files** — name the existing goal/spec files and brownfield source paths to inspect.
3. **Source Reality Check Required Before Changes** — require evidence of what is real runtime code vs descriptors/templates.
4. **Absolute TDD Gate** — forbid production-code edits until all planned RED tests are written and fail for the right reason.
5. **Required Test Manifest** — require a machine-readable manifest mapping test files to product states, contracts, RED failure reasons, GREEN behavior, validation commands, and engineering principle IDs.
6. **Product State Inventory** — enumerate observable states the tests must cover.
7. **Unit / Integration / E2E Test Contracts** — require real behavior tests, not substring checks.
8. **Engineering Principle Tests** — require all 18 principles to be proven at observable boundaries.
9. **Implementation Sequence After RED** — order the minimal GREEN implementation after tests.
10. **Documentation And Research Execution Requirements** — do not claim Firecrawl/source research was done while generating; preserve it as execution-time validation unless actually available.
11. **Persistence Requirement** — if user wants a long autonomous run, state not to collapse into a superficial scaffold or partial plan.

## Validation

After patching the generated prompt, validate in place with:

```bash
python3 - <<'PY'
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.home() / '.hermes/skills/software-development/goal-prompt-generator/src'))
from goal_prompt_generator.validation import validate_optimized_markdown, parse_metadata
path = pathlib.Path('<generated-goal>.md')
text = path.read_text()
result = validate_optimized_markdown(text)
print('valid:', result.valid)
print('reasons:', result.reasons)
print('metadata:', parse_metadata(text))
PY
```

Do not run the generated implementation goal while generating or validating the prompt.
