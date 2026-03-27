from __future__ import annotations

import ast
from pathlib import Path

from .models import RefactorHotspot, ValidationFinding

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
        fail_fragment = f"{key}={value}>={fail_limit}" if key == "nesting" else f"{key}={value}>{fail_limit}"
        if value > fail_limit or (key == "nesting" and value >= fail_limit):
            hard_hits.append(fail_fragment)
            continue
        if value >= warn_limit:
            soft_hits.append(f"{key}={value}")
    if not has_comment and (hard_hits or len(soft_hits) >= 2):
        soft_hits.append("missing_guiding_comment")
    return hard_hits, soft_hits


def _gather_function_metrics(source_lines: list[str], node: ast.AST) -> tuple[int, int, int, int, bool]:
    effective_lines = _count_effective_function_lines(source_lines, node)
    branches = _count_control_nodes(node)
    nesting = _max_control_nesting(node)
    local_vars = len(_collect_local_names(node))
    has_comment = _has_guiding_comment(source_lines, node)
    return effective_lines, branches, nesting, local_vars, has_comment


def _build_refactor_hotspot(relative: str, source_lines: list[str], node: ast.AST, qualified_name: str) -> RefactorHotspot | None:
    function_name = getattr(node, "name", "<lambda>")
    effective_lines, branches, nesting, local_vars, has_comment = _gather_function_metrics(source_lines, node)
    hard_hits, soft_hits = _evaluate_refactor_hits(
        effective_lines=effective_lines,
        branches=branches,
        nesting=nesting,
        local_vars=local_vars,
        has_comment=has_comment,
    )
    if not hard_hits and len(soft_hits) < 2:
        return None
    return RefactorHotspot(
        status="WARN" if hard_hits or len(soft_hits) >= 3 else "INFO",
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
        score=len(hard_hits) * 10 + len(soft_hits),
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


def _scan_file_for_hotspots(path: Path, project_root: Path) -> list[RefactorHotspot]:
    relative = path.relative_to(project_root).as_posix()
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return []
    source_lines = source.splitlines()
    hotspots: list[RefactorHotspot] = []
    for node, qualified_name in _iter_refactor_watch_candidates(tree):
        hotspot = _build_refactor_hotspot(relative, source_lines, node, qualified_name)
        if hotspot is not None:
            hotspots.append(hotspot)
    return hotspots


def collect_refactor_watch_hotspots(project_root: Path) -> list[RefactorHotspot]:
    candidates: list[RefactorHotspot] = []
    for path in _iter_refactor_watch_files(project_root):
        candidates.extend(_scan_file_for_hotspots(path, project_root))
    return sorted(candidates, key=lambda item: (-item.score, item.rank_token))[:REFACTOR_OUTPUT_LIMIT]


def collect_refactor_watch_findings(project_root: Path) -> list[ValidationFinding]:
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