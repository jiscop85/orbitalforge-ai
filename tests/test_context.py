from pathlib import Path

from orbitalforge.config import load_config
from orbitalforge.context import collect_context
from orbitalforge.models import ForgeState, Task


def test_context_respects_character_budget(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_config(root)
    (tmp_path / "README.md").write_text("x" * 100000, encoding="utf-8")
    task = Task("T01", "terrain model", "build terrain model", ("tested", "deterministic"))
    context = collect_context(tmp_path, ForgeState(), task, config)
    assert len(context) <= config.max_context_chars + 1000
