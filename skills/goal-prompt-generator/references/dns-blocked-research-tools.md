# DNS-blocked research tools during goal prompt generation

Use this when goal-prompt-generator work involves browsing failures, provider sites being blocked, or Firecrawl/opensrc suddenly failing mid-run.

## Observed pattern

During a generation for local GitHub browsing reliability, GitHub and Hugging Face both became unreachable through the system resolver while unrelated hosts still resolved. Firecrawl and opensrc failures then looked like tool failures, but the root evidence pointed to local DNS/resolver policy.

Key symptoms:

- `firecrawl --status` may still show the CLI is authenticated, but also report account-fetch/network failures.
- `firecrawl map` / `scrape` may fail with `getaddrinfo ENOTFOUND api.firecrawl.dev`.
- `opensrc fetch github/docs` may fail because `api.github.com` cannot resolve.
- System resolver can fail selected hosts while public resolvers (`1.1.1.1`, `8.8.8.8`) resolve them.
- Hermes `security.website_blocklist.enabled: false` and empty domains means Hermes is not the likely blocker.

## Third failure mode: TCP handshake completes but HTTPS is RST mid-stream (selective L7 firewall)

Observed during a Daytona-backed goal-prompt-generator run on 2026-05-07 against `api.firecrawl.dev` (35.245.250.27:443). Distinct from §1 (DNS not resolving) and from `references/firecrawl-cli-1-16-quirks.md` §5b (transient `EHOSTUNREACH`).

Symptoms:

- `getent hosts api.firecrawl.dev` → resolves fine.
- `python3 -c "import socket; socket.create_connection(('api.firecrawl.dev', 443), timeout=4).close()"` → exits 0 in <1s.
- `curl -v https://api.firecrawl.dev/` → `Recv failure: Connection reset by peer`, exits 35.
- `python3 -c "import ssl, socket; ssl.create_default_context().wrap_socket(socket.create_connection(('api.firecrawl.dev', 443)), server_hostname='api.firecrawl.dev')"` → `[Errno 104] Connection reset by peer`.
- Simultaneously: `github.com`, `api.github.com`, `huggingface.co`, `docs.railway.com`, `api.openai.com`, `api.anthropic.com` all return 200/401/404 — i.e. a generic-internet-works diagnosis.
- `firecrawl --status` reports `Authenticated via FIRECRAWL_API_KEY` AND `Could not fetch account info: fetch failed` on the same call. The CLI parses the env var and prints "authenticated" before any HTTP request, then the actual request RSTs.
- Retries with `sleep 3`/`sleep 5` between attempts produce identical RST every time — this is **persistent**, not the §5b transient blip.

Root cause hypothesis: an upstream firewall is doing L7 / SNI-based filtering on the Firecrawl edge IP from this network egress. Common in Daytona / sandboxed-CI / corporate-egress environments. It is NOT a Firecrawl outage and NOT an auth issue.

Probe to distinguish from the other failure modes:

```bash
python3 - <<'PY'
import socket, ssl, time
HOST = 'api.firecrawl.dev'
t0 = time.time()
try:
    s = socket.create_connection((HOST, 443), timeout=4)
    print(f'TCP_OK {HOST}:443 in {time.time()-t0:.2f}s')
except Exception as e:
    print(f'TCP_FAIL {HOST}: {type(e).__name__}: {e}')
    raise SystemExit
t0 = time.time()
try:
    ctx = ssl.create_default_context()
    ss = ctx.wrap_socket(s, server_hostname=HOST)
    print(f'TLS_OK in {time.time()-t0:.2f}s')
    ss.close()
except Exception as e:
    print(f'TLS_FAIL ({type(e).__name__}: {e}) — looks like selective L7 firewall RST, NOT DNS, NOT transient.')
PY
```

If TCP_OK + TLS_FAIL with `Connection reset by peer`, AND non-Firecrawl HTTPS hosts work, you have the L7-RST failure mode. Encoding in YAML:

```yaml
validation_evidence:
  firecrawl:
    auth: unavailable                     # ← exact literal validator expects
    cli_version: "1.16.x"
    required_maps_present: {}             # MUST be empty when auth=unavailable
    evidence:
      - tool: status
        result: >
          firecrawl --status reports 'Authenticated via FIRECRAWL_API_KEY' but every actual
          map/scrape API request RSTs (Connection reset by peer on 35.245.250.27:443). TCP
          handshake succeeds; HTTPS layer is selectively blocked by upstream firewall on this
          backend's egress. Per references/dns-blocked-research-tools.md, recorded as
          unavailable for source validation.
        captured_at: "<iso>"
        cited_in_tasks: [A05, B03]
    execution_time_required:              # canonical command templates the agent re-runs
      - target: "https://docs.railway.com/"
        command_template: "FIRECRAWL_NO_TELEMETRY=1 firecrawl map https://docs.railway.com/ --limit 5000 --json --pretty"
        output_path: "~/.hermes/goal-prompts/research/url-maps/railway.json"
        validate_with: "python3 -c \"import json; d=json.load(open('railway.json')); assert len(d.get('data',{}).get('links',[]))>0\""
        cited_in_tasks: [A05, B03]
```

The validator (`scripts/validate_task_list_yaml.py`) accepts `auth: unavailable` + empty `required_maps_present: {}` + non-empty `execution_time_required[]`; it rejects `auth: authenticated` + empty `required_maps_present: {}` (you can't claim authenticated and have no maps). Don't reach for `auth: authenticated` just because the API key parsed — base it on whether actual map requests succeeded.

When this happens during a generation pass, ALSO add a top-level Phase-0 task to switch the active terminal backend to a network where Firecrawl's edge is reachable (typically local) before validation re-runs. The downstream agent must complete that switch before promoting any `execution_time_required[]` entry to populated evidence.

## Probe matrix before claiming tool availability or provider-specific blocking

Run non-mutating diagnostics only:

```bash
python3 - <<'PY'
import os, socket
hosts = [
  'github.com', 'api.github.com', 'docs.github.com',
  'huggingface.co', 'status.huggingface.co', 'cdn-lfs.huggingface.co',
  'api.firecrawl.dev', 'google.com', 'cloudflare-dns.com',
]
for host in hosts:
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        addrs = sorted({item[4][0] for item in infos})
        print(f'DNS_OK {host} {addrs[:4]}')
    except Exception as exc:
        print(f'DNS_FAIL {host} {type(exc).__name__}: {exc}')
print('PROXY_ENV', {k: os.environ.get(k) for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy'] if os.environ.get(k)})
PY

python3 - <<'PY'
from pathlib import Path
for i, line in enumerate(Path('/etc/hosts').read_text(errors='replace').splitlines(), 1):
    if any(term in line.lower() for term in ['github', 'huggingface', 'firecrawl']):
        print(f'{i}: {line}')
PY

scutil --dns 2>/dev/null | sed -n '1,120p' || true

for host in github.com huggingface.co api.firecrawl.dev google.com; do
  for resolver in 192.168.50.1 1.1.1.1 8.8.8.8 100.100.100.100; do
    printf '%s @%s: ' "$host" "$resolver"
    dig +time=3 +tries=1 +short @"$resolver" "$host" 2>&1 | head -5 | tr '\n' ' '; printf '\n'
  done
done
```

## How to encode in generated artifacts

- Do not claim Firecrawl map/scrape/extract or opensrc evidence completed if DNS prevented the tool from reaching its API or target host.
- Record completed maps separately from failed follow-up `scrape`/`extract` attempts.
- Add an ANALYSIS task to reproduce the DNS matrix before remediation.
- Treat provider docs/status/source validation as execution-time required once DNS is restored.
- If multiple unrelated developer/AI sites fail (for example GitHub + Hugging Face), broaden the generated goal from site-specific repair to shared local DNS/resolver/proxy/VPN/content-filter diagnosis.

## Common cause hypotheses to keep non-destructive

Prioritize evidence for these before changes:

- router/upstream DNS filtering or `SERVFAIL`,
- Tailscale/MagicDNS/split-DNS behavior (`100.100.100.100`),
- proxy/VPN/firewall/content-filter settings,
- stale local DNS cache,
- certificate/time problems,
- browser-profile extension/content-blocker behavior.

Never reset browser profiles, delete cookies broadly, change router/Tailscale/DNS policy, or disable security tooling without explicit approval after reversible backup and evidence.
