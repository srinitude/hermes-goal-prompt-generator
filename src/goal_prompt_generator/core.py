from __future__ import annotations

from .constants import AUTONOMY, CLAUDE_CLI_EXECUTION_CONTRACT, CLAUDE_CLI_REQUIRED_FLAGS, GOAL_RUNTIME_CONTINUATION_CONTRACT, SOFTWARE_CLEANUP_REQUIREMENT, SOFTWARE_CONSTRAINTS, SOFTWARE_ENGINEERING_PRINCIPLES, VERSION
from .executors import (
    EXECUTOR_CATALOG,
    canonical_invocation_for,
    detect_installed_executors,
    resolve_executor_choice,
)
from .markdown import build_optimized_markdown
from .models import PreparedGoal, ValidationResult
from .prepare import prepare_goal_prompt
from .repository import render_repository_context_markdown, repository_evidence, workdir_path
from .tasklist import build_task_list, handoff_prompt, task_list_path, write_task_list
from .text import classify_domain, stable_hash
from .validation import parse_metadata, validate_optimized_markdown

__all__ = [
    "AUTONOMY",
    "CLAUDE_CLI_EXECUTION_CONTRACT",
    "CLAUDE_CLI_REQUIRED_FLAGS",
    "EXECUTOR_CATALOG",
    "GOAL_RUNTIME_CONTINUATION_CONTRACT",
    "SOFTWARE_CONSTRAINTS",
    "SOFTWARE_CLEANUP_REQUIREMENT",
    "SOFTWARE_ENGINEERING_PRINCIPLES",
    "VERSION",
    "PreparedGoal",
    "ValidationResult",
    "build_optimized_markdown",
    "build_task_list",
    "canonical_invocation_for",
    "classify_domain",
    "detect_installed_executors",
    "handoff_prompt",
    "parse_metadata",
    "prepare_goal_prompt",
    "render_repository_context_markdown",
    "repository_evidence",
    "resolve_executor_choice",
    "stable_hash",
    "task_list_path",
    "validate_optimized_markdown",
    "workdir_path",
    "write_task_list",
]
