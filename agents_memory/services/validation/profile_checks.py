from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from agents_memory.runtime import AppContext
from agents_memory.services.profiles import (
    PROFILE_MANIFEST_REL,
    PROJECT_FACTS_REL,
    detect_applied_profile,
    expected_profile_paths,
    load_profile,
    profile_agents_router_status,
    read_profile_manifest,
    render_profile_overlay,
    render_project_facts,
    resolve_overlay_destination,
)

from .models import ValidationFinding


def _collect_required_path_findings(key: str, project_root: Path, required_paths: list[Path]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for path in required_paths:
        relative = path.relative_to(project_root).as_posix()
        findings.append(
            ValidationFinding(
                "OK" if path.exists() else "FAIL",
                key,
                f"present: {relative}" if path.exists() else f"missing required file: {relative}",
            )
        )
    return findings


def _check_profile_standards_and_router(
    ctx: AppContext, findings: list[ValidationFinding], resolved_profile_id: str, project_root: Path
) -> None:
    # Load the profile and verify all expected standards, templates, overlays, and agents router.
    try:
        profile = load_profile(ctx, resolved_profile_id)
    except FileNotFoundError:
        findings.append(ValidationFinding("FAIL", "profile_source", f"profile definition not found: {resolved_profile_id}"))
        return
    findings.extend(_profile_required_path_findings(profile, project_root))
    findings.append(_profile_agents_file_finding(ctx, profile, project_root))
    findings.append(_profile_project_facts_finding(profile, project_root))
    findings.extend(_collect_profile_overlay_findings(ctx, profile, project_root))
    findings.append(_profile_commands_finding(profile))


def _profile_required_path_findings(profile, project_root: Path) -> list[ValidationFinding]:
    expected = expected_profile_paths(profile, project_root)
    findings: list[ValidationFinding] = []
    findings.extend(_collect_required_path_findings("profile_bootstrap_dirs", project_root, expected["bootstrap_dirs"]))
    findings.extend(_collect_required_path_findings("profile_standard_files", project_root, expected["standard_files"]))
    findings.extend(_collect_required_path_findings("profile_template_files", project_root, expected["template_files"]))
    return findings


def _profile_agents_file_finding(ctx: AppContext, profile, project_root: Path) -> ValidationFinding:
    agents_ok, agents_detail = profile_agents_router_status(ctx, profile, project_root)
    return ValidationFinding("OK" if agents_ok else "FAIL", "profile_agents_file", agents_detail)


def _profile_project_facts_finding(profile, project_root: Path) -> ValidationFinding:
    facts_path = project_root / PROJECT_FACTS_REL
    if not facts_path.exists():
        return ValidationFinding("FAIL", "profile_project_facts", f"missing project facts: {PROJECT_FACTS_REL.as_posix()}")
    if facts_path.read_text(encoding="utf-8") != render_project_facts(profile, project_root):
        return ValidationFinding("FAIL", "profile_project_facts", f"stale project facts: {PROJECT_FACTS_REL.as_posix()}")
    return ValidationFinding("OK", "profile_project_facts", f"present: {PROJECT_FACTS_REL.as_posix()}")


def _expected_profile_runtime_state(profile, project_root: Path) -> tuple[dict[str, str | None], dict[str, bool], dict[str, dict[str, object]]]:
    rendered_facts = json.loads(render_project_facts(profile, project_root))
    variables = cast(dict[str, str | None], rendered_facts.get("variables", {}))
    facts = cast(dict[str, bool], rendered_facts.get("facts", {}))
    detectors = cast(list[dict[str, object]], rendered_facts.get("detectors", []))
    detector_results = {str(item["id"]): item for item in detectors}
    return variables, facts, detector_results


def _collect_profile_overlay_findings(ctx: AppContext, profile, project_root: Path) -> list[ValidationFinding]:
    if not profile.overlays:
        return [ValidationFinding("OK", "profile_overlay_files", "no overlays declared")]

    findings: list[ValidationFinding] = []
    variables, facts, detector_results = _expected_profile_runtime_state(profile, project_root)
    for overlay in profile.overlays:
        finding = _profile_overlay_finding(
            ctx,
            profile,
            project_root,
            overlay,
            variables=variables,
            facts=facts,
            detector_results=detector_results,
        )
        if finding is not None:
            findings.append(finding)
    return findings


def _profile_overlay_finding(
    ctx: AppContext,
    profile,
    project_root: Path,
    overlay,
    *,
    variables: dict[str, str | None],
    facts: dict[str, bool],
    detector_results: dict[str, dict[str, object]],
) -> ValidationFinding | None:
    destination = resolve_overlay_destination(project_root, overlay.target)
    relative = destination.relative_to(project_root).as_posix()
    is_active = not overlay.detectors or all(bool(detector_results.get(detector_id, {}).get("matched")) for detector_id in overlay.detectors)
    if not is_active:
        if destination.exists():
            return ValidationFinding("FAIL", "profile_overlay_files", f"inactive overlay should be removed: {relative}")
        return None

    expected_overlay = render_profile_overlay(ctx, profile, overlay, variables=variables, facts=facts)
    if not destination.exists():
        return ValidationFinding("FAIL", "profile_overlay_files", f"missing overlay: {relative}")
    if destination.read_text(encoding="utf-8") != expected_overlay:
        return ValidationFinding("FAIL", "profile_overlay_files", f"stale overlay: {relative}")
    return ValidationFinding("OK", "profile_overlay_files", f"present: {relative}")


def _profile_commands_finding(profile) -> ValidationFinding:
    invalid_commands = [command for command in profile.commands.values() if not command.startswith(("amem ", "python3 scripts/memory.py "))]
    return ValidationFinding(
        "OK" if not invalid_commands else "WARN",
        "profile_commands",
        "profile commands use supported CLI forms" if not invalid_commands else f"unsupported profile commands: {', '.join(invalid_commands)}",
    )


def collect_profile_check_findings(ctx: AppContext, project_root: Path, profile_id: str | None = None) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    manifest = read_profile_manifest(project_root)
    resolved_profile_id = profile_id or detect_applied_profile(project_root)

    if manifest is None:
        return [ValidationFinding("FAIL", "profile_manifest", f"missing profile manifest: {PROFILE_MANIFEST_REL.as_posix()}")]
    findings.append(ValidationFinding("OK", "profile_manifest", f"present: {PROFILE_MANIFEST_REL.as_posix()}"))

    if not resolved_profile_id:
        return findings + [ValidationFinding("FAIL", "profile_id", "profile manifest does not declare profile_id")]

    manifest_profile_id = str(manifest.get("profile_id", "")).strip()
    if manifest_profile_id != resolved_profile_id:
        findings.append(
            ValidationFinding(
                "FAIL",
                "profile_id",
                f"manifest profile_id mismatch: expected {resolved_profile_id}, got {manifest_profile_id or 'empty'}",
            )
        )
        return findings

    findings.append(ValidationFinding("OK", "profile_id", f"resolved profile: {resolved_profile_id}"))
    _check_profile_standards_and_router(ctx, findings, resolved_profile_id, project_root)
    return findings