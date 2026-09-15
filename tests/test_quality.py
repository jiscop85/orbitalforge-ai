from pathlib import Path

from orbitalforge.quality import _sanitized_test_env


def test_test_environment_strips_credentials(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_secret_value")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_secret_value")
    monkeypatch.setenv("NORMAL_SETTING", "kept")
    src = tmp_path / "src"
    src.mkdir()
    env = _sanitized_test_env(src, tmp_path)
    assert "GROQ_API_KEY" not in env
    assert "GITHUB_TOKEN" not in env
    assert env["NORMAL_SETTING"] == "kept"
    assert env["PYTHONHASHSEED"] == "0"
