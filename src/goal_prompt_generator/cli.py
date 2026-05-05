from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import prepare_goal_prompt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or validate a Hermes /goal optimized Markdown prompt."
    )
    parser.add_argument("prompt", nargs="*", help="Raw prompt text or optimized .md path")
    parser.add_argument(
        "--dir",
        default=".",
        help="Directory where generated Markdown should be saved. Defaults to cwd.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prompt = " ".join(args.prompt).strip() or sys.stdin.read().strip()
    if not prompt:
        print("error: prompt is required via argv or stdin", file=sys.stderr)
        return 2

    prepared = prepare_goal_prompt(prompt, execution_dir=Path(args.dir))
    payload = {
        "file_path": str(prepared.file_path),
        "status": prepared.status,
        "title": prepared.title,
        "source_prompt_hash": prepared.source_prompt_hash,
        "valid": prepared.validation.valid,
        "reasons": prepared.validation.reasons,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Optimized goal file ({prepared.status}): {prepared.file_path}")
        print(f"Title: {prepared.title}")
        print(f"Source prompt hash: {prepared.source_prompt_hash}")
        print(f"Validation: {'valid' if prepared.validation.valid else 'invalid'}")
        for reason in prepared.validation.reasons:
            print(f"- {reason}")
    return 0 if prepared.validation.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
