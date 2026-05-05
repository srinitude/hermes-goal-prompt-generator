from __future__ import annotations

import hashlib
import re

from .constants import DOMAIN_TERMS, SOFTWARE_TERMS, STOP


def stable_hash(prompt: str) -> str:
    return hashlib.sha256((prompt or "").encode("utf-8")).hexdigest()


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9.+#_-]*", (text or "").lower())


def classify_domain(prompt: str) -> tuple[str, str]:
    tokens = words(prompt)
    soft = sum(1 for token in tokens if token in SOFTWARE_TERMS or token.replace("-", "") in SOFTWARE_TERMS)
    if soft:
        return "software-development", "high" if soft > 1 else "moderate"
    scores = [(name, len(set(tokens) & terms)) for name, terms in DOMAIN_TERMS.items()]
    domain, score = max(scores, key=lambda item: item[1]) if scores else ("uncertain", 0)
    if score:
        return domain, "high" if score > 1 else "moderate"
    return "uncertain", "low"


def make_title(prompt: str) -> str:
    candidates = [word.replace(".", "") for word in words(prompt.strip()) if word not in STOP]
    chosen = candidates[:5] or ["optimized", "goal"]
    title = " ".join(word.upper() if word in {"api", "cli", "sdk", "ci", "cd"} else word for word in chosen)
    return title[:1].upper() + title[1:]


def markdown_title(text: str) -> str | None:
    for line in (text or "").splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            return title[:-5] if title.endswith(" Goal") else title
    return None


def slug(title: str) -> str:
    slugged = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if slugged in {"prompt", "enhanced", "output", "optimized", "goal"} or len(slugged) < 4:
        slugged = "structured-goal"
    return f"{slugged[:60].strip('-')}-goal.md"
