#!/usr/bin/env python3
"""Validate the repository is shaped as a Hermes Agent skill."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
REQUIRED_LINKED = [
    ROOT / "references" / "isolation-contract.md",
    ROOT / "references" / "implementation-validation-notes.md",
    ROOT / "references" / "local-validation.md",
    ROOT / "references" / "research-and-source-validation.md",
    ROOT / "templates" / "optimized-goal-template.md",
    ROOT / "scripts" / "generate_goal_prompt.py",
]


def _frontmatter_and_body(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise AssertionError("SKILL.md frontmatter must close with ---")
    body = text[end + 5 :].strip()
    if not body:
        raise AssertionError("SKILL.md body must be non-empty")
    return text[4:end], body


def _scalar(frontmatter: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", frontmatter, re.M)
    if not match:
        return ""
    value = match.group(1).strip().strip('"\'')
    return "" if value in {">", "|"} else value


def _folded_block(frontmatter: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*>\s*\n((?:  .+\n?)+)", frontmatter, re.M)
    if not match:
        return _scalar(frontmatter, key)
    return " ".join(line.strip() for line in match.group(1).splitlines()).strip()


def parse_frontmatter(text: str) -> dict[str, str]:
    frontmatter, _ = _frontmatter_and_body(text)
    return {
        "name": _scalar(frontmatter, "name"),
        "description": _folded_block(frontmatter, "description"),
    }


def main() -> int:
    text = SKILL.read_text(encoding="utf-8")
    metadata = parse_frontmatter(text)
    assert metadata.get("name") == "goal-prompt-generator"
    description = metadata.get("description", "")
    assert description, "description is required"
    assert len(description) <= 1024, "description exceeds Hermes limit"
    assert "<" not in description and ">" not in description
    assert len(text) <= 100_000, "SKILL.md exceeds Hermes content limit"
    for path in REQUIRED_LINKED:
        assert path.exists(), f"missing linked file: {path.relative_to(ROOT)}"
    print("skill package validation ok")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
