from __future__ import annotations

import asyncio
import json
import threading
import uuid
from dataclasses import asdict, dataclass
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


@dataclass
class SchedulerTaskRecord:
    id: str
    name: str
    check_type: str
    project: str
    cron_expr: str
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""
    last_run: str = ""
    next_run: str = ""
    last_result: str = ""
    last_summary: str = ""


@dataclass
class CheckRunRecord:
    id: str
    task_id: str
    task_name: str
    project: str
    check_type: str
    status: str
    run_at: str
    duration_ms: int
    summary: str
    details: list[str]


def _now_local() -> datetime:
    return datetime.now().astimezone()


def _tasks_path(ctx: AppContext) -> Path:
    return ctx.memory_dir / "scheduler_tasks.json"


def _check_runs_path(ctx: AppContext) -> Path:
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


def _task_from_payload(payload: dict[str, Any]) -> SchedulerTaskRecord:
    return SchedulerTaskRecord(
        id=str(payload.get("id", "")),
        name=str(payload.get("name", "")),
        check_type=str(payload.get("check_type", "")),
        project=str(payload.get("project", "")),
        cron_expr=str(payload.get("cron_expr", "")),
        status=str(payload.get("status", "active")),
        created_at=str(payload.get("created_at", "")),
        updated_at=str(payload.get("updated_at", "")),
        last_run=str(payload.get("last_run", "")),
        next_run=str(payload.get("next_run", "")),
        last_result=str(payload.get("last_result", "")),
        last_summary=str(payload.get("last_summary", "")),
    )


def load_scheduler_tasks(ctx: AppContext) -> list[SchedulerTaskRecord]:
    payload = _read_json(_tasks_path(ctx), {"tasks": []})
    if not isinstance(payload, dict):
        return []
    raw_tasks = payload.get("tasks", [])
    if not isinstance(raw_tasks, list):
        return []
    return [_task_from_payload(item) for item in raw_tasks if isinstance(item, dict)]


def save_scheduler_tasks(ctx: AppContext, tasks: list[SchedulerTaskRecord]) -> None:
    _atomic_write_json(_tasks_path(ctx), {"tasks": [asdict(task) for task in tasks]})


def list_scheduler_tasks(ctx: AppContext) -> list[SchedulerTaskRecord]:
    return sorted(load_scheduler_tasks(ctx), key=lambda item: (item.project, item.name, item.check_type))


def append_check_run(ctx: AppContext, run: CheckRunRecord) -> None:
    path = _check_runs_path(ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(run), ensure_ascii=False) + "\n")


def load_check_runs(ctx: AppContext) -> list[CheckRunRecord]:
    path = _check_runs_path(ctx)
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
                project=str(payload.get("project", "")),
                check_type=str(payload.get("check_type", "")),
                status=str(payload.get("status", "")),
                run_at=str(payload.get("run_at", "")),
                duration_ms=int(payload.get("duration_ms", 0) or 0),
                summary=str(payload.get("summary", "")),
                details=[str(item) for item in payload.get("details", []) if str(item).strip()],
            )
        )
    return sorted(records, key=lambda item: (item.run_at, item.id), reverse=True)


def summarize_check_runs(runs: list[CheckRunRecord]) -> dict[str, dict[str, int]]:
    summary = {
        "docs": {"pass": 0, "warn": 0, "fail": 0},
        "profile": {"pass": 0, "warn": 0, "fail": 0},
        "plan": {"pass": 0, "warn": 0, "fail": 0},
    }
    latest_by_task: dict[str, CheckRunRecord] = {}
    for run in runs:
        if run.task_id and run.task_id not in latest_by_task:
            latest_by_task[run.task_id] = run
    for run in latest_by_task.values():
        if run.check_type not in summary:
            continue
        if run.status not in summary[run.check_type]:
            continue
        summary[run.check_type][run.status] += 1
    return summary


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


def create_scheduler_task_bundle(
    ctx: AppContext,
    *,
    name: str,
    project: str,
    cron_expr: str,
    now: datetime | None = None,
) -> list[SchedulerTaskRecord]:
    validate_cron_expr(cron_expr)
    current = _now_local() if now is None else now
    base_name = name.strip() or f"{project}-checks"
    tasks = load_scheduler_tasks(ctx)
    created_at = current.isoformat()
    next_run = compute_next_run(cron_expr, after=current)
    created: list[SchedulerTaskRecord] = []
    for check_type in SCHEDULER_CHECK_TYPES:
        task = SchedulerTaskRecord(
            id=str(uuid.uuid4())[:8],
            name=f"{base_name.strip()}-{check_type}",
            check_type=check_type,
            project=project,
            cron_expr=cron_expr,
            status="active",
            created_at=created_at,
            updated_at=created_at,
            next_run=next_run,
        )
        tasks.append(task)
        created.append(task)
    save_scheduler_tasks(ctx, tasks)
    return created


def delete_scheduler_task(ctx: AppContext, task_id: str) -> bool:
    tasks = load_scheduler_tasks(ctx)
    kept = [task for task in tasks if task.id != task_id]
    if len(kept) == len(tasks):
        return False
    save_scheduler_tasks(ctx, kept)
    return True


def _run_findings_for_task(ctx: AppContext, task: SchedulerTaskRecord) -> list[ValidationFinding]:
    project_id, project_root, _project = resolve_project_target(ctx, task.project)
    if not project_root:
        return [ValidationFinding("FAIL", "scheduler_project", f"registered project root not found: {project_id}")]
    if task.check_type == "docs":
        return collect_docs_check_findings(project_root)
    if task.check_type == "profile":
        return collect_profile_check_findings(ctx, project_root)
    if task.check_type == "plan":
        return collect_plan_check_findings(project_root, str(project_root))
    return [ValidationFinding("FAIL", "scheduler_check_type", f"unsupported check type: {task.check_type}")]


def _workflow_markdown_for_run(task: SchedulerTaskRecord, run: CheckRunRecord, findings: list[ValidationFinding]) -> str:
    lines = [
        "---",
        f"id: {run.id}",
        f"title: Scheduler {task.check_type}-check for {task.project}",
        "status: completed",
        f"completed_at: {run.run_at}",
        f"check_type: {task.check_type}",
        f"task_id: {task.id}",
        f"task_name: {task.name}",
        f"cron_expr: \"{task.cron_expr}\"",
        f"run_status: {run.status}",
        "---",
        "",
        "# Scheduler Check Run",
        "",
        f"- Project: `{task.project}`",
        f"- Check Type: `{task.check_type}`",
        f"- Task: `{task.name}`",
        f"- Status: `{run.status}`",
        f"- Run At: `{run.run_at}`",
        f"- Duration: `{run.duration_ms}ms`",
        f"- Summary: {run.summary}",
        "",
        "## Findings",
    ]
    if not findings:
        lines.append("- [OK] no findings")
    else:
        lines.extend(f"- [{finding.status}] `{finding.key}` {finding.detail}" for finding in findings)
    lines.append("")
    return "\n".join(lines)


def execute_scheduler_task(
    ctx: AppContext,
    task: SchedulerTaskRecord,
    *,
    run_at: datetime | None = None,
) -> CheckRunRecord:
    started = _now_local() if run_at is None else run_at
    findings = _run_findings_for_task(ctx, task)
    overall = findings_overall(findings)
    status = _STATUS_MAP.get(overall, "warn")
    summary = " | ".join(f"{finding.status}:{finding.key}" for finding in findings[:3]) or "no findings"
    finished = _now_local()
    duration_ms = max(1, int((finished - started).total_seconds() * 1000))
    run = CheckRunRecord(
        id=f"CHK-{started.strftime('%Y%m%d%H%M%S')}-{task.check_type}-{task.id}",
        task_id=task.id,
        task_name=task.name,
        project=task.project,
        check_type=task.check_type,
        status=status,
        run_at=started.isoformat(),
        duration_ms=duration_ms,
        summary=summary,
        details=[f"[{finding.status}] {finding.key}: {finding.detail}" for finding in findings],
    )
    append_check_run(ctx, run)
    workflow_content = _workflow_markdown_for_run(task, run, findings)
    write_workflow_record(ctx, content=workflow_content, project=task.project, source_type="scheduler_check")
    return run


def run_due_scheduler_tasks(ctx: AppContext, *, now: datetime | None = None) -> list[CheckRunRecord]:
    current = _now_local() if now is None else now
    tasks = load_scheduler_tasks(ctx)
    updated = False
    runs: list[CheckRunRecord] = []
    for task in tasks:
        if task.status != "active" or not task.next_run:
            if task.status == "active" and not task.next_run:
                task.next_run = compute_next_run(task.cron_expr, after=current)
                task.updated_at = current.isoformat()
                updated = True
            continue
        try:
            next_run = datetime.fromisoformat(task.next_run)
        except ValueError:
            task.next_run = compute_next_run(task.cron_expr, after=current)
            task.updated_at = current.isoformat()
            updated = True
            continue
        if next_run > current:
            continue
        run = execute_scheduler_task(ctx, task, run_at=current)
        task.last_run = run.run_at
        task.last_result = run.status
        task.last_summary = run.summary
        task.next_run = compute_next_run(task.cron_expr, after=current)
        task.updated_at = current.isoformat()
        runs.append(run)
        updated = True
    if updated:
        save_scheduler_tasks(ctx, tasks)
    return runs


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
            save_scheduler_tasks(ctx, load_scheduler_tasks(ctx))
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
                run_due_scheduler_tasks(ctx)
            except Exception as exc:  # pragma: no cover - defensive guard for production loop
                ctx.logger.exception("scheduler_loop_failed | detail=%s", exc)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval_seconds)
            except asyncio.TimeoutError:
                continue
