#!/usr/bin/env python3
"""Deterministic Firecrawl reachability probe.

Distinguishes the four failure modes the skill cares about:
  1. CLI absent          (PATH does not contain `firecrawl`)
  2. Env-var unparsed    (`firecrawl --status` reports `Not authenticated`)
  3. L7-RST blocked      (status banner says `Authenticated` BUT also
                          `Could not fetch`/`fetch failed`/`ECONNRESET`/
                          `Connection reset`; map call returns ECONNRESET)
  4. Truly authenticated (`firecrawl map https://docs.firecrawl.dev
                          --limit 5000 --json --pretty` writes a non-empty
                          JSON file with `data.links` populated)

Exit codes:
  0 — truly authenticated, real maps available
  1 — honest unavailability (any of modes 1-3); preserve as
      execution-time validation in the YAML
  2 — usage / unexpected error

This script is what `_firecrawl_auth()` in src/goal_prompt_generator/research.py
should behaviorally agree with. Run it before generating a goal prompt YAML
to confirm the right `auth:` value will land.
"""
from __future__ import annotations

import json
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
from pathlib import Path

FAILURE_SIGNALS = ("Could not fetch", "fetch failed", "ECONNRESET", "Connection reset")


def _run(args: list[str], timeout: int = 30) -> tuple[int | None, str]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:  # pragma: no cover
        return None, str(exc)
    return result.returncode, (result.stdout + result.stderr).strip()


def _tcp_tls_probe(host: str, port: int = 443, timeout: float = 10.0) -> dict:
    out: dict[str, object] = {"host": host, "port": port}
    try:
        addr = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
        out["dns"] = addr
    except Exception as exc:
        out["dns_error"] = repr(exc)
        return out
    try:
        sock = socket.create_connection((addr, port), timeout=timeout)
        out["tcp"] = "ok"
    except Exception as exc:
        out["tcp_error"] = repr(exc)
        return out
    try:
        ctx = ssl.create_default_context()
        wrapped = ctx.wrap_socket(sock, server_hostname=host)
        wrapped.send(b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\nConnection: close\r\n\r\n")
        data = wrapped.recv(64)
        wrapped.close()
        out["tls"] = "ok"
        out["first_bytes"] = data[:32].decode("latin-1", "replace")
    except Exception as exc:
        out["tls_error"] = repr(exc)
    return out


def _classify_status(code: int | None, banner: str) -> tuple[str, str]:
    if code != 0:
        return "unavailable", f"firecrawl --status exit {code}"
    if "Not authenticated" in banner:
        return "unavailable", "no FIRECRAWL_API_KEY"
    if "Authenticated" not in banner:
        return "unavailable", "status banner missing 'Authenticated' marker"
    for signal in FAILURE_SIGNALS:
        if signal in banner:
            return "unavailable", f"banner reports failure signal: {signal!r}"
    return "authenticated", "banner clean"


def _live_map_probe() -> dict:
    """Run a real `firecrawl map` and report whether it produced links."""
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "probe.json"
        code, stderr = _run([
            "firecrawl", "map", "https://docs.firecrawl.dev",
            "--limit", "5000", "--json", "--pretty",
        ], timeout=45)
        # CLI 1.16 writes to stdout; capture via shell would be better, but
        # we already captured combined stdout+stderr in _run. Re-run with
        # an explicit redirection to keep the JSON parseable.
        proc = subprocess.run(
            ["firecrawl", "map", "https://docs.firecrawl.dev",
             "--limit", "5000", "--json", "--pretty"],
            capture_output=True, text=True, timeout=45,
        )
        out_path.write_text(proc.stdout or "")
        if proc.returncode != 0 or not proc.stdout.strip():
            return {"ok": False, "exit": proc.returncode, "stderr": proc.stderr.strip()[:300]}
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            return {"ok": False, "parse_error": repr(exc)}
        links = data.get("data", {}).get("links") or data.get("links") or []
        return {"ok": bool(links), "url_count": len(links)}


def main() -> int:
    if not shutil.which("firecrawl"):
        print(json.dumps({"verdict": "unavailable", "mode": "cli-absent"}, indent=2))
        return 1
    code, banner = _run(["firecrawl", "--version"])
    cli_version = banner.splitlines()[0].strip() if banner else "unknown"
    code, banner = _run(["firecrawl", "--status"])
    verdict, reason = _classify_status(code, banner)
    report: dict[str, object] = {
        "cli_version": cli_version,
        "status_banner": banner[:500],
        "verdict_from_banner": verdict,
        "reason": reason,
        "tcp_tls_probe": _tcp_tls_probe("api.firecrawl.dev"),
    }
    if verdict == "authenticated":
        report["live_map_probe"] = _live_map_probe()
        if not report["live_map_probe"].get("ok"):
            report["verdict_from_banner"] = "unavailable"
            report["reason"] = "banner clean but live map call failed"
    print(json.dumps(report, indent=2))
    return 0 if report["verdict_from_banner"] == "authenticated" else 1


if __name__ == "__main__":
    sys.exit(main())
