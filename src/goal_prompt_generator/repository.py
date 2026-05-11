"""Deep repository/codebase context exploration for goal prompts.

The generator runs in the *invoking* repository: the cwd (or an explicit
``workdir`` override) is the codebase the user wants to act on. Before we
freeze a goal contract we MUST surface enough of that codebase so the
downstream coding agent does not flail through discovery — VCS state,
manifests, lockfiles, agent-context files (AGENTS.md / CLAUDE.md /
.cursorrules), CI config, primary languages, and a curated short list of
repository-level "key paths" that any task should treat as canonical
context_files.

This module is intentionally stdlib-only: no PyYAML, no shellouts beyond a
small set of bounded ``git`` reads. It must work when ``firecrawl`` and
``opensrc`` are unavailable.

Public surface: :func:`repository_evidence` and :func:`workdir_path`.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

# Files we always lift into the curated key_paths list when present. Order
# is meaningful — earlier entries are higher signal for a coding agent.
_AGENT_CONTEXT_FILES = (
    "AGENTS.md", "CLAUDE.md", ".cursorrules", ".cursor/rules", ".github/copilot-instructions.md",
    "CONTRIBUTING.md", "ARCHITECTURE.md", "DESIGN.md", "README.md", "Readme.md", "readme.md",
)
_MANIFEST_FILES = (
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json", "deno.json", "deno.jsonc", "bun.lock", "bunfig.toml",
    "Cargo.toml", "go.mod", "Gemfile", "composer.json", "pom.xml", "build.gradle",
    "build.gradle.kts", "Package.swift", "mix.exs", "pubspec.yaml",
    "Dockerfile", "docker-compose.yml", "compose.yaml", "Makefile", "justfile",
    "mise.toml", ".tool-versions", "Procfile",
)
_LOCKFILES = (
    "uv.lock", "poetry.lock", "Pipfile.lock", "package-lock.json", "yarn.lock",
    "pnpm-lock.yaml", "bun.lockb", "Cargo.lock", "go.sum", "Gemfile.lock",
    "composer.lock", "mix.lock", "pubspec.lock",
)
_CI_PATHS = (
    ".github/workflows", ".gitlab-ci.yml", ".circleci/config.yml", "azure-pipelines.yml",
    ".buildkite", ".travis.yml", "Jenkinsfile",
)
# Filename glob → primary language. First matched extension wins per file;
# we count files and report the top languages by file count.
_LANGUAGE_EXT = {
    ".py": "Python", ".pyi": "Python",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".rs": "Rust", ".go": "Go", ".rb": "Ruby", ".php": "PHP",
    ".java": "Java", ".kt": "Kotlin", ".scala": "Scala", ".swift": "Swift",
    ".c": "C", ".h": "C", ".cc": "C++", ".cpp": "C++", ".hpp": "C++", ".hh": "C++",
    ".cs": "C#", ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang",
    ".dart": "Dart", ".lua": "Lua", ".sh": "Shell", ".bash": "Shell", ".fish": "Shell", ".zsh": "Shell",
    ".sql": "SQL", ".tf": "Terraform", ".hcl": "HCL",
    ".md": "Markdown", ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".json": "JSON",
}
# Directories we never descend into when scanning for languages or top-level
# layout — they bloat the picture without adding signal.
_IGNORED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".tox", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
    "target", ".next", ".nuxt", ".turbo", ".cache", ".gradle", ".idea", ".vscode",
    "vendor", "bower_components", ".terraform",
}
_MAX_LANGUAGE_FILES = 4000  # cap so very large repos don't stall generation
_MAX_TOP_LEVEL_ENTRIES = 40
_MAX_KEY_PATHS = 24
_CLAUDE_WORKTREE_ROOT = Path(".claude") / "worktrees"

# Every coding-agent CLI the skill drives places its worktrees under its own
# dotdir inside the *active* repo root. Because `repo_root` is git's
# `--show-toplevel` (the active worktree root, not the parent checkout), every
# executor worktree automatically lives inside the active Hermes
# `.worktrees/hermes-*` checkout when Hermes itself is running from one.
# The catalog ordering mirrors `executors.EXECUTOR_CATALOG` so the validator
# and emitter agree on which dotdir each executor owns.
_EXECUTOR_WORKTREE_DOTDIRS: dict[str, str] = {
    "claude": ".claude/worktrees",
    "codex": ".codex/worktrees",
    "opencode": ".opencode/worktrees",
    "gemini": ".gemini/worktrees",
    "cursor": ".cursor/worktrees",
    "aider": ".aider/worktrees",
    "pi": ".pi/worktrees",
    "qwen": ".qwen/worktrees",
    "goose": ".goose/worktrees",
    "amp": ".amp/worktrees",
    "crush": ".crush/worktrees",
    "hermes": ".hermes/worktrees",
}


@dataclass(frozen=True)
class _GitState:
    head_sha: str = ""
    branch: str = ""
    remote_url: str = ""
    dirty: bool | None = None
    repo_root: str = ""


def workdir_path(workdir: str | os.PathLike[str] | None) -> Path:
    """Return the absolute, expanded workdir, defaulting to the cwd."""
    raw = workdir if workdir is not None else Path.cwd()
    return Path(raw).expanduser().resolve()


def _git(args: list[str], cwd: Path, timeout: int = 5) -> tuple[int | None, str]:
    if not shutil.which("git"):
        return None, ""
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
    except Exception:
        return None, ""
    return result.returncode, (result.stdout or "").strip()


def _git_state(workdir: Path) -> _GitState:
    code, root = _git(["rev-parse", "--show-toplevel"], workdir)
    if code != 0 or not root:
        return _GitState()
    repo_root = root
    _, head = _git(["rev-parse", "HEAD"], workdir)
    _, branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], workdir)
    _, remote = _git(["remote", "get-url", "origin"], workdir)
    code_status, status = _git(["status", "--porcelain"], workdir)
    dirty: bool | None = bool(status) if code_status == 0 else None
    return _GitState(head_sha=head, branch=branch, remote_url=remote, dirty=dirty, repo_root=repo_root)


def _exists_relative(workdir: Path, relpath: str) -> bool:
    candidate = (workdir / relpath)
    return candidate.exists()


def _present(workdir: Path, names: Iterable[str]) -> list[str]:
    return [name for name in names if _exists_relative(workdir, name)]


def _top_level_entries(workdir: Path) -> list[str]:
    if not workdir.is_dir():
        return []
    entries = []
    for entry in sorted(workdir.iterdir()):
        if entry.name in _IGNORED_DIRS:
            continue
        suffix = "/" if entry.is_dir() else ""
        entries.append(f"{entry.name}{suffix}")
        if len(entries) >= _MAX_TOP_LEVEL_ENTRIES:
            break
    return entries


def _language_breakdown(workdir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not workdir.is_dir():
        return counts
    seen = 0
    for root, dirs, files in os.walk(workdir):
        # prune ignored dirs in place (os.walk respects mutation)
        dirs[:] = [d for d in dirs if d not in _IGNORED_DIRS and not d.startswith(".")]
        for fname in files:
            ext = Path(fname).suffix.lower()
            language = _LANGUAGE_EXT.get(ext)
            if not language:
                continue
            counts[language] = counts.get(language, 0) + 1
            seen += 1
            if seen >= _MAX_LANGUAGE_FILES:
                return counts
    return counts


def _primary_languages(counts: dict[str, int], top: int = 5) -> list[dict[str, Any]]:
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"language": lang, "file_count": count} for lang, count in items[:top]]


def _agent_context_text(workdir: Path) -> dict[str, str]:
    """Read short excerpts from agent-context files. Bounded so we don't bloat output."""
    excerpts: dict[str, str] = {}
    for name in _AGENT_CONTEXT_FILES:
        path = workdir / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # First 800 chars — enough for the high-signal preamble most agent-context files put up top.
        excerpts[name] = re.sub(r"\s+\Z", "", text[:800])
        if len(excerpts) >= 3:
            break
    return excerpts


def _curated_key_paths(workdir: Path, manifests: list[str], lockfiles: list[str], agent_context: list[str], ci_paths: list[str]) -> list[str]:
    # Highest signal first: agent-context, then manifests, lockfiles, CI config, then a couple of obvious source dirs.
    ordered: list[str] = []
    seen: set[str] = set()
    for bucket in (agent_context, manifests, lockfiles, ci_paths):
        for entry in bucket:
            if entry in seen:
                continue
            ordered.append(entry)
            seen.add(entry)
            if len(ordered) >= _MAX_KEY_PATHS:
                return [str((workdir / e).resolve()) for e in ordered]
    claude_worktree_root = str(_CLAUDE_WORKTREE_ROOT)
    if (workdir / _CLAUDE_WORKTREE_ROOT).is_dir() and claude_worktree_root not in seen:
        ordered.append(claude_worktree_root)
        seen.add(claude_worktree_root)
        if len(ordered) >= _MAX_KEY_PATHS:
            return [str((workdir / e).resolve()) for e in ordered]
    # Add canonical source roots if they exist.
    for candidate in ("src", "lib", "app", "internal", "cmd", "pkg", "packages", "apps", "tests", "test"):
        if (workdir / candidate).is_dir() and candidate not in seen:
            ordered.append(candidate + "/")
            seen.add(candidate)
            if len(ordered) >= _MAX_KEY_PATHS:
                break
    return [str((workdir / entry.rstrip("/")).resolve()) + ("/" if entry.endswith("/") else "") for entry in ordered]


def _claude_worktree_evidence(repo_root: Path) -> dict[str, Any]:
    root = repo_root / _CLAUDE_WORKTREE_ROOT
    entries: list[str] = []
    if root.is_dir():
        entries = sorted(p.name for p in root.iterdir() if p.is_dir())
    return {
        "flag": "--worktree",
        "short_flag": "-w",
        "root": str(root.resolve(strict=False)),
        "directory_template": str((root / "<worktree-name>").resolve(strict=False)),
        "exists": root.is_dir(),
        "existing_worktrees": entries,
        "resolution_rule": "Claude Code resolves --worktree/-w inside the active repository root, so when Hermes itself is running from a .worktrees/hermes-* checkout the Claude worktree lives under that Hermes worktree's .claude/worktrees/<worktree-name> directory.",
    }


def _executor_worktree_evidence(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Build the worktree-directory snapshot for every executor in the catalog.

    Every entry resolves under ``repo_root`` (i.e. the active Hermes
    ``.worktrees/hermes-*`` checkout when running from one), so every coding
    agent that consumes the generated contract roots its working files inside
    the Hermes worktree — never at an arbitrary parent or a sibling checkout.
    """
    out: dict[str, dict[str, Any]] = {}
    for executor, dotdir in _EXECUTOR_WORKTREE_DOTDIRS.items():
        root = repo_root / dotdir
        entries: list[str] = []
        if root.is_dir():
            entries = sorted(p.name for p in root.iterdir() if p.is_dir())
        out[executor] = {
            "flag": "--worktree",
            "short_flag": "-w",
            "root": str(root.resolve(strict=False)),
            "directory_template": str((root / "<worktree-name>").resolve(strict=False)),
            "exists": root.is_dir(),
            "existing_worktrees": entries,
            "resolution_rule": (
                f"{executor} resolves its worktree under the active repository root, so when "
                f"Hermes itself is running from a .worktrees/hermes-* checkout the {executor} "
                f"worktree lives under that Hermes worktree's {dotdir}/<worktree-name> directory."
            ),
        }
    return out


def repository_evidence(workdir: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Return a structured snapshot of the invoking repository.

    Always returns a dict with the same shape so downstream consumers (the
    Markdown renderer, the YAML emitter, the contrarian validator) can rely
    on stable keys. Missing tools (no ``git``, no manifests, etc.) downgrade
    individual fields to empty strings / lists rather than failing the whole
    snapshot.
    """
    root = workdir_path(workdir)
    state = _git_state(root)
    repo_root = Path(state.repo_root) if state.repo_root else root
    manifests = _present(repo_root, _MANIFEST_FILES)
    lockfiles = _present(repo_root, _LOCKFILES)
    agent_files = _present(repo_root, _AGENT_CONTEXT_FILES)
    ci_paths = _present(repo_root, _CI_PATHS)
    languages = _primary_languages(_language_breakdown(repo_root))
    agent_excerpts = _agent_context_text(repo_root)
    key_paths = _curated_key_paths(repo_root, manifests, lockfiles, agent_files, ci_paths)
    claude_worktree = _claude_worktree_evidence(repo_root)
    executor_worktrees = _executor_worktree_evidence(repo_root)
    return {
        "workdir": str(root),
        "repo_root": str(repo_root),
        "is_git_repo": bool(state.repo_root),
        "vcs": {
            "head_sha": state.head_sha,
            "branch": state.branch,
            "remote_url": state.remote_url,
            "dirty": state.dirty,
        },
        "manifests": manifests,
        "lockfiles": lockfiles,
        "agent_context_files": agent_files,
        "agent_context_excerpts": agent_excerpts,
        "ci_paths": ci_paths,
        "top_level_entries": _top_level_entries(repo_root),
        "primary_languages": languages,
        "key_paths": key_paths,
        "claude_worktree": claude_worktree,
        "executor_worktrees": executor_worktrees,
    }


def render_repository_context_markdown(evidence: dict[str, Any]) -> str:
    """Render the repository_evidence dict as the goal Markdown's ``## Repository Context`` section.

    The body intentionally lists concrete absolute paths and the head SHA so a
    downstream coding agent can verify the contract without re-discovering the
    same facts.
    """
    vcs = evidence.get("vcs") or {}
    languages = evidence.get("primary_languages") or []
    lang_line = ", ".join(f"{l['language']} ({l['file_count']})" for l in languages) or "(no recognized source files at workdir)"
    manifests = evidence.get("manifests") or []
    lockfiles = evidence.get("lockfiles") or []
    agent_files = evidence.get("agent_context_files") or []
    ci_paths = evidence.get("ci_paths") or []
    key_paths = evidence.get("key_paths") or []
    top_level = evidence.get("top_level_entries") or []
    is_git = evidence.get("is_git_repo")
    workdir = evidence.get("workdir") or ""
    repo_root = evidence.get("repo_root") or workdir

    lines: list[str] = ["## Repository Context", ""]
    lines.append("This goal was generated against a concrete repository. Treat the snapshot below as the canonical")
    lines.append("starting context; the downstream coding agent MUST read every key path before producing a diff and")
    lines.append("MUST honor the existing repository conventions discovered there.")
    lines.append("")
    lines.append("### Workdir")
    lines.append("")
    lines.append(f"- workdir: `{workdir}`")
    lines.append(f"- repo_root: `{repo_root}`")
    lines.append(f"- vcs: {'git' if is_git else 'none-or-unavailable'}")
    if is_git:
        lines.append(f"- branch: `{vcs.get('branch') or '(detached)'}`")
        lines.append(f"- head_sha: `{vcs.get('head_sha') or '(unknown)'}`")
        if vcs.get("remote_url"):
            lines.append(f"- remote_url: `{vcs.get('remote_url')}`")
        dirty = vcs.get("dirty")
        if dirty is True:
            lines.append("- worktree: dirty (uncommitted changes present at generation time)")
        elif dirty is False:
            lines.append("- worktree: clean at generation time")
    lines.append("")
    claude = evidence.get("claude_worktree") or {}
    lines.append("### Claude Code worktree directory")
    lines.append("")
    lines.append("- invocation flag: `--worktree` / `-w`")
    lines.append(f"- directory root: `{claude.get('root') or str(Path(repo_root) / '.claude' / 'worktrees')}`")
    lines.append(f"- directory template: `{claude.get('directory_template') or str(Path(repo_root) / '.claude' / 'worktrees' / '<worktree-name>')}`")
    lines.append(f"- root_exists: `{bool(claude.get('exists'))}`")
    existing = claude.get("existing_worktrees") or []
    lines.append(f"- existing_worktrees: {', '.join(existing) if existing else '(none detected)'}")
    lines.append("- resolution: Claude Code resolves the worktree name under the active repository root; when Hermes is already running from `.worktrees/hermes-*`, this Claude worktree directory stays inside that current Hermes worktree.")
    lines.append("")
    lines.append("### Primary languages")
    lines.append("")
    lines.append(f"- {lang_line}")
    lines.append("")
    lines.append("### Top-level layout")
    lines.append("")
    if top_level:
        lines.append("```")
        lines.extend(top_level)
        lines.append("```")
    else:
        lines.append("- (workdir is empty or unreadable)")
    lines.append("")
    lines.append("### Manifests, lockfiles, CI, and agent-context files")
    lines.append("")
    lines.append(f"- manifests: {', '.join(manifests) if manifests else '(none detected)'}")
    lines.append(f"- lockfiles: {', '.join(lockfiles) if lockfiles else '(none detected)'}")
    lines.append(f"- ci_paths: {', '.join(ci_paths) if ci_paths else '(none detected)'}")
    lines.append(f"- agent_context_files: {', '.join(agent_files) if agent_files else '(none detected)'}")
    lines.append("")
    lines.append("### Curated key paths (read these before changing anything)")
    lines.append("")
    if key_paths:
        for entry in key_paths:
            lines.append(f"- `{entry}`")
    else:
        lines.append("- (no canonical key paths detected — perform a fresh discovery pass before editing)")
    lines.append("")
    lines.append("### Repository validation rules")
    lines.append("")
    lines.append("- Do not fabricate file paths that are not in this repository; verify every cited path exists before editing.")
    lines.append("- Preserve the conventions surfaced by manifests, lockfiles, CI configs, and agent-context files unless the goal explicitly requires changing them.")
    lines.append("- If a key path listed above no longer exists at execution time, treat it as a blocker and record the divergence under `learnings`/`gotchas` before continuing.")
    return "\n".join(lines).rstrip()
