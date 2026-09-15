# Contributing

Changes to OrbitalForge should preserve reproducibility, rollback safety and the generated-code trust
boundary. Before opening a change, run:

```bash
python -m pip install -e ".[dev]"
python -m compileall -q src tests
python -m ruff check src tests
python -m ruff format --check src tests
python -m pytest -q
python -m orbitalforge.cli validate --root . --all-projects
```

Do not commit API keys, PATs, private mission data, `.env` files, generated credentials, or secrets.
Tests for the trusted orchestrator must not require a live Groq call. Model-facing changes should
retain strict structured outputs and deterministic validation around all model output.
