# Re-validating an existing generated goal file

The CLI helper `scripts/generate_goal_prompt.py` is a *generator*, not an in-place validator. Use `--input-file <path-to-file>.md` only when you explicitly want the helper to reuse an existing valid generated Markdown file or regenerate a new optimized file from an invalid/incomplete file's contents. Positional arguments are always treated as raw prompt text. When you need to validate, hand-edit, or sanity-check a generated file in place without creating or reusing output files, call the validator directly.

## Inline one-liner

```bash
python3 -c "
import sys, pathlib
sys.path.insert(0, str(pathlib.Path.home() / '.hermes/skills/software-development/goal-prompt-generator/src'))
from goal_prompt_generator.validation import validate_optimized_markdown
text = pathlib.Path('<path-to-file>.md').read_text()
r = validate_optimized_markdown(text)
print('valid:', r.valid)
print('reasons:', r.reasons)
"
```

`validate_optimized_markdown` returns a `ValidationResult` with `.valid: bool`
and `.reasons: list[str]`. Any non-empty `reasons` list means the file does
not satisfy the contract even if the frontmatter looks correct.

## What the validator actually checks

From `goal_prompt_generator.validation`:

- `parse_metadata(...)` — frontmatter fields and `optimization_status == 'optimized'`.
- `REQUIRED_SECTIONS` — every header listed in SKILL.md "Required Markdown Sections" is present, in order.
- `AUTONOMY` — the autonomy paragraph appears as a **literal substring** in the rendered Markdown.
- The non-execution guardrail, isolated-generation boundary, the software-development constraints block (when the domain is software-development or uncertain), the cleanup requirement (when the domain is software-development), and the software engineering principles/rubric (when the domain is software-development) are similarly substring-matched.

## Boilerplate paragraphs you MUST NOT soft-wrap

Because the validator uses literal substring matching, hand-editing must
preserve these blocks as single physical lines (paragraph-break with blank
lines is fine; mid-paragraph `\n` is not):

1. The full Autonomy Requirement paragraph (under `## Autonomous Execution Requirement`).
2. The Non-Execution Guardrail sentence (under `## Non-Execution Guardrail`).
3. The Isolated Generation Boundary paragraph (under `## Isolated Generation Boundary`).
4. Each bullet of the Software Development Constraints block (under `## Software Development Constraints`), when present.
5. The Software-Development Cleanup Requirement paragraph, when the domain is `software-development`.
6. The Software Engineering Core Principles section, including the condensed rubric and bottom line, when the domain is `software-development`.

If your editor or formatter wraps these at ~80 cols, the file will fail
validation with reasons such as `['autonomy requirement missing']` even
though the human-readable content is correct. Re-flow the affected paragraph
back onto one line and re-run the inline validator.

## Symptom → fix table

| Symptom (`reasons` value)                        | Likely cause                                                                 | Fix                                                                                |
| ------------------------------------------------ | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `autonomy requirement missing`                   | Autonomy paragraph soft-wrapped, paraphrased, or split across lines.         | Restore the verbatim single-line paragraph from `validation.AUTONOMY`.             |
| `non-execution guardrail missing`                | Guardrail sentence reworded or wrapped.                                      | Use the verbatim sentence from SKILL.md "Non-Execution Rule".                      |
| `isolated generation boundary missing`           | Isolation paragraph wrapped or trimmed.                                      | Restore the canonical paragraph from SKILL.md "Isolation Boundary".                |
| `software-development constraints missing`       | Bullet list wrapped, reordered, or omitted on uncertain-domain prompt.       | Re-paste the constraints block verbatim; when uncertain, include it.               |
| `software-development cleanup requirement missing` | Cleanup paragraph wrapped, paraphrased, or omitted on software prompt.       | Re-paste `SOFTWARE_CLEANUP_REQUIREMENT` verbatim for software-development prompts. |
| `software engineering core principles missing` | Principles/rubric section wrapped, paraphrased, or omitted on software prompt. | Re-paste `SOFTWARE_ENGINEERING_PRINCIPLES` verbatim for software-development prompts. |
| `required section missing: <header>`             | Header omitted or misspelled.                                                | Reinsert the exact header text from SKILL.md "Required Markdown Sections".         |
| `metadata missing` / `optimization_status != optimized` | Frontmatter edited or stripped.                                       | Restore the full frontmatter contract; recompute `source_prompt_hash` if the source prompt changed. |

## Round-trip recipe used in practice

When a generator run completes but a downstream hand-edit invalidates the file:

1. Run the inline validator above; capture `reasons`.
2. Look up each reason in the table; apply the verbatim fix.
3. Re-run the inline validator until `valid: True, reasons: []`.
4. Do **not** re-run `generate_goal_prompt.py` when you only intend to validate the file in place — use the validator directly so no output file is created or reused.
