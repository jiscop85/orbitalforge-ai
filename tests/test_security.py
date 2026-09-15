from pathlib import Path

import pytest

from orbitalforge.config import load_config
from orbitalforge.models import FileOperation
from orbitalforge.security import (
    SecurityError,
    safe_target,
    scan_project_layout,
    scan_project_manifests,
    scan_python_project,
)


@pytest.mark.parametrize(
    "path",
    [
        "../escape.py",
        "/tmp/escape.py",
        ".github/workflows/bad.yml",
        ".env",
        "PROJECT.md",
        "STATUS.md",
        "src/credentials.json",
        "payload.exe",
        "src/bad\nname.py",
    ],
)
def test_safe_target_rejects_unsafe_paths(tmp_path: Path, path: str) -> None:
    config = load_config(Path(__file__).resolve().parents[1])
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(SecurityError):
        safe_target(project, FileOperation("write", path, "x = 1\n"), config)


def test_safe_target_accepts_normal_project_file(tmp_path: Path) -> None:
    config = load_config(Path(__file__).resolve().parents[1])
    project = tmp_path / "project"
    project.mkdir()
    target = safe_target(
        project, FileOperation("write", "src/pkg/model.py", "value = 1\n"), config
    )
    assert target == (project / "src/pkg/model.py").resolve()


def test_python_scanner_rejects_process_and_network_escape(tmp_path: Path) -> None:
    config = load_config(Path(__file__).resolve().parents[1])
    project = tmp_path / "project"
    source = project / "src" / "pkg"
    source.mkdir(parents=True)
    (source / "bad.py").write_text("import subprocess\nsubprocess.run(['echo', 'x'])\n", encoding="utf-8")
    with pytest.raises(SecurityError):
        scan_python_project(project, config)


def test_manifest_scanner_rejects_unapproved_optional_dependency(tmp_path: Path) -> None:
    config = load_config(Path(__file__).resolve().parents[1])
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='demo'\nversion='0.1'\n"
        "[project.optional-dependencies]\ndev=['requests>=2']\n",
        encoding="utf-8",
    )
    with pytest.raises(SecurityError):
        scan_project_manifests(project, config)


def test_project_layout_rejects_symlink(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = project / "linked.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this platform")
    with pytest.raises(SecurityError):
        scan_project_layout(project)


def test_manifest_scanner_requires_scikit_learn_distribution_name(tmp_path: Path) -> None:
    config = load_config(Path(__file__).resolve().parents[1])
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='demo'\nversion='0.1'\ndependencies=['sklearn>=0.0']\n",
        encoding="utf-8",
    )
    with pytest.raises(SecurityError):
        scan_project_manifests(project, config)
