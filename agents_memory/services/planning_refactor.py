from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agents_memory.runtime import AppContext
from agents_memory.services.planning_core import (
    JSON_CODE_FENCE,
    MANAGED_BUNDLE_FILENAMES,
    PLAN_PLAN_FILE,
    README_PLAN_FILE,
    SPEC_PLAN_FILE,
    TASK_GRAPH_PLAN_FILE,
    VALIDATION_PLAN_FILE,
    _planning_templates_dir,
    _render_template,
    init_plan_bundle,
    refresh_managed_bundle_files,
    slugify_task_name,
)
from agents_memory.services.validation import RefactorHotspot, collect_refactor_watch_hotspots, serialize_refactor_hotspot


@dataclass(frozen=True)
class RefactorBundleResult:
    task_name: str
    task_slug: str
    target_root: Path
    plan_root: Path
    hotspot_index: int
    hotspot_token: str
    hotspot: RefactorHotspot
    wrote_files: list[str]
    refreshed_files: list[str]
    skipped_files: list[str]
    dry_run: bool


def _default_refactor_slug(hotspot: RefactorHotspot, task_slug: str | None) -> str:
    base_slug = task_slug or slugify_task_name(f"{hotspot.relative_path}-{hotspot.function_name}")
    return base_slug if base_slug.startswith("refactor-") else f"refactor-{base_slug}"


def _resolve_refactor_hotspot(
    hotspots: list[RefactorHotspot],
    *,
    hotspot_index: int,
    hotspot_token: str | None,
) -> tuple[int, RefactorHotspot]:
    if hotspot_token:
        for resolved_index, candidate in enumerate(hotspots, start=1):
            if candidate.rank_token == hotspot_token:
                return resolved_index, candidate
        raise ValueError(
            f"hotspot token '{hotspot_token}' was not found; run `amem doctor .` or `memory_get_refactor_hotspots()` again"
        )

    if hotspot_index < 1:
        raise ValueError("hotspot index must be >= 1")
    if hotspot_index > len(hotspots):
        raise IndexError(f"hotspot index {hotspot_index} is out of range; found {len(hotspots)} hotspot(s)")
    return hotspot_index, hotspots[hotspot_index - 1]


def _render_refactor_bundle_content(
    source: Path,
    *,
    filename: str,
    task_name: str,
    task_slug: str,
    hotspot: RefactorHotspot,
    hotspot_index: int,
    hotspot_token: str,
) -> str:
    if not source.exists():
        raise FileNotFoundError(f"planning template not found: {source}")
    base = _render_template(source, task_name=task_name, task_slug=task_slug).rstrip()
    hotspot_payload = serialize_refactor_hotspot(hotspot)
    init_command = f"amem refactor-bundle . --token {hotspot_token}"
    appendix_map = {
        README_PLAN_FILE: [
            "## Refactor Hotspot",
            f"- hotspot: `{hotspot.identifier}`",
            f"- hotspot token: `{hotspot_token}`",
            f"- current rank index: `{hotspot_index}`",
            f"- line: `{hotspot.line}`",
            f"- status: `{hotspot.status}`",
            f"- issues: `{', '.join(hotspot.issues)}`",
            f"- bundle entry command: `{init_command}`",
            "- verify with: `amem doctor .`",
        ],
        SPEC_PLAN_FILE: [
            "## Refactor Inputs",
            "",
            JSON_CODE_FENCE,
            json.dumps(hotspot_payload, ensure_ascii=False, indent=2),
            "```",
        ],
        PLAN_PLAN_FILE: [
            "## Refactor Execution",
            f"- Target hotspot: `{hotspot.identifier}`",
            "- Split branches/state transitions before adding new behavior.",
            "- Preserve behavior with focused tests or validation commands before and after extraction.",
            "- Re-run `amem doctor .` after the refactor and confirm the hotspot disappears or shrinks.",
        ],
        TASK_GRAPH_PLAN_FILE: [
            "## Refactor Work Items",
            JSON_CODE_FENCE,
            json.dumps(
                [
                    {"step": 1, "title": "Map decision branches and data mutations", "done_when": "Current control flow is documented in spec.md."},
                    {"step": 2, "title": "Extract or simplify the hotspot", "done_when": "Complexity drivers are reduced without behavior regression."},
                    {"step": 3, "title": "Re-run validation", "done_when": "`amem doctor .` shows a smaller refactor_watch surface."},
                ],
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ],
        VALIDATION_PLAN_FILE: [
            "## Refactor Verification",
            "- primary verification command: `amem doctor .`",
            f"- expected outcome: `{hotspot.identifier}` is no longer the first hotspot, or its issue list is smaller.",
            "",
            "## Hotspot Snapshot",
            JSON_CODE_FENCE,
            json.dumps(hotspot_payload, ensure_ascii=False, indent=2),
            "```",
        ],
    }
    appendix = appendix_map.get(filename, [])
    appendix_text = "\n".join(appendix).rstrip()
    return base + ("\n\n" + appendix_text if appendix_text else "") + "\n"


def _refactor_appendix_heading(filename: str) -> str:
    heading_map = {
        README_PLAN_FILE: "## Refactor Hotspot",
        SPEC_PLAN_FILE: "## Refactor Inputs",
        PLAN_PLAN_FILE: "## Refactor Execution",
        TASK_GRAPH_PLAN_FILE: "## Refactor Work Items",
        VALIDATION_PLAN_FILE: "## Refactor Verification",
    }
    return heading_map[filename]


def init_refactor_bundle(
    ctx: AppContext,
    target_root: Path,
    *,
    hotspot_index: int = 1,
    hotspot_token: str | None = None,
    task_slug: str | None = None,
    dry_run: bool = False,
) -> RefactorBundleResult:
    hotspots = collect_refactor_watch_hotspots(target_root)
    if not hotspots:
        raise FileNotFoundError(f"no refactor hotspots found under: {target_root}")

    hotspot_index, hotspot = _resolve_refactor_hotspot(
        hotspots,
        hotspot_index=hotspot_index,
        hotspot_token=hotspot_token,
    )

    task_name = f"Refactor hotspot: {hotspot.identifier}"
    resolved_slug = _default_refactor_slug(hotspot, task_slug)
    templates_dir = _planning_templates_dir(ctx)
    if not templates_dir.exists():
        raise FileNotFoundError(f"planning templates directory not found: {templates_dir}")

    plan_result = init_plan_bundle(ctx, task_name, target_root, task_slug=resolved_slug, dry_run=dry_run)
    created_now = set(plan_result.wrote_files)
    refreshed_files, skipped_files = refresh_managed_bundle_files(
        ctx,
        target_root=target_root,
        plan_root=plan_result.plan_root,
        filenames=MANAGED_BUNDLE_FILENAMES,
        created_now=created_now,
        dry_run=dry_run,
        render_content=lambda filename: _render_refactor_bundle_content(
            templates_dir / f"{filename.replace('.md', '')}.template.md",
            filename=filename,
            task_name=task_name,
            task_slug=resolved_slug,
            hotspot=hotspot,
            hotspot_index=hotspot_index,
            hotspot_token=hotspot.rank_token,
        ),
        resolve_heading=_refactor_appendix_heading,
        create_action="refactor_bundle_file",
        refresh_action="refactor_bundle_refresh",
        log_detail=f"task_slug={resolved_slug};hotspot={hotspot.identifier}",
    )

    return RefactorBundleResult(
        task_name=task_name,
        task_slug=resolved_slug,
        target_root=target_root,
        plan_root=plan_result.plan_root,
        hotspot_index=hotspot_index,
        hotspot_token=hotspot.rank_token,
        hotspot=hotspot,
        wrote_files=list(plan_result.wrote_files),
        refreshed_files=refreshed_files,
        skipped_files=skipped_files,
        dry_run=dry_run,
    )