from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import ForgeConfig
from .security import scan_project_manifests, scan_project_text, scan_python_project


class QualityError(RuntimeError):
    pass


@dataclass(frozen=True)
class QualityReport:
    commands: tuple[str, ...]
    summary: str


_SENSITIVE_ENV_MARKERS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "APIKEY",
    "CREDENTIAL",
    "PRIVATE_KEY",
    "ACCESS_KEY",
)

_UNFINISHED_MARKERS = re.compile(
    r"(?im)(?:^|\s)(?:TODO|FIXME|TBD)(?:\s|:|$)|notimplementederror|placeholder implementation"
)
_REQUIRED_README_SECTIONS = ("usage", "reproducibility", "limitations")


def _sanitized_test_env(src_dir: Path, project_dir: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if any(marker in upper for marker in _SENSITIVE_ENV_MARKERS):
            continue
        env[key] = value
    private_home = project_dir / ".sandbox-home"
    private_tmp = project_dir / ".sandbox-tmp"
    private_home.mkdir(exist_ok=True)
    private_tmp.mkdir(exist_ok=True)
    env.update(
        {
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "HOME": str(private_home),
            "TMPDIR": str(private_tmp),
            "XDG_CACHE_HOME": str(private_home / ".cache"),
            "MPLCONFIGDIR": str(private_home / ".matplotlib"),
        }
    )
    pythonpath = str(src_dir) if src_dir.exists() else str(project_dir)
    env["PYTHONPATH"] = pythonpath
    return env


def _run(args: list[str], cwd: Path, timeout: int, env: dict[str, str] | None = None) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise QualityError(f"{' '.join(args)} timed out after {timeout}s") from exc
    if result.returncode != 0:
        tail = result.stdout[-8000:]
        raise QualityError(f"{' '.join(args)} failed ({result.returncode}):\n{tail}")
    return result.stdout[-5000:]


def _sandbox_copy(project_dir: Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    holder: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory(prefix="orbitalforge-")
    sandbox = Path(holder.name) / "project"
    shutil.copytree(project_dir, sandbox)
    return holder, sandbox


def run_quality_gate(
    project_dir: Path,
    config: ForgeConfig,
    autoformat_paths: list[Path] | tuple[Path, ...] | None = None,
) -> QualityReport:
    # Formatting is the only quality operation allowed to mutate the real worktree. All generated
    # code execution happens in an isolated disposable copy with a scrubbed environment.
    format_targets = [
        str(path)
        for path in (autoformat_paths or [])
        if path.exists() and path.suffix.lower() == ".py" and project_dir in path.parents
    ]
    commands: list[str] = []
    summaries: list[str] = []
    if format_targets:
        args = [sys.executable, "-m", "ruff", "format", *format_targets]
        summaries.append(_run(args, project_dir, config.quality_timeout_seconds))
        commands.append(" ".join(args))

    scan_project_text(project_dir)
    scan_project_manifests(project_dir, config)
    scan_python_project(project_dir, config)

    holder, sandbox = _sandbox_copy(project_dir)
    try:
        src_dir = sandbox / "src"
        tests_dir = sandbox / "tests"
        env = _sanitized_test_env(src_dir, sandbox)

        if src_dir.exists() and any(src_dir.rglob("*.py")):
            args = [sys.executable, "-m", "compileall", "-q", str(src_dir)]
            summaries.append(_run(args, sandbox, config.quality_timeout_seconds, env))
            commands.append(" ".join(args))

        lint_targets = [str(path) for path in (src_dir, tests_dir) if path.exists()]
        if lint_targets:
            args = [sys.executable, "-m", "ruff", "check", *lint_targets]
            summaries.append(_run(args, sandbox, config.quality_timeout_seconds, env))
            commands.append(" ".join(args))
            args = [sys.executable, "-m", "ruff", "format", "--check", *lint_targets]
            summaries.append(_run(args, sandbox, config.quality_timeout_seconds, env))
            commands.append(" ".join(args))

        python_sources = list(src_dir.rglob("*.py")) if src_dir.exists() else []
        tests = list(tests_dir.rglob("test_*.py")) if tests_dir.exists() else []
        if python_sources and not tests:
            raise QualityError("Executable source exists but the project has no tests")

        if tests:
            args = [sys.executable, "-m", "pytest", "-q", "--disable-socket"]
            if python_sources:
                args.extend(
                    [
                        "--cov=src",
                        "--cov-report=term-missing:skip-covered",
                        f"--cov-fail-under={config.coverage_min_percent}",
                    ]
                )
            args.append(str(tests_dir))
            summaries.append(_run(args, sandbox, config.quality_timeout_seconds, env))
            commands.append(" ".join(args))
    finally:
        holder.cleanup()

    return QualityReport(commands=tuple(commands), summary="\n".join(filter(None, summaries))[-8000:])


def _count_test_functions(tests_dir: Path) -> int:
    count = 0
    for path in tests_dir.rglob("test_*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        count += sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
        )
    return count


def run_completion_gate(
    project_dir: Path, config: ForgeConfig, validated_report: QualityReport | None = None
) -> QualityReport:
    report = validated_report or run_quality_gate(project_dir, config)
    readme = project_dir / "README.md"
    if not readme.exists():
        raise QualityError("Final project README is missing")
    readme_text = readme.read_text(encoding="utf-8", errors="replace")
    if len(readme_text) < config.min_final_readme_chars:
        raise QualityError(
            f"Final project README is too small ({len(readme_text)} < {config.min_final_readme_chars})"
        )
    lower_readme = readme_text.lower()
    missing_sections = [name for name in _REQUIRED_README_SECTIONS if name not in lower_readme]
    if missing_sections:
        raise QualityError(
            "Final README must document: " + ", ".join(missing_sections)
        )
    if "synthetic" not in lower_readme and "simulation" not in lower_readme:
        raise QualityError("Final README must explicitly document synthetic/simulation scope")

    src_dir = project_dir / "src"
    tests_dir = project_dir / "tests"
    if not src_dir.exists() or not any(src_dir.rglob("*.py")):
        raise QualityError("Final project has no executable Python source")
    if not tests_dir.exists() or not any(tests_dir.rglob("test_*.py")):
        raise QualityError("Final project has no test suite")
    test_count = _count_test_functions(tests_dir)
    if test_count < config.min_final_tests:
        raise QualityError(
            f"Final project needs at least {config.min_final_tests} explicit tests; found {test_count}"
        )

    for base in (src_dir, tests_dir):
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if _UNFINISHED_MARKERS.search(text):
                rel = path.relative_to(project_dir).as_posix()
                raise QualityError(f"Unfinished implementation marker remains in {rel}")

    return report
