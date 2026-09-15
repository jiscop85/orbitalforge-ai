from __future__ import annotations

from pathlib import Path

from .catalog import load_catalog
from .config import load_config
from .project import completed_dir, project_dir
from .quality import run_completion_gate, run_quality_gate
from .state import read_state


def validate_repository(root: Path, all_projects: bool = False) -> list[str]:
    root = root.resolve()
    config = load_config(root)
    state = read_state(root)
    catalog = load_catalog(root, state)
    messages = [f"catalog projects: {len(catalog)}"]
    if all_projects:
        for blueprint in catalog:
            active = project_dir(root, blueprint.id)
            completed = completed_dir(root, blueprint.id)
            if active.exists():
                run_quality_gate(active, config)
                messages.append(f"validated active {active.relative_to(root).as_posix()}")
            if completed.exists():
                run_completion_gate(completed, config)
                messages.append(f"validated completed {completed.relative_to(root).as_posix()}")
    elif state.current_project_id:
        active = project_dir(root, state.current_project_id)
        if active.exists():
            run_quality_gate(active, config)
            messages.append(f"validated {active.relative_to(root).as_posix()}")
    return messages
