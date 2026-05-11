#!/usr/bin/env python3
"""Pre-write source-claim verifier for goal-prompt-generator runs.

check() records original buckets; contrarian_check() records contrarian buckets and affects report() exit code. CLI: ``python3 scripts/validate_source_claims.py --smoke``.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import socket
import ssl
import subprocess
import sys
import time


class Verifier:
    def __init__(self) -> None:
        self.oks: list[str] = []
        self.failures: list[str] = []
        self.notes: list[str] = []
        self.original_pass: list[str] = []
        self.original_fail: list[str] = []
        self.contrarian_pass: list[str] = []
        self.contrarian_fail: list[str] = []
        self.reconciled: list[str] = []

    def check(self, label: str, ok: bool, evidence: str = "") -> bool:
        line = f"{'OK' if ok else 'FAIL'} {label} :: {evidence[:240]}"
        (self.oks if ok else self.failures).append(line)
        (self.original_pass if ok else self.original_fail).append(line)
        return ok

    def contrarian_check(self, label: str, ok: bool, evidence: str = "") -> bool:
        line = f"{'OK' if ok else 'FAIL'} {label} :: {evidence[:240]}"
        (self.contrarian_pass if ok else self.contrarian_fail).append(line)
        return ok

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    def opensrc_repo(self, slug: str, key_paths: list[str]) -> bool:
        roots = [pathlib.Path(f"/root/.opensrc/repos/github.com/{slug}/{b}") for b in ("main", "master")]
        root = next((r for r in roots if r.exists()), None)
        if root is None:
            return self.check(f"opensrc cached {slug}", False, "no main/ or master/ dir")
        self.check(f"opensrc cached {slug}", True, str(root))
        all_ok = True
        for raw in key_paths:
            rel = raw.split(":", 1)[0].rstrip("/")
            p = root / rel
            ok = p.exists()
            if not ok:
                p2 = root / rel.split(" ", 1)[0]
                if p2.exists():
                    ok, p = True, p2
            self.check(f"  {slug}::{rel}", ok, str(p))
            all_ok = all_ok and ok
        return all_ok

    def file_substring(self, path: str, needle: str) -> bool:
        p = pathlib.Path(path)
        if not p.exists():
            return self.check(f"file_exists {path}", False)
        try:
            txt = p.read_text(errors="replace")
        except Exception as exc:
            return self.check(f"file_readable {path}", False, str(exc))
        return self.check(f"file_contains_substring {path}", needle in txt, needle[:80])

    def tcp_reachable(self, host: str, port: int = 443, timeout: float = 4.0) -> bool:
        try:
            socket.create_connection((host, port), timeout=timeout).close()
            return self.check(f"tcp {host}:{port}", True)
        except Exception as exc:
            return self.check(f"tcp {host}:{port}", False, str(exc))

    def tls_reachable(self, host: str, port: int = 443, timeout: float = 4.0) -> bool:
        try:
            s = socket.create_connection((host, port), timeout=timeout)
        except Exception as exc:
            return self.check(f"tls {host}:{port} (tcp)", False, str(exc))
        try:
            ssl.create_default_context().wrap_socket(s, server_hostname=host).close()
            return self.check(f"tls {host}:{port}", True)
        except Exception as exc:
            self.note(
                f"selective L7 RST suspected on {host}:{port} (TCP ok, TLS fail: "
                f"{type(exc).__name__}: {exc}) — see references/dns-blocked-research-tools.md §3."
            )
            return self.check(f"tls {host}:{port}", False, str(exc))

    def firecrawl_usable(self) -> bool:
        host = "api.firecrawl.dev"
        tls_ok = self.tls_reachable(host, 443)
        try:
            r = subprocess.run(["firecrawl", "--status"], capture_output=True, text=True, timeout=10)
            stdout = r.stdout + r.stderr
            auth_ok = "Authenticated" in stdout
            self.check("firecrawl --status authenticated", auth_ok, stdout.splitlines()[0] if stdout else "")
        except FileNotFoundError:
            return self.check("firecrawl CLI present", False, "firecrawl not on PATH")
        except subprocess.TimeoutExpired:
            return self.check("firecrawl --status timeout", False)
        return tls_ok and auth_ok

    def helper_present(self, path: str) -> bool:
        return self.check(f"helper_present {path}", pathlib.Path(path).exists(), path)

    def opensrc_repo_main_drift(self, slug: str, max_age_days: int = 7) -> bool:
        bases = [pathlib.Path.home() / ".opensrc" / "repos" / "github.com",
                 pathlib.Path("/root/.opensrc/repos/github.com")]
        roots = [b / slug / branch for b in bases for branch in ("main", "master")]
        root = next((r for r in roots if os.path.exists(r)), None)
        label = f"opensrc_repo_main_drift {slug}"
        if root is None:
            return self.contrarian_check(label, False, "no cached repo for main/master")
        head = root / ".git" / "HEAD"
        target = head if head.exists() else root
        age_days = (time.time() - target.stat().st_mtime) / 86400
        return self.contrarian_check(label, age_days <= max_age_days,
                                     f"age={age_days:.1f}d max={max_age_days} root={root}")

    def firecrawl_map_url_count_changed(self, tech: str, expected: int,
                                        tolerance: int = 0, map_file: str | None = None) -> bool:
        path = pathlib.Path(map_file) if map_file else pathlib.Path(f"research/url-maps/{tech}.json")
        label = f"firecrawl_map_url_count {tech}"
        if not path.exists():
            return self.contrarian_check(label, False, f"map file missing: {path}")
        try:
            data = json.loads(path.read_text())
        except Exception as exc:
            return self.contrarian_check(label, False, f"invalid json: {exc}")
        count = len(self._extract_map_links(data))
        return self.contrarian_check(label, abs(count - expected) <= tolerance,
                                     f"count={count} expected={expected} tol={tolerance} path={path}")

    @staticmethod
    def _extract_map_links(data: object) -> list:
        if isinstance(data, dict):
            inner = data.get("data")
            if isinstance(inner, dict) and isinstance(inner.get("links"), list):
                return inner["links"]
            if isinstance(data.get("links"), list):
                return data["links"]
        return []

    def helper_path_visible_to_remote_backend(self, path: str, backend_kind: str = "local") -> bool:
        p = pathlib.Path(path)
        abs_ok, exists_ok = p.is_absolute(), p.exists()
        return self.contrarian_check(
            f"helper_path_visible_to_remote_backend {path}", abs_ok and exists_ok,
            f"backend={backend_kind} abs={abs_ok} exists={exists_ok} path={path}",
        )

    def report(self, exit_on_failure: bool = True) -> int:
        bar = "=" * 72
        print(bar)
        print(f"PASSED: {len(self.oks)}")
        print(f"FAILED: {len(self.failures)}")
        print(
            f"original_pass={len(self.original_pass)} original_fail={len(self.original_fail)} "
            f"contrarian_pass={len(self.contrarian_pass)} contrarian_fail={len(self.contrarian_fail)} "
            f"reconciled={len(self.reconciled)}"
        )
        print(bar)
        for label, items in (("notes", self.notes), ("original_fail", self.original_fail),
                             ("contrarian_fail", self.contrarian_fail), ("reconciled", self.reconciled)):
            if items:
                print(f"\n--- {label} ---")
                for line in items:
                    print(line)
        has_failures = bool(self.original_fail) or bool(self.contrarian_fail)
        if has_failures and exit_on_failure:
            sys.exit(1)
        return 1 if has_failures else 0


def _smoke() -> int:
    v = Verifier()
    v.tcp_reachable("github.com")
    v.tls_reachable("github.com")
    v.tls_reachable("docs.railway.com")
    v.firecrawl_usable()
    v.helper_present("/root/.hermes/skills/software-development/goal-prompt-generator/scripts/generate_goal_prompt.py")
    return v.report(exit_on_failure=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--smoke", action="store_true", help="run a stock probe matrix")
    if p.parse_args().smoke:
        sys.exit(_smoke())
    print(__doc__)
    sys.exit(2)
