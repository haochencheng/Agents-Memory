from __future__ import annotations

from pathlib import Path

from .docs_checks import DOCS_DIR, _parse_doc_metadata, _read_if_exists
from .models import ValidationFinding

PLAN_BUNDLES_DIR = Path(DOCS_DIR) / "plans"
TASK_GRAPH_FILE = "task-graph.md"

PLAN_FILE_REQUIREMENTS = {
    "README.md": ["planning bundle"],
    "spec.md": ["## Acceptance Criteria"],
    "plan.md": ["## Change Set"],
    TASK_GRAPH_FILE: ["## Work Items", "## Exit Criteria"],
    "validation.md": ["## Required Checks"],
}

_BUNDLE_PLACEHOLDER_FRAGMENTS: frozenset[str] = frozenset([
    "任务完成时必须满足哪些条件",
    "写下本任务额外需要跑的命令",
])


def _collect_phrase_coverage_findings(key: str, relative_path: str, text: str, phrases: list[str]) -> ValidationFinding:
    missing = [phrase for phrase in phrases if phrase not in text]
    return ValidationFinding(
        "OK" if not missing else "FAIL",
        key,
        f"{relative_path} covers required phrases" if not missing else f"{relative_path} missing required phrases: {', '.join(missing)}",
    )


def _resolve_plan_bundle_targets(project_root: Path, target_path: Path) -> tuple[Path, list[Path]]:
    resolved = target_path.expanduser().resolve()
    if resolved.is_dir() and resolved.name == "plans" and resolved.parent.name == DOCS_DIR:
        return resolved.parent.parent, sorted(path for path in resolved.iterdir() if path.is_dir())
    if resolved.is_dir() and (resolved / "spec.md").exists() and (resolved / TASK_GRAPH_FILE).exists():
        return resolved.parent.parent.parent, [resolved]
    root = resolved if resolved.is_dir() else project_root
    plans_root = root / PLAN_BUNDLES_DIR
    bundles = sorted(path for path in plans_root.iterdir() if path.is_dir()) if plans_root.exists() else []
    return root, bundles


def _plan_root_finding(plans_root: Path) -> ValidationFinding:
    return ValidationFinding(
        "OK" if plans_root.exists() else "WARN",
        "plan_root",
        f"present: {PLAN_BUNDLES_DIR.as_posix()}" if plans_root.exists() else f"missing planning root: {PLAN_BUNDLES_DIR.as_posix()}",
    )


def _plan_file_presence_finding(bundle_rel: str, filename: str, file_path: Path) -> ValidationFinding:
    return ValidationFinding(
        "OK" if file_path.exists() else "FAIL",
        "plan_files",
        f"present: {bundle_rel}/{filename}" if file_path.exists() else f"missing required file: {bundle_rel}/{filename}",
    )


def _plan_metadata_finding(bundle_rel: str, filename: str, file_path: Path) -> ValidationFinding:
    _, issues = _parse_doc_metadata(_read_if_exists(file_path))
    return ValidationFinding(
        "OK" if not issues else "FAIL",
        "plan_metadata",
        f"{bundle_rel}/{filename} metadata OK" if not issues else f"{bundle_rel}/{filename} -> {'; '.join(issues)}",
    )


def _collect_bundle_plan_findings(bundle: Path, root: Path) -> list[ValidationFinding]:
    bundle_rel = bundle.relative_to(root).as_posix()
    findings = [ValidationFinding("OK", "plan_bundle", f"bundle: {bundle_rel}")]
    for filename, phrases in PLAN_FILE_REQUIREMENTS.items():
        file_path = bundle / filename
        findings.append(_plan_file_presence_finding(bundle_rel, filename, file_path))
        if not file_path.exists():
            continue
        findings.append(_plan_metadata_finding(bundle_rel, filename, file_path))
        findings.append(
            _collect_phrase_coverage_findings(
                "plan_semantics",
                f"{bundle_rel}/{filename}",
                _read_if_exists(file_path),
                phrases,
            )
        )
    return findings


def collect_plan_check_findings(project_root: Path, target_path: str = ".") -> list[ValidationFinding]:
    root, bundles = _resolve_plan_bundle_targets(project_root, Path(target_path))
    plans_root = root / PLAN_BUNDLES_DIR
    findings: list[ValidationFinding] = [_plan_root_finding(plans_root)]
    if not bundles:
        findings.append(ValidationFinding("WARN", "plan_bundles", f"no planning bundles found under {PLAN_BUNDLES_DIR.as_posix()}"))
        return findings

    for bundle in bundles:
        findings.extend(_collect_bundle_plan_findings(bundle, root))
    return findings


def _parse_checkbox_items(text: str, heading: str) -> list[tuple[bool, str]]:
    lines = text.splitlines()
    in_section = False
    results: list[tuple[bool, str]] = []
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            in_section = True
            continue
        if in_section and stripped.startswith("##"):
            break
        if not in_section or not stripped.startswith("- ["):
            continue
        checked = stripped[3:4].lower() == "x"
        item_text = stripped[6:].strip()
        if not any(frag in item_text for frag in _BUNDLE_PLACEHOLDER_FRAGMENTS):
            results.append((checked, item_text))
    return results


def _append_unchecked_findings(findings: list[ValidationFinding], path: Path, section: str, key: str) -> None:
    for checked, text in _parse_checkbox_items(path.read_text(encoding="utf-8"), section):
        if not checked:
            findings.append(ValidationFinding(status="WARN", key=key, detail=text))


def collect_bundle_exit_criteria_findings(plan_root: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    task_graph_path = plan_root / TASK_GRAPH_FILE
    if task_graph_path.exists():
        _append_unchecked_findings(findings, task_graph_path, "## Exit Criteria", "exit_criteria_unchecked")
    validation_path = plan_root / "validation.md"
    if validation_path.exists():
        _append_unchecked_findings(findings, validation_path, "## Task-Specific Checks", "task_check_unchecked")
    if not findings:
        findings.append(ValidationFinding(status="OK", key="bundle_gate", detail="no unresolved exit criteria"))
    return findings