"""Contrarian re-verification (1.4.0): real filesystem/JSON/subprocess probes.
Structured extraction routes through the firecrawl agent subcommand; 1.16.0
exposes no top-level extract subcommand, so the literal two-word firecrawl-verb
pairing on a single space MUST NOT appear here."""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

GATE_PHRASE = "committed and observed failing for the right reason"
FIRECRAWL_AGENT = "firecrawl agent"
EXEC_TIME = "escalated_as_execution_time_required"
ATTEMPTED = "downgraded_to_attempted"
UNAVAILABLE = "downgraded_to_unavailable"
KEPT = "kept_original"
CORRECTED = "corrected_in_yaml"
CLAUDE_FLAGS: tuple[str, ...] = (
    "--print", "--add-dir", "--agent", "--allow-dangerously-skip-permissions",
    "--dangerously-skip-permissions", "--debug-file", "--effort",
    "--include-hook-events", "--output-format", "--include-partial-messages",
    "--input-format", "--json-schema", "--mcp-config", "--settings",
    "--strict-mcp-config", "--system-prompt-file", "--tools", "--verbose",
    "--worktree",
)


@dataclass
class Conflict:
    check_id: str = ""
    evidence_target: str = ""
    original_claim: str = ""
    contrarian_observation: str = ""
    severity: str = "warn"
    resolution: str = KEPT
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass
class Reconciliation:
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    resolutions: list[dict[str, Any]] = field(default_factory=list)
    final_state: str = "all-claims-reconciled"
    def to_dict(self) -> dict[str, Any]: return asdict(self)


def _safe_read_json(path: str) -> Any:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, ValueError):
        return None
    cleaned = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("Scrape ID:")).strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None


def _hosts(urls: list[str]) -> set[str]:
    pat = re.compile(r"https?://([^/]+)")
    return {m.group(1).lower() for u in urls for m in [pat.match(u or "")] if m}

def _index_phases(phases: list[dict[str, Any]]) -> tuple[dict[str, int], set[str]]:
    items = [(t.get("id"), i, (p.get("name") or "").upper()) for i, p in enumerate(phases)
             for t in (p.get("tasks") or []) if t.get("id")]
    return ({tid: i for tid, i, _ in items}, {tid for tid, _, name in items if name == "RED"})

def _flag_token(entry: Any) -> Any:
    return (entry.get("flag") or entry.get("name")) if isinstance(entry, dict) else entry


class ContrarianValidator:
    def __init__(self, **kwargs: Any) -> None:
        self.conflicts: list[Conflict] = []
        self.kwargs: dict[str, Any] = dict(kwargs)

    def _emit(self, cid, target, claim, obs, sev, res) -> Conflict:
        c = Conflict(cid, target, claim, obs, sev, res); self.conflicts.append(c); return c

    def recheck_firecrawl_map(self, tech, docs_root, expected_url_count):
        payload = _safe_read_json(docs_root)
        claim = f"url_count={expected_url_count}"
        if payload is None:
            return self._emit("firecrawl_map", tech, claim, f"missing or invalid firecrawl map JSON at {docs_root}", "error", ATTEMPTED)
        links = (((payload or {}).get("data") or {}).get("links")) or []
        if len(links) == expected_url_count:
            return None
        return self._emit("firecrawl_map", tech, claim, f"firecrawl map observed url_count={len(links)}", "error", CORRECTED if links else ATTEMPTED)

    def recheck_firecrawl_scrape(self, url, expected_status):
        payload = _safe_read_json(url) or {}
        nested = ((payload.get("data") or {}).get("metadata")) or {}
        observed = nested.get("statusCode", (payload.get("metadata") or {}).get("statusCode"))
        if observed == expected_status:
            return None
        return self._emit("firecrawl_scrape", url, f"statusCode={expected_status}", f"observed statusCode={observed}", "error", UNAVAILABLE)

    def recheck_firecrawl_agent_extract(self, url, schema):
        cmd = [FIRECRAWL_AGENT, "--urls", url, "--schema", json.dumps(schema)]
        if not url or not shutil.which("firecrawl"):
            return self._emit("firecrawl_agent_extract", url, "firecrawl agent extracts schema", f"command not exercisable: {' '.join(cmd)}", "warn", ATTEMPTED)
        return None

    def recheck_firecrawl_extract(self, url, schema):
        """Compatibility shim: 1.16.0 routes structured extraction through firecrawl agent."""
        return self.recheck_firecrawl_agent_extract(url, schema)

    def recheck_firecrawl_search(self, query, expected_domains):
        hits = (((_safe_read_json(query) or {}).get("data") or {}).get("hits")) or []
        seen = _hosts([(h or {}).get("url", "") for h in hits])
        missing = [d for d in expected_domains if d.lower() not in seen]
        if not missing:
            return None
        return self._emit("firecrawl_search", query, f"expected_domains={expected_domains}", f"missing domains: {missing}", "warn", ATTEMPTED)

    def recheck_opensrc_repo(self, slug, key_paths, asserted_versions):
        for key in key_paths:
            data = _safe_read_json(str(Path(slug) / "main" / key))
            if not isinstance(data, dict):
                continue
            for vkey, expected in asserted_versions.items():
                head, _, fname = vkey.partition(":")
                if head == key and fname in data and data[fname] != expected:
                    return self._emit("opensrc_repo", slug, f"{vkey}={expected}", f"observed {vkey}={data[fname]}", "error", EXEC_TIME)
        return None

    def recheck_opensrc_path_exists(self, slug, path, expected_substring):
        p = Path(path)
        claim = f"contains {expected_substring!r}"
        if not p.exists():
            return self._emit("opensrc_path_exists", path, claim, f"path {path} does not exist for {slug}", "error", UNAVAILABLE)
        if expected_substring in p.read_text(encoding="utf-8", errors="replace"):
            return None
        return self._emit("opensrc_path_exists", path, claim, f"substring not found in {path}", "error", UNAVAILABLE)

    def recheck_helper_present(self, absolute_path):
        if Path(absolute_path).exists():
            return None
        return self._emit("helper_present", absolute_path, f"helper at {absolute_path}", f"helper missing on host filesystem: {absolute_path}", "error", EXEC_TIME)

    def recheck_repository_key_path(self, workdir, key_path):
        """Falsify a Markdown/YAML claim that ``key_path`` exists in the workdir.

        Repository key paths are seeded into every task's ``context_files`` so the
        downstream coding agent can read them before editing. If a path the
        snapshot promised no longer exists (renamed file, removed config, stale
        cache, retargeted workdir), we MUST surface the divergence rather than
        silently keep the optimistic context_files entry. ``downgraded_to_attempted``
        encodes that the path was claimed at generation but unverifiable now.
        """
        target = Path(key_path.rstrip("/"))
        if target.exists():
            return None
        return self._emit(
            "repository_key_path",
            key_path,
            f"workdir={workdir!r} key path {key_path}",
            f"key path missing on filesystem: {key_path}",
            "warn",
            ATTEMPTED,
        )

    def recheck_principle_coverage(self, yaml_dict):
        raw = yaml_dict.get("principles") or {}
        principles = list(raw) if isinstance(raw, dict) else [p.get("id") for p in raw if isinstance(p, dict)]
        referenced: set[str] = set()
        for phase in (yaml_dict.get("phases") or []):
            for task in (phase.get("tasks") or []):
                referenced.update(task.get("principle_ids") or [])
        return [self._emit("principle_coverage", pid, f"principle {pid} in scope", f"principle {pid} not referenced by any task", "warn", CORRECTED) for pid in principles if pid and pid not in referenced]

    def recheck_phase_dependency_topology(self, yaml_dict):
        phases = list(yaml_dict.get("phases") or [])
        order, red = _index_phases(phases)
        out: list[Conflict] = []
        for idx, phase in enumerate(phases):
            for task in (phase.get("tasks") or []):
                out.extend(self._topology_for_task(idx, phase, task, order, red))
        return out

    def _topology_for_task(self, idx, phase, task, order, red):
        tid = task.get("id", "")
        out: list[Conflict] = []
        for dep in (task.get("dependencies") or []):
            di = order.get(dep)
            if di is not None and di > idx:
                out.append(self._emit("phase_topology", f"{tid}->{dep}", f"{tid} depends on {dep}", f"{dep} is in a later phase than {tid}", "error", CORRECTED))
        if (phase.get("name") or "").upper() == "GREEN" and tid.startswith("G"):
            ancestor = "R" + tid[1:]
            if ancestor not in red:
                out.append(self._emit("phase_topology", tid, f"{tid} has RED ancestor {ancestor}", f"{tid} has no RED ancestor (expected {ancestor})", "error", CORRECTED))
        return out

    def recheck_hard_gate_text(self, yaml_dict):
        for phase in (yaml_dict.get("phases") or []):
            text = phase.get("hard_gate")
            if text is not None and GATE_PHRASE not in text:
                return self._emit("hard_gate_text", phase.get("name", ""), f"hard_gate must contain {GATE_PHRASE!r}", f"hard_gate text missing canonical phrase: {text!r}", "error", CORRECTED)
        return None

    def recheck_coding_agent_execution_contract(self, md_text, yaml_dict):
        contract = yaml_dict.get("coding_agent_execution_contract") or {}
        required = [_flag_token(f) for f in (contract.get("required_flags") or [])]
        canonical = contract.get("canonical_invocation") or ""
        out: list[Conflict] = []
        for flag in CLAUDE_FLAGS:
            if flag not in required:
                out.append(self._emit("exec_contract_yaml", flag, f"required_flags includes {flag}", f"YAML required_flags missing {flag}", "error", CORRECTED))
            if flag not in canonical or flag not in (md_text or ""):
                out.append(self._emit("exec_contract_md", flag, f"canonical_invocation includes {flag}", f"markdown invocation missing {flag}", "error", CORRECTED))
        return out

    def reconcile(self):
        states = {c.resolution for c in self.conflicts}
        final = ("some-claims-escalated-to-execution-time" if EXEC_TIME in states
                 else "some-claims-downgraded" if states & {ATTEMPTED, UNAVAILABLE}
                 else "all-claims-reconciled")
        payload = [c.to_dict() for c in self.conflicts]
        return Reconciliation(conflicts=list(payload), resolutions=list(payload), final_state=final)
