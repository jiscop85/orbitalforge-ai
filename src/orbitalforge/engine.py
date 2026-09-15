from __future__ import annotations

import difflib
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .catalog import load_catalog, persist_generated_blueprint
from .config import ForgeConfig, load_config
from .context import collect_audit_context, collect_context
from .models import Blueprint, FileOperation, ForgeState, Task
from .project import (
    finalize_project,
    initialize_project,
    project_dir,
    render_projects_index,
    render_status,
)
from .quality import QualityError, QualityReport, run_completion_gate, run_quality_gate
from .security import SecurityError, safe_target
from .state import read_state, write_state


class ForgeError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _next_blueprint(root: Path, state: ForgeState, config: ForgeConfig) -> tuple[Blueprint, bool]:
    catalog = load_catalog(root, state)
    if state.catalog_index < len(catalog):
        return catalog[state.catalog_index], False
    from .llm import plan_new_blueprint

    blueprint = plan_new_blueprint(
        config,
        existing_ids=[item.id for item in catalog],
        existing_titles=[item.title for item in catalog],
        existing_summaries=[item.summary for item in catalog],
    )
    persist_generated_blueprint(root, state.catalog_index, blueprint)
    return blueprint, True


def _validated_operations(
    project: Path, operations: tuple[FileOperation, ...], config: ForgeConfig
) -> list[tuple[FileOperation, Path]]:
    if not operations:
        raise ForgeError("Worker returned no operations")
    if len(operations) > config.max_operations_per_tick:
        raise ForgeError("Worker exceeded max_operations_per_tick")
    total = sum(len(op.content.encode("utf-8")) for op in operations if op.action == "write")
    if total > config.max_total_write_bytes:
        raise ForgeError("Worker exceeded max_total_write_bytes")

    validated: list[tuple[FileOperation, Path]] = []
    seen: set[Path] = set()
    for operation in operations:
        target = safe_target(project, operation, config)
        if target in seen:
            raise ForgeError(f"Duplicate operation path: {operation.path}")
        seen.add(target)
        validated.append((operation, target))
    return validated


def _apply_operations(
    project: Path, operations: tuple[FileOperation, ...], config: ForgeConfig
) -> tuple[dict[Path, bytes | None], list[Path]]:
    """Validate all operations first, then apply atomically enough for local rollback."""

    validated = _validated_operations(project, operations, config)
    backups: dict[Path, bytes | None] = {
        target: target.read_bytes() if target.exists() else None for _, target in validated
    }
    touched: list[Path] = []
    try:
        for operation, target in validated:
            previous = backups[target]
            if operation.action == "delete":
                if target.exists():
                    target.unlink()
                    touched.append(target)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            new_bytes = operation.content.encode("utf-8")
            if previous == new_bytes:
                continue
            target.write_bytes(new_bytes)
            touched.append(target)
    except Exception:
        _rollback(backups)
        raise
    if not touched:
        raise ForgeError("Worker produced only no-op operations")
    return backups, touched


def _rollback(backups: dict[Path, bytes | None]) -> None:
    for path, previous in backups.items():
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(previous)


def _diff_from_backups(project: Path, backups: dict[Path, bytes | None], max_chars: int) -> str:
    chunks: list[str] = []
    remaining = max_chars
    for path, previous in backups.items():
        before = (previous or b"").decode("utf-8", errors="replace").splitlines(keepends=True)
        after_bytes = path.read_bytes() if path.exists() else b""
        after = after_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
        if before == after:
            continue
        rel = path.relative_to(project).as_posix()
        diff = "".join(
            difflib.unified_diff(before, after, fromfile=f"a/{rel}", tofile=f"b/{rel}", n=4)
        )
        piece = diff[:remaining]
        chunks.append(piece)
        remaining -= len(piece)
        if remaining <= 0:
            chunks.append("\n... diff truncated ...\n")
            break
    return "\n".join(chunks)


def _record_usage(state: ForgeState, results: Iterable[object]) -> None:
    for result in results:
        input_tokens = int(getattr(result, "input_tokens", 0) or 0)
        output_tokens = int(getattr(result, "output_tokens", 0) or 0)
        state.total_input_tokens += input_tokens
        state.total_output_tokens += output_tokens
        state.total_model_calls += 1


def _mark_success(
    state: ForgeState,
    touched: list[Path],
    project: Path,
    project_id: str,
    task_id: str,
    summary: str,
) -> None:
    state.recent_files = [
        path.relative_to(project).as_posix() for path in touched if path.exists()
    ][-12:]
    state.successful_ticks += 1
    state.last_attempt_utc = _now()
    state.last_success_utc = state.last_attempt_utc
    state.last_project_id = project_id
    state.last_task_id = task_id
    state.last_summary = summary[:1200]
    state.last_error = None


def _record_rejected_attempt(
    state: ForgeState,
    *,
    project_id: str,
    task_id: str,
    summary: str,
    error: str,
) -> None:
    state.rejected_ticks += 1
    state.last_attempt_utc = _now()
    state.last_project_id = project_id
    state.last_task_id = task_id
    state.last_summary = summary[:1200]
    state.last_error = error[-4000:]


def _write_status(project: Path, blueprint: Blueprint, state: ForgeState) -> None:
    if state.phase in {"final_review", "audit_pending"}:
        feedback = state.final_review_feedback
    else:
        feedback = state.reviewer_feedback
    (project / "STATUS.md").write_text(
        render_status(blueprint, state.current_task_index, state.phase, feedback),
        encoding="utf-8",
    )


def _persist(root: Path, state: ForgeState, blueprint: Blueprint) -> None:
    project = project_dir(root, blueprint.id)
    if project.exists():
        _write_status(project, blueprint, state)
    catalog = load_catalog(root, state)
    render_projects_index(root, state, catalog)
    write_state(root, state)


def _final_review_task(state: ForgeState) -> Task:
    feedback = state.final_review_feedback or (
        "Perform final integration, reproducibility, testing, and documentation cleanup before audit."
    )
    return Task(
        id="FINAL-AUDIT",
        title="Resolve final scientific/software audit findings",
        instruction=feedback,
        acceptance_criteria=(
            "Every final-audit/completion-gate finding is addressed without weakening behavior.",
            "All project quality gates and the coverage floor pass.",
            "README documents usage, reproducibility, assumptions/scope, and limitations accurately.",
            "AI/ML, robotics, data processing, and satellite-system components are integrated end to end.",
        ),
    )


def _final_audit(
    root: Path,
    state: ForgeState,
    blueprint: Blueprint,
    config: ForgeConfig,
    validated_report: QualityReport | None = None,
) -> tuple[bool, str]:
    """Run deterministic completion gates + independent model audit.

    Returns (completed, message). A deterministic final-gate failure becomes repair feedback rather
    than losing already validated useful work. API failures still raise so GitHub marks the run.
    """

    project = project_dir(root, blueprint.id)
    try:
        run_completion_gate(project, config, validated_report=validated_report)
    except QualityError as exc:
        state.phase = "final_review"
        state.final_review_feedback = f"Completion gate: {exc}"
        state.current_task_attempts = 0
        state.last_error = str(exc)[-4000:]
        return False, f"final completion gate requested repair: {exc}"

    from .llm import audit_project

    audit_context = collect_audit_context(
        project,
        max_chars=config.max_audit_context_chars,
        max_files=config.max_audit_context_files,
    )
    audit = audit_project(config, blueprint, audit_context)
    _record_usage(state, [audit])
    if audit.verdict == "pass":
        finalize_project(root, state, blueprint)
        state.last_error = None
        return True, f"completed {blueprint.id}; next project starts automatically on next tick"

    state.phase = "final_review"
    state.final_review_feedback = audit.feedback or audit.summary
    state.current_task_attempts = 0
    state.last_error = f"Final audit requested revision: {state.final_review_feedback}"[-4000:]
    return False, "final independent audit requested another repair cycle"


def tick(root: Path) -> str:
    root = root.resolve()
    config = load_config(root)
    state = read_state(root)
    blueprint, newly_planned = _next_blueprint(root, state, config)

    if state.current_project_id not in {None, blueprint.id}:
        raise ForgeError(
            f"State/catalog mismatch: state={state.current_project_id}, catalog={blueprint.id}"
        )
    if state.current_project_id is None:
        state.current_project_id = blueprint.id
        state.current_task_index = 0
        state.current_task_attempts = 0
        state.phase = "build"
        state.reviewer_feedback = None
        state.final_review_feedback = None
        initialize_project(root, blueprint, 0)

    project = project_dir(root, blueprint.id)

    # After all task work is accepted, retry the final audit directly. Do not invent extra changes
    # merely because an earlier audit/API call was delayed.
    if state.phase == "audit_pending":
        completed, message = _final_audit(root, state, blueprint, config)
        state.last_attempt_utc = _now()
        if completed:
            catalog = load_catalog(root, state)
            render_projects_index(root, state, catalog)
            write_state(root, state)
            return message
        _persist(root, state, blueprint)
        return message

    if state.phase == "final_review":
        task = _final_review_task(state)
    else:
        if state.current_task_index >= len(blueprint.tasks):
            state.phase = "audit_pending"
            _persist(root, state, blueprint)
            return "all roadmap tasks are accepted; final audit queued"
        task = blueprint.tasks[state.current_task_index]

    state.current_task_attempts += 1
    recovery = state.current_task_attempts > config.max_task_attempts_before_recovery
    context = collect_context(project, state, task, config)
    feedback = state.final_review_feedback if state.phase == "final_review" else state.reviewer_feedback

    from .llm import build_work_unit, review_task_completion

    work = build_work_unit(
        config,
        blueprint,
        task,
        project.relative_to(root).as_posix(),
        context,
        feedback,
        recovery,
    )
    _record_usage(state, [work])

    backups: dict[Path, bytes | None] = {}
    touched: list[Path] = []
    try:
        backups, touched = _apply_operations(project, work.operations, config)
        quality: QualityReport = run_quality_gate(project, config, touched)
    except (ForgeError, SecurityError, QualityError) as exc:
        if backups:
            _rollback(backups)
        guidance = f"Previous attempt was rolled back by automated validation: {exc}"
        if state.phase == "final_review":
            state.final_review_feedback = guidance
        else:
            state.reviewer_feedback = guidance
        _record_rejected_attempt(
            state,
            project_id=blueprint.id,
            task_id=task.id,
            summary="candidate work rejected and rolled back",
            error=str(exc),
        )
        _persist(root, state, blueprint)
        return f"rejected {blueprint.id}/{task.id}; rollback complete; retry automatically next tick"

    diff = _diff_from_backups(project, backups, config.max_diff_chars_for_review)

    if state.phase == "build" and (work.task_complete or recovery):
        try:
            review_context = collect_context(project, state, task, config)
            review = review_task_completion(
                config, blueprint, task, review_context, diff, quality.summary
            )
        except Exception:
            _rollback(backups)
            raise
        _record_usage(state, [review])
        if review.verdict == "reject":
            _rollback(backups)
            state.reviewer_feedback = review.feedback or review.summary
            _record_rejected_attempt(
                state,
                project_id=blueprint.id,
                task_id=task.id,
                summary=review.summary or "independent reviewer rejected candidate",
                error=state.reviewer_feedback,
            )
            _persist(root, state, blueprint)
            return f"reviewer rejected {blueprint.id}/{task.id}; rollback complete"
        if review.verdict == "accept":
            state.current_task_index += 1
            state.current_task_attempts = 0
            state.reviewer_feedback = None
        else:
            state.reviewer_feedback = review.feedback or review.summary
    elif state.phase == "build":
        # Keep bounded validated partial progress. Recovery eventually forces independent review.
        state.reviewer_feedback = None

    _mark_success(state, touched, project, blueprint.id, task.id, work.summary)

    if state.phase == "build" and state.current_task_index >= len(blueprint.tasks):
        state.phase = "audit_pending"
        state.final_review_feedback = None

    if state.phase in {"audit_pending", "final_review"}:
        try:
            completed, message = _final_audit(
                root,
                state,
                blueprint,
                config,
                validated_report=quality,
            )
        except Exception:
            # The local work already passed deterministic gates; if the external audit service is
            # unavailable, preserve nothing remotely until the run succeeds, avoiding unaudited final
            # archival state. The runner is ephemeral, so re-raising safely retries later.
            raise
        if completed:
            catalog = load_catalog(root, state)
            render_projects_index(root, state, catalog)
            write_state(root, state)
            return message
        _persist(root, state, blueprint)
        return f"advanced {blueprint.id}/{task.id}; {message}"

    _persist(root, state, blueprint)
    planning_note = " (newly planned)" if newly_planned else ""
    return (
        f"advanced {blueprint.id}{planning_note}; task={task.id}; "
        f"claimed_complete={work.task_complete}; phase={state.phase}; {work.summary}"
    )
