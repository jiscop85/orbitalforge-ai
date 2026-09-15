from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    instruction: str
    acceptance_criteria: tuple[str, ...] = ()


@dataclass(frozen=True)
class Blueprint:
    id: str
    title: str
    summary: str
    domains: tuple[str, ...]
    tasks: tuple[Task, ...]


@dataclass
class ForgeState:
    version: int = 3
    catalog_index: int = 0
    current_project_id: str | None = None
    current_task_index: int = 0
    phase: str = "build"
    completed_projects: list[str] = field(default_factory=list)
    generated_projects: list[dict[str, Any]] = field(default_factory=list)
    recent_files: list[str] = field(default_factory=list)
    successful_ticks: int = 0
    rejected_ticks: int = 0
    current_task_attempts: int = 0
    reviewer_feedback: str | None = None
    final_review_feedback: str | None = None
    last_attempt_utc: str | None = None
    last_success_utc: str | None = None
    last_project_completed_utc: str | None = None
    last_project_id: str | None = None
    last_task_id: str | None = None
    last_summary: str | None = None
    last_error: str | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_model_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ForgeState":
        allowed = set(cls.__dataclass_fields__)
        values = {key: value for key, value in raw.items() if key in allowed}
        return cls(**values)


@dataclass(frozen=True)
class FileOperation:
    action: Literal["write", "delete"]
    path: str
    content: str = ""


@dataclass(frozen=True)
class WorkResult:
    summary: str
    task_complete: bool
    operations: tuple[FileOperation, ...]
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class ReviewResult:
    verdict: Literal["accept", "continue", "reject"]
    summary: str
    feedback: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class FinalAuditResult:
    verdict: Literal["pass", "revise"]
    summary: str
    feedback: str
    input_tokens: int = 0
    output_tokens: int = 0
