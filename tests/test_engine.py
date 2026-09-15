from pathlib import Path

import pytest

from orbitalforge.config import load_config
from orbitalforge.engine import ForgeError, _apply_operations, _rollback
from orbitalforge.models import FileOperation
from orbitalforge.security import SecurityError


def test_apply_and_rollback(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_config(root)
    project = tmp_path / "project"
    project.mkdir()
    original = project / "src/a.py"
    original.parent.mkdir()
    original.write_text("x = 1\n", encoding="utf-8")
    backups, touched = _apply_operations(
        project, (FileOperation("write", "src/a.py", "x = 2\n"),), config
    )
    assert touched == [original.resolve()]
    assert original.read_text(encoding="utf-8") == "x = 2\n"
    _rollback(backups)
    assert original.read_text(encoding="utf-8") == "x = 1\n"


def test_noop_operations_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_config(root)
    project = tmp_path / "project"
    project.mkdir()
    file = project / "README.md"
    file.write_text("same\n", encoding="utf-8")
    with pytest.raises(ForgeError):
        _apply_operations(project, (FileOperation("write", "README.md", "same\n"),), config)


def test_tick_advances_only_after_independent_acceptance(tmp_path: Path, monkeypatch) -> None:
    import json
    import shutil
    import sys
    import types

    from orbitalforge.engine import tick
    from orbitalforge.models import FileOperation, ReviewResult, WorkResult
    from orbitalforge.quality import QualityReport

    # The real dependency is installed by the project workflow. The local artifact test only needs
    # llm.py to import so its API-calling functions can be replaced with deterministic fakes.
    if "openai" not in sys.modules:
        sys.modules["openai"] = types.SimpleNamespace(OpenAI=object)

    source_root = Path(__file__).resolve().parents[1]
    (tmp_path / "config").mkdir()
    (tmp_path / "catalog").mkdir()
    (tmp_path / ".autoforge").mkdir()
    (tmp_path / "projects" / "active").mkdir(parents=True)
    (tmp_path / "projects" / "completed").mkdir(parents=True)
    shutil.copy(source_root / "config" / "forge.yml", tmp_path / "config" / "forge.yml")
    shutil.copy(source_root / "catalog" / "projects.yml", tmp_path / "catalog" / "projects.yml")
    (tmp_path / ".autoforge" / "state.json").write_text(
        json.dumps({"version": 2}), encoding="utf-8"
    )
    (tmp_path / "PROJECTS.md").write_text("# Projects\n", encoding="utf-8")

    def fake_work(*args, **kwargs):
        return WorkResult(
            summary="implemented deterministic model",
            task_complete=True,
            operations=(FileOperation("write", "src/model.py", "VALUE = 1\n"),),
        )

    def fake_review(*args, **kwargs):
        return ReviewResult("accept", "criteria met", "")

    monkeypatch.setattr("orbitalforge.llm.build_work_unit", fake_work)
    monkeypatch.setattr("orbitalforge.llm.review_task_completion", fake_review)
    monkeypatch.setattr(
        "orbitalforge.engine.run_quality_gate",
        lambda *args, **kwargs: QualityReport(("fake",), "ok"),
    )

    result = tick(tmp_path)
    state = json.loads((tmp_path / ".autoforge" / "state.json").read_text(encoding="utf-8"))
    generated = (
        tmp_path
        / "projects"
        / "active"
        / "satellite-rover-intelligence"
        / "src"
        / "model.py"
    )
    assert "advanced satellite-rover-intelligence" in result
    assert state["current_project_id"] == "satellite-rover-intelligence"
    assert state["current_task_index"] == 1
    assert state["successful_ticks"] == 1
    assert generated.exists()


def test_operations_are_prevalidated_before_any_write(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_config(root)
    project = tmp_path / "project"
    project.mkdir()
    safe = project / "src" / "safe.py"

    with pytest.raises(SecurityError):
        _apply_operations(
            project,
            (
                FileOperation("write", "src/safe.py", "VALUE = 1\n"),
                FileOperation("write", "../escape.py", "bad = True\n"),
            ),
            config,
        )

    assert not safe.exists()
    assert not (tmp_path / "escape.py").exists()


def test_complete_project_archives_and_next_tick_starts_next_project(tmp_path: Path, monkeypatch) -> None:
    import json
    import shutil
    import sys
    import types

    import yaml

    from orbitalforge.engine import tick
    from orbitalforge.models import FileOperation, FinalAuditResult, ReviewResult, WorkResult
    from orbitalforge.quality import QualityReport

    if "openai" not in sys.modules:
        sys.modules["openai"] = types.SimpleNamespace(OpenAI=object)

    source_root = Path(__file__).resolve().parents[1]
    (tmp_path / "config").mkdir()
    (tmp_path / "catalog").mkdir()
    (tmp_path / ".autoforge").mkdir()
    (tmp_path / "projects" / "active").mkdir(parents=True)
    (tmp_path / "projects" / "completed").mkdir(parents=True)
    shutil.copy(source_root / "config" / "forge.yml", tmp_path / "config" / "forge.yml")
    (tmp_path / ".autoforge" / "state.json").write_text(
        json.dumps({"version": 3}), encoding="utf-8"
    )
    (tmp_path / "PROJECTS.md").write_text("# Projects\n", encoding="utf-8")

    def blueprint(pid: str, title: str) -> dict:
        return {
            "id": pid,
            "title": title,
            "summary": f"{title} integrated simulation research project.",
            "domains": ["AI/ML", "robotics", "data processing", "satellite systems"],
            "tasks": [
                {
                    "id": f"T{i:02d}",
                    "title": f"Task {i}",
                    "instruction": f"Implement validated unit {i}.",
                    "acceptance_criteria": ["implementation exists", "tests pass"],
                }
                for i in range(1, 9)
            ],
        }

    (tmp_path / "catalog" / "projects.yml").write_text(
        yaml.safe_dump(
            {
                "projects": [
                    blueprint("first-project", "First Project"),
                    blueprint("second-project", "Second Project"),
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def fake_work(config, project, task, *args, **kwargs):
        return WorkResult(
            summary=f"completed {task.id}",
            task_complete=True,
            operations=(
                FileOperation(
                    "write",
                    f"src/{task.id.lower()}.py",
                    f"VALUE = {int(task.id[1:])}\n",
                ),
            ),
        )

    monkeypatch.setattr("orbitalforge.llm.build_work_unit", fake_work)
    monkeypatch.setattr(
        "orbitalforge.llm.review_task_completion",
        lambda *args, **kwargs: ReviewResult("accept", "criteria met", ""),
    )
    monkeypatch.setattr(
        "orbitalforge.llm.audit_project",
        lambda *args, **kwargs: FinalAuditResult("pass", "archive ready", ""),
    )
    monkeypatch.setattr(
        "orbitalforge.engine.run_quality_gate",
        lambda *args, **kwargs: QualityReport(("fake",), "ok"),
    )
    monkeypatch.setattr(
        "orbitalforge.engine.run_completion_gate",
        lambda *args, **kwargs: QualityReport(("fake-final",), "ok"),
    )

    for _ in range(8):
        tick(tmp_path)

    state = json.loads((tmp_path / ".autoforge" / "state.json").read_text(encoding="utf-8"))
    assert "first-project" in state["completed_projects"]
    assert state["current_project_id"] is None
    assert (tmp_path / "projects" / "completed" / "first-project").is_dir()

    tick(tmp_path)
    state = json.loads((tmp_path / ".autoforge" / "state.json").read_text(encoding="utf-8"))
    assert state["current_project_id"] == "second-project"
    assert state["current_task_index"] == 1
    assert (tmp_path / "projects" / "active" / "second-project").is_dir()
