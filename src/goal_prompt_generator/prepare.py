from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .constants import default_output_dir
from .markdown import build_optimized_markdown
from .models import PreparedGoal, ValidationResult
from .repository import repository_evidence
from .tasklist import handoff_prompt, write_task_list
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
    if not candidate.endswith(".md"):
        return None
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        path = directory / path
    return path if path.exists() and path.is_file() else None


def _prepared(text: str, path: Path, status: str, source_hash: str, title: str, validation: ValidationResult, repository: dict | None = None, executor: str | None = None) -> PreparedGoal:
    task_path = write_task_list(path, source_hash, title, repository=repository, executor=executor)
    return PreparedGoal(text, path, status, source_hash, title, validation, task_path, handoff_prompt(path, task_path))


def _valid_existing(text: str, path: Path, status: str, repository: dict | None, executor: str | None = None) -> PreparedGoal | None:
    validation = validate_optimized_markdown(text)
    if not validation.valid:
        return None
    title = markdown_title(text) or make_title(text)
    return _prepared(text, path, status, validation.metadata["source_prompt_hash"], title, validation, repository=repository, executor=executor)


def prepare_goal_prompt(
    prompt: str,
    execution_dir: str | Path | None = None,
    now: datetime | None = None,
    allow_existing_path: bool = False,
    workdir: str | Path | None = None,
    executor: str | None = None,
) -> PreparedGoal:
    directory = Path(execution_dir).expanduser().resolve() if execution_dir else default_output_dir()
    directory.mkdir(parents=True, exist_ok=True)
    raw = (prompt or "").strip()
    repo = repository_evidence(workdir)
    existing = path_candidate(raw, directory) if allow_existing_path else None
    if existing:
        text = existing.read_text(encoding="utf-8")
        prepared = _valid_existing(text, existing, "reused", repo, executor=executor)
        if prepared:
            return prepared
        raw = text
    else:
        validation = validate_optimized_markdown(raw)
        if validation.valid:
            title = markdown_title(raw) or make_title(raw)
            path = unique_path(directory, title)
            path.write_text(raw, encoding="utf-8")
            return _prepared(raw, path, "validated-saved", validation.metadata["source_prompt_hash"], title, validation, repository=repo, executor=executor)

    text = build_optimized_markdown(raw, now, repository=repo)
    validation = validate_optimized_markdown(text)
    if not validation.valid:
        raise ValueError("generated goal failed validation: " + "; ".join(validation.reasons))
    title = make_title(raw)
    path = unique_path(directory, title)
    path.write_text(text, encoding="utf-8")
    status = "regenerated" if existing else "generated"
    return _prepared(text, path, status, validation.metadata["source_prompt_hash"], title, validation, repository=repo, executor=executor)
