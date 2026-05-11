from __future__ import annotations

from .constants import AUTONOMY, CLAUDE_CLI_EXECUTION_CONTRACT, CLAUDE_CLI_REQUIRED_FLAGS, GOAL_RUNTIME_CONTINUATION_CONTRACT, REQUIRED_SECTIONS, SOFTWARE_CLEANUP_REQUIREMENT, SOFTWARE_ENGINEERING_PRINCIPLES, VERSION
from .models import ValidationResult

# Generator versions whose immutable, already-generated goal contracts the
# current validator must continue to accept verbatim. Re-initialized at
# 0.1.0 (the first published release), so this tuple is intentionally
# empty for now. When `VERSION` is bumped in a future release, append the
# previous `VERSION` value here so previously generated Markdown files do
# not silently invalidate after the bump.
LEGACY_GENERATOR_VERSIONS: tuple[str, ...] = ()


def parse_metadata(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"\'')
    return meta


def accepted_generator_versions() -> tuple[str, ...]:
    """Return every goal_prompt_generator_version literal the validator accepts."""
    return (VERSION, *LEGACY_GENERATOR_VERSIONS)


def _validate_metadata(meta: dict[str, str]) -> list[str]:
    reasons: list[str] = []
    fixed_meta = {
        "generated_by": "goal-prompt-generator",
        "optimized_for": "hermes-agent-goal",
        "optimization_status": "optimized",
    }
    for key, value in fixed_meta.items():
        if meta.get(key) != value:
            reasons.append(f"metadata {key} must equal {value}")
    accepted = accepted_generator_versions()
    if meta.get("goal_prompt_generator_version") not in accepted:
        listing = ", ".join(accepted)
        reasons.append(f"metadata goal_prompt_generator_version must be one of: {listing}")
    for required in ("source_prompt_hash", "generated_at", "domain"):
        if not meta.get(required):
            reasons.append(f"{required} is required")
    if meta.get("domain_confidence") not in {"high", "moderate", "low"}:
        reasons.append("domain_confidence must be high, moderate, or low")
    return reasons


def _validate_structure(text: str, meta: dict[str, str]) -> list[str]:
    reasons: list[str] = []
    # LEGACY_GENERATOR_VERSIONS tracks every prior `VERSION` value whose
    # already-shipped contracts on disk we still want to accept. Currently
    # empty because `0.1.0` is the first published release. When a future
    # release bumps `VERSION`, append the previous value here and add any
    # newly-introduced required sections to ``legacy_optional_sections`` so
    # older contracts continue to validate after the bump.
    legacy = meta.get("goal_prompt_generator_version") in LEGACY_GENERATOR_VERSIONS
    legacy_optional_sections: set[str] = set()
    for section in REQUIRED_SECTIONS:
        if legacy and section in legacy_optional_sections:
            continue
        if f"## {section}" not in text:
            reasons.append(f"missing section: {section}")
    if AUTONOMY not in text:
        reasons.append("autonomy requirement missing")
    if not legacy and GOAL_RUNTIME_CONTINUATION_CONTRACT not in text:
        reasons.append("goal runtime continuation contract missing")
    if "Do not execute this prompt while generating it." not in text:
        reasons.append("non-execution guardrail missing")
    if "## Acceptance Criteria" not in text or "## Validation Commands" not in text:
        reasons.append("acceptance criteria and validation requirements missing")
    domain = meta.get("domain", "uncertain")
    confidence = meta.get("domain_confidence", "low")
    if (domain in {"software-development", "uncertain"} or confidence == "low") and "## Software Development Constraints" not in text:
        reasons.append("software-development constraints missing")
    if domain == "software-development" and SOFTWARE_CLEANUP_REQUIREMENT not in text:
        reasons.append("software-development cleanup requirement missing")
    if domain == "software-development" and SOFTWARE_ENGINEERING_PRINCIPLES not in text:
        reasons.append("software engineering core principles missing")
    if CLAUDE_CLI_EXECUTION_CONTRACT not in text:
        reasons.append("claude CLI execution contract missing")
    if "<instructions-from-hermes-agent>" not in text:
        if not (legacy and "positional prompt argument" in text):
            reasons.append("claude CLI positional prompt argument missing")
    for name, _placeholder in CLAUDE_CLI_REQUIRED_FLAGS:
        if name not in text:
            reasons.append(f"required claude CLI flag missing: {name}")
    return reasons


def validate_optimized_markdown(text: str) -> ValidationResult:
    meta = parse_metadata(text or "")
    reasons = _validate_metadata(meta) + _validate_structure(text, meta)
    return ValidationResult(not reasons, reasons, meta)
