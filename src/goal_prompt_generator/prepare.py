from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .markdown import build_optimized_markdown
from .models import PreparedGoal
from .text import make_title, markdown_title, slug
from .validation import validate_optimized_markdown


def unique_path(directory: Path, title: str) -> Path:
    base = slug(title)
    path = directory / base
    if not path.exists():
        return path
    stem = path.stem
    for idx in range(2, 1000):
        candidate = directory / f"{stem}-{idx}.md"
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"too many filename collisions for {base}")


def path_candidate(raw: str, directory: Path) -> Path | None:
    if "\n" in raw or len(raw) > 500:
        return None
    candidate = raw.strip().strip('"\'')
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        path = directory / path
    return path if path.exists() and path.is_file() else None


def _valid_existing(text: str, path: Path, status: str) -> PreparedGoal | None:
    validation = validate_optimized_markdown(text)
    if not validation.valid:
        return None
    title = markdown_title(text) or make_title(text)
    return PreparedGoal(text, path, status, validation.metadata["source_prompt_hash"], title, validation)


def prepare_goal_prompt(
    prompt: str,
    execution_dir: str | Path | None = None,
    now: datetime | None = None,
) -> PreparedGoal:
    directory = Path(execution_dir or Path.cwd()).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    raw = (prompt or "").strip()
    existing = path_candidate(raw, directory)
    if existing:
        text = existing.read_text(encoding="utf-8")
        prepared = _valid_existing(text, existing, "reused")
        if prepared:
            return prepared
        raw = text
    else:
        validation = validate_optimized_markdown(raw)
        if validation.valid:
            title = markdown_title(raw) or make_title(raw)
            path = unique_path(directory, title)
            path.write_text(raw, encoding="utf-8")
            return PreparedGoal(raw, path, "validated-saved", validation.metadata["source_prompt_hash"], title, validation)

    text = build_optimized_markdown(raw, now)
    validation = validate_optimized_markdown(text)
    if not validation.valid:
        raise ValueError("generated goal failed validation: " + "; ".join(validation.reasons))
    path = unique_path(directory, make_title(raw))
    path.write_text(text, encoding="utf-8")
    status = "regenerated" if existing else "generated"
    return PreparedGoal(text, path, status, validation.metadata["source_prompt_hash"], make_title(raw), validation)
