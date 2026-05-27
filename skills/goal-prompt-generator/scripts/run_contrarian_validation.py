#!/usr/bin/env python3
"""Standalone contrarian re-verification CLI for generated TDD task-list YAMLs.

Loads each YAML, replays a practical ContrarianValidator pass against
``validation_evidence.firecrawl.required_maps_present`` and
``validation_evidence.opensrc.fetched``, prints one JSON summary that always
contains the per-YAML ``final_state``, and (unless ``--dry-run``) writes the
resulting ``validation_reconciliation`` block back into the YAML in place.

Exit codes:
  * ``--strict``: 2 if any YAML's ``final_state`` is
    ``some-claims-escalated-to-execution-time`` (per
    ``references/contrarian-validation.md``); no other final_state trips it.
  * Otherwise: 0 on success, 2 on argument/IO errors.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import yaml  # noqa: E402

from goal_prompt_generator.contrarian_validation import (  # noqa: E402
    Conflict,
    ContrarianValidator,
)

EXEC_TIME = "escalated_as_execution_time_required"
FINAL_ESCALATED = "some-claims-escalated-to-execution-time"


def _emit_escalated(
    validator: ContrarianValidator,
    check_id: str,
    target: str,
    claim: str,
    observation: str,
) -> Conflict:
    """Push an execution-time-required Conflict so --strict trips for missing evidence."""
    conflict = Conflict(
        check_id=check_id,
        evidence_target=target,
        original_claim=claim,
        contrarian_observation=observation,
        severity="error",
        resolution=EXEC_TIME,
    )
    validator.conflicts.append(conflict)
    return conflict


def _replay_firecrawl(validator: ContrarianValidator, fc_block: Any) -> None:
    """Replay firecrawl-map rechecks against every required_maps_present entry."""
    maps = (fc_block or {}).get("required_maps_present") or {}
    if not isinstance(maps, dict):
        return
    for tech, entry in maps.items():
        if not isinstance(entry, dict):
            _emit_escalated(
                validator,
                "firecrawl_map",
                str(tech),
                "required_maps_present entry shape",
                f"entry for {tech!r} is not a mapping",
            )
            continue
        path = entry.get("file")
        expected = entry.get("url_count")
        if isinstance(path, str) and path and isinstance(expected, int):
            validator.recheck_firecrawl_map(str(tech), path, expected)
            continue
        _emit_escalated(
            validator,
            "firecrawl_map",
            str(tech),
            f"required_maps_present[{tech}] usable evidence",
            f"missing live `file` and/or `url_count` for {tech!r}",
        )


def _replay_opensrc(validator: ContrarianValidator, osrc_block: Any) -> None:
    """Replay opensrc-path rechecks; escalate when key paths are absent on host."""
    fetched = (osrc_block or {}).get("fetched") or {}
    if not isinstance(fetched, dict):
        return
    for slug, entry in fetched.items():
        if not isinstance(entry, dict):
            _emit_escalated(
                validator,
                "opensrc_path_exists",
                str(slug),
                "opensrc.fetched entry shape",
                f"entry for {slug!r} is not a mapping",
            )
            continue
        key_paths = entry.get("key_paths") or []
        if not isinstance(key_paths, list) or not key_paths:
            _emit_escalated(
                validator,
                "opensrc_path_exists",
                str(slug),
                "opensrc.fetched key_paths non-empty",
                f"no usable key_paths recorded for {slug!r}",
            )
            continue
        for kp in key_paths:
            if not isinstance(kp, str) or not Path(kp).exists():
                _emit_escalated(
                    validator,
                    "opensrc_path_exists",
                    str(slug),
                    f"key_path accessible: {kp!r}",
                    f"opensrc cached key_path missing on host: {kp!r}",
                )


def _process_yaml(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a YAML, run the contrarian replay, attach validation_reconciliation."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: top-level YAML must be a mapping")
    evidence = data.get("validation_evidence") or {}
    validator = ContrarianValidator()
    _replay_firecrawl(validator, evidence.get("firecrawl"))
    _replay_opensrc(validator, evidence.get("opensrc"))
    rec_dict = validator.reconcile().to_dict()
    data["validation_reconciliation"] = rec_dict
    return data, rec_dict


def _write(path: Path, data: dict[str, Any]) -> None:
    """Persist the reconciled YAML in place with deterministic ordering."""
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay the contrarian re-verification pass against task-list YAMLs."
    )
    parser.add_argument(
        "yamls",
        nargs="+",
        help="One or more <project>-<intent>-tdd-tasks.yaml paths.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not mutate the YAML; only print the reconciliation summary.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 when any YAML escalates a claim to execution time.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary: list[dict[str, Any]] = []
    escalated = False
    for raw in args.yamls:
        path = Path(raw)
        if not path.exists():
            print(json.dumps({"path": str(path), "error": "file not found"}))
            return 2
        data, rec = _process_yaml(path)
        final_state = rec.get("final_state", "all-claims-reconciled")
        if final_state == FINAL_ESCALATED:
            escalated = True
        summary.append({
            "path": str(path),
            "final_state": final_state,
            "conflicts": len(rec.get("conflicts") or []),
        })
        if not args.dry_run:
            _write(path, data)
    print(json.dumps({"reconciliation": summary, "dry_run": args.dry_run}, indent=2))
    return 2 if (args.strict and escalated) else 0


if __name__ == "__main__":
    raise SystemExit(main())
