from __future__ import annotations

import json
from pathlib import Path

from .models import ForgeState


STATE_REL = Path(".autoforge/state.json")
CURRENT_STATE_VERSION = 3


def read_state(root: Path) -> ForgeState:
    path = root / STATE_REL
    if not path.exists():
        return ForgeState()
    raw = json.loads(path.read_text(encoding="utf-8"))
    version = int(raw.get("version", 1))
    if version == 2:
        raw = dict(raw)
        raw["version"] = CURRENT_STATE_VERSION
    elif version != CURRENT_STATE_VERSION:
        raise RuntimeError(f"Unsupported state version: {version}")
    return ForgeState.from_dict(raw)


def write_state(root: Path, state: ForgeState) -> None:
    path = root / STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)
