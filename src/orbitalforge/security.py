from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath

from .config import ForgeConfig
from .models import FileOperation


class SecurityError(RuntimeError):
    pass


_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)(api[_-]?key|secret|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
]

_DANGEROUS_OS_CALLS = {"system", "popen"}
_DANGEROUS_OS_PREFIXES = ("exec", "spawn")
_DANGEROUS_BUILTINS = {"eval", "exec", "compile", "__import__"}


def safe_target(project_dir: Path, operation: FileOperation, config: ForgeConfig) -> Path:
    normalized_path = operation.path.replace("\\", "/")
    if any(ord(char) < 32 or ord(char) == 127 for char in normalized_path):
        raise SecurityError(f"Control characters are not allowed in generated paths: {operation.path!r}")
    pure = PurePosixPath(normalized_path)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts:
        raise SecurityError(f"Unsafe generated path: {operation.path!r}")
    if any(part in {".github", ".git", ".autoforge"} for part in pure.parts):
        raise SecurityError(f"Protected generated path: {operation.path!r}")
    if pure.as_posix() in {"PROJECT.md", "STATUS.md"}:
        raise SecurityError(f"System-managed project file is protected: {operation.path!r}")
    lowered_parts = [part.lower() for part in pure.parts]
    for forbidden in config.forbidden_names:
        if any(part == forbidden or part.startswith(forbidden + ".") for part in lowered_parts):
            raise SecurityError(f"Forbidden generated filename: {operation.path!r}")
    suffix = Path(pure.name).suffix.lower()
    special = pure.name if pure.name.startswith(".") else ""
    if suffix not in config.allowed_extensions and special not in config.allowed_extensions:
        raise SecurityError(f"Disallowed extension: {operation.path!r}")
    target = (project_dir / Path(*pure.parts)).resolve()
    base = project_dir.resolve()
    if target != base and base not in target.parents:
        raise SecurityError(f"Path escaped project root: {operation.path!r}")
    if operation.action == "write":
        size = len(operation.content.encode("utf-8"))
        if size > config.max_file_bytes:
            raise SecurityError(f"Generated file too large: {operation.path!r}")
        scan_text(operation.content, operation.path)
    return target


def scan_text(text: str, label: str) -> None:
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            raise SecurityError(f"Possible secret/credential material detected in {label}")


def scan_project_layout(project_dir: Path) -> None:
    for path in project_dir.rglob("*"):
        if path.is_symlink():
            raise SecurityError(
                f"Symbolic links are not allowed in generated projects: "
                f"{path.relative_to(project_dir).as_posix()}"
            )
        if path.is_file() and path.stat().st_size > 2_000_000:
            raise SecurityError(
                f"Unexpectedly large generated file: {path.relative_to(project_dir).as_posix()}"
            )


def _local_packages(project_dir: Path) -> set[str]:
    src = project_dir / "src"
    if not src.exists():
        return set()
    names = {path.stem for path in src.glob("*.py")}
    names.update(path.name for path in src.iterdir() if path.is_dir())
    return names


def scan_python_project(project_dir: Path, config: ForgeConfig) -> None:
    allowed = set(config.allowed_python_packages) | _local_packages(project_dir)
    denied = set(config.denied_python_imports)
    stdlib = set(sys.stdlib_module_names)

    for path in sorted(project_dir.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="strict")
        scan_text(text, path.relative_to(project_dir).as_posix())
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            raise SecurityError(f"Syntax error in {path}: {exc}") from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [] if node.level else [(node.module or "").split(".")[0]]
            else:
                names = []
            for name in filter(None, names):
                if name in denied:
                    raise SecurityError(f"Denied import {name!r} in {path}")
                if name not in stdlib and name not in allowed:
                    raise SecurityError(f"Unapproved third-party import {name!r} in {path}")

            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in _DANGEROUS_BUILTINS:
                raise SecurityError(f"Dangerous call {node.func.id}() in {path}")
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                owner = node.func.value.id
                attr = node.func.attr
                if owner == "os" and (
                    attr in _DANGEROUS_OS_CALLS
                    or any(attr.startswith(prefix) for prefix in _DANGEROUS_OS_PREFIXES)
                ):
                    raise SecurityError(f"Dangerous os.{attr}() in {path}")


def _dependency_name(dependency: object) -> str:
    text = str(dependency).strip()
    if not text or "@" in text or "://" in text:
        raise SecurityError(f"Direct URL/path dependencies are not allowed: {text!r}")
    return re.split(r"[<>=!~\[ ;]", text, maxsplit=1)[0].strip().lower().replace("_", "-")


def scan_project_manifests(project_dir: Path, config: ForgeConfig) -> None:
    manifest = project_dir / "pyproject.toml"
    if not manifest.exists():
        return
    try:
        raw = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise SecurityError(f"Invalid generated pyproject.toml: {exc}") from exc

    allowed = {name.lower().replace("_", "-") for name in config.allowed_python_packages}
    aliases = {"scikit-learn": "sklearn"}
    allowed.update({"setuptools", "wheel"})

    dependency_groups: list[object] = list(raw.get("project", {}).get("dependencies", []) or [])
    optional = raw.get("project", {}).get("optional-dependencies", {}) or {}
    if isinstance(optional, dict):
        for values in optional.values():
            dependency_groups.extend(values or [])
    dependency_groups.extend(raw.get("build-system", {}).get("requires", []) or [])

    for dependency in dependency_groups:
        name = _dependency_name(dependency)
        if name == "sklearn":
            raise SecurityError(
                "Use the maintained distribution name 'scikit-learn' rather than 'sklearn'"
            )
        normalized = aliases.get(name, name)
        if normalized not in allowed:
            raise SecurityError(f"Unapproved project dependency {dependency!r}")


def scan_project_text(project_dir: Path) -> None:
    scan_project_layout(project_dir)
    for path in project_dir.rglob("*"):
        if not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        if path.suffix.lower() in {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".csv"}:
            scan_text(path.read_text(encoding="utf-8", errors="replace"), path.as_posix())
