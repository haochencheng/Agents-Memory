from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agents_memory.runtime import AppContext
from agents_memory.services.projects import resolve_project_target
from agents_memory.services.validation import (
    ValidationFinding,
    collect_docs_check_findings,
    collect_plan_check_findings,
    collect_profile_check_findings,
)
from agents_memory.services.validation.reporting import findings_overall
from agents_memory.services.workflow_records import write_workflow_record


SCHEDULER_CHECK_TYPES = ("docs", "profile", "plan")
_RUNNER_INTERVAL_SECONDS = 30
_TASK_GROUP_HISTORY_LIMIT = 200
_CRON_FIELD_RANGES = (
    ("minute", 0, 59),
    ("hour", 0, 23),
    ("day", 1, 31),
    ("month", 1, 12),
    ("weekday", 0, 6),
)
_STATUS_MAP = {
    "OK": "pass",
    "PARTIAL": "warn",
    "FAIL": "fail",
}
_OVERALL_STATUS_ORDER = {"pass": 0, "warn": 1, "fail": 2}


@dataclass
class SchedulerTaskGroupRecord:
    id: str
    name: str
    project: str
    cron_expr: str
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""
    last_run_at: str = ""
    next_run_at: str = ""
    last_result: str = ""
    last_summary: str = ""


@dataclass
class SchedulerRunStepRecord:
    id: str
    batch_id: str
    task_group_id: str
    check_type: str
    status: str
    duration_ms: int
    summary: str
    details: list[str]
    workflow_record_id: str = ""


@dataclass
class SchedulerRunBatchRecord:
    id: str
    task_group_id: str
    task_group_name: str
    project: str
    run_at: str
    finished_at: str
    overall_status: str
    duration_ms: int
    trigger: str
    steps: list[SchedulerRunStepRecord] = field(default_factory=list)


@dataclass
class CheckRunRecord:
    id: str
    task_id: str
    task_name: str
    task_group_id: str
    task_group_name: str
    batch_id: str
    project: str
    check_type: str
    status: str
    run_at: str
    duration_ms: int
    summary: str
    details: list[str]
    trigger: str
    workflow_record_id: str = ""


def _now_local() -> datetime:
    return datetime.now().astimezone()


def _task_groups_path(ctx: AppContext) -> Path:
    return ctx.memory_dir / "scheduler_tasks.json"


def _scheduler_runs_path(ctx: AppContext) -> Path:
    return ctx.memory_dir / "scheduler_runs.jsonl"


def _legacy_check_runs_path(ctx: AppContext) -> Path:
    return ctx.memory_dir / "check_runs.jsonl"


def _json_default(value: object) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported value: {type(value)!r}")


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _read_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _stable_group_id(project: str, name: str, cron_expr: str, created_at: str) -> str:
    raw = f"{project}|{name}|{cron_expr}|{created_at}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _task_group_from_payload(payload: dict[str, Any]) -> SchedulerTaskGroupRecord:
    return SchedulerTaskGroupRecord(
        id=str(payload.get("id", "")),
        name=str(payload.get("name", "")),
        project=str(payload.get("project", "")),
        cron_expr=str(payload.get("cron_expr", "")),
        status=str(payload.get("status", "active")),
        created_at=str(payload.get("created_at", "")),
        updated_at=str(payload.get("updated_at", "")),
        last_run_at=str(payload.get("last_run_at", "")),
        next_run_at=str(payload.get("next_run_at", "")),
        last_result=str(payload.get("last_result", "")),
        last_summary=str(payload.get("last_summary", "")),
    )


def _step_from_payload(payload: dict[str, Any]) -> SchedulerRunStepRecord:
    return SchedulerRunStepRecord(
        id=str(payload.get("id", "")),
        batch_id=str(payload.get("batch_id", "")),
        task_group_id=str(payload.get("task_group_id", "")),
        check_type=str(payload.get("check_type", "")),
        status=str(payload.get("status", "")),
        duration_ms=int(payload.get("duration_ms", 0) or 0),
        summary=str(payload.get("summary", "")),
        details=[str(item) for item in payload.get("details", []) if str(item).strip()],
        workflow_record_id=str(payload.get("workflow_record_id", "")),
    )


def _batch_from_payload(payload: dict[str, Any]) -> SchedulerRunBatchRecord:
    return SchedulerRunBatchRecord(
        id=str(payload.get("id", "")),
        task_group_id=str(payload.get("task_group_id", "")),
        task_group_name=str(payload.get("task_group_name", "")),
        project=str(payload.get("project", "")),
        run_at=str(payload.get("run_at", "")),
        finished_at=str(payload.get("finished_at", "")),
        overall_status=str(payload.get("overall_status", "")),
        duration_ms=int(payload.get("duration_ms", 0) or 0),
        trigger=str(payload.get("trigger", "scheduled")),
        steps=[_step_from_payload(item) for item in payload.get("steps", []) if isinstance(item, dict)],
    )


def _legacy_group_base_name(name: str, check_type: str) -> str:
    suffix = f"-{check_type}"
    if name.endswith(suffix):
        return name[: -len(suffix)] or name
    return name


def _overall_from_statuses(statuses: list[str]) -> str:
    if not statuses:
        return "pass"
    return max(statuses, key=lambda item: _OVERALL_STATUS_ORDER.get(item, 0))


def _legacy_groups_from_tasks(payload: dict[str, Any]) -> list[SchedulerTaskGroupRecord]:
    raw_tasks = payload.get("tasks", [])
    if not isinstance(raw_tasks, list):
        return []

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in raw_tasks:
        if not isinstance(item, dict):
            continue
        project = str(item.get("project", ""))
        cron_expr = str(item.get("cron_expr", ""))
        name = str(item.get("name", ""))
        check_type = str(item.get("check_type", "docs"))
        grouped.setdefault((project, cron_expr, _legacy_group_base_name(name, check_type)), []).append(item)

    task_groups: list[SchedulerTaskGroupRecord] = []
    for (_project, _cron_expr, base_name), items in grouped.items():
        first = items[0]
        created_at = str(first.get("created_at", "")) or _now_local().isoformat()
        next_run_values = [str(item.get("next_run", "")) for item in items if str(item.get("next_run", "")).strip()]
        last_run_values = [str(item.get("last_run", "")) for item in items if str(item.get("last_run", "")).strip()]
        result_values = [str(item.get("last_result", "")) for item in items if str(item.get("last_result", "")).strip()]
        summary_values = [str(item.get("last_summary", "")) for item in items if str(item.get("last_summary", "")).strip()]
        task_groups.append(
            SchedulerTaskGroupRecord(
                id=_stable_group_id(str(first.get("project", "")), base_name, str(first.get("cron_expr", "")), created_at),
                name=base_name,
                project=str(first.get("project", "")),
                cron_expr=str(first.get("cron_expr", "")),
                status=str(first.get("status", "active")),
                created_at=created_at,
                updated_at=str(first.get("updated_at", "")) or created_at,
                last_run_at=max(last_run_values) if last_run_values else "",
                next_run_at=min(next_run_values) if next_run_values else "",
                last_result=_overall_from_statuses(result_values),
                last_summary=" | ".join(summary_values[:3]),
            )
        )
    return sorted(task_groups, key=lambda item: (item.project, item.name))


def load_task_groups(ctx: AppContext) -> list[SchedulerTaskGroupRecord]:
    payload = _read_json(_task_groups_path(ctx), {"task_groups": []})
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("task_groups"), list):
        groups = payload.get("task_groups", [])
        return [_task_group_from_payload(item) for item in groups if isinstance(item, dict)]
    if isinstance(payload.get("tasks"), list):
        return _legacy_groups_from_tasks(payload)
    return []


def save_task_groups(ctx: AppContext, groups: list[SchedulerTaskGroupRecord]) -> None:
    _atomic_write_json(_task_groups_path(ctx), {"task_groups": [asdict(group) for group in groups]})


def list_task_groups(ctx: AppContext) -> list[SchedulerTaskGroupRecord]:
    groups = load_task_groups(ctx)
    return sorted(groups, key=lambda item: (item.project, item.name))


def get_task_group(ctx: AppContext, task_group_id: str) -> SchedulerTaskGroupRecord | None:
    return next((group for group in load_task_groups(ctx) if group.id == task_group_id), None)


def create_task_group(
    ctx: AppContext,
    *,
    name: str,
    project: str,
    cron_expr: str,
    now: datetime | None = None,
) -> SchedulerTaskGroupRecord:
    validate_cron_expr(cron_expr)
    current = _now_local() if now is None else now
    created_at = current.isoformat()
    task_group = SchedulerTaskGroupRecord(
        id=_stable_group_id(project, name.strip(), cron_expr, created_at),
        name=name.strip(),
        project=project,
        cron_expr=cron_expr,
        status="active",
        created_at=created_at,
        updated_at=created_at,
        next_run_at=compute_next_run(cron_expr, after=current),
    )
    groups = load_task_groups(ctx)
    groups.append(task_group)
    save_task_groups(ctx, groups)
    return task_group


def update_task_group(
    ctx: AppContext,
    task_group_id: str,
    *,
    name: str,
    project: str,
    cron_expr: str,
    status: str,
    now: datetime | None = None,
) -> SchedulerTaskGroupRecord | None:
    validate_cron_expr(cron_expr)
    current = _now_local() if now is None else now
    groups = load_task_groups(ctx)
    updated_group: SchedulerTaskGroupRecord | None = None
    for group in groups:
        if group.id != task_group_id:
            continue
        group.name = name.strip()
        group.project = project
        group.cron_expr = cron_expr
        group.status = status
        group.updated_at = current.isoformat()
        if group.status == "active":
            reference = current
            if group.next_run_at:
                try:
                    reference = datetime.fromisoformat(group.next_run_at) - timedelta(minutes=1)
                except ValueError:
                    reference = current
            group.next_run_at = compute_next_run(group.cron_expr, after=max(reference, current))
        else:
            group.next_run_at = ""
        updated_group = group
        break
    if updated_group is None:
        return None
    save_task_groups(ctx, groups)
    return updated_group


def set_task_group_status(
    ctx: AppContext,
    task_group_id: str,
    *,
    status: str,
    now: datetime | None = None,
) -> SchedulerTaskGroupRecord | None:
    current = _now_local() if now is None else now
    groups = load_task_groups(ctx)
    updated_group: SchedulerTaskGroupRecord | None = None
    for group in groups:
        if group.id != task_group_id:
            continue
        group.status = status
        group.updated_at = current.isoformat()
        if status == "active":
            group.next_run_at = compute_next_run(group.cron_expr, after=current)
        else:
            group.next_run_at = ""
        updated_group = group
        break
    if updated_group is None:
        return None
    save_task_groups(ctx, groups)
    return updated_group


def delete_task_group(ctx: AppContext, task_group_id: str) -> bool:
    groups = load_task_groups(ctx)
    kept = [group for group in groups if group.id != task_group_id]
    if len(kept) == len(groups):
        return False
    save_task_groups(ctx, kept)
    return True


def _append_legacy_check_run(ctx: AppContext, run: CheckRunRecord) -> None:
    path = _legacy_check_runs_path(ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(run), ensure_ascii=False) + "\n")


def _load_batches_from_jsonl(path: Path) -> list[SchedulerRunBatchRecord]:
    if not path.exists():
        return []
    batches: list[SchedulerRunBatchRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        batches.append(_batch_from_payload(payload))
    return sorted(batches, key=lambda item: (item.run_at, item.id), reverse=True)


def load_scheduler_run_batches(
    ctx: AppContext,
    *,
    task_group_id: str | None = None,
    limit: int | None = None,
) -> list[SchedulerRunBatchRecord]:
    batches = _load_batches_from_jsonl(_scheduler_runs_path(ctx))
    if task_group_id:
        batches = [batch for batch in batches if batch.task_group_id == task_group_id]
    if limit is not None:
        batches = batches[:limit]
    return batches


def _write_scheduler_run_batches(ctx: AppContext, batches: list[SchedulerRunBatchRecord]) -> None:
    path = _scheduler_runs_path(ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(asdict(batch), ensure_ascii=False) for batch in batches]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _trim_batches_per_group(batches: list[SchedulerRunBatchRecord]) -> list[SchedulerRunBatchRecord]:
    kept: list[SchedulerRunBatchRecord] = []
    counters: dict[str, int] = {}
    for batch in sorted(batches, key=lambda item: (item.run_at, item.id), reverse=True):
        count = counters.get(batch.task_group_id, 0)
        if count >= _TASK_GROUP_HISTORY_LIMIT:
            continue
        kept.append(batch)
        counters[batch.task_group_id] = count + 1
    return sorted(kept, key=lambda item: (item.run_at, item.id))


def append_scheduler_run_batch(ctx: AppContext, batch: SchedulerRunBatchRecord) -> None:
    batches = _load_batches_from_jsonl(_scheduler_runs_path(ctx))
    batches.append(batch)
    _write_scheduler_run_batches(ctx, _trim_batches_per_group(batches))


def _flatten_check_runs_from_batches(batches: list[SchedulerRunBatchRecord]) -> list[CheckRunRecord]:
    records: list[CheckRunRecord] = []
    for batch in batches:
        for step in batch.steps:
            records.append(
                CheckRunRecord(
                    id=step.id,
                    task_id=f"{batch.task_group_id}:{step.check_type}",
                    task_name=f"{batch.task_group_name}-{step.check_type}",
                    task_group_id=batch.task_group_id,
                    task_group_name=batch.task_group_name,
                    batch_id=batch.id,
                    project=batch.project,
                    check_type=step.check_type,
                    status=step.status,
                    run_at=batch.run_at,
                    duration_ms=step.duration_ms,
                    summary=step.summary,
                    details=step.details,
                    trigger=batch.trigger,
                    workflow_record_id=step.workflow_record_id,
                )
            )
    return sorted(records, key=lambda item: (item.run_at, item.id), reverse=True)


def _load_legacy_check_runs(ctx: AppContext) -> list[CheckRunRecord]:
    path = _legacy_check_runs_path(ctx)
    if not path.exists():
        return []
    records: list[CheckRunRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        records.append(
            CheckRunRecord(
                id=str(payload.get("id", "")),
                task_id=str(payload.get("task_id", "")),
                task_name=str(payload.get("task_name", "")),
                task_group_id=str(payload.get("task_group_id", "")),
                task_group_name=str(payload.get("task_group_name", "")),
                batch_id=str(payload.get("batch_id", "")),
                project=str(payload.get("project", "")),
                check_type=str(payload.get("check_type", "")),
                status=str(payload.get("status", "")),
                run_at=str(payload.get("run_at", "")),
                duration_ms=int(payload.get("duration_ms", 0) or 0),
                summary=str(payload.get("summary", "")),
                details=[str(item) for item in payload.get("details", []) if str(item).strip()],
                trigger=str(payload.get("trigger", "scheduled")),
                workflow_record_id=str(payload.get("workflow_record_id", "")),
            )
        )
    return records


def load_check_runs(ctx: AppContext) -> list[CheckRunRecord]:
    batches = load_scheduler_run_batches(ctx)
    records = _flatten_check_runs_from_batches(batches)
    if records:
        return records
    return sorted(_load_legacy_check_runs(ctx), key=lambda item: (item.run_at, item.id), reverse=True)


def summarize_check_runs(runs: list[CheckRunRecord]) -> dict[str, dict[str, int]]:
    summary = {
        "docs": {"pass": 0, "warn": 0, "fail": 0},
        "profile": {"pass": 0, "warn": 0, "fail": 0},
        "plan": {"pass": 0, "warn": 0, "fail": 0},
    }
    latest_by_virtual_task: dict[tuple[str, str], CheckRunRecord] = {}
    for run in runs:
        key = (run.task_group_id or run.task_name, run.check_type)
        if key not in latest_by_virtual_task:
            latest_by_virtual_task[key] = run
    for run in latest_by_virtual_task.values():
        if run.check_type in summary and run.status in summary[run.check_type]:
            summary[run.check_type][run.status] += 1
    return summary


def recent_results_for_task_group(ctx: AppContext, task_group_id: str, *, limit: int = 5) -> list[str]:
    batches = load_scheduler_run_batches(ctx, task_group_id=task_group_id, limit=limit)
    return [batch.overall_status for batch in batches]


def latest_batch_for_task_group(ctx: AppContext, task_group_id: str) -> SchedulerRunBatchRecord | None:
    batches = load_scheduler_run_batches(ctx, task_group_id=task_group_id, limit=1)
    return batches[0] if batches else None


def _normalize_weekday(value: int) -> int:
    return (value + 1) % 7


def _parse_cron_part(part: str, min_value: int, max_value: int) -> set[int]:
    token = part.strip()
    if token == "*":
        return set(range(min_value, max_value + 1))
    allowed: set[int] = set()
    for chunk in token.split(","):
        item = chunk.strip()
        if not item:
            continue
        step = 1
        base = item
        if "/" in item:
            base, step_text = item.split("/", 1)
            step = int(step_text)
            if step <= 0:
                raise ValueError("cron step must be positive")
        if base == "*":
            start = min_value
            end = max_value
        elif "-" in base:
            start_text, end_text = base.split("-", 1)
            start = int(start_text)
            end = int(end_text)
        else:
            value = int(base)
            start = value
            end = value
        if start < min_value or end > max_value or start > end:
            raise ValueError("cron value out of range")
        allowed.update(range(start, end + 1, step))
    if not allowed:
        raise ValueError("cron field cannot be empty")
    return allowed


def validate_cron_expr(cron_expr: str) -> None:
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError("cron expression must have 5 fields")
    for part, (_name, min_value, max_value) in zip(parts, _CRON_FIELD_RANGES, strict=True):
        _parse_cron_part(part, min_value, max_value)


def _cron_matches(dt: datetime, cron_expr: str) -> bool:
    minute, hour, day, month, weekday = cron_expr.split()
    minute_values = _parse_cron_part(minute, 0, 59)
    hour_values = _parse_cron_part(hour, 0, 23)
    day_values = _parse_cron_part(day, 1, 31)
    month_values = _parse_cron_part(month, 1, 12)
    weekday_values = _parse_cron_part(weekday, 0, 6)
    return (
        dt.minute in minute_values
        and dt.hour in hour_values
        and dt.day in day_values
        and dt.month in month_values
        and _normalize_weekday(dt.weekday()) in weekday_values
    )


def compute_next_run(cron_expr: str, *, after: datetime | None = None) -> str:
    validate_cron_expr(cron_expr)
    current = (after or _now_local()).replace(second=0, microsecond=0) + timedelta(minutes=1)
    deadline = current + timedelta(days=370)
    while current <= deadline:
        if _cron_matches(current, cron_expr):
            return current.isoformat()
        current += timedelta(minutes=1)
    raise ValueError(f"unable to compute next run for cron '{cron_expr}'")


def _run_findings_for_check(ctx: AppContext, group: SchedulerTaskGroupRecord, check_type: str) -> list[ValidationFinding]:
    project_id, project_root, _project = resolve_project_target(ctx, group.project)
    if not project_root:
        return [ValidationFinding("FAIL", "scheduler_project", f"registered project root not found: {project_id}")]
    if check_type == "docs":
        return collect_docs_check_findings(project_root)
    if check_type == "profile":
        return collect_profile_check_findings(ctx, project_root)
    if check_type == "plan":
        return collect_plan_check_findings(project_root, str(project_root))
    return [ValidationFinding("FAIL", "scheduler_check_type", f"unsupported check type: {check_type}")]


def _workflow_markdown_for_step(
    group: SchedulerTaskGroupRecord,
    batch: SchedulerRunBatchRecord,
    step: SchedulerRunStepRecord,
) -> str:
    lines = [
        "---",
        f"id: {step.id}",
        f"title: Scheduler {step.check_type}-check for {group.project}",
        "status: completed",
        f"completed_at: {batch.finished_at}",
        f"check_type: {step.check_type}",
        f"task_group_id: {group.id}",
        f"task_group_name: {group.name}",
        f"batch_id: {batch.id}",
        f"cron_expr: \"{group.cron_expr}\"",
        f"run_status: {step.status}",
        f"trigger: {batch.trigger}",
        "---",
        "",
        "# Scheduler Check Run",
        "",
        f"- Project: `{group.project}`",
        f"- Task Group: `{group.name}`",
        f"- Check Type: `{step.check_type}`",
        f"- Status: `{step.status}`",
        f"- Trigger: `{batch.trigger}`",
        f"- Run At: `{batch.run_at}`",
        f"- Duration: `{step.duration_ms}ms`",
        f"- Summary: {step.summary}",
        "",
        "## Findings",
    ]
    if not step.details:
        lines.append("- [OK] no findings")
    else:
        lines.extend(f"- {detail}" for detail in step.details)
    lines.append("")
    return "\n".join(lines)


def execute_task_group(
    ctx: AppContext,
    group: SchedulerTaskGroupRecord,
    *,
    trigger: str = "manual",
    run_at: datetime | None = None,
) -> SchedulerRunBatchRecord:
    started = _now_local() if run_at is None else run_at
    batch_id = f"RUN-{started.strftime('%Y%m%d%H%M%S')}-{group.id}"
    steps: list[SchedulerRunStepRecord] = []
    for check_type in SCHEDULER_CHECK_TYPES:
        step_started = _now_local()
        findings = _run_findings_for_check(ctx, group, check_type)
        overall = findings_overall(findings)
        status = _STATUS_MAP.get(overall, "warn")
        summary = " | ".join(f"{finding.status}:{finding.key}" for finding in findings[:3]) or "no findings"
        step_finished = _now_local()
        step = SchedulerRunStepRecord(
            id=f"{batch_id}-{check_type}",
            batch_id=batch_id,
            task_group_id=group.id,
            check_type=check_type,
            status=status,
            duration_ms=max(1, int((step_finished - step_started).total_seconds() * 1000)),
            summary=summary,
            details=[f"[{finding.status}] {finding.key}: {finding.detail}" for finding in findings],
        )
        temp_batch = SchedulerRunBatchRecord(
            id=batch_id,
            task_group_id=group.id,
            task_group_name=group.name,
            project=group.project,
            run_at=started.isoformat(),
            finished_at=step_finished.isoformat(),
            overall_status=status,
            duration_ms=step.duration_ms,
            trigger=trigger,
            steps=[step],
        )
        stored = write_workflow_record(
            ctx,
            content=_workflow_markdown_for_step(group, temp_batch, step),
            project=group.project,
            source_type="scheduler_check",
        )
        step.workflow_record_id = stored.record_id
        steps.append(step)

    finished = _now_local()
    batch = SchedulerRunBatchRecord(
        id=batch_id,
        task_group_id=group.id,
        task_group_name=group.name,
        project=group.project,
        run_at=started.isoformat(),
        finished_at=finished.isoformat(),
        overall_status=_overall_from_statuses([step.status for step in steps]),
        duration_ms=max(1, int((finished - started).total_seconds() * 1000)),
        trigger=trigger,
        steps=steps,
    )
    append_scheduler_run_batch(ctx, batch)
    for step in steps:
        _append_legacy_check_run(
            ctx,
            CheckRunRecord(
                id=step.id,
                task_id=f"{group.id}:{step.check_type}",
                task_name=f"{group.name}-{step.check_type}",
                task_group_id=group.id,
                task_group_name=group.name,
                batch_id=batch.id,
                project=group.project,
                check_type=step.check_type,
                status=step.status,
                run_at=batch.run_at,
                duration_ms=step.duration_ms,
                summary=step.summary,
                details=step.details,
                trigger=trigger,
                workflow_record_id=step.workflow_record_id,
            ),
        )
    return batch


def run_due_task_groups(ctx: AppContext, *, now: datetime | None = None) -> list[SchedulerRunBatchRecord]:
    current = _now_local() if now is None else now
    groups = load_task_groups(ctx)
    updated = False
    runs: list[SchedulerRunBatchRecord] = []
    for group in groups:
        if group.status != "active":
            continue
        if not group.next_run_at:
            group.next_run_at = compute_next_run(group.cron_expr, after=current)
            group.updated_at = current.isoformat()
            updated = True
            continue
        try:
            next_run = datetime.fromisoformat(group.next_run_at)
        except ValueError:
            group.next_run_at = compute_next_run(group.cron_expr, after=current)
            group.updated_at = current.isoformat()
            updated = True
            continue
        if next_run > current:
            continue
        batch = execute_task_group(ctx, group, trigger="scheduled", run_at=current)
        group.last_run_at = batch.run_at
        group.last_result = batch.overall_status
        group.last_summary = " | ".join(f"{step.check_type}:{step.status}" for step in batch.steps)
        group.next_run_at = compute_next_run(group.cron_expr, after=current)
        group.updated_at = current.isoformat()
        runs.append(batch)
        updated = True
    if updated:
        save_task_groups(ctx, groups)
    return runs


def execute_task_group_now(ctx: AppContext, task_group_id: str, *, now: datetime | None = None) -> SchedulerRunBatchRecord | None:
    current = _now_local() if now is None else now
    groups = load_task_groups(ctx)
    target: SchedulerTaskGroupRecord | None = None
    for group in groups:
        if group.id == task_group_id:
            target = group
            break
    if target is None:
        return None
    batch = execute_task_group(ctx, target, trigger="manual", run_at=current)
    target.last_run_at = batch.run_at
    target.last_result = batch.overall_status
    target.last_summary = " | ".join(f"{step.check_type}:{step.status}" for step in batch.steps)
    if target.status == "active":
        target.next_run_at = compute_next_run(target.cron_expr, after=current)
    target.updated_at = current.isoformat()
    save_task_groups(ctx, groups)
    return batch


def flatten_groups_to_legacy_tasks(ctx: AppContext) -> list[dict[str, Any]]:
    groups = list_task_groups(ctx)
    flattened: list[dict[str, Any]] = []
    for group in groups:
        latest_batch = latest_batch_for_task_group(ctx, group.id)
        latest_steps = {step.check_type: step for step in latest_batch.steps} if latest_batch else {}
        for check_type in SCHEDULER_CHECK_TYPES:
            step = latest_steps.get(check_type)
            flattened.append(
                {
                    "id": f"{group.id}:{check_type}",
                    "name": f"{group.name}-{check_type}",
                    "check_type": check_type,
                    "project": group.project,
                    "cron_expr": group.cron_expr,
                    "status": group.status,
                    "created_at": group.created_at,
                    "updated_at": group.updated_at,
                    "last_run": group.last_run_at,
                    "next_run": group.next_run_at,
                    "last_result": step.status if step else group.last_result,
                    "last_summary": step.summary if step else group.last_summary,
                }
            )
    return flattened


class SchedulerRuntime:
    def __init__(self, *, interval_seconds: int = _RUNNER_INTERVAL_SECONDS) -> None:
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._lock = threading.RLock()

    def start(self, ctx: AppContext) -> None:
        with self._lock:
            if self._task and not self._task.done():
                return
            self._stop_event = asyncio.Event()
            save_task_groups(ctx, load_task_groups(ctx))
            self._task = asyncio.create_task(self._run_loop(ctx))

    async def stop(self) -> None:
        with self._lock:
            task = self._task
            if task is None:
                return
            self._stop_event.set()
        await task
        with self._lock:
            self._task = None

    async def _run_loop(self, ctx: AppContext) -> None:
        while not self._stop_event.is_set():
            try:
                run_due_task_groups(ctx)
            except Exception as exc:  # pragma: no cover
                ctx.logger.exception("scheduler_loop_failed | detail=%s", exc)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval_seconds)
            except asyncio.TimeoutError:
                continue
