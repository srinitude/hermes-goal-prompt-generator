# Principle-ID Wiring + Evidence Construction (Positive Pattern)

Two complementary patterns observed during real generation runs that the SKILL.md
pitfalls describe only in failure-mode terms. This file captures the positive,
deterministic construction patterns so future runs don't have to re-derive them.

---

## 1. Principle-ID wiring: canonical P-id → task-family mapping

When the structural validator fails with `principles: unused ids [...]` (pitfall
#50), the skill body says to "wire each orphan into existing tasks where it
actually fits." The mapping below is the canonical table — use it before
considering option (b) "add a small synthetic task" or option (c) "remove the
unused id," both of which are last-resort.

The 18 software-engineering core principles fall into recurring families that
recur across almost every software goal. Map orphan P-ids by **what the task
fundamentally validates**, not by surface keyword match.

| P-id | Principle (short) | Wires into task families that … |
|------|-------------------|--------------------------------|
| P1   | Programs as descriptions before execution | declare workflows, runtime contracts, execution plans, supervisors |
| P2   | Expected failure as domain model | model auth-failure, validation-failure, rate-limit, OAuth denied/cancelled |
| P3   | Recoverable failures vs defects | classify errors, fail-fast paths, error-state UI, defect telemetry |
| P4   | Preserve failure causes | structured error types, telemetry/circuit-breaker, cause chains, log enrichment |
| P5   | Resource lifecycle ownership | Effect.Scope, browser sessions, temp files, fixtures, generation supervisors |
| P6   | First-class cancellation | cancel buttons, abort handlers, request handler timeouts, long-running canvas/agent work |
| P7   | Structured concurrency | parent/child fiber ownership, supervised work, no untracked async |
| P8   | Push dependencies to boundary | contract types, interface-based services, capability injection |
| P9   | Clean service interfaces | small components, modular UI, configuration assembly outside core APIs |
| P10  | Validate data at boundaries | Zod/Effect-Schema parsing, request validation, contract types, fixture parsers |
| P11  | Typed-validated-redacted config | env parsing, secret handling, config startup checks, Settings pages |
| P12  | Timeout/retry/idempotency on external calls | LLM calls, payment APIs, webhook delivery, integration OAuth |
| P13  | **Measurement-driven optimization** | telemetry primitives, observability dashboards, **visual regression baselines**, performance budgets |
| P14  | Observability not afterthought | structured logging, request-id propagation, tracing, audit transcripts |
| P15  | Deliberate caching with invalidation | Mastra session reads, semantic-recall cache, parity-harness cache, library caching |
| P16  | Coordinate shared-state updates | bounded queues, index writes, single-writer policies, transactions |
| P17  | Compose small units into workflows | aggregator tasks, parametric routes, design-system primitives, navigation graphs |
| P18  | Provider-shape isolation | LLM/payment/storage/auth contracts, vendor API hidden behind internal types |

### Lookup recipe (canonical):

```python
import yaml
y = yaml.safe_load(open('<path>.yaml').read())

declared = set(y.get('principles', {}).keys())
referenced = set()
for ph in y.get('phases', []):
    for t in ph.get('tasks', []):
        referenced.update(t.get('principle_ids', []))

orphans = sorted(declared - referenced)
print('orphans:', orphans)
```

### Wiring recipe (single cell, no `mcp_patch` flake risk):

```python
TARGETS = {
    'P13': ['G25', 'G30'],   # telemetry primitives + visual regression baselines
    'P15': ['G24', 'G28'],   # caching with invalidation
    'P16': ['G28'],          # serialize shared-state updates
    # ... add per-orphan based on the table above
}
green = next(p for p in y['phases'] if p['name'] == 'GREEN')
fixed = []
for t in green['tasks']:
    for orphan, ids in TARGETS.items():
        if t['id'] in ids and orphan not in t['principle_ids']:
            t['principle_ids'] = list(t['principle_ids']) + [orphan]
            fixed.append((t['id'], orphan))
print('fixed:', fixed)
open('<path>.yaml', 'w').write(yaml.safe_dump(y, sort_keys=False, allow_unicode=True, width=1000))
```

Re-run `validate_task_list_yaml.py` immediately after; expect `OK: N tasks, 18
principles`.

### Anti-pattern: synthetic "validate this principle" tasks

Avoid `T("X99", "Validate principle PXX is honored", ...)` to silence the
validator. The validator passes, but the task ledger is now polluted with a
content-free row that the downstream agent has to skip. Always prefer the
mapping table above.

---

## 2. Evidence construction: positive pattern (build, don't trim)

Pitfall #47's May-2026 addendum warns that the helper baseline dumps EVERY
cached URL map (often 70+) into `required_maps_present` regardless of relevance,
and instructs you to "trim to ONLY the techs named in the spec." In practice,
**building from scratch** is faster and produces cleaner evidence than trimming.

### Recipe (live `firecrawl map` for the 5–8 techs actually named in the goal)

```python
import os, json, subprocess
from pathlib import Path

URL_MAPS_DIR = "/Users/kiren/.hermes/goal-prompts/research/url-maps"
os.makedirs(URL_MAPS_DIR, exist_ok=True)

# Pick docs roots from the SPEC, not from the helper baseline.
TARGETS = [
    ("next-docs",       "https://nextjs.org/docs"),
    ("react-docs",      "https://react.dev"),
    ("bun-docs",        "https://bun.sh/docs"),
    ("mastra-docs",     "https://mastra.ai/docs"),
    ("effect-docs",     "https://effect.website"),
    ("playwright-docs", "https://playwright.dev/docs"),
]

required_maps_present = {}
for name, url in TARGETS:
    out_path = f"{URL_MAPS_DIR}/{name}.json"
    # NOTE: macOS has no `timeout` builtin; rely on subprocess timeout instead.
    proc = subprocess.run(
        ["firecrawl", "map", "--json", "--pretty", "--limit", "5000", url],
        capture_output=True, text=True, timeout=120, env=os.environ.copy(),
    )
    Path(out_path).write_text(proc.stdout)
    # Strip any leading banner before the first '{' (firecrawl-cli-1-16-quirks §3a)
    txt = proc.stdout
    i = txt.find("{")
    data = json.loads(txt[i:]) if i >= 0 else {}
    url_count = len(data.get("data", {}).get("links", []))
    required_maps_present[name] = {
        "file": out_path,
        "url_count": url_count,
        "map_command": f"firecrawl map --json --pretty --limit 5000 {url}",
        "map_limit": 5000,
    }
    assert url_count > 0, f"map {name} returned 0 links — refuse to write"
```

Then drop `required_maps_present` straight into
`validation_evidence.firecrawl.required_maps_present` in the YAML you build
from a Python dict (programmatic-yaml-rebuild pattern).

### Why this is better than trimming

- The helper baseline `required_maps_present` has `map_command:
  "cache-inspected; refresh with firecrawl map ..."` — a downstream agent
  reading that thinks the map is stale and may re-run unnecessarily.
- Building from scratch lets you set `auth: authenticated` honestly because you
  have a live banner + a live `data.links` populated array (pitfall #34).
- The 5–8 maps you actually need cost ~20s total; trimming a 70-entry baseline
  takes the same time mentally and leaves stale `cache-inspected` provenance.

### Companion: opensrc.fetched positive construction

```python
from pathlib import Path

CANDIDATES = {
    "vercel/next.js": ("canary", [
        "/Users/kiren/.opensrc/repos/github.com/vercel/next.js/canary/packages/next/package.json",
        "/Users/kiren/.opensrc/repos/github.com/vercel/next.js/canary/packages/next/src/server/app-render/app-render.tsx",
    ]),
    # ... one entry per spec-named OSS dep
}

fetched = {}
for slug, (branch, paths) in CANDIDATES.items():
    verified = [p for p in paths if Path(p).exists()]
    if not verified:
        # Cache miss — `opensrc fetch <slug>` then re-verify.
        subprocess.run(["opensrc", "fetch", slug], timeout=180, check=False)
        verified = [p for p in paths if Path(p).exists()]
    fetched[slug] = {
        "branch": branch,
        "path": str(Path(verified[0]).parents[2]) if verified else "",
        "cache_busted": False,
        "key_paths": verified,
        "rationale": "<one-line on why this dep matters to the goal>",
    }
```

Every `key_paths[]` entry is verified with `Path(p).exists()` before write
(pitfall #43, #47): real on-disk paths only, no help-text / schema /
signature observations (those go into `rationale` or a sibling
`signatures_observed` field).

---

## 3. Quick checklist (apply before writing the YAML)

- [ ] Walked the P-id table above; every declared `P*` appears in ≥1 task's
      `principle_ids` BEFORE first validator run.
- [ ] Built `required_maps_present` from live `firecrawl map` calls for the
      5–8 techs actually named in the goal — not trimmed from helper dump.
- [ ] Built `opensrc.fetched` with `Path(p).exists()`-verified `key_paths[]`
      for every spec-named OSS dep.
- [ ] `validation_reconciliation.conflicts[]` records each helper-baseline
      override (auth, fetched, required_maps_present, key_paths, task count) as
      `corrected_in_yaml` with severity `info` or `warn`.
- [ ] Contrarian pass run **dry-run only** (per pitfall #43 generalization);
      write-back would clobber historical reconciliation entries.
