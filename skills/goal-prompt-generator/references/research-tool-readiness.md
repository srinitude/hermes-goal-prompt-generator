# Research Tool Readiness During Goal Prompt Editing

When a generated goal prompt requires a specific research or validation tool (for example Firecrawl `map --limit 5000`, `opensrc`, or provider docs scraping), distinguish **prompt-generation evidence** from **future goal-execution requirements**.

## Pattern

1. Probe the requested tool before saying it was used.
   - Firecrawl example: `FIRECRAWL_NO_TELEMETRY=1 firecrawl --status`.
   - If mapping is required, run a small/auth-checking map command or verify credentials are available.
   - Firecrawl CLI may exit `0` while printing an auth/setup prompt such as "Welcome! To get started, authenticate..." instead of map JSON. Treat that as **not usable** for source validation and do not claim mapping succeeded.
2. If the tool is usable, record the mapped source requirement normally in the generated prompt.
3. If the tool is unavailable or unauthenticated, keep the tool requirement in the prompt as an execution-time validation requirement, but do not label alternate discovery as tool-validated.
4. If you use another lookup mechanism to seed targets, label it honestly, e.g. `initial_discovery_evidence: "web_search result; validate with Firecrawl map: ..."`.
5. If the user directly supplies an additional target URL, add it without inventing discovery evidence and label it as user-provided, e.g. `initial_discovery_evidence: "user-provided target; validate with Firecrawl map: <name> documentation at <url>"`.
6. When an existing valid generated prompt contains duplicated preserved original-intent sections, apply list additions and requirement edits to every semantically duplicated location, then validate once in place.
7. Avoid broad `replace_all` patches anchored only on generic Markdown delimiters such as ``` or `---`; they can insert the same requirement after every code fence. Patch around unique headings or surrounding sentences, then search for the inserted phrase and remove duplicates before validation.
8. Run the in-place validator after edits to ensure the generated Markdown contract still passes.

## Pitfall Example

Bad phrasing when Firecrawl is unauthenticated:

```yaml
official_source_evidence: "Firecrawl search result: Claude Code overview"
```

Better phrasing:

```yaml
initial_discovery_evidence: "web_search result; validate with Firecrawl map: Claude Code overview"
```

User-provided target phrasing:

```yaml
initial_discovery_evidence: "user-provided target; validate with Firecrawl map: Pi documentation at https://pi.dev"
```

This preserves the user's requested Firecrawl requirement without falsely claiming Firecrawl was available during prompt editing.

## When the helper baseline says `auth: unavailable` but the live probe says authenticated

Confirmed pattern (May 2026 generation runs from `mcp_execute_code` on macOS host): the helper-emitted YAML can write `validation_evidence.firecrawl.auth: unavailable` even when Firecrawl is genuinely usable. Two independent root causes:

1. **`_firecrawl_auth()` banner-parse over-cautious / pitfall #34 false-negative shape.** The helper prefers to downgrade on any banner imperfection. If the live `firecrawl map ... --json --pretty --limit 5000` returns a populated `data.links` array, trust the live probe.

2. **`mcp_execute_code` does not inherit `set -gx` fish global vars into the python child's `os.environ`.** Even with `subprocess.run(..., env=os.environ.copy())`, `FIRECRAWL_API_KEY` may be missing because the parent python process never had it. Confirm with `print('FIRECRAWL_API_KEY' in os.environ)` — if False, the helper subprocess shows the same.

### Recipe to recover

```python
# 1. Live probe first — exit 0 + url_count > 0 means authenticated regardless of helper baseline.
import subprocess, json
p = subprocess.run(
    ["python3", "/Users/kiren/.hermes/skills/software-development/goal-prompt-generator/scripts/probe_firecrawl_reachability.py"],
    capture_output=True, text=True, timeout=60,
)
probe = json.loads(p.stdout)
assert probe["live_map_probe"]["ok"] and probe["live_map_probe"]["url_count"] > 0

# 2. If python's os.environ lacks the key, parse it out of the fish config directly.
import pathlib, os
env = os.environ.copy()
if "FIRECRAWL_API_KEY" not in env:
    for line in (pathlib.Path.home() / ".config/fish/config.fish").read_text().splitlines():
        s = line.strip()
        if s.startswith("set -gx FIRECRAWL_API_KEY"):
            parts = s.split()
            if len(parts) >= 4 and parts[3].startswith("fc-"):
                env["FIRECRAWL_API_KEY"] = parts[3]
                break
    assert "FIRECRAWL_API_KEY" in env, "no key in env or fish config"

# 3. Run the maps with the recovered env.
subprocess.run(["firecrawl", "map", url, "--json", "--pretty", "--limit", "5000"],
               env=env, capture_output=True, text=True, timeout=180)

# 4. Override the helper's auth: unavailable in the YAML directly.
y["validation_evidence"]["firecrawl"]["auth"] = "authenticated"
y["validation_evidence"]["firecrawl"]["auth_evidence"] = (
    "live probe via probe_firecrawl_reachability.py: tcp/tls ok; live_map_probe url_count=<N>; "
    "FIRECRAWL_API_KEY parsed from fish global config and threaded into helper subprocess env"
)
```

DO NOT use `subprocess.Popen` with a file-redirected stdout if you want the env to flow correctly through nested wrappers — `capture_output=True` (or `stdout=subprocess.PIPE`) is more reliable. The 493-byte banner JSON file is the diagnostic giveaway that the child saw an interactive auth prompt instead of the API key.

## `opensrc`: probe `list` before claiming `path`/`fetch` failed

`opensrc 0.7.x` has a known failure mode where `opensrc path <org>/<repo>` and `opensrc fetch <org>/<repo>` can return:

```
Error: error sending request for url (https://api.github.com/repos/<org>/<repo>)
```

even when the repo IS already cached locally under `~/.opensrc/repos/<host>/<org>/<repo>/<ref>/`. The `path`/`fetch` subcommands hit the GitHub API to resolve metadata BEFORE checking the cache, so a transient `api.github.com` blip looks like a hard failure.

Always probe `opensrc list` first:

```bash
opensrc list 2>&1 | grep -F "<org>/<repo>"
# Example output:
#   github.com/badlogic/pi-mono@main
#     Path: /Users/kiren/.opensrc/repos/github.com/badlogic/pi-mono/main
```

If the repo appears in `opensrc list`, use the path directly from the list output and treat the `path`/`fetch` API error as transient. Only after `opensrc list` confirms the repo is **not** cached should you treat the API error as a real fetch failure (and either retry, switch to `firecrawl scrape` of the raw README, or record the source as unavailable).

Concrete pattern:

```bash
REPO=github.com/badlogic/pi-mono
SRC_PATH=$(opensrc list 2>&1 | awk -v r="$REPO" '$0 ~ r"@" {found=1; next} found && /^ +Path:/ {print $2; exit}')
if [ -z "$SRC_PATH" ]; then
  opensrc fetch "$REPO" || { echo "opensrc unavailable; record as execution-time validation"; exit 1; }
  SRC_PATH=$(opensrc path "$REPO")
fi
echo "source at $SRC_PATH"
```
