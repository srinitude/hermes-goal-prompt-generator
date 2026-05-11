# Auditing a persisted CLI flag inventory against official docs

The Coding Agent Execution Contract pins a literal flag set into every generated Markdown and YAML, and that set silently rots when the upstream CLI evolves. The 1.6.0 → 1.6.1 audit caught two flags that had been wrong since the contract was first persisted (`--p` was never a real Claude Code flag; `--strict-mcp-config <file>` collapsed two separate flags into one). Use this playbook whenever a user reports a runtime rejection like `error: unknown option '--X'`, or proactively whenever you bump a major contract version.

## The 4-step audit pattern

### 1. Probe the live binary

```bash
which <cli> && <cli> --version
<cli> --help 2>&1 | head -200
```

`--help` is the ground truth for what the *currently-installed* binary parses. Capture every flag the contract lists; any that's missing is suspicious.

Important: `--help` is NOT the official inventory — Claude Code's CLI reference explicitly states "`claude --help` does not list every flag, so a flag's absence from `--help` does not mean it is unavailable." So a flag missing from `--help` is a yellow flag, not a red one. The official docs are the tiebreaker.

### 2. Map the official docs root with Firecrawl

```bash
firecrawl map --limit 5000 --json --pretty https://<docs-root> > /tmp/<cli>-docs.json
jq '.data.links | length' /tmp/<cli>-docs.json
jq -r '.data.links[].url' /tmp/<cli>-docs.json | grep -iE 'cli-?ref|flags?|commands?'
```

For Claude Code: `https://code.claude.com/docs` mapped to 1368 links and surfaced the canonical reference at `https://code.claude.com/docs/en/cli-reference`. Mapping `https://docs.claude.com/en/docs/claude-code` (the older domain) returned only 1 link and is the wrong root — verify the link count is healthy before scraping.

### 3. Scrape the canonical reference page

```bash
firecrawl scrape --format markdown --json https://<docs-root>/<cli-reference> > /tmp/<cli>-ref.json
```

Then parse defensively — `firecrawl scrape` prepends a `Scrape ID: <uuid>` line that breaks `json.load()` (see `firecrawl-cli-1-16-quirks.md` §3a):

```python
import json, re, pathlib
text = pathlib.Path('/tmp/<cli>-ref.json').read_text()
text = re.sub(r'^Scrape ID: [a-f0-9-]+\n', '', text, count=1)
md = json.loads(text)['markdown']
```

Slice out the flag table and extract every flag token:

```python
positions = [m.start() for m in re.finditer(r'CLI flags', md)]
section = md[positions[1]:positions[1] + 15000]  # second occurrence is the section header
flags = sorted(set(re.findall(r'`(--[\w\-]+)`', section)))
print(len(flags), flags)
```

### 4. Diff against the persisted contract

```python
from goal_prompt_generator.constants import CLAUDE_CLI_REQUIRED_FLAGS
contract = {name for name, _ in CLAUDE_CLI_REQUIRED_FLAGS}
official = set(flags)
print('in contract but NOT in official docs:', contract - official)
print('in official but NOT in contract     :', official - contract)
```

Anything in `contract - official` is a rot candidate. For each candidate, scrape the doc page and read the row description: it tells you whether the flag was renamed, deprecated, or never existed under that spelling.

## Two real failure modes the audit catches

### Failure mode A: invented long-form alias for a short flag

`--p` looks like a long form of `-p` but isn't — Commander.js (Claude Code's option parser) never auto-generates `--p` from `-p`. The real long form is `--print`, and the prompt payload is the **positional argument**, not the flag's value. Symptom: `claude --p "test"` → `error: unknown option '--p'`.

Audit-step output that proves the bug:
```
in contract but NOT in official docs: {'--p'}
in official but NOT in contract     : {'--print', '--mcp-config', ...}
```

Fix: replace `("--p", "<instructions>")` with `("--print", "<no-arg>")` in `CLAUDE_CLI_REQUIRED_FLAGS`, and move the prompt payload to the canonical invocation's positional slot: `claude --print ... --worktree x "<instructions-from-hermes-agent>"`.

### Failure mode B: collapsed two flags into one

`--strict-mcp-config <mcp-json-file>` collapsed two real flags. Reading the official row reveals: `--strict-mcp-config` is a **boolean** that constrains MCP loading to whatever `--mcp-config <file>` points at. Both flags are required when fully sandboxing MCP. Symptom: `claude --strict-mcp-config /tmp/m.json` parses *something*, but `--mcp-config` is silently absent so MCP is never loaded.

Fix: split into two tuples and bump the required-flag count:
```python
("--mcp-config",        "<mcp-json-file>"),  # NEW
("--strict-mcp-config", "<no-arg>"),          # was "<mcp-json-file>"
```

## Where to land the fix

Every flag-inventory change must touch all of these in the same PR (the 1.6.1 patch list, in dependency order):

1. `src/goal_prompt_generator/constants.py` — `CLAUDE_CLI_REQUIRED_FLAGS` tuple, `CLAUDE_CLI_EXECUTION_CONTRACT` paragraph (single physical line, no soft wrap), `VERSION` bump.
2. `src/goal_prompt_generator/validation.py` — append the previous `VERSION` value to `LEGACY_GENERATOR_VERSIONS` so already-shipped Markdown contracts on disk continue to validate.
3. `src/goal_prompt_generator/contrarian_validation.py` — `CLAUDE_FLAGS` tuple.
4. `scripts/validate_task_list_yaml.py` — `REQUIRED_CLAUDE_FLAGS` tuple.
5. `tests/test_core.py::REQUIRED_CLAUDE_FLAGS` and the `claude --<prompt-flag>` assertion.
6. `tests/test_contrarian_validation.py::CLAUDE_FLAGS` (the space-joined string).
7. `tests/test_repository_evidence.py` — make sure any test that pinned the literal old VERSION uses the imported `VERSION` symbol now (otherwise the legacy-version test silently turns into a no-op).
8. `SKILL.md` — execution contract paragraph (line ~275), checklist items mentioning the flag count and the flag list (~line 497–498), pitfall #25 (flag list and count), pitfall #41 (the runtime-correction guidance).
9. `templates/optimized-goal-template.md` — both the prose paragraph and the `bash` canonical invocation block.
10. `references/coding-agent-task-list-yaml.md` — both the `required_flags:` YAML block and the `canonical_invocation:` folded scalar; bump the "N flags" count in the validator-enforcement section.
11. `references/claude-cli-execution-syntax.md` — refresh the "stale contract" wording so it explains both old and new shapes.
12. `CHANGELOG.md` — new entry citing the official-docs URL, the firecrawl commands used, and the exact before/after flag shapes.
13. `examples/<example>-goal.md` — regenerate via `python scripts/generate_goal_prompt.py --dir <tmp> "<original-prompt>"` then `cp` over the example. CONTRIBUTING.md item 3 requires this.

`MANIFEST.md` byte-counts and SHA prefixes are stale-by-design; they're release-packaging artifacts and `validate_skill.py` does not enforce them. Don't waste a turn updating them.

## Verification before claiming done

```bash
PYTHONPATH=src python -m pytest --tb=short                      # full suite, must be green
PYTHONPATH=src python scripts/validate_skill.py                 # skill packaging
PYTHONPATH=src python scripts/validate_task_list_yaml.py <newly-generated-yaml>
PYTHONPATH=src python -c "                                       # example file still valid
import sys, pathlib; sys.path.insert(0,'src')
from goal_prompt_generator.validation import validate_optimized_markdown
r = validate_optimized_markdown(pathlib.Path('examples/<example>-goal.md').read_text())
print('valid:', r.valid, 'reasons:', r.reasons)"
```

And one live-binary smoke test that proves the new canonical invocation parses cleanly. For Claude Code:

```bash
claude --print --add-dir /tmp --agent x --debug-file /tmp/x --effort max \
  --include-hook-events --output-format stream-json --include-partial-messages \
  --input-format stream-json --json-schema '{}' --mcp-config /tmp/m.json \
  --settings /tmp/s.json --strict-mcp-config --system-prompt-file /tmp/sp.txt \
  --tools "Bash" --verbose --worktree x "test prompt"
```

Expected outcome: `Error: Settings file not found: /tmp/s.json` (or any other *runtime* error). That proves every flag was *parsed* successfully — runtime failures are out of scope. An `error: unknown option '--X'` would mean the audit missed something.

Confirm the previous bad form still fails:

```bash
claude --p "test"
# → error: unknown option '--p'
```

## When to run this audit proactively

- Before every minor version bump of `goal-prompt-generator` that touches the contract paragraph.
- Whenever a user reports `error: unknown option '--X'` from a generated handoff.
- Whenever Claude Code releases a major version (check `claude --version` between sessions).
- Whenever the doc site domain moves (Claude Code moved from `docs.claude.com/en/docs/claude-code` to `code.claude.com/docs/en/cli-reference`; the old root only returns 1 mapped link now).
