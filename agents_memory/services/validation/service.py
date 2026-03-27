from __future__ import annotations

from pathlib import Path

from agents_memory.runtime import AppContext
from agents_memory.services.profiles import detect_applied_profile

from .docs_checks import collect_docs_check_findings, touch_doc_metadata
from .plan_checks import collect_plan_check_findings
from .profile_checks import collect_profile_check_findings
from .reporting import emit_findings_report, findings_json, findings_overall

OVERALL_LABEL = "Overall:"
SUPPORTED_OUTPUT_FORMATS = {"text", "json"}


def _validate_output_format(output_format: str) -> bool:
    return output_format in SUPPORTED_OUTPUT_FORMATS


def cmd_plan_check(ctx: AppContext, project_id_or_path: str = ".", *, strict: bool = False, output_format: str = "text") -> int:
    project_root = Path(project_id_or_path).expanduser().resolve()
    findings = collect_plan_check_findings(project_root, project_id_or_path)
    overall = findings_overall(findings)
    ctx.logger.info("plan_check | target=%s | overall=%s | strict=%s", project_id_or_path, overall, strict)

    emit_findings_report(
        title="Plan Check",
        heading_fields=[("Target:", project_id_or_path), (OVERALL_LABEL, overall)],
        findings=findings,
        output_format=output_format,
        json_payload={"target": project_id_or_path, "overall": overall, "strict": strict, "findings": findings_json(findings)},
    )
    return 1 if overall == "FAIL" or (strict and overall == "PARTIAL") else 0


def cmd_docs_check(ctx: AppContext, project_id_or_path: str = ".", *, strict: bool = False, output_format: str = "text") -> int:
    project_root = Path(project_id_or_path).expanduser().resolve()
    findings = collect_docs_check_findings(project_root)
    overall = findings_overall(findings)
    ctx.logger.info("docs_check | root=%s | overall=%s | strict=%s", project_root, overall, strict)

    emit_findings_report(
        title="Docs Check",
        heading_fields=[("Root:", str(project_root)), (OVERALL_LABEL, overall)],
        findings=findings,
        output_format=output_format,
        json_payload={"project_root": str(project_root), "overall": overall, "strict": strict, "findings": findings_json(findings)},
    )
    return 1 if overall == "FAIL" or (strict and overall == "PARTIAL") else 0


def cmd_docs_touch(
    ctx: AppContext,
    project_id_or_path: str = ".",
    *,
    updated_at: str | None = None,
    dry_run: bool = False,
    output_format: str = "text",
) -> int:
    if not _validate_output_format(output_format):
        print(f"Unsupported output format: {output_format}")
        return 1

    project_root = Path(".").expanduser().resolve()
    result = touch_doc_metadata(project_root, project_id_or_path, updated_at=updated_at, dry_run=dry_run)
    ctx.logger.info(
        "docs_touch | root=%s | target=%s | updated_at=%s | dry_run=%s | updated=%s | skipped=%s",
        project_root,
        project_id_or_path,
        result.updated_at,
        dry_run,
        len(result.updated_files),
        len(result.skipped_files),
    )

    if output_format == "json":
        emit_findings_report(
            title="Docs Touch",
            heading_fields=[],
            findings=[],
            output_format=output_format,
            json_payload={
                "target": result.target,
                "updated_at": result.updated_at,
                "updated_files": result.updated_files,
                "skipped_files": result.skipped_files,
                "dry_run": result.dry_run,
            },
        )
        return 0

    print("\n=== Docs Touch ===")
    print(f"Root:      {project_root}")
    print(f"Target:    {project_id_or_path}")
    print(f"UpdatedAt: {result.updated_at}")
    print(f"DryRun:    {str(dry_run).lower()}\n")
    print(f"Updated ({len(result.updated_files)}):")
    for path in result.updated_files:
        print(f"- {path}")
    print(f"Skipped ({len(result.skipped_files)}):")
    for path in result.skipped_files:
        print(f"- {path}")
    return 0


def cmd_profile_check(
    ctx: AppContext,
    project_id_or_path: str = ".",
    *,
    profile_id: str | None = None,
    strict: bool = False,
    output_format: str = "text",
) -> int:
    project_root = Path(project_id_or_path).expanduser().resolve()
    findings = collect_profile_check_findings(ctx, project_root, profile_id=profile_id)
    overall = findings_overall(findings)
    ctx.logger.info("profile_check | root=%s | profile_id=%s | overall=%s | strict=%s", project_root, profile_id, overall, strict)

    emit_findings_report(
        title="Profile Check",
        heading_fields=[("Root:", str(project_root)), ("Profile:", profile_id or detect_applied_profile(project_root) or "-"), (OVERALL_LABEL, overall)],
        findings=findings,
        output_format=output_format,
        json_payload={
            "project_root": str(project_root),
            "profile_id": profile_id,
            "overall": overall,
            "strict": strict,
            "findings": findings_json(findings),
        },
    )
    return 1 if overall == "FAIL" or (strict and overall == "PARTIAL") else 0