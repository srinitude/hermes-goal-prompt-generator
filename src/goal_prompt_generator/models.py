from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reasons: list[str]
    metadata: dict[str, str]


@dataclass(frozen=True)
class PreparedGoal:
    goal_text: str
    file_path: Path
    status: str
    source_prompt_hash: str
    title: str
    validation: ValidationResult
    task_list_path: Path | None = None
    handoff_prompt: str = ""
