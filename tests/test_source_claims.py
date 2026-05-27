from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "goal-prompt-generator" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_source_claims as vsc  # noqa: E402


def _repo(tmp_path: Path, slug: str, branch: str = "main", with_head: bool = True) -> Path:
    root = tmp_path / ".opensrc" / "repos" / "github.com" / slug / branch
    root.mkdir(parents=True)
    head = root / ".git" / "HEAD"
    if with_head:
        head.parent.mkdir()
        head.write_text(f"ref: refs/heads/{branch}\n")
    return head


def _map(tmp_path: Path, payload: dict | str) -> Path:
    f = tmp_path / "map.json"
    f.write_text(payload if isinstance(payload, str) else json.dumps(payload))
    return f


def test_check_dual_records_oks_and_original_pass():
    v = vsc.Verifier()
    v.check("alpha", True, "ev-a")
    v.check("beta", False, "ev-b")
    assert (len(v.oks), len(v.failures)) == (1, 1)
    assert (len(v.original_pass), len(v.original_fail)) == (1, 1)
    assert "alpha" in v.original_pass[0] and "beta" in v.original_fail[0]
    assert v.contrarian_pass == v.contrarian_fail == v.reconciled == []


def test_contrarian_check_records_into_contrarian_buckets_only():
    v = vsc.Verifier()
    v.contrarian_check("c1", True, "ok-evidence")
    v.contrarian_check("c2", False, "drift-evidence")
    assert (len(v.contrarian_pass), len(v.contrarian_fail)) == (1, 1)
    assert v.oks == v.failures == v.original_pass == v.original_fail == []


def test_contrarian_failure_makes_report_exit_one():
    v = vsc.Verifier()
    v.contrarian_check("drift-detected", False, "count=1 expected=10")
    with pytest.raises(SystemExit) as exc:
        v.report(exit_on_failure=True)
    assert exc.value.code == 1


def test_report_returns_int_zero_when_no_failures(capsys):
    v = vsc.Verifier()
    v.check("only-good", True, "ev")
    v.contrarian_check("also-good", True, "ev")
    assert v.report(exit_on_failure=False) == 0
    out = capsys.readouterr().out
    for key in ("original_pass", "original_fail", "contrarian_pass", "contrarian_fail", "reconciled"):
        assert key in out


def test_report_returns_int_one_without_exit_when_failures(capsys):
    v = vsc.Verifier()
    v.check("bad-original", False)
    v.contrarian_check("bad-contrarian", False)
    assert v.report(exit_on_failure=False) == 1
    assert "bad-original" in capsys.readouterr().out


def test_opensrc_repo_main_drift_fresh_repo_passes(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _repo(tmp_path, "test-org/fresh-repo")
    v = vsc.Verifier()
    assert v.opensrc_repo_main_drift("test-org/fresh-repo", max_age_days=7) is True
    assert v.contrarian_pass and not v.contrarian_fail


def test_opensrc_repo_main_drift_stale_repo_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    head = _repo(tmp_path, "test-org/stale-repo")
    old = time.time() - 30 * 86400
    os.utime(head, (old, old))
    v = vsc.Verifier()
    assert v.opensrc_repo_main_drift("test-org/stale-repo", max_age_days=7) is False
    assert v.contrarian_fail and "age=" in v.contrarian_fail[0]


def test_opensrc_repo_main_drift_no_cache_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    v = vsc.Verifier()
    assert v.opensrc_repo_main_drift("missing/repo", max_age_days=1) is False
    assert "no cached repo" in v.contrarian_fail[0]


def test_opensrc_repo_main_drift_master_branch_also_resolved(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _repo(tmp_path, "old/proj", branch="master", with_head=False)
    v = vsc.Verifier()
    assert v.opensrc_repo_main_drift("old/proj", max_age_days=365) is True
    assert "root=" in v.contrarian_pass[0]


def test_firecrawl_map_data_links_exact_match(tmp_path):
    v = vsc.Verifier()
    assert v.firecrawl_map_url_count_changed("tech", 3, 0, str(_map(tmp_path, {"data": {"links": ["a", "b", "c"]}}))) is True


def test_firecrawl_map_top_level_links_within_tolerance(tmp_path):
    v = vsc.Verifier()
    assert v.firecrawl_map_url_count_changed("tech", 3, 1, str(_map(tmp_path, {"links": ["a", "b", "c", "d"]}))) is True
    assert "count=4" in v.contrarian_pass[0]


def test_firecrawl_map_drift_outside_tolerance_fails(tmp_path):
    v = vsc.Verifier()
    assert v.firecrawl_map_url_count_changed("tech", 10, 0, str(_map(tmp_path, {"data": {"links": ["only-one"]}}))) is False
    assert "count=1 expected=10" in v.contrarian_fail[0]


def test_firecrawl_map_missing_file_fails(tmp_path):
    v = vsc.Verifier()
    assert v.firecrawl_map_url_count_changed("absent", 0, map_file=str(tmp_path / "nope.json")) is False
    assert "map file missing" in v.contrarian_fail[0]


def test_firecrawl_map_invalid_json_fails(tmp_path):
    v = vsc.Verifier()
    assert v.firecrawl_map_url_count_changed("broken", 0, map_file=str(_map(tmp_path, "not-json{{{"))) is False
    assert "invalid json" in v.contrarian_fail[0]


def test_firecrawl_map_default_path_resolved_against_cwd(tmp_path, monkeypatch):
    research = tmp_path / "research" / "url-maps"
    research.mkdir(parents=True)
    (research / "default-tech.json").write_text(json.dumps({"links": ["a", "b"]}))
    monkeypatch.chdir(tmp_path)
    assert vsc.Verifier().firecrawl_map_url_count_changed("default-tech", 2) is True


def test_helper_path_visible_absolute_existing_passes(tmp_path):
    helper = tmp_path / "helper.py"
    helper.write_text("# real helper\n")
    v = vsc.Verifier()
    assert v.helper_path_visible_to_remote_backend(str(helper), backend_kind="daytona") is True
    assert all(token in v.contrarian_pass[0] for token in ("backend=daytona", "abs=True", "exists=True"))


def test_helper_path_visible_relative_path_fails():
    v = vsc.Verifier()
    assert v.helper_path_visible_to_remote_backend("relative/helper.py", backend_kind="local") is False
    assert "backend=local" in v.contrarian_fail[0] and "abs=False" in v.contrarian_fail[0]


def test_helper_path_visible_missing_absolute_path_fails(tmp_path):
    v = vsc.Verifier()
    assert v.helper_path_visible_to_remote_backend(str(tmp_path / "missing-helper.py"), backend_kind="devcontainer") is False
    assert "backend=devcontainer" in v.contrarian_fail[0] and "exists=False" in v.contrarian_fail[0]


def test_helper_present_records_original_only(tmp_path):
    helper = tmp_path / "g.py"
    helper.write_text("x = 1")
    v = vsc.Verifier()
    assert v.helper_present(str(helper)) is True
    assert v.original_pass and not v.contrarian_pass


def test_file_substring_records_through_check(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello world")
    v = vsc.Verifier()
    assert v.file_substring(str(p), "world") is True
    assert v.original_pass and v.oks
