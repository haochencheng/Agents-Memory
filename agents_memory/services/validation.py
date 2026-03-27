from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from agents_memory.runtime import AppContext
from agents_memory.services.profiles import PROFILE_MANIFEST_REL, detect_applied_profile, expected_profile_paths, load_profile, profile_agents_router_status, read_profile_manifest


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
    "mcp-setup",
    "doctor",
    "onboarding-execute",
    "plan-init",
    "onboarding-bundle",
    "refactor-bundle",
    "plan-check",
    "profile-list",
    "profile-show",
    "profile-apply",
    "profile-diff",
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
GETTING_STARTED_FILE = "getting-started.md"
LLMS_FILE = "llms.txt"
TESTS_DIR = "tests"
LICENSE_FILE = "LICENSE"
CONTRIBUTING_FILE = "CONTRIBUTING.md"
PYPROJECT_FILE = "pyproject.toml"
PLAN_BUNDLES_DIR = Path(DOCS_DIR) / "plans"

PLAN_FILE_REQUIREMENTS = {
    "README.md": ["planning bundle"],
    "spec.md": ["## Acceptance Criteria"],
    "plan.md": ["## Change Set"],
    "task-graph.md": ["## Work Items", "## Exit Criteria"],
    "validation.md": ["## Required Checks"],
}

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
        "phrases": ["README 是开源仓库首页，不展开完整教程正文", "安装与启动细节见 docs/getting-started.md", "接入其他项目见 docs/integration.md", "最新架构设计见 docs/ai-engineering-operating-system.md"],
    },
    "engineering_brain": {
        "path": Path(DOCS_DIR) / "ai-engineering-operating-system.md",
        "phrases": ["Shared Engineering Brain", "Memory", "Standards", "Planning", "Validation", "实施状态矩阵"],
    },
    "repo_architecture": {
        "path": Path(DOCS_DIR) / "architecture.md",
        "phrases": ["仓库级实现决策与技术取舍", "不重复产品定位", "AI Engineering Operating System", "仓库实现 ADR"],
    },
    "modular_architecture": {
        "path": Path(DOCS_DIR) / "modular-architecture.md",
        "phrases": ["代码目录结构与模块分层", "runtime / services / commands / integrations", "为什么这样实现", "代码如何分层与扩展"],
    },
    "integration_flow": {
        "path": Path(DOCS_DIR) / "integration.md",
        "phrases": ["目标项目如何接入", "用户执行哪些命令", "如何验证是否生效", "外部项目如何接入与验证"],
    },
    "commands_reference": {
        "path": Path(DOCS_DIR) / "commands.md",
        "phrases": ["命令签名与参数形态", "命令参考", "外部项目接入流程", "本仓库本地启动与运维"],
    },
    "local_getting_started": {
        "path": Path(DOCS_DIR) / "getting-started.md",
        "phrases": ["本仓库如何克隆、安装、启动", "目标项目如何接入 Agents-Memory", "本仓库首次安装与启动", "日常运维与故障处理"],
    },
    "ops_runbook": {
        "path": Path(DOCS_DIR) / "ops.md",
        "phrases": ["日常运维命令和例行维护", "日志、索引、Qdrant、备份、排障", "本仓库如何首次安装与启动", "外部项目接入流程"],
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
    "python -m pip install .",
    "python -m py_compile",
    "python -m unittest discover -s tests -p 'test_*.py'",
    "python scripts/memory.py docs-check .",
]

GITHUB_DIR = Path(".github")
CI_WORKFLOW_PATH = GITHUB_DIR / "workflows" / "ci.yml"

OPEN_SOURCE_REQUIRED_FILES = [
    Path(LICENSE_FILE),
    Path(CONTRIBUTING_FILE),
    Path(PYPROJECT_FILE),
    Path("CODE_OF_CONDUCT.md"),
    Path("SECURITY.md"),
    Path("SUPPORT.md"),
    Path("PULL_REQUEST_TEMPLATE.md"),
    GITHUB_DIR / "FUNDING.yml",
    CI_WORKFLOW_PATH,
    GITHUB_DIR / "ISSUE_TEMPLATE" / "bug_report.md",
    GITHUB_DIR / "ISSUE_TEMPLATE" / "feature_request.md",
]

REFACTOR_SKIP_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "logs",
    "vectors",
    "tests",
}
REFACTOR_WARN_LIMITS = {
    "lines": 30,
    "branches": 4,
    "nesting": 3,
    "locals": 6,
}
REFACTOR_FAIL_LIMITS = {
    "lines": 40,
    "branches": 5,
    "nesting": 4,
    "locals": 8,
}
REFACTOR_OUTPUT_LIMIT = 5


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
class DocumentMetadata:
    created_at: str
    updated_at: str
    doc_status: str


@dataclass(frozen=True)
class DocsTouchResult:
    target: str
    updated_at: str
    updated_files: list[str]
    skipped_files: list[str]
    dry_run: bool


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


def touch_doc_metadata(project_root: Path, target_path: str = ".", *, updated_at: str | None = None, dry_run: bool = False) -> DocsTouchResult:
    touch_date = updated_at or date.today().isoformat()
    targets = _resolve_docs_touch_targets(project_root, Path(target_path))
    updated_files: list[str] = []
    skipped_files: list[str] = []
    for path in targets:
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
            skipped_files.append(relative)
            continue
        updated_files.append(relative)
        if not dry_run:
            path.write_text(rendered, encoding="utf-8")
    return DocsTouchResult(
        target=target_path,
        updated_at=touch_date,
        updated_files=updated_files,
        skipped_files=skipped_files,
        dry_run=dry_run,
    )


@dataclass(frozen=True)
class ValidationFinding:
    status: str
    key: str
    detail: str


@dataclass(frozen=True)
class RefactorHotspot:
    status: str
    relative_path: str
    function_name: str
    qualified_name: str
    line: int
    effective_lines: int
    branches: int
    nesting: int
    local_vars: int
    has_guiding_comment: bool
    issues: list[str]
    score: int

    @property
    def identifier(self) -> str:
        return f"{self.relative_path}::{self.qualified_name}"

    @property
    def rank_token(self) -> str:
        digest = hashlib.sha1(self.identifier.encode("utf-8")).hexdigest()[:12]
        return f"hotspot-{digest}"

    @property
    def summary(self) -> str:
        label = "high complexity" if self.status == "WARN" else "approaching refactor threshold"
        return f"{self.identifier} {label} ({', '.join(self.issues)})"


def _should_skip_refactor_watch(path: Path) -> bool:
    return any(part in REFACTOR_SKIP_PARTS for part in path.parts)


def _iter_refactor_watch_files(project_root: Path) -> list[Path]:
    return sorted(
        path
        for path in project_root.rglob("*.py")
        if path.is_file() and not _should_skip_refactor_watch(path.relative_to(project_root))
    )


def _iter_non_nested_nodes(node: ast.AST):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield child


def _count_control_nodes(node: ast.AST) -> int:
    control_types = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.Match)
    count = 0
    for child in _iter_non_nested_nodes(node):
        if isinstance(child, control_types):
            count += 1
        count += _count_control_nodes(child)
    return count


def _max_control_nesting(node: ast.AST) -> int:
    control_types = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.Match)

    def walk(current: ast.AST, depth: int) -> int:
        next_depth = depth + 1 if isinstance(current, control_types) else depth
        max_depth = next_depth
        for child in _iter_non_nested_nodes(current):
            max_depth = max(max_depth, walk(child, next_depth))
        return max_depth

    return max((walk(child, 0) for child in _iter_non_nested_nodes(node)), default=0)


def _collect_local_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in _iter_non_nested_nodes(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            names.add(child.id)
        names.update(_collect_local_names(child))
    return names


def _count_effective_function_lines(source_lines: list[str], node: ast.AST) -> int:
    start = max(getattr(node, "lineno", 1) - 1, 0)
    end = max(getattr(node, "end_lineno", getattr(node, "lineno", 1)), getattr(node, "lineno", 1))
    count = 0
    for line in source_lines[start:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count


def _has_guiding_comment(source_lines: list[str], node: ast.AST) -> bool:
    start = max(getattr(node, "lineno", 1) - 1, 0)
    end = max(getattr(node, "end_lineno", getattr(node, "lineno", 1)), getattr(node, "lineno", 1))
    comment_lines = source_lines[max(start - 1, 0):end]
    for line in comment_lines:
        stripped = line.strip()
        if stripped.startswith("#") and len(stripped.lstrip("# ").strip()) >= 8:
            return True
    return False


def _evaluate_refactor_hits(*, effective_lines: int, branches: int, nesting: int, local_vars: int, has_comment: bool) -> tuple[list[str], list[str]]:
    hard_hits: list[str] = []
    soft_hits: list[str] = []
    metrics = {
        "lines": effective_lines,
        "branches": branches,
        "nesting": nesting,
        "locals": local_vars,
    }
    for key, value in metrics.items():
        fail_limit = REFACTOR_FAIL_LIMITS[key]
        warn_limit = REFACTOR_WARN_LIMITS[key]
        if key == "nesting":
            fail_fragment = f"{key}={value}>={fail_limit}"
        else:
            fail_fragment = f"{key}={value}>{fail_limit}"
        if value > fail_limit or (key == "nesting" and value >= fail_limit):
            hard_hits.append(fail_fragment)
        elif value >= warn_limit:
            soft_hits.append(f"{key}={value}")
    if not has_comment and (hard_hits or len(soft_hits) >= 2):
        soft_hits.append("missing_guiding_comment")
    return hard_hits, soft_hits


def _build_refactor_hotspot(relative: str, source_lines: list[str], node: ast.AST, qualified_name: str) -> RefactorHotspot | None:
    function_name = getattr(node, "name", "<lambda>")
    effective_lines = _count_effective_function_lines(source_lines, node)
    branches = _count_control_nodes(node)
    nesting = _max_control_nesting(node)
    local_vars = len(_collect_local_names(node))
    has_comment = _has_guiding_comment(source_lines, node)
    hard_hits, soft_hits = _evaluate_refactor_hits(
        effective_lines=effective_lines,
        branches=branches,
        nesting=nesting,
        local_vars=local_vars,
        has_comment=has_comment,
    )
    if not hard_hits and len(soft_hits) < 2:
        return None

    score = len(hard_hits) * 10 + len(soft_hits)
    status = "WARN" if hard_hits or len(soft_hits) >= 3 else "INFO"
    return RefactorHotspot(
        status=status,
        relative_path=relative,
        function_name=function_name,
        qualified_name=qualified_name,
        line=max(getattr(node, "lineno", 1), 1),
        effective_lines=effective_lines,
        branches=branches,
        nesting=nesting,
        local_vars=local_vars,
        has_guiding_comment=has_comment,
        issues=hard_hits + soft_hits,
        score=score,
    )


def _iter_refactor_watch_candidates(node: ast.AST, scope: tuple[str, ...] = ()): 
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            yield from _iter_refactor_watch_candidates(child, (*scope, child.name))
            continue
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualified_name = ".".join((*scope, child.name))
            yield child, qualified_name
            yield from _iter_refactor_watch_candidates(child, (*scope, child.name))
            continue
        yield from _iter_refactor_watch_candidates(child, scope)


def serialize_refactor_hotspot(hotspot: RefactorHotspot) -> dict[str, object]:
    return {
        "identifier": hotspot.identifier,
        "rank_token": hotspot.rank_token,
        "relative_path": hotspot.relative_path,
        "function_name": hotspot.function_name,
        "qualified_name": hotspot.qualified_name,
        "line": hotspot.line,
        "status": hotspot.status,
        "effective_lines": hotspot.effective_lines,
        "branches": hotspot.branches,
        "nesting": hotspot.nesting,
        "local_vars": hotspot.local_vars,
        "has_guiding_comment": hotspot.has_guiding_comment,
        "issues": hotspot.issues,
        "score": hotspot.score,
    }


def collect_refactor_watch_hotspots(project_root: Path) -> list[RefactorHotspot]:
    candidates: list[RefactorHotspot] = []

    for path in _iter_refactor_watch_files(project_root):
        relative = path.relative_to(project_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:
            continue

        source_lines = source.splitlines()
        for node, qualified_name in _iter_refactor_watch_candidates(tree):
            hotspot = _build_refactor_hotspot(relative, source_lines, node, qualified_name)
            if hotspot is not None:
                candidates.append(hotspot)

    return sorted(candidates, key=lambda item: (-item.score, item.rank_token))[:REFACTOR_OUTPUT_LIMIT]


def collect_refactor_watch_findings(project_root: Path) -> list[ValidationFinding]:
    # This scan intentionally stays heuristic and cheap: it is meant to surface
    # likely refactor hotspots during onboarding/governance, not replace a full
    # static-analysis pipeline or block normal development on exact metrics.
    findings: list[ValidationFinding] = []
    hotspots = collect_refactor_watch_hotspots(project_root)

    for path in _iter_refactor_watch_files(project_root):
        relative = path.relative_to(project_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source)
        except Exception as exc:
            findings.append(ValidationFinding("WARN", "refactor_watch", f"unable to inspect {relative}: {exc}"))
            continue

    if not hotspots:
        return [ValidationFinding("OK", "refactor_watch", "no Python functions are close to configured refactor thresholds")]

    findings.extend(ValidationFinding(hotspot.status, "refactor_watch", hotspot.summary) for hotspot in hotspots)
    return findings


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
    path = project_root / DOCS_DIR / "ai-engineering-operating-system.md"
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


def _resolve_plan_bundle_targets(project_root: Path, target_path: Path) -> tuple[Path, list[Path]]:
    resolved = target_path.expanduser().resolve()
    if resolved.is_dir() and resolved.name in {"plans"} and resolved.parent.name == DOCS_DIR:
        return resolved.parent.parent, sorted(path for path in resolved.iterdir() if path.is_dir())
    if resolved.is_dir() and (resolved / "spec.md").exists() and (resolved / "task-graph.md").exists():
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
    try:
        profile = load_profile(ctx, resolved_profile_id)
    except FileNotFoundError:
        return findings + [ValidationFinding("FAIL", "profile_source", f"profile definition not found: {resolved_profile_id}")]

    expected = expected_profile_paths(profile, project_root)
    findings.extend(_collect_required_path_findings("profile_bootstrap_dirs", project_root, expected["bootstrap_dirs"]))
    findings.extend(_collect_required_path_findings("profile_standard_files", project_root, expected["standard_files"]))
    findings.extend(_collect_required_path_findings("profile_template_files", project_root, expected["template_files"]))
    agents_ok, agents_detail = profile_agents_router_status(ctx, profile, project_root)
    findings.append(ValidationFinding("OK" if agents_ok else "FAIL", "profile_agents_file", agents_detail))

    invalid_commands = [command for command in profile.commands.values() if not command.startswith(("amem ", "python3 scripts/memory.py "))]
    findings.append(
        ValidationFinding(
            "OK" if not invalid_commands else "WARN",
            "profile_commands",
            "profile commands use supported CLI forms" if not invalid_commands else f"unsupported profile commands: {', '.join(invalid_commands)}",
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


def cmd_plan_check(ctx: AppContext, project_id_or_path: str = ".", *, strict: bool = False, output_format: str = "text") -> int:
    project_root = Path(project_id_or_path).expanduser().resolve()
    findings = collect_plan_check_findings(project_root, project_id_or_path)
    has_fail = any(finding.status == "FAIL" for finding in findings)
    has_warn = any(finding.status == "WARN" for finding in findings)
    if has_fail:
        overall = "FAIL"
    elif has_warn:
        overall = "PARTIAL"
    else:
        overall = "OK"
    ctx.logger.info("plan_check | target=%s | overall=%s | strict=%s", project_id_or_path, overall, strict)

    if output_format == "json":
        print(
            json.dumps(
                {
                    "target": project_id_or_path,
                    "overall": overall,
                    "strict": strict,
                    "findings": [asdict(finding) for finding in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("\n=== Plan Check ===")
        print(f"Target:  {project_id_or_path}")
        print(f"Overall: {overall}\n")
        for finding in findings:
            print(f"[{finding.status:<4}] {finding.key:<28} {finding.detail}")

    return 1 if has_fail or (strict and has_warn) else 0


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


def cmd_docs_touch(ctx: AppContext, project_id_or_path: str = ".", *, updated_at: str | None = None, dry_run: bool = False, output_format: str = "text") -> int:
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
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
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


def cmd_profile_check(ctx: AppContext, project_id_or_path: str = ".", *, profile_id: str | None = None, strict: bool = False, output_format: str = "text") -> int:
    project_root = Path(project_id_or_path).expanduser().resolve()
    findings = collect_profile_check_findings(ctx, project_root, profile_id=profile_id)
    has_fail = any(finding.status == "FAIL" for finding in findings)
    has_warn = any(finding.status == "WARN" for finding in findings)
    if has_fail:
        overall = "FAIL"
    elif has_warn:
        overall = "PARTIAL"
    else:
        overall = "OK"
    ctx.logger.info("profile_check | root=%s | profile_id=%s | overall=%s | strict=%s", project_root, profile_id, overall, strict)

    if output_format == "json":
        print(
            json.dumps(
                {
                    "project_root": str(project_root),
                    "profile_id": profile_id,
                    "overall": overall,
                    "strict": strict,
                    "findings": [asdict(finding) for finding in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("\n=== Profile Check ===")
        print(f"Root:    {project_root}")
        print(f"Profile: {profile_id or detect_applied_profile(project_root) or '-'}")
        print(f"Overall: {overall}\n")
        for finding in findings:
            print(f"[{finding.status:<4}] {finding.key:<28} {finding.detail}")

    return 1 if has_fail or (strict and has_warn) else 0
