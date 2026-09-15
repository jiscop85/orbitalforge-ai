from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ForgeConfig:
    worker_model: str
    reviewer_model: str
    planner_model: str
    fallback_model: str
    worker_reasoning_effort: str
    recovery_reasoning_effort: str
    reviewer_reasoning_effort: str
    planner_reasoning_effort: str
    max_output_tokens: int
    reviewer_max_output_tokens: int
    planner_max_output_tokens: int
    max_context_chars: int
    max_context_files: int
    max_context_file_chars: int
    max_audit_context_chars: int
    max_audit_context_files: int
    max_diff_chars_for_review: int
    max_operations_per_tick: int
    max_file_bytes: int
    max_total_write_bytes: int
    quality_timeout_seconds: int
    coverage_min_percent: int
    min_final_tests: int
    min_final_readme_chars: int
    max_api_attempts: int
    max_task_attempts_before_recovery: int
    allowed_extensions: tuple[str, ...]
    forbidden_names: tuple[str, ...]
    allowed_python_packages: tuple[str, ...]
    denied_python_imports: tuple[str, ...]
    project_policy: dict[str, Any]


def _env(name: str, default: Any) -> str:
    return os.getenv(name, str(default))


def load_config(root: Path) -> ForgeConfig:
    raw = yaml.safe_load((root / "config" / "forge.yml").read_text(encoding="utf-8"))
    return ForgeConfig(
        worker_model=_env("FORGE_WORKER_MODEL", raw["worker_model"]),
        reviewer_model=_env("FORGE_REVIEWER_MODEL", raw["reviewer_model"]),
        planner_model=_env("FORGE_PLANNER_MODEL", raw["planner_model"]),
        fallback_model=_env("FORGE_FALLBACK_MODEL", raw["fallback_model"]),
        worker_reasoning_effort=_env(
            "FORGE_WORKER_REASONING_EFFORT", raw["worker_reasoning_effort"]
        ),
        recovery_reasoning_effort=_env(
            "FORGE_RECOVERY_REASONING_EFFORT", raw["recovery_reasoning_effort"]
        ),
        reviewer_reasoning_effort=_env(
            "FORGE_REVIEWER_REASONING_EFFORT", raw["reviewer_reasoning_effort"]
        ),
        planner_reasoning_effort=_env(
            "FORGE_PLANNER_REASONING_EFFORT", raw["planner_reasoning_effort"]
        ),
        max_output_tokens=int(_env("FORGE_MAX_OUTPUT_TOKENS", raw["max_output_tokens"])),
        reviewer_max_output_tokens=int(raw["reviewer_max_output_tokens"]),
        planner_max_output_tokens=int(raw["planner_max_output_tokens"]),
        max_context_chars=int(raw["max_context_chars"]),
        max_context_files=int(raw["max_context_files"]),
        max_context_file_chars=int(raw["max_context_file_chars"]),
        max_audit_context_chars=int(raw["max_audit_context_chars"]),
        max_audit_context_files=int(raw["max_audit_context_files"]),
        max_diff_chars_for_review=int(raw["max_diff_chars_for_review"]),
        max_operations_per_tick=int(raw["max_operations_per_tick"]),
        max_file_bytes=int(raw["max_file_bytes"]),
        max_total_write_bytes=int(raw["max_total_write_bytes"]),
        quality_timeout_seconds=int(raw["quality_timeout_seconds"]),
        coverage_min_percent=int(raw["coverage_min_percent"]),
        min_final_tests=int(raw["min_final_tests"]),
        min_final_readme_chars=int(raw["min_final_readme_chars"]),
        max_api_attempts=int(raw["max_api_attempts"]),
        max_task_attempts_before_recovery=int(raw["max_task_attempts_before_recovery"]),
        allowed_extensions=tuple(raw["allowed_extensions"]),
        forbidden_names=tuple(str(x).lower() for x in raw["forbidden_names"]),
        allowed_python_packages=tuple(raw["allowed_python_packages"]),
        denied_python_imports=tuple(raw["denied_python_imports"]),
        project_policy=dict(raw["project_policy"]),
    )
