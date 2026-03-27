from __future__ import annotations

import re
import subprocess
from pathlib import Path

from agents_memory.constants import DEFAULT_BRIDGE_INSTRUCTION_REL, DOMAIN_HINTS
from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext


def _process_header_line(line: str, current: dict, projects: list[dict]) -> dict:
    project_id = re.match(r"^## (.+)", line).group(1).strip()
    if current.get("id"):
        projects.append(current)
    if any(char > "\u4e00" for char in project_id):
        return {}
    return {"id": project_id}


def _apply_field_to_entry(line: str, current: dict) -> None:
    field_match = re.match(r"\s*-\s+\*\*(\w+)\*\*:\s*(.*)", line)
    if field_match:
        current[field_match.group(1).strip()] = field_match.group(2).strip()


def parse_projects(ctx: AppContext) -> list[dict]:
    # Parse project registry markdown into a list of active project dicts.
    if not ctx.projects_file.exists():
        return []
    projects: list[dict] = []
    current: dict = {}
    for line in ctx.projects_file.read_text(encoding="utf-8").splitlines():
        if re.match(r"^## (.+)", line):
            current = _process_header_line(line, current, projects)
        elif current:
            _apply_field_to_entry(line, current)
    if current.get("id"):
        projects.append(current)
    return [p for p in projects if p.get("active", "true").lower() == "true"]


def detect_project_id(root: Path) -> str:
    try:
        url = subprocess.check_output(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        repo_name = re.split(r"[/:]", url.rstrip(".git").rstrip("/"))[-1]
        return repo_name.lower().replace("_", "-")
    except Exception:
        return root.name.lower().replace("_", "-")


def detect_domains(instruction_dir: Path) -> list[str]:
    # Infer a de-duplicated list of domain names from instruction file names.
    if not instruction_dir.exists():
        return ["python", "docs"]
    found: set[str] = set()
    for filepath in instruction_dir.glob("*.instructions.md"):
        name = filepath.name.lower()
        for hint, domain in DOMAIN_HINTS:
            if hint in name:
                found.add(domain)
    return sorted(found) if found else ["python", "docs"]


def detect_instruction_files(instruction_dir: Path, root: Path) -> dict[str, str]:
    # Map domain names to relative instruction file paths found in instruction_dir.
    mapping: dict[str, str] = {}
    if not instruction_dir.exists():
        return mapping
    for filepath in sorted(instruction_dir.glob("*.instructions.md")):
        name = filepath.name.lower()
        for hint, domain in DOMAIN_HINTS:
            if hint in name and domain not in mapping:
                mapping[domain] = str(filepath.relative_to(root))
    return mapping


def project_already_registered(ctx: AppContext, project_id: str) -> bool:
    if not ctx.projects_file.exists():
        return False
    return f"## {project_id}" in ctx.projects_file.read_text(encoding="utf-8")


def _resolve_root_path(root_value: str) -> Path | None:
    try:
        return Path(root_value).expanduser().resolve()
    except Exception:
        return None


def _lookup_project_by_id(projects: list[dict], project_id_or_path: str) -> tuple[str, Path | None, dict] | None:
    project = next((item for item in projects if item.get("id") == project_id_or_path), None)
    if not project:
        return None
    root_value = project.get("root", "").strip()
    if root_value:
        return project["id"], Path(root_value).expanduser().resolve(), project
    return project["id"], None, project


def _lookup_project_by_candidate_path(projects: list[dict], candidate: Path) -> tuple[str, Path, dict] | None:
    # Scan registered projects to find one whose root resolves to the given path.
    for project in projects:
        root_value = project.get("root", "").strip()
        if not root_value:
            continue
        resolved = _resolve_root_path(root_value)
        if resolved == candidate:
            return project.get("id", candidate.name.lower().replace("_", "-")), candidate, project
    return None


def resolve_project_target(ctx: AppContext, project_id_or_path: str = ".") -> tuple[str, Path | None, dict | None]:
    # Route lookup by explicit project ID match, then by filesystem path.
    projects = parse_projects(ctx)
    if project_id_or_path not in ("", "."):
        result = _lookup_project_by_id(projects, project_id_or_path)
        if result is not None:
            return result
    candidate = Path(project_id_or_path).expanduser().resolve()
    if candidate.is_dir():
        result = _lookup_project_by_candidate_path(projects, candidate)
        if result is not None:
            return result
        return candidate.name.lower().replace("_", "-"), candidate, None
    return project_id_or_path, None, None


def project_agents_reference_exists(project_root: Path, bridge_rel: str) -> bool:
    for candidate in (project_root / "AGENTS.md", project_root / "docs" / "AGENTS.md"):
        if candidate.exists() and bridge_rel in candidate.read_text(encoding="utf-8"):
            return True
    return False


def append_project_entry(ctx: AppContext, entry: str) -> None:
    ctx.memory_dir.mkdir(parents=True, exist_ok=True)
    if not ctx.projects_file.exists():
        ctx.projects_file.write_text("# Project Registry\n\n", encoding="utf-8")
    content = ctx.projects_file.read_text(encoding="utf-8")
    marker = "## 注册新项目"
    if marker in content:
        content = content.replace(marker, entry + "\n" + marker, 1)
    else:
        content = content.rstrip() + "\n\n" + entry + "\n"
    ctx.projects_file.write_text(content, encoding="utf-8")
    first_line = entry.splitlines()[0].strip() if entry.strip() else "unknown"
    log_file_update(ctx.logger, action="update_registry", path=ctx.projects_file, detail=first_line)


def resolve_bridge_rel(project: dict | None) -> str:
    if project:
        raw = project.get("bridge_instruction", DEFAULT_BRIDGE_INSTRUCTION_REL).strip()
        normalized = raw.strip('"').strip("'").strip()
        return normalized
    return DEFAULT_BRIDGE_INSTRUCTION_REL
