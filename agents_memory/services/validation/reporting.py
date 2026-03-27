from __future__ import annotations

import json
from dataclasses import asdict

from .models import ValidationFinding


def findings_overall(findings: list[ValidationFinding]) -> str:
    if any(f.status == "FAIL" for f in findings):
        return "FAIL"
    if any(f.status == "WARN" for f in findings):
        return "PARTIAL"
    return "OK"


def emit_findings_report(
    *,
    title: str,
    heading_fields: list[tuple[str, str]],
    findings: list[ValidationFinding],
    output_format: str,
    json_payload: dict[str, object],
) -> None:
    if output_format == "json":
        print(json.dumps(json_payload, ensure_ascii=False, indent=2))
        return

    print(f"\n=== {title} ===")
    for label, value in heading_fields:
        print(f"{label:<8} {value}")
    print()
    for finding in findings:
        print(f"[{finding.status:<4}] {finding.key:<28} {finding.detail}")


def findings_json(findings: list[ValidationFinding]) -> list[dict[str, object]]:
    return [asdict(finding) for finding in findings]