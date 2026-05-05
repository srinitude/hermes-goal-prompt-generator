"""Standalone helpers for the Hermes Agent goal-prompt-generator skill."""

from .core import (
    AUTONOMY,
    SOFTWARE_CONSTRAINTS,
    VERSION,
    PreparedGoal,
    ValidationResult,
    build_optimized_markdown,
    classify_domain,
    parse_metadata,
    prepare_goal_prompt,
    stable_hash,
    validate_optimized_markdown,
)

__all__ = [
    "AUTONOMY",
    "SOFTWARE_CONSTRAINTS",
    "VERSION",
    "PreparedGoal",
    "ValidationResult",
    "build_optimized_markdown",
    "classify_domain",
    "parse_metadata",
    "prepare_goal_prompt",
    "stable_hash",
    "validate_optimized_markdown",
]
