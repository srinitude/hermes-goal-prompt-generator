from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _run(args: list[str], timeout: int = 20) -> tuple[int | None, str]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:  # pragma: no cover - exact platform errors vary
        return None, str(exc)
    return result.returncode, (result.stdout + result.stderr).strip()


def _first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "unavailable")


_AUTH_RST_MARKERS = ("ECONNRESET", "Connection reset", "fetch failed", "Could not fetch")


def _firecrawl_auth(banner: str) -> str:
    """Map a `firecrawl --status` banner to ``authenticated`` / ``unavailable``.

    Pitfall #34: a banner that prints ``Authenticated`` only proves env-var parsing.
    When the same banner ALSO surfaces a live HTTP failure marker (RST, fetch failed,
    Could not fetch) we MUST downgrade to ``unavailable`` rather than silently keep
    the optimistic claim.
    """
    text = banner or ""
    if "Authenticated" not in text:
        return "unavailable"
    if any(marker in text for marker in _AUTH_RST_MARKERS):
        return "unavailable"
    return "authenticated"


def _map_entries(url_maps_root: Path) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    if not url_maps_root.exists():
        return entries
    for path in sorted(url_maps_root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        links = data.get("data", {}).get("links", [])
        if not isinstance(links, list) or not links:
            continue
        entries[path.stem] = {
            "file": str(path),
            "url_count": len(links),
            "map_command": "cache-inspected; refresh with firecrawl map --json --pretty --limit 5000 <official-docs-root>",
            "map_limit": 5000,
        }
    return entries


def firecrawl_evidence(output_dir: Path) -> dict[str, Any]:
    url_maps_root = output_dir / "research" / "url-maps"
    evidence = {
        "cli_version": "unavailable",
        "auth": "unavailable",
        "url_maps_root": "research/url-maps",
        "required_maps_present": _map_entries(url_maps_root),
        "evidence": ["Validate official docs with Firecrawl at execution time."],
    }
    if not shutil.which("firecrawl"):
        evidence["evidence"].append("firecrawl CLI not found during generation.")
        return evidence

    _, version = _run(["firecrawl", "--version"])
    evidence["cli_version"] = _first_line(version)
    code, status = _run(["firecrawl", "--status"])
    evidence["auth"] = _firecrawl_auth(status) if code == 0 else "unavailable"
    if evidence["auth"] == "authenticated" and not evidence["required_maps_present"]:
        evidence["auth"] = "unavailable"
        evidence["evidence"].append("Firecrawl authenticated but no cached map evidence was present; official documentation validation remains execution-time required.")
    evidence["evidence"].append("Firecrawl readiness probed with `firecrawl --status` and downgraded via _firecrawl_auth when the banner surfaces a live HTTP RST/fetch-failed marker; refresh map/scrape/crawl/agent evidence at execution time unless cached entries above are still valid.")
    return evidence


def opensrc_evidence() -> dict[str, Any]:
    evidence = {"cli_version": "unavailable", "cache_root": "", "fetched": {}, "divergences": []}
    if not shutil.which("opensrc"):
        return evidence
    _, version = _run(["opensrc", "--version"])
    evidence["cache_root"] = str((Path.home() / ".opensrc" / "repos").resolve())
    evidence["divergences"].append(
        f"opensrc readiness probed ({_first_line(version)}) but the generic generator did not record spec-specific fetched repos; execution-time source validation remains required."
    )
    return evidence


def research_evidence(output_dir: Path) -> dict[str, Any]:
    return {
        "firecrawl": firecrawl_evidence(output_dir),
        "opensrc": opensrc_evidence(),
        "authoritative_reference_urls": {"execution_time_required": []},
    }
