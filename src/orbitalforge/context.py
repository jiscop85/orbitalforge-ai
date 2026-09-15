from __future__ import annotations

import re
from pathlib import Path

from .config import ForgeConfig
from .models import ForgeState, Task


_TEXT_EXTENSIONS = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".csv"}


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text)}


def _tree(project_dir: Path, limit: int = 180) -> str:
    rows: list[str] = []
    for path in sorted(project_dir.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            rows.append(path.relative_to(project_dir).as_posix())
            if len(rows) >= limit:
                rows.append("... tree truncated ...")
                break
    return "\n".join(rows)


def _sample_for_scoring(path: Path, limit: int = 18000) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= limit:
        return text
    head = int(limit * 0.75)
    tail = limit - head
    return text[:head] + "\n... scoring sample truncated ...\n" + text[-tail:]


def _bounded_excerpt(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit < 500:
        return text[:limit]
    head = int(limit * 0.72)
    tail = limit - head - 48
    return text[:head] + "\n... file content truncated ...\n" + text[-max(0, tail):]


def collect_context(
    project_dir: Path, state: ForgeState, task: Task, config: ForgeConfig
) -> str:
    candidates: list[tuple[int, Path]] = []
    priority = {"PROJECT.md": 2000, "STATUS.md": 1900, "README.md": 1800, "pyproject.toml": 1200}
    query = _tokens(task.title + " " + task.instruction + " " + " ".join(task.acceptance_criteria))

    for path in project_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _TEXT_EXTENSIONS:
            continue
        rel = path.relative_to(project_dir).as_posix()
        score = priority.get(rel, 0)
        if rel in state.recent_files:
            score += 1100
        rel_tokens = _tokens(rel.replace("/", " "))
        score += 70 * len(query & rel_tokens)
        if path.suffix == ".py":
            score += 80
        try:
            sample_tokens = _tokens(_sample_for_scoring(path))
        except OSError:
            continue
        score += 14 * min(40, len(query & sample_tokens))
        candidates.append((score, path))

    candidates.sort(key=lambda item: (-item[0], item[1].as_posix()))
    tree = "--- FILE TREE ---\n" + _tree(project_dir)
    chunks = [tree]
    remaining = max(0, config.max_context_chars - len(tree))

    for _, path in candidates[: config.max_context_files]:
        if remaining <= 300:
            break
        rel = path.relative_to(project_dir).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        header = f"\n--- {rel} ---\n"
        allowance = min(config.max_context_file_chars, max(0, remaining - len(header)))
        if allowance <= 0:
            break
        excerpt = _bounded_excerpt(text, allowance)
        chunks.append(header + excerpt)
        remaining -= len(header) + len(excerpt)
    return "".join(chunks)


def collect_audit_context(
    project_dir: Path, max_chars: int = 140000, max_files: int = 36
) -> str:
    priority_names = {"PROJECT.md": 3000, "README.md": 2900, "STATUS.md": 2800, "pyproject.toml": 2500}
    candidates: list[tuple[int, Path]] = []
    for path in project_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _TEXT_EXTENSIONS:
            continue
        rel = path.relative_to(project_dir).as_posix()
        score = priority_names.get(rel, 0)
        if rel.startswith("src/"):
            score += 2000
        elif rel.startswith("tests/"):
            score += 1900
        elif rel.startswith("examples/") or rel.startswith("docs/"):
            score += 900
        if path.suffix == ".py":
            score += 300
        candidates.append((score, path))
    candidates.sort(key=lambda item: (-item[0], item[1].as_posix()))

    tree = "--- FILE TREE ---\n" + _tree(project_dir, limit=260)
    chunks = [tree]
    remaining = max(0, max_chars - len(tree))
    per_file_cap = max(2500, max_chars // max(1, max_files))
    for _, path in candidates[:max_files]:
        if remaining <= 300:
            break
        rel = path.relative_to(project_dir).as_posix()
        header = f"\n--- {rel} ---\n"
        text = path.read_text(encoding="utf-8", errors="replace")
        allowance = min(per_file_cap, max(0, remaining - len(header)))
        excerpt = _bounded_excerpt(text, allowance)
        chunks.append(header + excerpt)
        remaining -= len(header) + len(excerpt)
    return "".join(chunks)
