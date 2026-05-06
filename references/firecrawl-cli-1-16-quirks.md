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

## 4. Background terminal sessions can lose `FIRECRAWL_API_KEY`

Symptom: `firecrawl map` exits `0` but the output file starts with the welcome banner ("Welcome! To get started, authenticate..."). `python3 -c "import json; json.load(...)"` then raises `JSONDecodeError: Expecting value: line 2 column 3`.

Cause: certain MCP/terminal backgrounding paths spawn the child without the parent's exported env.

Fix — pick one:

- Run `firecrawl map` calls in the **foreground**.
- Or explicitly carry the key: `FIRECRAWL_API_KEY="$FIRECRAWL_API_KEY" firecrawl map ...`.

Always immediately re-probe each map with the validator snippet in §2 before recording evidence in the YAML.

## 5. Leaf / docc / dynamic roots return only the seed URL

If a map's `data.links` length is `< 5` or just `[seed_url]`, you mapped a leaf page (e.g. `https://docs.example.com/api/SomeClass`). Re-map at a higher root (`/docs` or `/`) and cite the deep page via `firecrawl scrape <deep-url>` instead.

## 6. Rate / concurrency budget

`firecrawl --status` reports concurrency (e.g. `0/50 jobs`) and credits (e.g. `Credits: 133022 / 100000 (133% left this cycle)`). For a typical generator run, 6–10 maps + 5–10 scrapes is well under budget, but check the report before kicking off a large `crawl --depth 2`.

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

# Probe every scrape's markdown length
python3 -c "
import json, pathlib
for p in sorted(pathlib.Path('analysis/research/scrapes').glob('*.json')):
    d = json.loads(p.read_text())
    md = d.get('markdown') or d.get('data', {}).get('markdown', '')
    print(p.stem, 'len:', len(md))
"
```

Use this pattern verbatim for any goal-prompt-generator run that needs Firecrawl evidence.
