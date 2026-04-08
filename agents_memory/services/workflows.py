from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents_memory.runtime import AppContext
from agents_memory.services.integration import cmd_enable, onboarding_next_action
from agents_memory.services.integration_doctor import _doctor_report, _recommended_step_metadata, _state_recommended_steps, _write_onboarding_state_file, load_onboarding_state
from agents_memory.services.planning import cmd_plan_init
from agents_memory.services.planning_core import DEFAULT_PLAN_ROOT, README_PLAN_FILE, TASK_GRAPH_PLAN_FILE, VALIDATION_PLAN_FILE, json_block, refresh_managed_bundle_files, slugify_task_name
from agents_memory.services.validation import ValidationFinding, collect_bundle_exit_criteria_findings, collect_docs_check_findings, collect_plan_check_findings, collect_profile_check_findings, touch_doc_metadata
from agents_memory.services.wiki import search_wiki


TASK_STATUS_HEADING = "## Task Status"
CLOSE_OUT_SUMMARY_HEADING = "## Close-Out Summary"


@dataclass(frozen=True)
class WorkflowValidationSection:
    name: str
    overall: str
    findings: list[ValidationFinding]


@dataclass(frozen=True)
class WorkflowValidationReport:
    project_root: Path
    overall: str
    sections: list[WorkflowValidationSection]

    @property
    def required_failures(self) -> int:
        return sum(1 for section in self.sections for finding in section.findings if finding.status == "FAIL")

    @property
    def recommended_warnings(self) -> int:
        return sum(1 for section in self.sections for finding in section.findings if finding.status == "WARN")


@dataclass(frozen=True)
class CloseTaskResult:
    task_slug: str
    task_name: str
    project_root: Path
    plan_root: Path
    closed_at: str
    validation_report: WorkflowValidationReport
    bundle_gate_section: WorkflowValidationSection
    skip_global_gate: bool
    updated_files: list[str]
    state_path: Path


def _resolve_target_root(project_id_or_path: str) -> Path:
    return Path(project_id_or_path).expanduser().resolve()


def _validate_target_root(project_root: Path) -> int | None:
    if not project_root.exists():
        print(f"路径不存在: {project_root}")
        return 1
    if not project_root.is_dir():
        print(f"目标不是目录: {project_root}")
        return 1
    return None


def _section_overall(findings: list[ValidationFinding]) -> str:
    has_fail = any(finding.status == "FAIL" for finding in findings)
    has_warn = any(finding.status == "WARN" for finding in findings)
    if has_fail:
        return "FAIL"
    if has_warn:
        return "PARTIAL"
    return "OK"


def _overall_from_sections(sections: list[WorkflowValidationSection]) -> str:
    if any(section.overall == "FAIL" for section in sections):
        return "FAIL"
    if any(section.overall == "PARTIAL" for section in sections):
        return "PARTIAL"
    return "OK"


def _doctor_validation_section(ctx: AppContext, project_id_or_path: str) -> WorkflowValidationSection:
    report = _doctor_report(ctx, project_id_or_path)
    if report is None:
        findings = [ValidationFinding(status="FAIL", key="doctor_target", detail=f"unable to resolve target: {project_id_or_path}")]
        return WorkflowValidationSection(name="doctor", overall="FAIL", findings=findings)

    raw_checks = report.get("checks")
    checks = raw_checks if isinstance(raw_checks, list) else []
    findings = [
        ValidationFinding(status=str(status), key=str(key), detail=str(detail))
        for item in checks
        if isinstance(item, (list, tuple)) and len(item) == 3
        for status, key, detail in [item]
        if status in {"OK", "WARN", "FAIL", "INFO"}
    ]
    return WorkflowValidationSection(name="doctor", overall=_section_overall(findings), findings=findings)


def collect_workflow_validation_report(ctx: AppContext, project_id_or_path: str = ".") -> WorkflowValidationReport:
    project_root = _resolve_target_root(project_id_or_path)
    sections = [
        WorkflowValidationSection(name="docs", overall="OK", findings=collect_docs_check_findings(project_root)),
        WorkflowValidationSection(name="profile", overall="OK", findings=collect_profile_check_findings(ctx, project_root)),
        WorkflowValidationSection(name="planning", overall="OK", findings=collect_plan_check_findings(project_root, project_id_or_path)),
        _doctor_validation_section(ctx, project_id_or_path),
    ]
    normalized = [
        WorkflowValidationSection(name=section.name, overall=_section_overall(section.findings), findings=section.findings)
        for section in sections
    ]
    return WorkflowValidationReport(project_root=project_root, overall=_overall_from_sections(normalized), sections=normalized)


def _print_validation_report(report: WorkflowValidationReport) -> None:
    print("\n=== Validate ===")
    print(f"Root:    {report.project_root}")
    print(f"Overall: {report.overall}")
    for section in report.sections:
        print(f"\n[{section.name}] {section.overall}")
        for finding in section.findings:
            print(f"- [{finding.status}] {finding.key}: {finding.detail}")
    print("\nNext:")
    print("- Run amem do-next . if validation points to onboarding follow-up work")


def _workflow_validation_exit_code(report: WorkflowValidationReport, *, strict: bool) -> int:
    has_partial = any(section.overall == "PARTIAL" for section in report.sections)
    return 1 if report.overall == "FAIL" or (strict and has_partial) else 0


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative_bundle_path(task_slug: str) -> str:
    return (DEFAULT_PLAN_ROOT / task_slug).as_posix()


def _active_task_payload(*, task_name: str, task_slug: str, started_at: str) -> dict[str, object]:
    return {
        "task_name": task_name,
        "task_slug": task_slug,
        "bundle_path": _relative_bundle_path(task_slug),
        "status": "active",
        "started_at": started_at,
    }


def _persist_started_task_state(ctx: AppContext, project_root: Path, *, task_name: str, task_slug: str) -> Path:
    state = load_onboarding_state(project_root) or {
        "project_root": str(project_root),
        "project_bootstrap_ready": True,
        "project_bootstrap_complete": True,
    }
    task_payload = _active_task_payload(task_name=task_name, task_slug=task_slug, started_at=_iso_now())
    state["active_task"] = task_payload
    state["last_started_task"] = task_payload
    return _write_onboarding_state_file(ctx, project_root, state)


def _state_active_task(project_root: Path) -> dict[str, object] | None:
    state = load_onboarding_state(project_root)
    if not state:
        return None
    active_task = state.get("active_task")
    return active_task if isinstance(active_task, dict) else None


def _print_do_next_header(project_root: Path, status: str, action: dict[str, object]) -> None:
    print("\n=== Next Action ===")
    print(f"Root:      {project_root}")
    print(f"Status:    {status}")
    if "project_bootstrap_ready" in action:
        ready = "yes" if bool(action.get("project_bootstrap_ready")) else "no"
        complete = "yes" if bool(action.get("project_bootstrap_complete")) else "no"
        print(f"Bootstrap: ready={ready} complete={complete}")
    print(f"Message:   {action.get('message') or '-'}")


def _print_pending_do_next(action: dict[str, object]) -> None:
    print(f"Source:    {action.get('step_source') or '-'}")
    print(f"Group:     {action.get('group') or '-'}")
    print(f"Key:       {action.get('key') or '-'}")
    print(f"Priority:  {action.get('priority') or '-'}")
    print(f"Command:   {action.get('command') or '-'}")
    print(f"Verify:    {action.get('verify_with') or '-'}")
    print(f"DoneWhen:  {action.get('done_when') or '-'}")
    print(f"Next:      {action.get('next_command') or '-'}")
    bundle_path = action.get("bundle_path")
    if bundle_path:
        print(f"Bundle:    {bundle_path}")


def _print_non_pending_do_next(action: dict[str, object]) -> None:
    recommended = action.get("recommended_command") or action.get("verify_with") or 'amem start-task "<task>" .'
    print(f"Recommended: {recommended}")


def _print_active_task_hint(active_task: dict[str, object]) -> None:
    print(f"ActiveTask: {active_task.get('task_slug') or '-'}")
    print(f"Bundle:     {active_task.get('bundle_path') or '-'}")
    print("Validate:   amem validate .")
    print(f"Close:      amem close-task . --slug {active_task.get('task_slug') or '<task-slug>'}")


def _bundle_candidates(project_root: Path) -> list[Path]:
    plans_root = project_root / DEFAULT_PLAN_ROOT
    if not plans_root.exists():
        return []
    return sorted(path for path in plans_root.iterdir() if path.is_dir())


def _resolve_close_task_bundle(project_root: Path, *, task_slug: str | None) -> tuple[str, Path]:
    if task_slug:
        return task_slug, project_root / DEFAULT_PLAN_ROOT / task_slug

    active_task = _state_active_task(project_root)
    if active_task and active_task.get("task_slug"):
        resolved_slug = str(active_task["task_slug"])
        return resolved_slug, project_root / DEFAULT_PLAN_ROOT / resolved_slug

    bundles = _bundle_candidates(project_root)
    if len(bundles) == 1:
        return bundles[0].name, bundles[0]
    raise ValueError("unable to determine task bundle; pass --slug <task-slug>")


def _bundle_required_files(plan_root: Path) -> list[Path]:
    return [plan_root / filename for filename in (README_PLAN_FILE, TASK_GRAPH_PLAN_FILE, VALIDATION_PLAN_FILE)]


def _bundle_task_name(plan_root: Path) -> str:
    readme_path = plan_root / README_PLAN_FILE
    if readme_path.exists():
        for line in readme_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return plan_root.name.replace("-", " ").strip() or "Untitled Task"


def _close_task_payload(report: WorkflowValidationReport, *, task_name: str, task_slug: str, closed_at: str) -> dict[str, object]:
    return {
        "task_name": task_name,
        "task_slug": task_slug,
        "bundle_path": _relative_bundle_path(task_slug),
        "status": "completed",
        "closed_at": closed_at,
        "validation_overall": report.overall,
        "required_failures": report.required_failures,
        "recommended_warnings": report.recommended_warnings,
        "sections": [{"name": section.name, "overall": section.overall} for section in report.sections],
        "verify_command": "amem validate .",
    }


def _render_close_task_content(filename: str, *, payload: dict[str, object], target_root: Path) -> str:
    if filename == README_PLAN_FILE:
        lines = [
            TASK_STATUS_HEADING,
            f"- status: `{payload['status']}`",
            f"- task slug: `{payload['task_slug']}`",
            f"- closed at: `{payload['closed_at']}`",
            f"- validation overall: `{payload['validation_overall']}`",
            f"- required failures: `{payload['required_failures']}`",
            f"- recommended warnings: `{payload['recommended_warnings']}`",
        ]
        return "\n".join(lines) + "\n"
    lines = [TASK_STATUS_HEADING] if filename == TASK_GRAPH_PLAN_FILE else [CLOSE_OUT_SUMMARY_HEADING]
    lines.extend(["```json", json_block(payload, target_root=target_root), "```"])
    return "\n".join(lines) + "\n"


def _close_task_heading(filename: str) -> str:
    return CLOSE_OUT_SUMMARY_HEADING if filename == VALIDATION_PLAN_FILE else TASK_STATUS_HEADING


def _touch_close_task_files(project_root: Path, updated_files: list[str]) -> None:
    for relative in updated_files:
        touch_doc_metadata(project_root, str(project_root / relative))


def _filtered_recommended_steps(existing_state: dict[str, object], *, bundle_path: str, task_slug: str) -> list[dict[str, object]]:
    filtered: list[dict[str, object]] = []
    for step in _state_recommended_steps(existing_state):
        if step.get("bundle_path") == bundle_path:
            continue
        if step.get("task_slug") == task_slug:
            continue
        filtered.append(step)
    return filtered


def _apply_completion_fields(
    state: dict[str, object],
    completion: dict[str, object],
    *,
    task_slug: str,
    report: WorkflowValidationReport,
    closed_at: str,
) -> None:
    # Idempotently merge the completed task into the cumulative list.
    raw = state.get("completed_tasks")
    prior: list[dict[str, Any]] = [item for item in raw if isinstance(item, dict) and item.get("task_slug") != task_slug] if isinstance(raw, list) else []
    prior.append(completion)
    state["completed_tasks"] = prior
    state["last_completed_task"] = completion
    state["last_validation_report"] = {
        "overall": report.overall,
        "required_failures": report.required_failures,
        "recommended_warnings": report.recommended_warnings,
        "closed_task_slug": task_slug,
        "closed_at": closed_at,
    }
    active_task = state.get("active_task")
    if isinstance(active_task, dict) and active_task.get("task_slug") == task_slug:
        state.pop("active_task", None)


def _apply_remaining_steps(
    state: dict[str, object],
    *,
    bundle_path: str,
    task_slug: str,
) -> None:
    # Remove completed bundle's steps; reset recommendation fields if nothing remains.
    remaining = _filtered_recommended_steps(state, bundle_path=bundle_path, task_slug=task_slug)
    if remaining:
        state["recommended_steps"] = remaining
        state.update(_recommended_step_metadata(remaining[0]))
        return
    state.pop("recommended_steps", None)
    refactor_bundle = state.get("recommended_refactor_bundle")
    if isinstance(refactor_bundle, dict) and refactor_bundle.get("task_slug") == task_slug:
        state.pop("recommended_refactor_bundle", None)
    state.update({
        "recommended_next_group": None,
        "recommended_next_key": None,
        "recommended_next_command": None,
        "recommended_verify_command": "amem validate .",
        "recommended_done_when": "No pending onboarding steps remain.",
        "recommended_next_safe_to_auto_execute": False,
        "recommended_next_approval_required": False,
        "recommended_next_approval_reason": None,
    })


def _update_close_task_state(
    ctx: AppContext,
    project_root: Path,
    *,
    task_name: str,
    task_slug: str,
    closed_at: str,
    report: WorkflowValidationReport,
) -> Path:
    state: dict[str, object] = load_onboarding_state(project_root) or {
        "project_root": str(project_root),
        "project_bootstrap_ready": True,
        "project_bootstrap_complete": True,
    }
    completion = _close_task_payload(report, task_name=task_name, task_slug=task_slug, closed_at=closed_at)
    _apply_completion_fields(state, completion, task_slug=task_slug, report=report, closed_at=closed_at)
    _apply_remaining_steps(state, bundle_path=_relative_bundle_path(task_slug), task_slug=task_slug)
    return _write_onboarding_state_file(ctx, project_root, state)


def _bundle_gate_section(plan_root: Path) -> WorkflowValidationSection:
    findings = collect_bundle_exit_criteria_findings(plan_root)
    return WorkflowValidationSection(name="bundle_gate", overall=_section_overall(findings), findings=findings)


def _validate_bundle_files(plan_root: Path) -> None:
    missing_files = [path.name for path in _bundle_required_files(plan_root) if not path.exists()]
    if missing_files:
        raise FileNotFoundError(f"task bundle missing required files: {', '.join(missing_files)}")


def _merge_close_task_reports(
    ctx: AppContext,
    project_root: Path,
    *,
    bundle_section: WorkflowValidationSection,
    strict: bool,
    skip_global_gate: bool,
) -> WorkflowValidationReport:
    # Run the repo-wide gate and merge with the bundle gate into a combined report.
    report = collect_workflow_validation_report(ctx, str(project_root))
    if not skip_global_gate and _workflow_validation_exit_code(report, strict=strict) != 0:
        raise RuntimeError("validate gate failed; close-task aborted")
    merged_sections = [bundle_section, *report.sections]
    return WorkflowValidationReport(
        project_root=project_root,
        overall=_overall_from_sections(merged_sections),
        sections=merged_sections,
    )


def _apply_close_task_changes(
    ctx: AppContext,
    project_root: Path,
    *,
    resolved_slug: str,
    plan_root: Path,
    task_name: str,
    closed_at: str,
    merged_report: WorkflowValidationReport,
) -> tuple[list[str], Path]:
    # Write bundle files and update onboarding state for the closed task.
    payload = _close_task_payload(merged_report, task_name=task_name, task_slug=resolved_slug, closed_at=closed_at)
    updated_files, _ = refresh_managed_bundle_files(
        ctx,
        target_root=project_root,
        plan_root=plan_root,
        filenames=(README_PLAN_FILE, TASK_GRAPH_PLAN_FILE, VALIDATION_PLAN_FILE),
        created_now=set(),
        dry_run=False,
        render_content=lambda filename: _render_close_task_content(filename, payload=payload, target_root=project_root),
        resolve_heading=_close_task_heading,
        create_action="close_task_bundle_file",
        refresh_action="close_task_bundle_refresh",
        log_detail=f"task_slug={resolved_slug}",
    )
    _touch_close_task_files(project_root, updated_files)
    state_path = _update_close_task_state(
        ctx, project_root, task_name=task_name, task_slug=resolved_slug,
        closed_at=closed_at, report=merged_report,
    )
    return updated_files, state_path


def _close_task_core(
    ctx: AppContext,
    project_root: Path,
    *,
    task_slug: str | None,
    strict: bool,
    skip_global_gate: bool,
) -> CloseTaskResult:
    # Execute stage-1/2 gates, write bundle files, and record the closing action.
    resolved_slug, plan_root = _resolve_close_task_bundle(project_root, task_slug=task_slug)
    _validate_bundle_files(plan_root)
    bundle_section = _bundle_gate_section(plan_root)
    if bundle_section.overall != "OK":
        raise RuntimeError(
            f"bundle exit criteria gate failed ({bundle_section.overall}); "
            "resolve unchecked items in task-graph.md (## Exit Criteria) or validation.md (## Task-Specific Checks)"
        )
    merged_report = _merge_close_task_reports(
        ctx, project_root, bundle_section=bundle_section, strict=strict, skip_global_gate=skip_global_gate
    )
    task_name = _bundle_task_name(plan_root)
    closed_at = _iso_now()
    updated_files, state_path = _apply_close_task_changes(
        ctx, project_root, resolved_slug=resolved_slug, plan_root=plan_root,
        task_name=task_name, closed_at=closed_at, merged_report=merged_report,
    )
    return CloseTaskResult(
        task_slug=resolved_slug,
        task_name=task_name,
        project_root=project_root,
        plan_root=plan_root,
        closed_at=closed_at,
        validation_report=merged_report,
        bundle_gate_section=bundle_section,
        skip_global_gate=skip_global_gate,
        updated_files=updated_files,
        state_path=state_path,
    )


def close_task(
    ctx: AppContext,
    project_id_or_path: str = ".",
    *,
    task_slug: str | None = None,
    strict: bool = False,
    skip_global_gate: bool = False,
) -> CloseTaskResult:
    # Validate project root then delegate to core close-task workflow.
    project_root = _resolve_target_root(project_id_or_path)
    validation_error = _validate_target_root(project_root)
    if validation_error is not None:
        raise ValueError(f"invalid project root: {project_root}")
    return _close_task_core(ctx, project_root, task_slug=task_slug, strict=strict, skip_global_gate=skip_global_gate)


def _print_close_task_summary(result: CloseTaskResult) -> None:
    print("\n=== Close Task ===")
    print(f"Task:        {result.task_name}")
    print(f"Slug:        {result.task_slug}")
    print(f"Target:      {result.project_root}")
    print(f"PlanDir:     {result.plan_root}")
    print(f"ClosedAt:    {result.closed_at}")
    print(f"BundleGate:  {result.bundle_gate_section.overall}")
    print(f"GlobalGate:  {'skipped' if result.skip_global_gate else result.validation_report.overall}")
    print(f"Overall:     {result.validation_report.overall}")
    print(f"State:       {result.state_path}")
    print(f"Updated:     {len(result.updated_files)} files")
    if result.updated_files:
        print("\nUpdated Files:")
        for item in result.updated_files:
            print(f"- {item}")
    print("\nNext:")
    print("- Run amem do-next . to inspect the next recommended action")
    print("- Run amem wiki-sync <topic> --content '<learnings>' to capture task knowledge in the wiki")


def cmd_bootstrap(
    ctx: AppContext,
    project_id_or_path: str = ".",
    *,
    full: bool = False,
    dry_run: bool = False,
    json_output: bool = False,
    ingest_wiki: bool = False,
    wiki_limit: int | None = None,
) -> int:
    return cmd_enable(
        ctx,
        project_id_or_path,
        full=full,
        dry_run=dry_run,
        json_output=json_output,
        ingest_wiki=ingest_wiki,
        wiki_limit=wiki_limit,
    )


def _print_wiki_context(ctx: AppContext, task_name: str) -> None:
    """Print relevant wiki pages for the task as context before the bundle."""
    matches = search_wiki(ctx.wiki_dir, task_name, limit=3)
    if not matches:
        return
    print("\n=== Wiki Context ===")
    print(f"Relevant wiki pages for: '{task_name}'\n")
    for match in matches:
        print(f"─── [{match['topic']}] ───")
        print(match["excerpt"])
        print()


def cmd_start_task(
    ctx: AppContext,
    task_name: str,
    project_id_or_path: str = ".",
    *,
    task_slug: str | None = None,
    dry_run: bool = False,
    wiki_context: bool = False,
) -> int:
    if wiki_context and not dry_run:
        _print_wiki_context(ctx, task_name)
    exit_code = cmd_plan_init(ctx, task_name, project_id_or_path, task_slug=task_slug, dry_run=dry_run)
    if exit_code != 0 or dry_run:
        return exit_code
    project_root = _resolve_target_root(project_id_or_path)
    resolved_slug = task_slug or slugify_task_name(task_name)
    _persist_started_task_state(ctx, project_root, task_name=task_name, task_slug=resolved_slug)
    print(f"- active task state: .agents-memory/onboarding-state.json -> {resolved_slug}")
    return 0


def cmd_do_next(ctx: AppContext, project_id_or_path: str = ".", *, output_format: str = "text") -> int:
    # Resolve the project root and print or return the next recommended action.
    project_root = _resolve_target_root(project_id_or_path)
    action = onboarding_next_action(project_root)
    status = str(action.get("status") or "invalid")
    active_task = _state_active_task(project_root)
    ctx.logger.info("workflow_do_next | target=%s | status=%s", project_root, status)

    if output_format == "json":
        payload = dict(action)
        if active_task is not None:
            payload["active_task"] = active_task
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_do_next_header(project_root, status, action)
        if status == "pending":
            _print_pending_do_next(action)
        else:
            _print_non_pending_do_next(action)
            if active_task is not None:
                _print_active_task_hint(active_task)

    return 1 if status in {"missing", "invalid"} else 0


def cmd_validate(ctx: AppContext, project_id_or_path: str = ".", *, strict: bool = False, output_format: str = "text") -> int:
    project_root = _resolve_target_root(project_id_or_path)
    validation_error = _validate_target_root(project_root)
    if validation_error is not None:
        return validation_error

    report = collect_workflow_validation_report(ctx, project_id_or_path)
    ctx.logger.info("workflow_validate | target=%s | overall=%s | strict=%s", project_root, report.overall, strict)

    if output_format == "json":
        print(
            json.dumps(
                {
                    "project_root": str(report.project_root),
                    "overall": report.overall,
                    "strict": strict,
                    "required_failures": report.required_failures,
                    "recommended_warnings": report.recommended_warnings,
                    "sections": [
                        {
                            "name": section.name,
                            "overall": section.overall,
                            "findings": [asdict(finding) for finding in section.findings],
                        }
                        for section in report.sections
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_validation_report(report)

    return _workflow_validation_exit_code(report, strict=strict)


def cmd_close_task(ctx: AppContext, project_id_or_path: str = ".", *, task_slug: str | None = None, strict: bool = False, output_format: str = "text", skip_global_gate: bool = False) -> int:
    try:
        result = close_task(ctx, project_id_or_path, task_slug=task_slug, strict=strict, skip_global_gate=skip_global_gate)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1

    if output_format == "json":
        print(
            json.dumps(
                {
                    "task_name": result.task_name,
                    "task_slug": result.task_slug,
                    "project_root": str(result.project_root),
                    "plan_root": str(result.plan_root),
                    "closed_at": result.closed_at,
                    "bundle_gate": result.bundle_gate_section.overall,
                    "skip_global_gate": result.skip_global_gate,
                    "overall": result.validation_report.overall,
                    "updated_files": result.updated_files,
                    "state_path": str(result.state_path),
                    "wiki_sync_hint": f"amem wiki-sync {result.task_slug} --content 'task learnings here'",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_close_task_summary(result)
    return 0
