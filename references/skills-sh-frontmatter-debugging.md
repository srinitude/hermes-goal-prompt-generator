# Debugging skills.sh / `npx skills add` failures

Use when a user reports that `npx skills add <owner>/<repo>` fails with **"No valid skills found. Skills require a SKILL.md with name and description."** or **"No skills found"**, regardless of whether the repository's own `validate_skill.py` (or equivalent CI) passes.

This is a parser-tracing recipe, not a guess-from-symptoms playbook. Run it whole.

## What that error actually means

The error is emitted from exactly one code path in `vercel-labs/skills` (the npm package powering `npx skills add`):

| File | Line | Behavior |
| --- | --- | --- |
| `src/add.ts` | 1066-1068 | `if (skills.length === 0) { spinner.stop(pc.red('No skills found')); p.outro(pc.red('No valid skills found. Skills require a SKILL.md with name and description.')); ... process.exit(1); }` |
| `src/skills.ts::discoverSkills()` | 109+ | Returns `Skill[]`. Walks priority dirs (`./`, `skills/`, `.claude/skills/`, ...) and recursively if nothing found. Each candidate is run through `parseSkillMd()`. |
| `src/skills.ts::parseSkillMd()` | 28+ | Wraps the whole body in `try { … } catch { return null; }`. Returns `null` if frontmatter parsing throws OR if `data.name` / `data.description` is missing or non-string. |
| `src/frontmatter.ts::parseFrontmatter()` | 8+ | `yaml.parse(match[1])` from the `yaml` npm package. Any parser exception bubbles up to `parseSkillMd`'s catch, which silently returns `null`. |

The CLI never tells you *why* parsing failed. It just reports the empty array.

## Most common root cause: YAML 2.x compact-mapping rejection

The `yaml` npm package (currently `2.x` series) implements YAML 1.2 strictly. A frontmatter line of the form:

```yaml
compatibility: Platform-agnostic. Requires Python 3.9+ for bundled scripts. Optional but recommended: vision-capable LLM access ...
```

throws `YAMLParseError: Nested mappings are not allowed in compact mappings at line N, column M` because `yaml` interprets the second `:` (in `recommended:`) as a nested-mapping key separator inside an unquoted scalar.

The Python `pyyaml` library used by most repository-side `validate_skill.py` scripts is more permissive (accepts the same line as a long unquoted scalar), so the SKILL.md can pass local CI and still break `npx skills add`. Any repository-bundled validator that uses a regex-based YAML reader will miss this entirely.

Affected lines look like any of:
- `key: value with: an embedded colon-space`
- `key: cmd --flag value:value`
- `key: URL like http://example.com/foo:bar` (the `://` is fine, but a path containing `:` after a space breaks)

## Deterministic debugging recipe

```bash
# 1. Reproduce against the local clone (rules out telemetry / network / cache issues).
cd /tmp && rm -rf dc-repro && mkdir dc-repro && cd dc-repro
npx --yes skills add /path/to/local/clone -y --all
# Confirm: exit 1, "No valid skills found".

# 2. Fetch / refresh the operative parser source.
opensrc fetch vercel-labs/skills
opensrc path vercel-labs/skills
# -> /Users/<user>/.opensrc/repos/github.com/vercel-labs/skills/main

# 3. Confirm the parser path against your reproduction.
grep -n "No valid skills found" \
  ~/.opensrc/repos/github.com/vercel-labs/skills/main/src/add.ts
sed -n '20,90p' ~/.opensrc/repos/github.com/vercel-labs/skills/main/src/skills.ts
cat ~/.opensrc/repos/github.com/vercel-labs/skills/main/src/frontmatter.ts

# 4. Re-parse the live SKILL.md frontmatter using the same `yaml` package the CLI uses.
#    The npx-cached install is at ~/.npm/_npx/<hash>/node_modules/yaml.
#    Find ANY skills install to source the package:
SKILLS_NPX=$(find ~/.npm/_npx -path '*/node_modules/skills' -type d 2>/dev/null | head -1)
YAML_PKG=$(dirname "$SKILLS_NPX")/yaml

node -e "
const { parse } = require('$YAML_PKG');
const fs = require('fs');
const txt = fs.readFileSync('/path/to/clone/skills/<name>/SKILL.md', 'utf8');
const m = txt.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
if (!m) { console.log('NO_FRONTMATTER_FENCES'); process.exit(2); }
try {
  const d = parse(m[1]);
  console.log('PARSE_OK');
  console.log('typeof name:', typeof d.name);
  console.log('typeof description:', typeof d.description);
} catch (e) {
  console.log('PARSE_ERROR:', e.message);
  console.log(e.stack.split('\n').slice(0, 6).join('\n'));
  process.exit(1);
}
"
```

The `node -e` block surfaces the literal scanner error verbatim. From there:
- `Nested mappings are not allowed in compact mappings at line N, column M` → quote the value on line N.
- `typeof name: undefined` or `typeof description: undefined` → frontmatter parsed but the field is missing or under a different key.
- `typeof name: object` (from `name: { something }`) → a nested map collapsed into the field.

## Canonical fix: quote the offending value

Smallest possible change. Don't refactor the value, don't shorten it, don't break it across lines:

```yaml
# BEFORE (rejected by yaml@2.x)
compatibility: Platform-agnostic. Requires Python 3.9+ for bundled scripts. Optional but recommended: vision-capable LLM access for the design-evaluator subagent ...

# AFTER (parses cleanly)
compatibility: "Platform-agnostic. Requires Python 3.9+ for bundled scripts. Optional but recommended: vision-capable LLM access for the design-evaluator subagent ..."
```

Re-verify end-to-end:

```bash
node -e "<above script with the patched file>"   # PARSE_OK + name/description string
cd /tmp && rm -rf dc-verify && mkdir dc-verify && cd dc-verify
npx --yes skills add /path/to/clone -y --all     # exit 0, "Found 1 skill", "Installed 1 skill"
```

## Style rule for SKILL.md authors

When a YAML frontmatter scalar contains ANY colon-space pattern (`: ` anywhere after the leading key separator), quote the entire value with double quotes. This is a one-line invariant that's easy to enforce in CI:

```bash
# add to repo CI: warn on any unquoted frontmatter line whose value contains colon-space
python3 -c "
import sys, re, yaml, pathlib
p = pathlib.Path('skills/<name>/SKILL.md')
txt = p.read_text()
m = re.match(r'^---\n(.*?)\n---\n', txt, re.S)
fm = m.group(1)
# strict yaml round-trip — any throw is a fail
try:
    yaml.safe_load(fm)
except Exception as e:
    print('FAIL pyyaml:', e); sys.exit(1)
# also check the strict yaml@2.x semantics: every top-level scalar with `: ` in its value must be quoted
for line in fm.splitlines():
    m2 = re.match(r'^([A-Za-z0-9_-]+):\s*(.+)$', line)
    if m2 and ': ' in m2.group(2) and not m2.group(2).startswith(('\"','\\''))):
        print('WARN unquoted colon-space in frontmatter line:', line); sys.exit(1)
print('OK')
"
```

(The repository's own `validate_skill.py` is line-regex based and does not enforce strict YAML 2.x semantics. Either patch it to call `js-yaml`/`yaml@2.x` via Node, or add a Node-based pre-commit hook. This is a future-work learning, not a blocker for shipping the fix.)

## Other failure modes (less common)

- **`data.name` is a number/boolean.** YAML happily parses `name: 0.1.0` as a float. The CLI rejects it (`typeof data.name !== 'string'`). Quote it: `name: "0.1.0"`. (Note: the skill's outer `name:` should be a slug, not a version. If you see this, the frontmatter was probably mis-edited.)
- **Internal skill flag set without `INSTALL_INTERNAL_SKILLS=1`.** `metadata.internal: true` makes `parseSkillMd` return `null` unless the env var is set or the user names the skill explicitly. Surfaces as the same "No valid skills found" error.
- **No frontmatter fences at all.** `parseFrontmatter` returns `{ data: {}, content: raw }` and the missing `name` / `description` makes `parseSkillMd` return `null`. Diagnostic: `head -1 SKILL.md` returns something other than `---`.
- **CRLF line endings on a fresh Windows clone.** The frontmatter regex is `^---\r?\n([\s\S]*?)\r?\n---\r?\n` so CRLF is fine, but BOM-prefixed `---` is not. `head -c 3 SKILL.md | od -c` should show `-` `-` `-`, not `357` `273` `277` `-`.

## Cross-references

- `references/firecrawl-cli-1-16-quirks.md` — for the `firecrawl scrape` JSON shape used to confirm `skills.sh/docs` and `skills.sh/docs/cli`.
- `references/research-tool-readiness.md` — for `opensrc fetch` patterns used to materialize the parser source.
- Pitfall #25 (Coding Agent Execution Contract) — same general lesson on YAML quoting strictness, applied to the goal Markdown rather than third-party SKILL.md files.
