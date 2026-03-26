from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from agents_memory.runtime import AppContext


CORE_DOC_COMMANDS = [
    "new",
    "list",
    "stats",
    "search",
    "embed",
    "vsearch",
    "promote",
    "sync",
    "bridge-install",
    "copilot-setup",
    "agent-list",
    "agent-setup",
    "register",
    "mcp-setup",
    "doctor",
    "profile-list",
    "profile-show",
    "profile-apply",
    "profile-diff",
    "docs-check",
    "archive",
    "to-qdrant",
    "update-index",
]

STALE_PHRASES = [
    "未来扩展路径（不需要现在做）",
    "Shared Error Memory Platform",
    "CLI 主入口（所有命令）",
]

README_FILE = "README.md"
DOCS_DIR = "docs"
GETTING_STARTED_FILE = "getting-started.md"
LLMS_FILE = "llms.txt"
TESTS_DIR = "tests"

CONTRACT_REQUIREMENTS = {
    "engineering_brain": {
        "path": Path(DOCS_DIR) / "ai-engineering-operating-system.md",
        "phrases": ["Shared Engineering Brain", "Memory", "Standards", "Planning", "Validation"],
    },
    "foundation_hardening": {
        "path": Path(DOCS_DIR) / "foundation-hardening.md",
        "phrases": ["Behavior change", "=> code change", "=> docs change", "=> test or validation change"],
    },
}

REQUIRED_TEST_FILES = [
    Path(TESTS_DIR) / "test_runtime_bootstrap.py",
    Path(TESTS_DIR) / "test_projects_service.py",
    Path(TESTS_DIR) / "test_records_service.py",
    Path(TESTS_DIR) / "test_integration_service.py",
    Path(TESTS_DIR) / "test_docs_check.py",
]

POLICY_REQUIREMENTS = {
    "docs_sync": {
        "path": Path("standards") / "docs" / "docs-sync.instructions.md",
        "phrases": ["docs", "code", "tests"],
    },
    "docs_check_rules": {
        "path": Path("standards") / "validation" / "docs-check.rules.md",
        "phrases": [
            "docs entrypoint 完整",
            "核心 services 有单元测试",
            "行为变更必须同时看到 code diff、docs diff、test diff 中至少两层联动",
        ],
    },
    "harness_engineering": {
        "path": Path("standards") / "planning" / "harness-engineering.md",
        "phrases": ["docs、code、validation", "plan / task graph / validation route"],
    },
    "review_checklist": {
        "path": Path("standards") / "planning" / "review-checklist.md",
        "phrases": ["docs / code / tests", "最小验证结果"],
    },
    "spec_kit": {
        "path": Path("standards") / "planning" / "spec-kit.md",
        "phrases": ["spec-first", "验收标准必须可被测试或命令验证"],
    },
}


def _required_doc_files(project_root: Path) -> list[tuple[str, Path]]:
    return [
        ("readme", project_root / README_FILE),
        ("docs_index", project_root / DOCS_DIR / README_FILE),
        ("getting_started", project_root / DOCS_DIR / GETTING_STARTED_FILE),
        ("llms", project_root / LLMS_FILE),
    ]


def _read_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


@dataclass(frozen=True)
class ValidationFinding:
    status: str
    key: str
    detail: str


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


def _collect_phrase_coverage_findings(key: str, relative_path: str, text: str, phrases: list[str]) -> ValidationFinding:
    missing = [phrase for phrase in phrases if phrase not in text]
    return ValidationFinding(
        "OK" if not missing else "FAIL",
        key,
        f"{relative_path} covers required phrases" if not missing else f"{relative_path} missing required phrases: {', '.join(missing)}",
    )


def _extract_local_markdown_links(markdown: str) -> list[str]:
    links: list[str] = []
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown):
        cleaned = target.strip()
        if not cleaned or cleaned.startswith(("http://", "https://", "#", "mailto:")):
            continue
        links.append(cleaned.split("#", 1)[0])
    return links


def _collect_required_file_findings(project_root: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for key, path in _required_doc_files(project_root):
        findings.append(
            ValidationFinding(
                "OK" if path.exists() else "FAIL",
                key,
                str(path) if path.exists() else f"missing required file: {path}",
            )
        )
    return findings


def _collect_docs_readme_link_findings(docs_readme: Path) -> list[ValidationFinding]:
    if not docs_readme.exists():
        return []

    findings: list[ValidationFinding] = []
    docs_readme_text = docs_readme.read_text(encoding="utf-8")
    local_links = _extract_local_markdown_links(docs_readme_text)
    if not local_links:
        findings.append(ValidationFinding("WARN", "docs_readme_links", "docs/README.md has no local doc links"))
        return findings

    for rel_target in local_links:
        target_path = (docs_readme.parent / rel_target).resolve()
        findings.append(
            ValidationFinding(
                "OK" if target_path.exists() else "FAIL",
                "docs_readme_links",
                f"docs index link -> {rel_target}" if target_path.exists() else f"broken docs index link: {rel_target}",
            )
        )
    return findings


def _collect_command_coverage_findings(getting_started: Path, llms: Path) -> list[ValidationFinding]:
    if not getting_started.exists() or not llms.exists():
        return []

    findings: list[ValidationFinding] = []
    llms_text = llms.read_text(encoding="utf-8")
    getting_started_text = getting_started.read_text(encoding="utf-8")
    missing_in_llms = [command for command in CORE_DOC_COMMANDS if f"python3 scripts/memory.py {command}" not in llms_text]
    missing_in_getting_started = [command for command in CORE_DOC_COMMANDS if command not in getting_started_text]
    findings.append(
        ValidationFinding(
            "OK" if not missing_in_llms else "FAIL",
            "llms_command_coverage",
            "all commands documented in llms.txt" if not missing_in_llms else f"missing commands in llms.txt: {', '.join(missing_in_llms)}",
        )
    )
    findings.append(
        ValidationFinding(
            "OK" if not missing_in_getting_started else "FAIL",
            "getting_started_command_coverage",
            "all commands documented in docs/getting-started.md" if not missing_in_getting_started else f"missing commands in docs/getting-started.md: {', '.join(missing_in_getting_started)}",
        )
    )
    return findings


def _collect_hygiene_findings(project_root: Path, paths: list[Path]) -> list[ValidationFinding]:
    absolute_path_hits: list[str] = []
    stale_phrase_hits: list[str] = []
    for path in paths:
        content = path.read_text(encoding="utf-8")
        if "/Users/" in content:
            absolute_path_hits.append(path.relative_to(project_root).as_posix())
        for phrase in STALE_PHRASES:
            if phrase in content:
                stale_phrase_hits.append(f"{path.relative_to(project_root).as_posix()}: {phrase}")

    return [
        ValidationFinding(
            "WARN" if absolute_path_hits else "OK",
            "absolute_paths",
            "no obvious local absolute paths in key docs" if not absolute_path_hits else f"local absolute paths found in: {', '.join(absolute_path_hits)}",
        ),
        ValidationFinding(
            "WARN" if stale_phrase_hits else "OK",
            "stale_phrases",
            "no tracked stale phrases found" if not stale_phrase_hits else "; ".join(stale_phrase_hits),
        ),
    ]


def _collect_contract_findings(project_root: Path) -> list[ValidationFinding]:
    required_paths = [project_root / requirement["path"] for requirement in CONTRACT_REQUIREMENTS.values()]
    findings = _collect_required_path_findings("contract_files", project_root, required_paths)
    if any(finding.status == "FAIL" for finding in findings):
        return findings

    for requirement in CONTRACT_REQUIREMENTS.values():
        path = project_root / requirement["path"]
        findings.append(
            _collect_phrase_coverage_findings(
                "contract_semantics",
                requirement["path"].as_posix(),
                _read_if_exists(path),
                requirement["phrases"],
            )
        )
    return findings


def _collect_test_findings(project_root: Path) -> list[ValidationFinding]:
    tests_dir = project_root / TESTS_DIR
    findings = [
        ValidationFinding(
            "OK" if tests_dir.exists() else "FAIL",
            "test_layout",
            f"present: {TESTS_DIR}" if tests_dir.exists() else f"missing required directory: {TESTS_DIR}",
        )
    ]
    findings.extend(_collect_required_path_findings("test_files", project_root, [project_root / path for path in REQUIRED_TEST_FILES]))

    readme_text = _read_if_exists(project_root / README_FILE)
    getting_started_text = _read_if_exists(project_root / DOCS_DIR / GETTING_STARTED_FILE)
    unittest_phrase = "unittest discover -s tests -p 'test_*.py'"
    documented = unittest_phrase in readme_text or unittest_phrase in getting_started_text
    findings.append(
        ValidationFinding(
            "OK" if documented else "FAIL",
            "test_commands",
            "test command documented in README or docs/getting-started.md"
            if documented
            else "missing unittest validation command in README and docs/getting-started.md",
        )
    )
    return findings


def _collect_policy_findings(project_root: Path) -> list[ValidationFinding]:
    required_paths = [project_root / requirement["path"] for requirement in POLICY_REQUIREMENTS.values()]
    findings = _collect_required_path_findings("policy_files", project_root, required_paths)
    if any(finding.status == "FAIL" for finding in findings):
        return findings

    for requirement in POLICY_REQUIREMENTS.values():
        path = project_root / requirement["path"]
        findings.append(
            _collect_phrase_coverage_findings(
                "policy_semantics",
                requirement["path"].as_posix(),
                _read_if_exists(path),
                requirement["phrases"],
            )
        )
    return findings


def collect_docs_check_findings(project_root: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    docs_readme = project_root / DOCS_DIR / README_FILE
    getting_started = project_root / DOCS_DIR / GETTING_STARTED_FILE
    llms = project_root / LLMS_FILE
    searchable_files = [path for _, path in _required_doc_files(project_root) if path.exists()]

    findings.extend(_collect_required_file_findings(project_root))
    findings.extend(_collect_docs_readme_link_findings(docs_readme))
    findings.extend(_collect_command_coverage_findings(getting_started, llms))
    findings.extend(_collect_contract_findings(project_root))
    findings.extend(_collect_test_findings(project_root))
    findings.extend(_collect_policy_findings(project_root))
    findings.extend(_collect_hygiene_findings(project_root, searchable_files))
    return findings


def cmd_docs_check(ctx: AppContext, project_id_or_path: str = ".", *, strict: bool = False, output_format: str = "text") -> int:
    project_root = Path(project_id_or_path).expanduser().resolve()
    findings = collect_docs_check_findings(project_root)
    has_fail = any(finding.status == "FAIL" for finding in findings)
    has_warn = any(finding.status == "WARN" for finding in findings)
    if has_fail:
        overall = "FAIL"
    elif has_warn:
        overall = "PARTIAL"
    else:
        overall = "OK"
    ctx.logger.info("docs_check | root=%s | overall=%s | strict=%s", project_root, overall, strict)

    if output_format == "json":
        print(
            json.dumps(
                {
                    "project_root": str(project_root),
                    "overall": overall,
                    "strict": strict,
                    "findings": [asdict(finding) for finding in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("\n=== Docs Check ===")
        print(f"Root:    {project_root}")
        print(f"Overall: {overall}\n")
        for finding in findings:
            print(f"[{finding.status:<4}] {finding.key:<28} {finding.detail}")

    should_fail = has_fail or (strict and has_warn)
    return 1 if should_fail else 0