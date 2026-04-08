from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from agents_memory.constants import COPILOT_INSTRUCTIONS_REL, DEFAULT_BRIDGE_INSTRUCTION_REL, MCP_CONFIG_NAME, VSCODE_DIRNAME
from agents_memory.runtime import AppContext
from agents_memory.services.integration_register import _ensure_registered_project
from agents_memory.services.project_onboarding import ProjectKnowledgeIngestResult, ingest_project_wiki_sources
from agents_memory.services.integration_setup import cmd_bridge_install, cmd_copilot_setup, write_vscode_mcp_json
from agents_memory.services.profiles import PROFILE_MANIFEST_REL, PROJECT_FACTS_REL, ProfileStandardsSyncResult, apply_profile, detect_applied_profile, load_profile, expected_profile_paths, sync_profile_standards
from agents_memory.services.projects import project_already_registered, resolve_project_target
from agents_memory.services.validation import collect_refactor_watch_hotspots

if TYPE_CHECKING:
    from agents_memory.services.planning import RefactorBundleResult


DoctorReportFn = Callable[[AppContext, str], dict[str, object] | None]
DoctorCommandFn = Callable[[AppContext, str], None]
LoadStateFn = Callable[[Path], dict[str, object] | None]
MergeRefactorStateFn = Callable[..., dict[str, object]]
WriteStateFn = Callable[[AppContext, Path, dict[str, object]], Path]


def _doctor_artifact_paths(project_root: Path, *, write_state: bool, write_checklist: bool) -> list[Path]:
    artifacts: list[Path] = []
    if write_checklist:
        artifacts.append(project_root / "docs" / "plans" / "bootstrap-checklist.md")
        artifacts.append(project_root / "docs" / "plans" / "refactor-watch.md")
    if write_state:
        artifacts.append(project_root / ".agents-memory" / "onboarding-state.json")
    return artifacts


def _preview_enable_profile_actions(ctx: AppContext, project_root: Path, *, full: bool) -> tuple[list[str], list[str], list[str]]:
    capabilities: list[str] = []
    planned_writes: list[str] = []
    skipped_existing: list[str] = []

    applied_profile_id = detect_applied_profile(project_root)
    if full and not applied_profile_id:
        recommended_profile_id = _recommended_enable_profile_id(project_root)
        if not recommended_profile_id:
            skipped_existing.append("profile auto-apply skipped: no default profile detected")
            return capabilities, planned_writes, skipped_existing

        capabilities.append(f"apply recommended profile `{recommended_profile_id}`")
        profile = load_profile(ctx, recommended_profile_id)
        expected = expected_profile_paths(profile, project_root)
        planned_writes.extend(str(path) for path in expected["bootstrap_dirs"])
        planned_writes.extend(str(path) for path in expected["standard_files"])
        planned_writes.extend(str(path) for path in expected["template_files"])
        planned_writes.extend(str(path) for path in expected["overlay_files"])
        planned_writes.extend(str(path) for path in expected["managed_files"])
        planned_writes.append(str(project_root / PROFILE_MANIFEST_REL))
        planned_writes.append(str(project_root / PROJECT_FACTS_REL))
        return capabilities, planned_writes, skipped_existing

    if applied_profile_id:
        capabilities.append(f"refresh profile-managed standards for `{applied_profile_id}`")
        profile = load_profile(ctx, applied_profile_id)
        expected = expected_profile_paths(profile, project_root)
        planned_writes.extend(str(path) for path in expected["standard_files"])
        planned_writes.extend(str(path) for path in expected["overlay_files"])
        planned_writes.extend(str(path) for path in expected["managed_files"])
        planned_writes.append(str(project_root / PROFILE_MANIFEST_REL))
        planned_writes.append(str(project_root / PROJECT_FACTS_REL))
    else:
        skipped_existing.append("profile auto-apply skipped in default mode")
    return capabilities, planned_writes, skipped_existing


def _preview_onboarding_bundle_actions(ctx: AppContext, project_root: Path, *, doctor_report_fn: DoctorReportFn) -> tuple[list[str], list[str]]:
    report = doctor_report_fn(ctx, str(project_root))
    recommended_key = "onboarding"
    if isinstance(report, dict):
        runbook_steps = report.get("runbook_steps")
        if isinstance(runbook_steps, list) and runbook_steps and isinstance(runbook_steps[0], dict):
            recommended_key = str(runbook_steps[0].get("key") or recommended_key)

    onboarding_slug = f"onboarding-{recommended_key.replace('_', '-')}"
    onboarding_plan_root = project_root / "docs" / "plans" / onboarding_slug
    planned_writes = [
        str(onboarding_plan_root / filename)
        for filename in ("README.md", "spec.md", "plan.md", "task-graph.md", "validation.md")
    ]
    return ["generate onboarding planning bundle"], planned_writes


def _preview_refactor_bundle_actions(project_root: Path) -> tuple[list[str], list[str], list[str]]:
    hotspots = collect_refactor_watch_hotspots(project_root)
    if not hotspots:
        return [], [], ["refactor bundle generation skipped: no hotspots"]

    hotspot = hotspots[0]
    refactor_slug = f"refactor-{re.sub(r'[^a-zA-Z0-9]+', '-', f'{hotspot.relative_path}-{hotspot.function_name}'.lower()).strip('-') or 'untitled-task'}"
    refactor_root = project_root / "docs" / "plans" / refactor_slug
    planned_writes = [
        str(refactor_root / filename)
        for filename in ("README.md", "spec.md", "plan.md", "task-graph.md", "validation.md")
    ]
    planned_writes.append(str(project_root / ".agents-memory" / "onboarding-state.json"))
    capability = f"generate refactor bundle for `{hotspot.identifier}` using `{hotspot.rank_token}`"
    return [capability], planned_writes, []


def _collect_registry_preview(ctx: AppContext, project_id: str) -> tuple[list[str], list[str], list[str]]:
    # Determine whether project registration is needed or already present.
    if not project_already_registered(ctx, project_id):
        return [f"register project `{project_id}`"], [str(ctx.projects_file)], []
    return [], [], [f"registry entry already exists for `{project_id}`"]


def _collect_bridge_preview(project_root: Path) -> tuple[list[str], list[str], list[str]]:
    # Determine whether the bridge instruction file needs to be installed.
    bridge_path = project_root / DEFAULT_BRIDGE_INSTRUCTION_REL
    if not bridge_path.exists():
        return ["install bridge instruction"], [str(bridge_path)], []
    return [], [], [str(bridge_path)]


def _collect_full_mode_preview(project_root: Path) -> tuple[list[str], list[str], list[str]]:
    # Collect preview items that are only executed in --full mode.
    capabilities = ["install or update Copilot activation block"]
    planned_writes = [str(project_root / COPILOT_INSTRUCTIONS_REL)]
    refactor_caps, refactor_writes, refactor_skipped = _preview_refactor_bundle_actions(project_root)
    return capabilities + refactor_caps, planned_writes + refactor_writes, refactor_skipped


def _extend_previews(
    caps: list[str],
    writes: list[str],
    skipped: list[str],
    preview: tuple[list[str], list[str], list[str]],
) -> None:
    # Unpack a (caps, writes, skipped) preview tuple and extend the accumulators.
    c, w, s = preview
    caps.extend(c)
    writes.extend(w)
    skipped.extend(s)


def _collect_standard_previews(
    ctx: AppContext,
    project_root: Path,
    *,
    project_id: str,
    full: bool,
    ingest_wiki: bool,
    wiki_limit: int | None,
    doctor_report_fn: DoctorReportFn,
) -> tuple[list[str], list[str], list[str]]:
    # Collect preview data for registry, bridge, MCP, profile, doctor, and onboarding steps.
    caps: list[str] = []
    writes: list[str] = []
    skipped: list[str] = []
    _extend_previews(caps, writes, skipped, _collect_registry_preview(ctx, project_id))
    _extend_previews(caps, writes, skipped, _collect_bridge_preview(project_root))
    writes.append(str(project_root / VSCODE_DIRNAME / MCP_CONFIG_NAME))
    caps.append("merge agents-memory MCP server config")
    _extend_previews(caps, writes, skipped, _preview_enable_profile_actions(ctx, project_root, full=full))
    caps.append("refresh doctor state and checklist artifacts")
    writes.extend(str(path) for path in _doctor_artifact_paths(project_root, write_state=True, write_checklist=True))
    onboarding_caps, onboarding_writes = _preview_onboarding_bundle_actions(ctx, project_root, doctor_report_fn=doctor_report_fn)
    caps.extend(onboarding_caps)
    writes.extend(onboarding_writes)
    if ingest_wiki:
        preview_result = ingest_project_wiki_sources(
            ctx,
            project_root,
            project_id=project_id,
            max_files=wiki_limit,
            dry_run=True,
        )
        if preview_result.sources:
            caps.append(f"ingest {len(preview_result.sources)} project knowledge files into the shared wiki")
            writes.extend(str(ctx.wiki_dir / f"{item.topic}.md") for item in preview_result.sources)
        else:
            skipped.append("project wiki ingest skipped: no markdown knowledge sources found")
    return caps, writes, skipped


def _preview_enable_actions(
    ctx: AppContext,
    project_root: Path,
    *,
    project_id: str,
    full: bool,
    ingest_wiki: bool,
    wiki_limit: int | None,
    doctor_report_fn: DoctorReportFn,
) -> dict[str, object]:
    # Aggregate all planned capabilities and writes for a dry-run preview.
    caps, writes, skipped = _collect_standard_previews(
        ctx,
        project_root,
        project_id=project_id,
        full=full,
        ingest_wiki=ingest_wiki,
        wiki_limit=wiki_limit,
        doctor_report_fn=doctor_report_fn,
    )
    if full:
        full_caps, full_writes, full_skipped = _collect_full_mode_preview(project_root)
        caps.extend(full_caps)
        writes.extend(full_writes)
        skipped.extend(full_skipped)
    return {
        "status": "ok",
        "project_id": project_id,
        "project_root": str(project_root),
        "mode": "full" if full else "default",
        "dry_run": True,
        "capabilities": caps,
        "planned_writes": list(dict.fromkeys(writes)),
        "skipped_existing": skipped,
    }


def _detect_profile_by_structure(project_root: Path) -> str | None:
    # Map project directory structure to the best-fit profile ID.
    if (project_root / "package.json").exists() and (project_root / "apps").exists():
        return "fullstack-product"
    if (project_root / "package.json").exists() and ((project_root / "src").exists() or (project_root / "app").exists()):
        return "frontend-app"
    if (project_root / "scripts" / "mcp_server.py").exists() or (project_root / "runtime").exists():
        return "agent-runtime"
    if any((project_root / name).exists() for name in ("pyproject.toml", "requirements.txt", "setup.py")):
        return "python-service"
    if list(project_root.glob("**/*.py")):
        return "python-service"
    return None


def _recommended_enable_profile_id(project_root: Path) -> str | None:
    # Return the best-fit profile ID, or None if a profile is already applied.
    if detect_applied_profile(project_root):
        return None
    return _detect_profile_by_structure(project_root)


def _validate_enable_request(project_root: Path, *, dry_run: bool, json_output: bool) -> int | None:
    if not project_root.exists():
        print(f"路径不存在: {project_root}")
        return 1
    if not project_root.is_dir():
        print(f"目标不是目录: {project_root}")
        return 1
    if json_output and not dry_run:
        print("--json 目前仅支持与 --dry-run 一起使用")
        return 1
    return None


def _print_enable_header(project_root: Path, *, full: bool, dry_run: bool) -> None:
    print("\n=== Agents-Memory Enable ===")
    print(f"Target: {project_root}")
    print(f"Mode:   {'full' if full else 'default'}")
    print(f"DryRun: {'yes' if dry_run else 'no'}")


def _preview_strings(preview: dict[str, object], key: str) -> list[str]:
    values = preview.get(key)
    if not isinstance(values, list):
        return []
    return [str(item) for item in values]


def _render_enable_preview(preview: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return

    print("\nCapabilities:")
    for item in _preview_strings(preview, "capabilities"):
        print(f"- {item}")
    print("\nPlanned Writes:")
    for path in _preview_strings(preview, "planned_writes"):
        print(f"- {path}")
    print("\nSkipped Existing:")
    skipped_existing = _preview_strings(preview, "skipped_existing")
    if skipped_existing:
        for item in skipped_existing:
            print(f"- {item}")
    else:
        print("- none")
    print("\nNext:")
    print("- Re-run without --dry-run to apply these changes")


def _run_enable_dry_run(
    ctx: AppContext,
    project_root: Path,
    *,
    project_id: str,
    full: bool,
    ingest_wiki: bool,
    wiki_limit: int,
    json_output: bool,
    doctor_report_fn: DoctorReportFn,
) -> int:
    preview = _preview_enable_actions(
        ctx,
        project_root,
        project_id=project_id,
        full=full,
        ingest_wiki=ingest_wiki,
        wiki_limit=wiki_limit,
        doctor_report_fn=doctor_report_fn,
    )
    _render_enable_preview(preview, json_output=json_output)
    ctx.logger.info(
        "enable_preview | target=%s | full=%s | planned_writes=%s",
        project_root,
        full,
        len(_preview_strings(preview, "planned_writes")),
    )
    return 0


def _apply_enable_profile(ctx: AppContext, project_root: Path, *, full: bool) -> str | None:
    applied_profile_id = detect_applied_profile(project_root)
    if full and not applied_profile_id:
        recommended_profile_id = _recommended_enable_profile_id(project_root)
        if not recommended_profile_id:
            print("- profile: skipped (no default profile detected)")
            return None

        profile = load_profile(ctx, recommended_profile_id)
        profile_result = apply_profile(ctx, profile, project_root)
        print(f"- profile: enabled ({profile_result.profile_id})")
        return profile_result.profile_id

    if applied_profile_id:
        print(f"- profile: ready ({applied_profile_id})")
        return applied_profile_id

    print("- profile: skipped in default mode")
    return None


def _print_enable_standards_sync(result: ProfileStandardsSyncResult) -> None:
    if result.missing_sources:
        missing = ", ".join(result.missing_sources)
        print(f"- standards: incomplete (missing sources: {missing})")
        return
    if result.synced_standards or result.synced_managed_files or result.manifest_updated:
        detail = f"{len(result.synced_standards)} standards"
        if result.synced_managed_files:
            detail += ", AGENTS.md refreshed"
        print(f"- standards: synced ({detail})")
        return
    print("- standards: ready")


def _print_enable_wiki_ingest(result: ProjectKnowledgeIngestResult) -> None:
    if not result.sources:
        print("- wiki ingest: skipped (no markdown knowledge sources found)")
        return
    print(f"- wiki ingest: imported {result.ingested_count} files into {len(result.sources)} wiki topics")
    for item in result.sources[:5]:
        print(f"  - {item.source_path} -> {item.topic}")
    remaining = len(result.sources) - 5
    if remaining > 0:
        print(f"  - ... and {remaining} more")


def _sync_enable_profile_standards(ctx: AppContext, project_root: Path, profile_id: str | None) -> None:
    if not profile_id:
        return
    profile = load_profile(ctx, profile_id)
    result = sync_profile_standards(ctx, profile, project_root)
    _print_enable_standards_sync(result)


def _repair_enable_planning_bundles(ctx: AppContext, project_root: Path, *, full: bool) -> None:
    if not full:
        return

    from agents_memory.services.planning import repair_plan_bundles

    result = repair_plan_bundles(ctx, project_root)
    if result.repaired_files:
        print(f"- planning bundles: repaired ({len(result.repaired_files)} files)")
        return
    print("- planning bundles: ready")


def _write_enable_refactor_followup(
    ctx: AppContext,
    project_root: Path,
    *,
    refactor_result: RefactorBundleResult,
    load_state_fn: LoadStateFn,
    merge_refactor_state_fn: MergeRefactorStateFn,
    write_state_fn: WriteStateFn,
) -> None:
    existing_state = load_state_fn(project_root)
    hotspot_payload = {
        "identifier": refactor_result.hotspot.identifier,
        "rank_token": refactor_result.hotspot_token,
        "relative_path": refactor_result.hotspot.relative_path,
        "function_name": refactor_result.hotspot.function_name,
        "qualified_name": refactor_result.hotspot.qualified_name,
        "line": refactor_result.hotspot.line,
        "status": refactor_result.hotspot.status,
        "effective_lines": refactor_result.hotspot.effective_lines,
        "branches": refactor_result.hotspot.branches,
        "nesting": refactor_result.hotspot.nesting,
        "local_vars": refactor_result.hotspot.local_vars,
        "has_guiding_comment": refactor_result.hotspot.has_guiding_comment,
        "issues": refactor_result.hotspot.issues,
        "score": refactor_result.hotspot.score,
    }
    updated_state = merge_refactor_state_fn(
        existing_state,
        project_root=project_root,
        plan_root=refactor_result.plan_root,
        hotspot_index=refactor_result.hotspot_index,
        hotspot_token=refactor_result.hotspot_token,
        hotspot=hotspot_payload,
        task_name=refactor_result.task_name,
        task_slug=refactor_result.task_slug,
    )
    write_state_fn(ctx, project_root, updated_state)


def _run_enable_full_followup(
    ctx: AppContext,
    project_root: Path,
    *,
    load_state_fn: LoadStateFn,
    merge_refactor_state_fn: MergeRefactorStateFn,
    write_state_fn: WriteStateFn,
) -> None:
    hotspots = collect_refactor_watch_hotspots(project_root)
    if not hotspots:
        print("- refactor bundle: skipped (no hotspots)")
        return

    from agents_memory.services.planning import init_refactor_bundle

    refactor_result = init_refactor_bundle(ctx, project_root, hotspot_token=hotspots[0].rank_token)
    _write_enable_refactor_followup(
        ctx,
        project_root,
        refactor_result=refactor_result,
        load_state_fn=load_state_fn,
        merge_refactor_state_fn=merge_refactor_state_fn,
        write_state_fn=write_state_fn,
    )
    print(f"- refactor bundle: {refactor_result.plan_root.relative_to(project_root).as_posix()} ({refactor_result.hotspot_token})")


def _print_enable_next_steps(*, full: bool) -> None:
    print("\nNext:")
    print("- Review onboarding-state.json and docs/plans/bootstrap-checklist.md")
    print("- Run amem doctor . after your next structural change")
    if full:
        print("- If a refactor bundle was generated, review its spec.md before editing code")


def _run_enable_core_steps(
    ctx: AppContext,
    project_root: Path,
    *,
    project_id: str,
    full: bool,
    doctor_command_fn: DoctorCommandFn,
) -> None:
    # Execute registration, bridge, MCP, profile, planning repair, and doctor.
    cmd_bridge_install(ctx, project_id)
    mcp_changed = write_vscode_mcp_json(ctx, project_root)
    print(f"- mcp config: {'updated' if mcp_changed else 'ready'}")
    profile_id = _apply_enable_profile(ctx, project_root, full=full)
    _sync_enable_profile_standards(ctx, project_root, profile_id)
    _repair_enable_planning_bundles(ctx, project_root, full=full)
    if full:
        print("- copilot activation: applying")
        cmd_copilot_setup(ctx, str(project_root))
    doctor_command_fn(ctx, str(project_root))


def cmd_enable(
    ctx: AppContext,
    project_id_or_path: str = ".",
    *,
    full: bool = False,
    dry_run: bool = False,
    json_output: bool = False,
    ingest_wiki: bool = False,
    wiki_limit: int | None = None,
    doctor_report_fn: DoctorReportFn,
    doctor_command_fn: DoctorCommandFn,
    load_state_fn: LoadStateFn,
    merge_refactor_state_fn: MergeRefactorStateFn,
    write_state_fn: WriteStateFn,
) -> int:
    # Unified enable workflow: register → bridge → mcp → profile → doctor → bundle → optional wiki ingest.
    project_root = Path(project_id_or_path).expanduser().resolve()
    ctx.logger.info(
        "enable_start | target=%s | full=%s | dry_run=%s | json_output=%s | ingest_wiki=%s | wiki_limit=%s",
        project_root,
        full,
        dry_run,
        json_output,
        ingest_wiki,
        wiki_limit,
    )
    validation_error = _validate_enable_request(project_root, dry_run=dry_run, json_output=json_output)
    if validation_error is not None:
        return validation_error
    if not json_output:
        _print_enable_header(project_root, full=full, dry_run=dry_run)

    project_id = resolve_project_target(ctx, str(project_root))[0]
    if dry_run:
        return _run_enable_dry_run(
            ctx,
            project_root,
            project_id=project_id,
            full=full,
            ingest_wiki=ingest_wiki,
            wiki_limit=wiki_limit,
            json_output=json_output,
            doctor_report_fn=doctor_report_fn,
        )

    project_id, registered_now = _ensure_registered_project(ctx, project_root)
    print(f"- registry: {'created' if registered_now else 'ready'} ({project_id})")

    project_id = resolve_project_target(ctx, project_id)[0]
    _run_enable_core_steps(ctx, project_root, project_id=project_id, full=full, doctor_command_fn=doctor_command_fn)

    from agents_memory.services.planning import init_onboarding_bundle
    onboarding_result = init_onboarding_bundle(ctx, project_root)
    print(f"- onboarding bundle: {onboarding_result.plan_root.relative_to(project_root).as_posix()}")

    if full:
        _run_enable_full_followup(
            ctx, project_root,
            load_state_fn=load_state_fn,
            merge_refactor_state_fn=merge_refactor_state_fn,
            write_state_fn=write_state_fn,
        )

    if ingest_wiki:
        wiki_result = ingest_project_wiki_sources(ctx, project_root, project_id=project_id, max_files=wiki_limit)
        _print_enable_wiki_ingest(wiki_result)

    _print_enable_next_steps(full=full)
    ctx.logger.info(
        "enable_complete | target=%s | full=%s | dry_run=%s | project_id=%s | ingest_wiki=%s | wiki_limit=%s",
        project_root,
        full,
        dry_run,
        project_id,
        ingest_wiki,
        wiki_limit,
    )
    return 0