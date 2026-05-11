"""Behavior matrix for contrarian validation (1.4.0).
Real files, dictionaries, and subprocesses only."""
from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import goal_prompt_generator.contrarian_validation as cv

GATE_PHRASE = "committed and observed failing for the right reason"
FORBIDDEN = "firecrawl" + " " + "extract"
SKILL_ROOT = Path(__file__).resolve().parents[1]
RUN_SCRIPT = SKILL_ROOT / "scripts" / "run_contrarian_validation.py"
TASK_VALIDATOR = SKILL_ROOT / "scripts" / "validate_task_list_yaml.py"
CLAUDE_FLAGS = (
    "--print --add-dir --agent --allow-dangerously-skip-permissions "
    "--dangerously-skip-permissions --debug-file --effort --include-hook-events "
    "--output-format --include-partial-messages --input-format --json-schema "
    "--mcp-config --settings --strict-mcp-config --system-prompt-file --tools "
    "--verbose --worktree"
).split()
EVIDENCE_NO_RECONCILE = (
    "metadata: {plan_id: x, plan_version: 1.4.0}\n"
    "validation_evidence: {firecrawl: {required_maps_present: {a: {url_count: 1}}}, "
    "opensrc: {fetched: {x: {cached_path: /tmp/x, key_paths: []}}}}\n"
    "validation_reconciliation: {}\nstyleguide_rules: {}\nguardrails: {}\nci_commands: {}\n"
    "principles: {P1: x}\nphases: []\nagent_runtime_protocol: {}\n"
    "coding_agent_execution_contract: {required_flags: [], canonical_invocation: ''}\n"
)
DRY_RUN_FIXTURE = (
    "metadata: {plan_id: f, plan_version: 1.4.0}\n"
    "validation_evidence: {firecrawl: {auth: authenticated, required_maps_present: {}}, "
    "opensrc: {fetched: {}}}\nphases: []\n"
)
STRICT_FIXTURE = (
    "metadata: {plan_id: f, plan_version: 1.4.0}\nvalidation_evidence: {firecrawl: "
    "{auth: authenticated, required_maps_present: {a: {url_count: 1}}}, opensrc: "
    "{fetched: {x: {cached_path: /tmp/x, key_paths: [/non/existent]}}}}\nphases: []\n"
)

def _run(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=30)

def _gate(text):
    return {"phases": [{"name": "RED", "hard_gate": text, "tasks": []}]}

def _canonical(flags):
    return "claude " + " ".join(f"{f} <x>" for f in flags)

def _contract(flags, canonical=None):
    return {"coding_agent_execution_contract": {
        "required_flags": [{"flag": f} for f in flags],
        "canonical_invocation": canonical if canonical is not None else _canonical(flags)}}

def _links(n):
    return {"data": {"links": [f"u{i}" for i in range(n)]}}

def test_R01_conflict_dataclass_round_trip():
    assert dataclasses.is_dataclass(cv.Conflict)
    c = cv.Conflict(check_id="X", evidence_target="Y", original_claim="Z",
                    contrarian_observation="W", severity="warn", resolution="kept_original")
    assert json.loads(json.dumps(dataclasses.asdict(c)))["check_id"] == "X"

def test_R02_recheck_firecrawl_map_drift_and_match(tmp_path):
    drift = tmp_path / "d.json"; drift.write_text(json.dumps(_links(50)))
    match = tmp_path / "m.json"; match.write_text(json.dumps(_links(7)))
    v = cv.ContrarianValidator()
    c = v.recheck_firecrawl_map("firecrawl-docs", str(drift), 999)
    assert c is not None and c.severity == "error"
    assert c.resolution in {"corrected_in_yaml", "downgraded_to_attempted"}
    assert v.recheck_firecrawl_map("firecrawl-docs", str(match), 7) is None

def test_R03_recheck_firecrawl_scrape_404_and_200(tmp_path):
    bad = tmp_path / "404.json"; bad.write_text(json.dumps({"data": {"metadata": {"statusCode": 404}}}))
    ok = tmp_path / "200.json"; ok.write_text(json.dumps({"data": {"metadata": {"statusCode": 200}}}))
    v = cv.ContrarianValidator()
    c = v.recheck_firecrawl_scrape(url=str(bad), expected_status=200)
    assert c is not None and c.severity == "error" and c.resolution == "downgraded_to_unavailable"
    assert v.recheck_firecrawl_scrape(str(ok), 200) is None

def test_R04_agent_extract_subcommand_uses_firecrawl_agent():
    src = Path(cv.__file__).read_text(encoding="utf-8")
    assert "firecrawl agent" in src
    assert FORBIDDEN not in src
    cv.ContrarianValidator().recheck_firecrawl_agent_extract(
        url="https://example.com", schema={"name": "x"})

def test_R05_recheck_firecrawl_search_missing_domain(tmp_path):
    f = tmp_path / "search.json"; f.write_text(json.dumps({"data": {"hits": [
        {"url": "https://example.com/a"}, {"url": "https://other.dev/b"}]}}))
    c = cv.ContrarianValidator().recheck_firecrawl_search(
        query=str(f), expected_domains=["docs.firecrawl.dev"])
    assert c is not None and c.resolution == "downgraded_to_attempted"

def test_R06_recheck_opensrc_repo_main_drift(tmp_path):
    repo = tmp_path / "main"; repo.mkdir()
    (repo / "package.json").write_text(json.dumps({"version": "1.10.0"}))
    (tmp_path / "HEAD_TIMESTAMP").write_text("2025-01-01T00:00:00Z")
    c = cv.ContrarianValidator(opensrc_root=str(tmp_path)).recheck_opensrc_repo(
        slug=str(tmp_path), key_paths=["package.json"],
        asserted_versions={"package.json:version": "1.16.0"})
    assert c is not None and c.resolution == "escalated_as_execution_time_required"

def test_R07_recheck_opensrc_path_exists_real_path_and_missing(tmp_path):
    real = tmp_path / "AGENTS.md"; real.write_text("Hermes Agent - Development Guide")
    v = cv.ContrarianValidator()
    assert v.recheck_opensrc_path_exists(
        slug="NousResearch/hermes-agent", path=str(real),
        expected_substring="Hermes Agent - Development Guide") is None
    c = v.recheck_opensrc_path_exists(
        slug="x", path=str(tmp_path / "missing.md"), expected_substring="z")
    assert c is not None and c.resolution == "downgraded_to_unavailable"

def test_R08_recheck_helper_present_existing_and_missing(tmp_path):
    helper = tmp_path / "helper.py"; helper.write_text("# helper")
    v = cv.ContrarianValidator()
    assert v.recheck_helper_present(str(helper)) is None
    c = v.recheck_helper_present("/non/existent/helper.py")
    assert c is not None and c.resolution == "escalated_as_execution_time_required"

def test_R09_recheck_principle_coverage_unused_and_full():
    v = cv.ContrarianValidator()
    partial = {"principles": [{"id": f"P{i}"} for i in range(1, 6)],
               "phases": [{"tasks": [{"principle_ids": ["P1", "P2", "P3"]}]}]}
    conflicts = v.recheck_principle_coverage(partial)
    assert conflicts and {c.evidence_target for c in conflicts} >= {"P4", "P5"}
    full = {"principles": [{"id": "P1"}], "phases": [{"tasks": [{"principle_ids": ["P1"]}]}]}
    assert v.recheck_principle_coverage(full) == []
    mapping = {"principles": {"P1": "x", "P2": "y"}, "phases": [{"tasks": [{"principle_ids": ["P1"]}]}]}
    assert [c.evidence_target for c in v.recheck_principle_coverage(mapping)] == ["P2"]

def test_R10_phase_topology_forward_dep_and_green_without_red_ancestor():
    v = cv.ContrarianValidator()
    forward = {"phases": [
        {"name": "ANALYSIS", "tasks": [{"id": "A1", "dependencies": ["G01"]}]},
        {"name": "GREEN", "tasks": [{"id": "G01", "dependencies": []}]}]}
    assert any(c.resolution == "corrected_in_yaml"
               for c in v.recheck_phase_dependency_topology(forward))
    orphan = {"phases": [
        {"name": "RED", "tasks": [{"id": "R01", "dependencies": []}]},
        {"name": "GREEN", "tasks": [{"id": "G02", "dependencies": []}]}]}
    assert any(c.resolution == "corrected_in_yaml"
               for c in v.recheck_phase_dependency_topology(orphan))

def test_R11_recheck_hard_gate_text_canonical_and_missing():
    v = cv.ContrarianValidator()
    assert v.recheck_hard_gate_text(_gate(f"x {GATE_PHRASE} y")) is None
    c = v.recheck_hard_gate_text(_gate("missing the magic phrase"))
    assert c is not None and c.severity == "error"

def test_R12_coding_agent_execution_contract_full_set_passes():
    canonical = _canonical(CLAUDE_FLAGS)
    assert cv.ContrarianValidator().recheck_coding_agent_execution_contract(
        canonical, _contract(CLAUDE_FLAGS)) == []

def test_R12_yaml_required_flags_missing_worktree_emits_conflict():
    flags = [f for f in CLAUDE_FLAGS if f != "--worktree"]
    md_text = _canonical(CLAUDE_FLAGS)
    conflicts = cv.ContrarianValidator().recheck_coding_agent_execution_contract(
        md_text, _contract(flags, canonical=md_text))
    assert any("--worktree" in c.contrarian_observation for c in conflicts)

def test_R12_markdown_canonical_invocation_missing_worktree_emits_conflict():
    md_text = _canonical([f for f in CLAUDE_FLAGS if f != "--worktree"])
    conflicts = cv.ContrarianValidator().recheck_coding_agent_execution_contract(
        md_text, _contract(list(CLAUDE_FLAGS), canonical=md_text))
    assert any("--worktree" in c.contrarian_observation for c in conflicts)

def test_reconcile_final_state_precedence():
    v = cv.ContrarianValidator()
    v.conflicts = [
        cv.Conflict(check_id="a", resolution="kept_original"),
        cv.Conflict(check_id="b", resolution="downgraded_to_attempted"),
        cv.Conflict(check_id="c", resolution="escalated_as_execution_time_required")]
    assert v.reconcile().final_state == "some-claims-escalated-to-execution-time"

def test_task_list_validator_rejects_evidence_without_reconciliation(tmp_path):
    p = tmp_path / "x-tdd-tasks.yaml"; p.write_text(EVIDENCE_NO_RECONCILE)
    proc = _run([sys.executable, str(TASK_VALIDATOR), str(p)])
    assert proc.returncode != 0
    assert "reconciliation" in (proc.stdout + proc.stderr).lower()

def test_standalone_dry_run_against_fixture(tmp_path):
    p = tmp_path / "f-tdd-tasks.yaml"; p.write_text(DRY_RUN_FIXTURE)
    proc = _run([sys.executable, str(RUN_SCRIPT), "--dry-run", str(p)])
    assert proc.returncode == 0
    assert "final_state" in (proc.stdout + proc.stderr).lower()

def test_standalone_strict_exits_two_on_escalation(tmp_path):
    p = tmp_path / "f-tdd-tasks.yaml"; p.write_text(STRICT_FIXTURE)
    proc = _run([sys.executable, str(RUN_SCRIPT), "--strict", str(p)])
    assert proc.returncode == 2
    out = (proc.stdout + proc.stderr).lower()
    assert "escalat" in out or "final_state" in out
