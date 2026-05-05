#!/usr/bin/env python3
"""Generate a Hermes `/goal` optimized Markdown file without executing it."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))

from goal_prompt_generator.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
