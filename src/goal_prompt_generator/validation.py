from __future__ import annotations

from .constants import AUTONOMY, REQUIRED_SECTIONS, SOFTWARE_CLEANUP_REQUIREMENT, SOFTWARE_ENGINEERING_PRINCIPLES, VERSION
from .models import ValidationResult


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


def validate_optimized_markdown(text: str) -> ValidationResult:
    meta = parse_metadata(text or "")
    reasons: list[str] = []
    required_meta = {
        "generated_by": "goal-prompt-generator",
        "goal_prompt_generator_version": VERSION,
        "optimized_for": "hermes-agent-goal",
        "optimization_status": "optimized",
    }
    for key, value in required_meta.items():
        if meta.get(key) != value:
            reasons.append(f"metadata {key} must equal {value}")
    if not meta.get("source_prompt_hash"):
        reasons.append("source_prompt_hash is required")
    if not meta.get("generated_at"):
        reasons.append("generated_at is required")
    if not meta.get("domain"):
        reasons.append("domain is required")
    if meta.get("domain_confidence") not in {"high", "moderate", "low"}:
        reasons.append("domain_confidence must be high, moderate, or low")
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in text:
            reasons.append(f"missing section: {section}")
    if AUTONOMY not in text:
        reasons.append("autonomy requirement missing")
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
    return ValidationResult(not reasons, reasons, meta)
