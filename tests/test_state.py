from pathlib import Path

from orbitalforge.models import ForgeState
from orbitalforge.state import read_state, write_state


def test_state_round_trip(tmp_path: Path) -> None:
    state = ForgeState(current_project_id="demo", current_task_index=3, successful_ticks=9)
    write_state(tmp_path, state)
    loaded = read_state(tmp_path)
    assert loaded.current_project_id == "demo"
    assert loaded.current_task_index == 3
    assert loaded.successful_ticks == 9


def test_v2_state_is_migrated_to_v3(tmp_path: Path) -> None:
    import json

    state_path = tmp_path / ".autoforge" / "state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps({"version": 2, "current_project_id": "legacy", "successful_ticks": 4}),
        encoding="utf-8",
    )
    loaded = read_state(tmp_path)
    assert loaded.version == 3
    assert loaded.current_project_id == "legacy"
    assert loaded.successful_ticks == 4
    assert loaded.rejected_ticks == 0
    assert loaded.total_model_calls == 0
