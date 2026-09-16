from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from .catalog import blueprint_to_dict
from .models import Blueprint, ForgeState


def project_dir(root: Path, project_id: str) -> Path:
    return root / "projects" / "active" / project_id


def completed_dir(root: Path, project_id: str) -> Path:
    return root / "projects" / "completed" / project_id


def render_status(blueprint: Blueprint, completed_count: int, phase: str, feedback: str | None) -> str:
    lines = [f"# Build status — {blueprint.title}", "", f"**Phase:** `{phase}`", ""]
    for index, task in enumerate(blueprint.tasks):
        marker = "x" if index < completed_count else " "
        lines.append(f"- [{marker}] **{task.id} — {task.title}**")
    if phase == "audit_pending":
        lines.extend(["", "> All roadmap tasks are accepted; final archive audit is pending."])
    if feedback:
        lines.extend(["", "## Current automated review guidance", "", feedback])
    lines.extend(["", "> Progress advances only after security, quality, test, and review gates.", ""])
    return "\n".join(lines)


def initialize_project(root: Path, blueprint: Blueprint, task_index: int = 0) -> None:
    project = project_dir(root, blueprint.id)
    project.mkdir(parents=True, exist_ok=True)
    (project / "README.md").write_text(
        f"# {blueprint.title}\n\n{blueprint.summary}\n\n"
        f"**Domains:** {', '.join(blueprint.domains)}\n\n"
        "This project is developed incrementally by OrbitalForge with independent review and "
        "offline quality gates. It uses synthetic/simulation data by default and is not intended "
        "for direct physical actuation.\n",
        encoding="utf-8",
    )
    (project / "PROJECT.md").write_text(
        "# Project specification\n\n```json\n"
        + json.dumps(blueprint_to_dict(blueprint), indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    (project / "STATUS.md").write_text(
        render_status(blueprint, task_index, "build", None), encoding="utf-8"
    )


def finalize_project(root: Path, state: ForgeState, blueprint: Blueprint) -> None:
    active = project_dir(root, blueprint.id)
    completed = completed_dir(root, blueprint.id)
    if completed.exists():
        raise RuntimeError(f"Completed project already exists: {blueprint.id}")
    completed.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(active), str(completed))
    state.completed_projects.append(blueprint.id)
    state.catalog_index += 1
    state.current_project_id = None
    state.current_task_index = 0
    state.current_task_attempts = 0
    state.phase = "build"
    state.recent_files = []
    state.reviewer_feedback = None
    state.final_review_feedback = None
    state.last_project_completed_utc = datetime.now(UTC).isoformat()


def render_projects_index(root: Path, state: ForgeState, catalog: list[Blueprint]) -> None:
    lines = [
        "# OrbitalForge research program",
        "",
        f"Validated work units: **{state.successful_ticks}**",
        f"Rejected/rolled-back candidates: **{state.rejected_ticks}**",
        f"Model usage recorded: **{state.total_input_tokens:,} input / {state.total_output_tokens:,} output tokens**",
        "",
    ]
    if state.current_project_id:
        current = next((b for b in catalog if b.id == state.current_project_id), None)
        if current:
            lines.extend(
                [
                    "## Active",
                    "",
                    f"- **{current.title}** (`{current.id}`) — task "
                    f"{min(state.current_task_index + 1, len(current.tasks))}/{len(current.tasks)}, "
                    f"phase `{state.phase}`",
                    "",
                ]
            )
    lines.extend(["## Completed", ""])
    if state.completed_projects:
        titles = {b.id: b.title for b in catalog}
        for project_id in state.completed_projects:
            lines.append(f"- [{titles.get(project_id, project_id)}](projects/completed/{project_id}/)")
    else:
        lines.append("- None yet.")
    if state.last_summary:
        lines.extend(
            [
                "",
                "## Latest autonomous event",
                "",
                f"- `{state.last_project_id}/{state.last_task_id}` — {state.last_summary}",
            ]
        )
    if state.last_error:
        lines.extend(["", "## Latest gate/audit note", "", f"> {state.last_error}"])
    lines.extend(["", f"Last updated: {datetime.now(UTC).isoformat()}", ""])
    (root / "PROJECTS.md").write_text("\n".join(lines), encoding="utf-8")
