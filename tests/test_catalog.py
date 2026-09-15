from pathlib import Path

from orbitalforge.catalog import CORE_DOMAINS, load_catalog
from orbitalforge.state import read_state


def test_seed_catalog_is_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = load_catalog(root, read_state(root))
    assert len(catalog) >= 6
    assert len({project.id for project in catalog}) == len(catalog)
    assert all(len(project.tasks) >= 8 for project in catalog)
    assert all(len(project.domains) >= 3 for project in catalog)
    assert all(CORE_DOMAINS.issubset(set(project.domains)) for project in catalog)
    assert all(all(len(task.acceptance_criteria) >= 2 for task in project.tasks) for project in catalog)


def test_generated_catalog_files_are_loaded_in_order(tmp_path: Path) -> None:
    import json
    import shutil

    from orbitalforge.catalog import blueprint_to_dict
    from orbitalforge.models import Blueprint, ForgeState, Task

    source_root = Path(__file__).resolve().parents[1]
    (tmp_path / "catalog" / "generated").mkdir(parents=True)
    shutil.copy(source_root / "catalog" / "projects.yml", tmp_path / "catalog" / "projects.yml")
    blueprint = Blueprint(
        id="generated-demo",
        title="Generated Demo",
        summary="Integrated AI robotics data and satellite simulation.",
        domains=("AI/ML", "robotics", "data processing", "satellite systems"),
        tasks=tuple(
            Task(
                id=f"T{i:02d}",
                title=f"Task {i}",
                instruction="Implement a deterministic unit.",
                acceptance_criteria=("implemented", "tested"),
            )
            for i in range(1, 11)
        ),
    )
    (tmp_path / "catalog" / "generated" / "000007-generated-demo.json").write_text(
        json.dumps(blueprint_to_dict(blueprint)), encoding="utf-8"
    )
    catalog = load_catalog(tmp_path, ForgeState())
    assert catalog[-1].id == "generated-demo"


def test_legacy_generated_blueprints_keep_order_before_new_files(tmp_path: Path) -> None:
    import json
    import shutil

    from orbitalforge.catalog import blueprint_to_dict
    from orbitalforge.models import Blueprint, ForgeState, Task

    source_root = Path(__file__).resolve().parents[1]
    (tmp_path / "catalog" / "generated").mkdir(parents=True)
    shutil.copy(source_root / "catalog" / "projects.yml", tmp_path / "catalog" / "projects.yml")

    def make_blueprint(pid: str) -> Blueprint:
        return Blueprint(
            id=pid,
            title=pid.replace("-", " ").title(),
            summary="Integrated AI robotics data and satellite simulation.",
            domains=("AI/ML", "robotics", "data processing", "satellite systems"),
            tasks=tuple(
                Task(
                    id=f"T{i:02d}",
                    title=f"Task {i}",
                    instruction="Implement a deterministic unit.",
                    acceptance_criteria=("implemented", "tested"),
                )
                for i in range(1, 11)
            ),
        )

    legacy = make_blueprint("legacy-generated")
    newer = make_blueprint("file-generated")
    state = ForgeState(generated_projects=[blueprint_to_dict(legacy)])
    (tmp_path / "catalog" / "generated" / "000008-file-generated.json").write_text(
        json.dumps(blueprint_to_dict(newer)), encoding="utf-8"
    )
    catalog = load_catalog(tmp_path, state)
    assert [catalog[-2].id, catalog[-1].id] == ["legacy-generated", "file-generated"]
