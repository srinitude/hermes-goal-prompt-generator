# Firecrawl 1.16.0 CLI quirks (observed during real generator runs)

These are the concrete CLI quirks I have hit while running the goal-prompt-generator's mandatory Firecrawl map + scrape evidence flow. Treat this as the operational supplement to `references/research-tool-readiness.md` and to pitfalls 14, 15, 22, 23 in SKILL.md.

## 1. Auth probe vs map shape

```bash
firecrawl --status     # only proves auth; NOT proof that any tool ran
firecrawl --version    # 1.16.0 at time of writing
```

`--status` exiting `0` is necessary but not sufficient. Always cite a real `firecrawl map` JSON file with `data.links` length and at least one real `firecrawl scrape` markdown body in `validation_evidence.firecrawl.evidence[]`.

## 2. `firecrawl map` JSON shape

```bash
firecrawl map https://<docs-root> --limit 5000 --json --pretty > research/url-maps/<tech>.json
```

Required output shape (top-level `success` + nested `data.links`, each link is an object):

```json
{
  "success": true,
  "data": {
    "links": [
      {"url": "https://...", "title": "...", "description": "..."}
    ]
  }
}
```

Validate with:

```python
import json
d = json.load(open("research/url-maps/<tech>.json"))
links = d.get("data", {}).get("links") or d.get("links") or []
assert len(links) > 5, "map looks empty/leaf — re-map a higher root"
```

If `head -3 <file>` shows `🔥 firecrawl cli` instead of `{"success": true,`, the run lost auth (see §4) — the file is the welcome banner, not JSON.

## 3. `firecrawl scrape` JSON shape

```bash
firecrawl scrape https://<page> --format markdown --json > research/scrapes/<page>.json
```

Note: the flag is `--format` **singular** (not `--formats`); the latter is rejected with `error: unknown option '--formats'`.

Required output shape (TOP-LEVEL `markdown` and `metadata`, *not* nested under `data`):

```json
{
  "markdown": "We use tracking cookies...",
  "metadata": { "title": "...", "sourceURL": "..." }
}
```

Defensive read:

```python
md = d.get("markdown") or d.get("data", {}).get("markdown", "")
```

The map shape and the scrape shape are *not* the same. Do not assume `data.X` everywhere.

### 3a. ⚠️ `Scrape ID:` prefix line breaks `json.load()` (observed 2026-05-06)

Firecrawl 1.16.0 prints a `Scrape ID: <uuid>` line to stdout **before** the JSON body whenever `firecrawl scrape ... --json` is redirected to a file. The resulting file looks like:

```
Scrape ID: 019dfe7e-ef5e-7088-a0e5-b5cee3122fd1
{"markdown":"...","metadata":{...}}
```

Calling `json.load(open(path))` blows up with `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`. This is NOT an auth-loss banner (§4) — the JSON body is right there on line 2, the `Scrape ID:` line is just status chatter that survived the redirect.

`firecrawl map` does **not** have this problem; only `scrape`. Map output is pure JSON.

Defensive parser (use this for every scrape file, every time):

```python
import json, pathlib, re
def load_scrape(path):
    txt = pathlib.Path(path).read_text()
    txt = re.sub(r'^(Scrape ID:[^\n]*\n)+', '', txt)
    return json.loads(txt)
```

Don't unconditionally `tail -n +2` — some firecrawl versions emit zero such lines and stripping line 1 unconditionally would corrupt those files. The regex strip handles both shapes.

### 3b. Treat scrape `metadata.statusCode` before trusting `markdown`

A successful `firecrawl scrape` exit `0` and a non-empty `markdown` body do NOT mean the page existed. Firecrawl renders the site's 404 page and returns it as markdown. Always check:

```python
meta = d.get("metadata") or d.get("data", {}).get("metadata") or {}
status = meta.get("statusCode")
if status != 200:
    raise RuntimeError(f"scrape returned HTTP {status} for {meta.get('sourceURL')}")
```

Observed examples during real generator runs: `https://git-scm.com/docs/git-subtree` → 404 (`Page doesn't exist`), `https://github.com/<org>/<repo>` (a literal repo home page on github.com) → 404 when scraped through Firecrawl. Cite a scrape only if `statusCode == 200`.

## 4. Background terminal sessions can lose `FIRECRAWL_API_KEY`

Symptom: `firecrawl map` exits `0` but the output file starts with the welcome banner ("Welcome! To get started, authenticate..."). `python3 -c "import json; json.load(...)"` then raises `JSONDecodeError: Expecting value: line 2 column 3`.

Cause: certain MCP/terminal backgrounding paths spawn the child without the parent's exported env.

Fix — pick one:

- Run `firecrawl map` calls in the **foreground**.
- Or explicitly carry the key: `FIRECRAWL_API_KEY="$FIRECRAWL_API_KEY" firecrawl map ...`.

Always immediately re-probe each map with the validator snippet in §2 before recording evidence in the YAML.

## 5. Leaf / docc / dynamic roots return only the seed URL

If a map's `data.links` length is `< 5` or just `[seed_url]`, you mapped a leaf page (e.g. `https://docs.example.com/api/SomeClass`). Re-map at a higher root (`/docs` or `/`) and cite the deep page via `firecrawl scrape <deep-url>` instead.

### 5a. `github.com/<org>/<repo>` returns 0 links

Mapping a repo's home page (e.g. `https://github.com/badlogic/pi-mono`) returns `success: true, data.links: []` — the GitHub UI is rendered behind interactive JS that Firecrawl's mapper can't follow. Don't waste a map call on a `github.com/<org>/<repo>` URL; instead:

- For repo source citations, use `opensrc fetch <org>/<repo>` and cite file paths under `validation_evidence.opensrc.fetched[<repo>].key_paths[]`.
- For doc sites that GitHub-Pages-host (e.g. `https://hono.dev/docs`), map the *docs domain*, not the repo.
- If you really need the README, `firecrawl scrape https://raw.githubusercontent.com/<org>/<repo>/<branch>/README.md` works because that URL serves plain markdown directly.

## 5b. Transient `EHOSTUNREACH` on Firecrawl's edge

During a real run on 2026-05-06, three of five `firecrawl map ... --json --pretty` calls returned exit `1` with:

```
Error: connect EHOSTUNREACH 35.245.250.27:443 - Local (192.168.50.66:53799)
```

A simple `sleep 3 && firecrawl map ...` retry succeeded for all three. Treat `EHOSTUNREACH` to `35.245.250.27:443` (Firecrawl's edge IP) as a transient network blip, not a permanent failure or auth issue. Bake retries into batched map runs:

```bash
for url in <list>; do
  for attempt in 1 2 3; do
    firecrawl map "$url" --limit 5000 --json --pretty > "research/url-maps/$(basename "$url").json" 2>&1 && break
    sleep 3
  done
done
```

## 6. Rate / concurrency budget

`firecrawl --status` reports concurrency (e.g. `0/50 jobs`) and credits (e.g. `Credits: 133022 / 100000 (133% left this cycle)`). For a typical generator run, 6–10 maps + 5–10 scrapes is well under budget, but check the report before kicking off a large `crawl --depth 2`.

## 6a. `extract` may not exist in Firecrawl CLI 1.16.0

During a real generator run on 2026-05-06, `firecrawl extract --help` printed the top-level help and did not list an `extract` subcommand. Do **not** fabricate extract evidence because the contract names the full Firecrawl toolset. Probe first; if unavailable, record it honestly in `validation_evidence.firecrawl.evidence[]`, e.g. `tool: extract`, `result: "CLI 1.16.0 lacks extract; downstream execution must use scrape/search/crawl or newer extract before claiming extract evidence."`, `cited_in_tasks: [A02]`.

## 6b. Small `crawl --wait` can still hang or time out

A minimal crawl such as `firecrawl crawl https://mise.jdx.dev/tasks --limit 1 --max-depth 0 --wait --timeout 60 --pretty --output ...` timed out locally despite successful map/scrape/search commands. Treat crawl as best-effort evidence unless it returns a usable JSON result. If it times out, record an attempted-but-not-claimed evidence entry instead of blocking the whole generator run when map + scrape + search + opensrc already validate the emitted URLs and source claims.

## 7. End-to-end pattern that worked

```bash
# Maps (foreground, --limit 5000 --json --pretty mandatory)
firecrawl map https://mastra.ai/docs --limit 5000 --json --pretty > analysis/research/url-maps/mastra.json
firecrawl map https://hono.dev/docs   --limit 5000 --json --pretty > analysis/research/url-maps/hono.json
# ... etc

# Probe every map immediately
python3 -c "
import json, pathlib
for p in sorted(pathlib.Path('analysis/research/url-maps').glob('*.json')):
    d = json.loads(p.read_text())
    links = d.get('data',{}).get('links') or d.get('links') or []
    print(p.stem, len(links))
"

# Scrapes (top-level shape; --format singular)
firecrawl scrape https://mastra.ai/docs/memory/overview --format markdown --json > analysis/research/scrapes/mastra-memory-overview.json

# Probe every scrape's markdown length using the same top-level-or-data fallback as §3.
python3 -c "import json,pathlib; [print(p.stem, 'len:', len((d:=json.loads(p.read_text())).get('markdown') or d.get('data',{}).get('markdown',''))) for p in sorted(pathlib.Path('analysis/research/scrapes').glob('*.json'))]"
```

Use this pattern verbatim for any goal-prompt-generator run that needs Firecrawl evidence.

## 8. When handoff output violates the current contract

The generator's final `/goal` line is executable handoff text for another agent, so it must stay synchronized with SKILL.md. In one real run, the helper's `handoff_prompt()` omitted `principle_ids` even though the canonical template required it. Correct workflow:

1. Patch the helper source, not just the chat output (currently `src/goal_prompt_generator/tasklist.py::handoff_prompt`).
2. Re-run Markdown validation on the generated `.md` and `scripts/validate_task_list_yaml.py` on the paired YAML.
3. Run `scripts/validate_skill.py <skill-dir>` before reporting completion.
4. Search the generated artifact directory to ensure the handoff line was not persisted into either generated artifact; it must only be emitted at runtime.
