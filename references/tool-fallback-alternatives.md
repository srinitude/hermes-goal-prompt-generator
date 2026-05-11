# Tool fallback alternatives (research + source validation)

The skill's contract requires Firecrawl and `opensrc` for research and source
validation when the goal references real technologies. When those tools are
unavailable on the installer's machine, the skill must degrade honestly —
record the requirement as an execution-time validation requirement instead
of silently claiming the tool was used.

This reference documents valid alternatives.

## Why fallbacks matter

`firecrawl` (the documentation mapper / scraper) and `opensrc` (the
source-of-truth fetcher for open-source repos) are the only two external
tools the skill calls during generation. Both can be missing because:

- the installer didn't authenticate Firecrawl (`FIRECRAWL_API_KEY` not set),
- the installer is running on a host where `opensrc` is unavailable,
- network is blocked (Daytona / Modal / sandboxed remote runtime),
- the user explicitly opted out.

The non-execution guardrail still holds: the skill writes a contract, it
doesn't run it. But the YAML's `validation_evidence` block must not lie
about which tool was used.

## Firecrawl fallbacks

| Mode | What to do | Honest evidence shape |
| --- | --- | --- |
| Authenticated + reachable | `firecrawl map --limit 5000 --json --pretty <docs-root>` then `firecrawl scrape --format markdown --json <url>` per cited URL | `validation_evidence.firecrawl: {cli_version, auth: "authenticated", url_maps_root, required_maps_present: {<tech>: {file, url_count, map_command, map_limit: 5000}}}` |
| Authenticated banner only (cached) | Cite the cache, do NOT claim a fresh map ran | `validation_evidence.firecrawl: {cli_version, auth: "cache-only", required_maps_present: {<tech>: {file: "<path>", url_count: <int>, note: "verified from cached map; refresh required at execution time"}}}` |
| Unauthenticated / banner shows login prompt | Treat as **not usable** — do not claim any map/scrape ran | `validation_evidence.firecrawl: {cli_version, auth: "unauthenticated", required_maps_present: {<tech>: {note: "execution-time validation required: run firecrawl --status, then map --limit 5000 <docs-root>"}}}` |
| CLI absent | Same as unauthenticated | `validation_evidence.firecrawl: {cli_version: "absent", auth: "absent", ...}` |
| L7 RST / corporate firewall | Use `scripts/probe_firecrawl_reachability.py` to record the actual TCP+TLS+API state | `validation_evidence.firecrawl: {... probe: {tcp: "ok", tls: "ok", live_map_probe: {ok: false, reason: "..."}}}` |

### Alternative crawlers (when Firecrawl is unavailable AND a fresh map is required)

These are documented alternatives — the skill does NOT automatically switch
to them, because their output shapes differ from Firecrawl's and the
validator only knows Firecrawl's. When you use one of these, label discovery
honestly as `validation_evidence.alternative_research_tool`:

| Tool | When | Notes |
| --- | --- | --- |
| `wget --recursive --level=2 --no-parent <docs-root>` | Static doc sites with predictable URL structure | Captures full HTML; pair with `pandoc` for markdown. No JS execution. |
| `curl <docs-root>/sitemap.xml` + parse | Doc sites that publish a sitemap (Mintlify, Docusaurus) | Cheapest URL discovery; no scraping. Recipe: `xmllint --xpath '//*[local-name()="loc"]/text()' sitemap.xml`. |
| `markdown-crawler` / `markitdown` | Sandbox runtimes that ship Python but no Firecrawl | Slower than Firecrawl, no JS execution. |
| Browser MCP / `mcp_browser_navigate` | When the doc site requires JS rendering | Limited throughput; use only for spot-checking a handful of URLs. |
| `web_search` + targeted `web_extract` | When you only need 3–5 specific URLs | Faster than crawling for sparse validation; record cited URLs verbatim. |

In every case, the YAML's `validation_evidence.firecrawl.required_maps_present`
stays absent for that technology and the validator-honest phrasing is
`"firecrawl unavailable; alternative discovery via <tool> with N cited URLs;
execution-time validation must run firecrawl map --limit 5000 <docs-root>
once authenticated"`.

## `opensrc` fallbacks

| Mode | What to do | Honest evidence shape |
| --- | --- | --- |
| Available + repo cached | Cite `<repo>/<file>:<line>` for every API/version assertion | `validation_evidence.opensrc: {cli_version, cache_root, fetched: {<slug>: {key_paths: [...]}}}` |
| Available + repo not cached | Run `opensrc fetch <org>/<repo>`, then cite | Same as above. |
| Available + network blocked | Cite the cache only; flag that the cached SHA may be stale | `validation_evidence.opensrc: {cli_version, fetched: {<slug>: {key_paths: [...], note: "verified against cached <slug>; refresh required at execution time"}}}` |
| `opensrc` absent | Do NOT claim source-grounded validation | `validation_evidence.opensrc: {cli_version: "absent", required_repos: [<slug>, ...], note: "execution-time validation required: opensrc fetch <slug> + cross-check key paths"}` |

### Alternative source fetchers (when `opensrc` is unavailable)

The skill never silently swaps in one of these — they have different cache
semantics and version-pinning behavior. When you use one, label discovery
honestly as `validation_evidence.alternative_source_tool`:

| Tool | When | Notes |
| --- | --- | --- |
| `gh repo clone <org>/<repo>` | `gh` is authenticated, network OK | No version pinning. Capture the commit SHA at clone time. |
| `git clone --depth 1 https://github.com/<org>/<repo>` | `gh` unavailable, plain `git` OK | Shallow clone; can't `git log` for older versions. |
| `npm view <pkg> repository.url` + `git clone` | Validating npm packages whose repo URL isn't in opensrc | Pair with `npm pack <pkg>` to inspect published artifacts. |
| `pip download <pkg> --no-deps` + unpack | Validating Python packages | Inspect the wheel's `METADATA` and `RECORD`. |
| `cargo vendor` | Validating Rust packages | Captures the exact pinned crate. |
| Web-based source viewer (`web_extract https://github.com/<org>/<repo>/blob/<ref>/<path>`) | One-off citation, no clone needed | Costs Firecrawl credits or hits GitHub's rate limit; do not loop. |

In every case, the YAML's `validation_evidence.opensrc.fetched` stays absent
for that repo and the validator-honest phrasing is `"opensrc unavailable;
alternative source fetch via <tool> at <SHA>; execution-time validation must
run opensrc fetch <slug> + cross-check key paths"`.

## Probing readiness BEFORE writing evidence

Two scripts ship with the skill specifically for honest readiness probing:

- `scripts/probe_firecrawl_reachability.py` — distinguishes the four
  Firecrawl reachability modes (CLI absent / env-var unparsed /
  banner-authenticated-but-API-blocked / truly authenticated). Exits 0 only
  when a real `firecrawl map ... --limit 5000 --json --pretty` returns a
  populated `data.links` array.
- `scripts/validate_source_claims.py` — pre-flight verifier for opensrc repo
  caches, cited file paths, host reachability (TCP and TLS separately, so
  selective L7 firewall RST is detectable), Firecrawl usability, and helper
  presence BEFORE the generator writes any artifact.

Run both on every generation pass that names ≥1 opensrc repo or ≥1
Firecrawl-validated technology. Fabrication is the most expensive failure
mode for a generated goal.

## Continuity invariant (every fallback)

Switching research/source tools never weakens the **non-execution
guardrail** or the **GoalManager continuation contract**:

- The skill, the helper script, and every code path that produces artifacts
  MUST NEVER instantiate `/goal`, dispatch a goal run, push the handoff line
  back into Hermes Agent's command bus, or otherwise act on the handoff.
- Every non-final assistant response on a `/goal` execution turn must still
  end with `GOAL_RUNTIME_STATUS: CONTINUE — next autonomous step queued`
  plus the next YAML task id, regardless of which research/source tool was
  used.

## Cross-references

- `references/research-tool-readiness.md` — handling requested
  Firecrawl/source-validation requirements without falsely claiming
  unavailable tooling was used.
- `references/dns-blocked-research-tools.md` — provider websites or research
  tools failing due to local DNS/resolver behavior; non-mutating DNS matrix
  and validation-honesty wording.
- `references/remote-backend-helper-unavailable.md` — Hermes terminal
  execution in Daytona or another remote backend; fallback workflow using
  `skill_view()` support-file content, local validators, honest
  research-tool evidence, and the same final handoff contract.
- `references/firecrawl-cli-1-16-quirks.md` — concrete CLI quirks (map vs
  scrape JSON shape, `--format` singular, background-shell auth-loss, leaf-
  root detection, missing `extract`, crawl timeout honesty, handoff drift
  fixes, end-to-end working pattern).
- `references/executor-fallbacks-and-model-selection.md` — the parallel
  catalog for **coding-agent CLI** fallbacks (Claude Code, Codex, OpenCode,
  Gemini, Cursor, Aider, Pi, Qwen, Goose, Amp, Crush, Hermes) and the
  Hermes-as-executor model-selection rule.
