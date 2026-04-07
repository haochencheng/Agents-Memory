from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .models import DocumentMetadata, DocsTouchResult, ValidationFinding

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
    "enable",
    "bootstrap",
    "mcp-setup",
    "doctor",
    "onboarding-execute",
    "plan-init",
    "start-task",
    "do-next",
    "validate",
    "close-task",
    "onboarding-bundle",
    "refactor-bundle",
    "plan-check",
    "profile-list",
    "profile-show",
    "profile-apply",
    "profile-diff",
    "profile-render",
    "standards-sync",
    "profile-check",
    "docs-check",
    "docs-touch",
    "archive",
    "to-qdrant",
    "update-index",
]

STALE_PHRASES = [
    "未来扩展路径（不需要现在做）",
    "Shared Error Memory Platform",
    "CLI 主入口（所有命令）",
]

AI_OS_LEGACY_SECTION_MARKERS = [
    "### 已有",
    "### 缺失",
    "## 3. 目标能力模型",
    "## 4. 产品核心闭环",
    "## 5. 新的目录设计",
    "## 6. `standards/` 目录设计",
    "## 7. `profiles/` 目录设计",
    "## 8. `amem profile-apply` 命令设计",
    "## 9. `amem docs-check` 命令设计",
    "## 10. 同步机制设计",
    "## 11. Harness Engineering 与 Spec Kit 的纳入方式",
    "## 12. MVP 路线",
    "## 13. 成功标准",
    "## 14. 下一步实现建议",
]

README_FILE = "README.md"
DOCS_DIR = "docs"
GETTING_STARTED_FILE = "guides/getting-started.md"
LLMS_FILE = "llms.txt"
TESTS_DIR = "tests"
LICENSE_FILE = "LICENSE"
CONTRIBUTING_FILE = "CONTRIBUTING.md"
PYPROJECT_FILE = "pyproject.toml"

DOC_METADATA_REQUIRED_FIELDS = ("created_at", "updated_at", "doc_status")
DOC_METADATA_ALLOWED_STATUS = {"draft", "active", "stable", "deprecated", "archived"}
DOC_METADATA_PATTERNS = (
    README_FILE,
    CONTRIBUTING_FILE,
    f"{DOCS_DIR}/**/*.md",
    ".github/instructions/**/*.md",
    "standards/**/*.md",
)
DOC_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DOC_FRONT_MATTER_PATTERN = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)

CONTRACT_REQUIREMENTS = {
    "open_source_readme": {
        "path": Path(README_FILE),
        "phrases": ["安装与启动细节见 docs/guides/getting-started.md", "接入其他项目见 docs/guides/integration.md", "最新架构设计见 docs/product/ai-engineering-operating-system.md"],
    },
    "engineering_brain": {
        "path": Path(DOCS_DIR) / "product" / "ai-engineering-operating-system.md",
        "phrases": ["Shared Engineering Brain", "Memory", "Standards", "Planning", "Validation", "实施状态矩阵"],
    },
    "repo_architecture": {
        "path": Path(DOCS_DIR) / "architecture" / "overview.md",
        "phrases": ["仓库级实现决策与技术取舍", "不重复产品定位", "AI Engineering Operating System", "仓库实现 ADR"],
    },
    "modular_architecture": {
        "path": Path(DOCS_DIR) / "architecture" / "modular.md",
        "phrases": ["代码目录结构与模块分层", "runtime / services / commands / integrations", "为什么这样实现", "代码如何分层与扩展"],
    },
    "integration_flow": {
        "path": Path(DOCS_DIR) / "guides" / "integration.md",
        "phrases": ["目标项目如何接入", "用户执行哪些命令", "如何验证是否生效", "外部项目如何接入与验证"],
    },
    "commands_reference": {
        "path": Path(DOCS_DIR) / "guides" / "commands.md",
        "phrases": ["命令签名与参数形态", "命令参考", "外部项目接入流程", "本仓库本地启动与运维"],
    },
    "local_getting_started": {
        "path": Path(DOCS_DIR) / GETTING_STARTED_FILE,
        "phrases": ["本仓库如何克隆、安装、启动", "目标项目如何接入 Agents-Memory", "本仓库首次安装与启动", "日常运维与故障处理"],
    },
    "ops_runbook": {
        "path": Path(DOCS_DIR) / "ops" / "runbook.md",
        "phrases": ["日常运维命令和例行维护", "日志、索引、Qdrant、备份、排障", "本仓库如何首次安装与启动", "外部项目接入流程"],
    },
    "foundation_hardening": {
        "path": Path(DOCS_DIR) / "ops" / "foundation-hardening.md",
        "phrases": ["Behavior change", "=> code change", "=> docs change", "=> test or validation change"],
    },
}

REQUIRED_TEST_FILES = [
    Path(TESTS_DIR) / "test_runtime_bootstrap.py",
    Path(TESTS_DIR) / "test_projects_service.py",
    Path(TESTS_DIR) / "test_records_service.py",
    Path(TESTS_DIR) / "test_integration_service.py",
    Path(TESTS_DIR) / "test_planning_service.py",
    Path(TESTS_DIR) / "test_docs_check.py",
]

POLICY_REQUIREMENTS = {
    "docs_sync": {
        "path": Path("standards") / "docs" / "docs-sync.instructions.md",
        "phrases": ["docs", "code", "tests", "created_at", "updated_at", "doc_status"],
    },
    "docs_check_rules": {
        "path": Path("standards") / "validation" / "docs-check.rules.md",
        "phrases": [
            "docs entrypoint 完整",
            "文档元数据完整",
            "核心 services 有单元测试",
            "行为变更必须同时看到 code diff、docs diff、test diff 中至少两层联动",
        ],
    },
    "harness_engineering": {
        "path": Path("standards") / "planning" / "harness-engineering.md",
        "phrases": ["docs、code、validation", "plan / task graph / validation route", "文档元数据"],
    },
    "review_checklist": {
        "path": Path("standards") / "planning" / "review-checklist.md",
        "phrases": ["docs / code / tests", "最小验证结果"],
    },
    "spec_kit": {
        "path": Path("standards") / "planning" / "spec-kit.md",
        "phrases": ["spec-first", "验收标准必须可被测试或命令验证"],
    },
    "python_base": {
        "path": Path("standards") / "python" / "base.instructions.md",
        "phrases": ["复杂度", "重构", "40 行", "嵌套深度", "注释"],
    },
}

OPEN_SOURCE_URL_PHRASES = [
    'Repository = "',
    'Documentation = "',
    'Issues = "',
]

OPEN_SOURCE_CI_WORKFLOW_PHRASES = [
    "tests:",
    "docs:",
    "python -m pip install .",
    "python -m py_compile",
    "python -m unittest discover -s tests -p 'test_*.py'",
    "python scripts/memory.py docs-check .",
]

OPEN_SOURCE_RELEASE_CHECKLIST_PHRASES = [
    "更新 CHANGELOG.md",
    ".github/workflows/ci.yml",
    "Git tag",
    "GitHub Release",
]

GITHUB_DIR = Path(".github")
CI_WORKFLOW_PATH = GITHUB_DIR / "workflows" / "ci.yml"
RELEASE_CHECKLIST_PATH = Path(DOCS_DIR) / "ops" / "release-checklist.md"

OPEN_SOURCE_REQUIRED_FILES = [
    Path("CHANGELOG.md"),
    Path(LICENSE_FILE),
    Path(CONTRIBUTING_FILE),
    Path(PYPROJECT_FILE),
    Path("CODE_OF_CONDUCT.md"),
    Path("SECURITY.md"),
    Path("SUPPORT.md"),
    Path("PULL_REQUEST_TEMPLATE.md"),
    RELEASE_CHECKLIST_PATH,
    GITHUB_DIR / "FUNDING.yml",
    CI_WORKFLOW_PATH,
    GITHUB_DIR / "ISSUE_TEMPLATE" / "bug_report.md",
    GITHUB_DIR / "ISSUE_TEMPLATE" / "feature_request.md",
]


def _required_doc_files(project_root: Path) -> list[tuple[str, Path]]:
    return [
        ("readme", project_root / README_FILE),
        ("docs_index", project_root / DOCS_DIR / README_FILE),
        ("getting_started", project_root / DOCS_DIR / GETTING_STARTED_FILE),
        ("llms", project_root / LLMS_FILE),
    ]


def _read_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _iter_governed_doc_files(project_root: Path) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in DOC_METADATA_PATTERNS:
        for path in sorted(project_root.glob(pattern)):
            if not path.is_file() or path.suffix != ".md" or path in seen:
                continue
            seen.add(path)
            files.append(path)
    return files


def _doc_front_matter_body(content: str) -> str | None:
    match = DOC_FRONT_MATTER_PATTERN.match(content)
    if not match:
        return None
    return match.group("body")


def _doc_front_matter_match(content: str) -> re.Match[str] | None:
    return DOC_FRONT_MATTER_PATTERN.match(content)


def _parse_doc_metadata_fields(front_matter_body: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in front_matter_body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _doc_metadata_missing_fields(values: dict[str, str]) -> list[str]:
    missing = [field for field in DOC_METADATA_REQUIRED_FIELDS if not values.get(field)]
    return [f"missing fields: {', '.join(missing)}"] if missing else []


def _doc_metadata_value_issues(created_at: str, updated_at: str, doc_status: str) -> list[str]:
    issues: list[str] = []
    if created_at and not DOC_DATE_PATTERN.match(created_at):
        issues.append("created_at must use YYYY-MM-DD")
    if updated_at and not DOC_DATE_PATTERN.match(updated_at):
        issues.append("updated_at must use YYYY-MM-DD")
    if doc_status and doc_status not in DOC_METADATA_ALLOWED_STATUS:
        issues.append(f"doc_status must be one of: {', '.join(sorted(DOC_METADATA_ALLOWED_STATUS))}")
    if created_at and updated_at and DOC_DATE_PATTERN.match(created_at) and DOC_DATE_PATTERN.match(updated_at) and created_at > updated_at:
        issues.append("updated_at must be >= created_at")
    return issues


def _parse_doc_metadata(content: str) -> tuple[DocumentMetadata | None, list[str]]:
    front_matter_body = _doc_front_matter_body(content)
    if front_matter_body is None:
        return None, ["missing front matter"]

    values = _parse_doc_metadata_fields(front_matter_body)
    issues = _doc_metadata_missing_fields(values)

    created_at = values.get("created_at", "")
    updated_at = values.get("updated_at", "")
    doc_status = values.get("doc_status", "")
    issues.extend(_doc_metadata_value_issues(created_at, updated_at, doc_status))

    if issues:
        return None, issues
    return DocumentMetadata(created_at=created_at, updated_at=updated_at, doc_status=doc_status), []


def _fallback_doc_metadata(content: str, *, updated_at: str) -> DocumentMetadata:
    front_matter_body = _doc_front_matter_body(content)
    values = _parse_doc_metadata_fields(front_matter_body) if front_matter_body is not None else {}
    created_at = values.get("created_at", "")
    if not DOC_DATE_PATTERN.match(created_at):
        created_at = updated_at
    doc_status = values.get("doc_status", "")
    if doc_status not in DOC_METADATA_ALLOWED_STATUS:
        doc_status = "active"
    return DocumentMetadata(created_at=created_at, updated_at=updated_at, doc_status=doc_status)


def _serialize_doc_metadata(metadata: DocumentMetadata) -> str:
    return "\n".join(
        [
            "---",
            f"created_at: {metadata.created_at}",
            f"updated_at: {metadata.updated_at}",
            f"doc_status: {metadata.doc_status}",
            "---",
            "",
        ]
    )


def _doc_body_without_front_matter(content: str) -> str:
    match = _doc_front_matter_match(content)
    if match is None:
        return content.lstrip("\n")
    return content[match.end():]


def _render_doc_with_metadata(content: str, metadata: DocumentMetadata) -> str:
    body = _doc_body_without_front_matter(content)
    return _serialize_doc_metadata(metadata) + body


def _collect_doc_metadata_findings(project_root: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for path in _iter_governed_doc_files(project_root):
        metadata, issues = _parse_doc_metadata(_read_if_exists(path))
        relative = path.relative_to(project_root).as_posix()
        if issues:
            findings.append(ValidationFinding("FAIL", "doc_metadata", f"{relative} -> {'; '.join(issues)}"))
            continue
        assert metadata is not None
        findings.append(
            ValidationFinding(
                "OK",
                "doc_metadata",
                f"{relative} metadata OK (created_at={metadata.created_at}, updated_at={metadata.updated_at}, doc_status={metadata.doc_status})",
            )
        )
    return findings


def _resolve_docs_touch_targets(project_root: Path, target_path: Path) -> list[Path]:
    governed_files = _iter_governed_doc_files(project_root)
    resolved = target_path.expanduser().resolve()
    if resolved.is_file():
        return [resolved] if resolved.suffix == ".md" else []
    if resolved.is_dir():
        governed_targets = [path for path in governed_files if path == resolved or resolved in path.parents]
        if governed_targets:
            return governed_targets
        return sorted(path for path in resolved.rglob("*.md") if path.is_file())
    return governed_files


def _touch_result_path(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path)


def _update_single_doc_file(
    path: Path, touch_date: str, dry_run: bool, project_root: Path
) -> tuple[str, bool]:
    original = path.read_text(encoding="utf-8")
    metadata, _issues = _parse_doc_metadata(original)
    normalized = metadata or _fallback_doc_metadata(original, updated_at=touch_date)
    if normalized.updated_at != touch_date:
        normalized = DocumentMetadata(
            created_at=normalized.created_at,
            updated_at=touch_date,
            doc_status=normalized.doc_status,
        )
    rendered = _render_doc_with_metadata(original, normalized)
    relative = _touch_result_path(path, project_root)
    if rendered == original:
        return relative, False
    if not dry_run:
        path.write_text(rendered, encoding="utf-8")
    return relative, True


def touch_doc_metadata(project_root: Path, target_path: str = ".", *, updated_at: str | None = None, dry_run: bool = False) -> DocsTouchResult:
    touch_date = updated_at or date.today().isoformat()
    targets = _resolve_docs_touch_targets(project_root, Path(target_path))
    updated_files: list[str] = []
    skipped_files: list[str] = []
    for path in targets:
        relative, was_updated = _update_single_doc_file(path, touch_date, dry_run, project_root)
        (updated_files if was_updated else skipped_files).append(relative)
    return DocsTouchResult(
        target=target_path,
        updated_at=touch_date,
        updated_files=updated_files,
        skipped_files=skipped_files,
        dry_run=dry_run,
    )


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
    findings.extend(_collect_ai_os_structure_findings(project_root))
    return findings


def _collect_ai_os_structure_findings(project_root: Path) -> list[ValidationFinding]:
    path = project_root / DOCS_DIR / "product" / "ai-engineering-operating-system.md"
    text = _read_if_exists(path)
    if not text:
        return []

    issues: list[str] = []
    if text.count("# AI Engineering Operating System") != 1:
        issues.append("expected exactly one top-level title '# AI Engineering Operating System'")

    body = _doc_body_without_front_matter(text)
    if body.count("# AI Engineering Operating System") != 1:
        issues.append("found duplicate top-level title in document body")
    if "\n---\ncreated_at:" in body:
        issues.append("found duplicate front matter block in document body")

    legacy_hits = [marker for marker in AI_OS_LEGACY_SECTION_MARKERS if marker in text]
    if legacy_hits:
        issues.append(f"legacy sections present: {', '.join(legacy_hits)}")

    return [
        ValidationFinding(
            "FAIL" if issues else "OK",
            "ai_os_structure",
            "AI OS doc canonical structure OK" if not issues else "; ".join(issues),
        )
    ]


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


def _collect_open_source_findings(project_root: Path) -> list[ValidationFinding]:
    findings = _collect_required_path_findings(
        "open_source_files",
        project_root,
        [project_root / path for path in OPEN_SOURCE_REQUIRED_FILES],
    )
    ci_workflow = project_root / CI_WORKFLOW_PATH
    if ci_workflow.exists():
        findings.append(
            _collect_phrase_coverage_findings(
                "open_source_ci",
                CI_WORKFLOW_PATH.as_posix(),
                _read_if_exists(ci_workflow),
                OPEN_SOURCE_CI_WORKFLOW_PHRASES,
            )
        )
    release_checklist = project_root / RELEASE_CHECKLIST_PATH
    if release_checklist.exists():
        findings.append(
            _collect_phrase_coverage_findings(
                "open_source_release",
                RELEASE_CHECKLIST_PATH.as_posix(),
                _read_if_exists(release_checklist),
                OPEN_SOURCE_RELEASE_CHECKLIST_PHRASES,
            )
        )
    pyproject = project_root / PYPROJECT_FILE
    if not pyproject.exists():
        return findings

    findings.append(
        _collect_phrase_coverage_findings(
            "open_source_metadata",
            PYPROJECT_FILE,
            _read_if_exists(pyproject),
            OPEN_SOURCE_URL_PHRASES,
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
    findings.extend(_collect_doc_metadata_findings(project_root))
    findings.extend(_collect_docs_readme_link_findings(docs_readme))
    findings.extend(_collect_command_coverage_findings(getting_started, llms))
    findings.extend(_collect_contract_findings(project_root))
    findings.extend(_collect_test_findings(project_root))
    findings.extend(_collect_policy_findings(project_root))
    findings.extend(_collect_open_source_findings(project_root))
    findings.extend(_collect_hygiene_findings(project_root, searchable_files))
    return findings