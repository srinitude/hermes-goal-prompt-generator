from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .core import prepare_goal_prompt


def validate_task_list(path: Path | None) -> tuple[bool, str]:
    if path is None:
        return False, "missing task list path"
    root = Path(__file__).resolve().parents[2]
    validator = root / "scripts" / "validate_task_list_yaml.py"
    result = subprocess.run([sys.executable, str(validator), str(path)], capture_output=True, text=True)
    output = (result.stdout or result.stderr).strip()
    return result.returncode == 0, output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an isolated Hermes goal Markdown prompt plus paired TDD YAML."
    )
    parser.add_argument("prompt", nargs="*", help="Raw prompt text")
    parser.add_argument("--input-file", help="Explicit existing generated .md file to reuse or regenerate")
    parser.add_argument(
        "--dir",
        default=".",
        help="Directory where generated Markdown should be saved. Defaults to cwd.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prompt = str(Path(args.input_file).expanduser()) if args.input_file else " ".join(args.prompt).strip()
    prompt = prompt or sys.stdin.read().strip()
    if not prompt:
        print("error: prompt is required via argv, --input-file, or stdin", file=sys.stderr)
        return 2

    prepared = prepare_goal_prompt(prompt, execution_dir=Path(args.dir), allow_existing_path=bool(args.input_file))
    task_list_valid, task_list_validation = validate_task_list(prepared.task_list_path)
    payload = {
        "file_path": str(prepared.file_path),
        "status": prepared.status,
        "title": prepared.title,
        "source_prompt_hash": prepared.source_prompt_hash,
        "task_list_path": str(prepared.task_list_path) if prepared.task_list_path else "",
        "task_list_valid": task_list_valid,
        "task_list_validation": task_list_validation,
        "handoff_prompt": prepared.handoff_prompt,
        "valid": prepared.validation.valid,
        "reasons": prepared.validation.reasons,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Optimized isolated goal file ({prepared.status}): {prepared.file_path}")
        print(f"Paired TDD task list: {prepared.task_list_path}")
        print(f"Title: {prepared.title}")
        print(f"Source prompt hash: {prepared.source_prompt_hash}")
        print(f"Validation: {'valid' if prepared.validation.valid else 'invalid'}")
        print(f"Task list validation: {'valid' if task_list_valid else 'invalid'}")
        if task_list_validation:
            print(task_list_validation)
        for reason in prepared.validation.reasons:
            print(f"- {reason}")
        if prepared.handoff_prompt:
            print(prepared.handoff_prompt)
    return 0 if prepared.validation.valid and task_list_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
