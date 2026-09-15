from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .models import Blueprint, ForgeState, Task


ID_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*$")
TASK_ID_RE = re.compile(r"[A-Z][A-Z0-9-]{1,23}$")
CORE_DOMAINS = {"AI/ML", "robotics", "data processing", "satellite systems"}


def _blueprint(raw: dict[str, Any]) -> Blueprint:
    tasks = tuple(
        Task(
            id=str(task["id"]),
            title=str(task["title"]),
            instruction=str(task["instruction"]),
            acceptance_criteria=tuple(str(x) for x in task.get("acceptance_criteria", [])),
        )
        for task in raw["tasks"]
    )
    blueprint = Blueprint(
        id=str(raw["id"]),
        title=str(raw["title"]),
        summary=str(raw["summary"]),
        domains=tuple(str(x) for x in raw.get("domains", [])),
        tasks=tasks,
    )
    validate_blueprint(blueprint, require_core_domains=True)
    return blueprint


def validate_blueprint(blueprint: Blueprint, *, require_core_domains: bool = False) -> None:
    if not ID_RE.fullmatch(blueprint.id):
        raise ValueError(f"Invalid blueprint id: {blueprint.id}")
    if not blueprint.title.strip() or not blueprint.summary.strip():
        raise ValueError(f"{blueprint.id} needs a non-empty title and summary")
    if not 8 <= len(blueprint.tasks) <= 16:
        raise ValueError(f"{blueprint.id} must contain 8-16 tasks")
    ids = [task.id for task in blueprint.tasks]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate task ids in {blueprint.id}")
    if any(not TASK_ID_RE.fullmatch(task_id) for task_id in ids):
        raise ValueError(f"Invalid task id in {blueprint.id}: {ids}")
    if len(blueprint.domains) < 3:
        raise ValueError(f"{blueprint.id} must span at least three domains")
    if require_core_domains and not CORE_DOMAINS.issubset(set(blueprint.domains)):
        missing = sorted(CORE_DOMAINS - set(blueprint.domains))
        raise ValueError(f"{blueprint.id} is missing required core domains: {missing}")
    for task in blueprint.tasks:
        if not task.title.strip() or not task.instruction.strip():
            raise ValueError(f"{blueprint.id}/{task.id} needs title and instruction")
        if len(task.acceptance_criteria) < 2:
            raise ValueError(f"{blueprint.id}/{task.id} needs >=2 acceptance criteria")


def load_catalog(root: Path, state: ForgeState) -> list[Blueprint]:
    seed_raw = yaml.safe_load((root / "catalog" / "projects.yml").read_text(encoding="utf-8"))
    items = [_blueprint(item) for item in seed_raw["projects"]]

    # Backward compatibility: pre-3.0 snapshots kept dynamic blueprints in state.json. Keep those
    # immediately after seeds so their historical catalog indices remain stable.
    items.extend(_blueprint(item) for item in state.generated_projects)

    generated_dir = root / "catalog" / "generated"
    if generated_dir.exists():
        for path in sorted(generated_dir.glob("*.json")):
            items.append(_blueprint(json.loads(path.read_text(encoding="utf-8"))))
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate project ids in catalog/state")
    return items


def persist_generated_blueprint(root: Path, index: int, blueprint: Blueprint) -> Path:
    generated_dir = root / "catalog" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    path = generated_dir / f"{index:06d}-{blueprint.id}.json"
    if path.exists():
        existing = _blueprint(json.loads(path.read_text(encoding="utf-8")))
        if existing != blueprint:
            raise ValueError(f"Generated blueprint slot already exists with different content: {path}")
        return path
    path.write_text(canonical_blueprint_json(blueprint) + "\n", encoding="utf-8")
    return path


def blueprint_to_dict(blueprint: Blueprint) -> dict[str, Any]:
    return {
        "id": blueprint.id,
        "title": blueprint.title,
        "summary": blueprint.summary,
        "domains": list(blueprint.domains),
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "instruction": task.instruction,
                "acceptance_criteria": list(task.acceptance_criteria),
            }
            for task in blueprint.tasks
        ],
    }


def canonical_blueprint_json(blueprint: Blueprint) -> str:
    return json.dumps(blueprint_to_dict(blueprint), indent=2, sort_keys=True)
