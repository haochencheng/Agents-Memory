from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext


PROFILE_INSTALL_ROOT = Path(".github/instructions/agents-memory")
PROFILE_MANIFEST_REL = PROFILE_INSTALL_ROOT / "profile-manifest.json"


@dataclass(frozen=True)
class ProfileSpec:
    id: str
    display_name: str
    applies_to: list[str]
    standards: list[str]
    templates: list[str]
    commands: dict[str, str]
    bootstrap_create: list[str]
    source_path: Path


@dataclass(frozen=True)
class ProfileApplyResult:
    profile_id: str
    target_root: Path
    created_dirs: list[str]
    installed_standards: list[str]
    wrote_templates: list[str]
    skipped_paths: list[str]
    dry_run: bool


@dataclass(frozen=True)
class ProfileStandardsSyncResult:
    profile_id: str
    target_root: Path
    synced_standards: list[str]
    unchanged_standards: list[str]
    missing_sources: list[str]
    manifest_updated: bool
    dry_run: bool


def _profiles_dir(ctx: AppContext) -> Path:
    return ctx.base_dir / "profiles"


def _profile_path(ctx: AppContext, profile_id: str) -> Path:
    return _profiles_dir(ctx) / f"{profile_id}.yaml"


def _load_profile_data(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def load_profile(ctx: AppContext, profile_id: str) -> ProfileSpec:
    path = _profile_path(ctx, profile_id)
    if not path.exists():
        raise FileNotFoundError(f"profile not found: {profile_id}")

    data = _load_profile_data(path)
    commands = data.get("commands", {})
    bootstrap = data.get("bootstrap", {})
    if not isinstance(commands, dict):
        raise ValueError(f"invalid commands map in profile: {profile_id}")
    if not isinstance(bootstrap, dict):
        raise ValueError(f"invalid bootstrap map in profile: {profile_id}")

    return ProfileSpec(
        id=str(data.get("id", profile_id)),
        display_name=str(data.get("display_name", profile_id)),
        applies_to=_to_string_list(data.get("applies_to", [])),
        standards=_to_string_list(data.get("standards", [])),
        templates=_to_string_list(data.get("templates", [])),
        commands={str(key): str(value) for key, value in commands.items()},
        bootstrap_create=_to_string_list(bootstrap.get("create", [])),
        source_path=path,
    )


def list_profiles(ctx: AppContext) -> list[ProfileSpec]:
    profiles_dir = _profiles_dir(ctx)
    if not profiles_dir.exists():
        return []
    return sorted((load_profile(ctx, path.stem) for path in profiles_dir.glob("*.yaml")), key=lambda item: item.id)


def _copy_text_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _template_destination(template_rel: str) -> Path:
    path = Path(template_rel)
    parts = path.parts
    relative_parts = parts
    if len(parts) >= 3 and parts[0] == "templates" and parts[1] == "profile":
        relative_parts = parts[3:]
    name = relative_parts[-1]
    if ".example" in name:
        name = name.replace(".example", "", 1)
    if len(relative_parts) == 1:
        return Path(name)
    return Path(*relative_parts[:-1]) / name


def resolve_standard_destination(target_root: Path, standard_rel: str) -> Path:
    return target_root / PROFILE_INSTALL_ROOT / standard_rel


def resolve_template_destination(target_root: Path, template_rel: str) -> Path:
    return target_root / _template_destination(template_rel)


def expected_profile_paths(profile: ProfileSpec, target_root: Path) -> dict[str, list[Path]]:
    return {
        "bootstrap_dirs": [target_root / rel_dir for rel_dir in profile.bootstrap_create],
        "standard_files": [resolve_standard_destination(target_root, standard_rel) for standard_rel in profile.standards],
        "template_files": [resolve_template_destination(target_root, template_rel) for template_rel in profile.templates],
    }


def _apply_directory_items(ctx: AppContext, profile_id: str, target_root: Path, rel_paths: list[str], created_dirs: list[str], skipped_paths: list[str], *, dry_run: bool) -> None:
    for rel_dir in rel_paths:
        destination = target_root / rel_dir
        relative = destination.relative_to(target_root).as_posix()
        if destination.exists():
            skipped_paths.append(relative)
            continue
        created_dirs.append(relative)
        if dry_run:
            continue
        destination.mkdir(parents=True, exist_ok=True)
        log_file_update(ctx.logger, action="profile_create_dir", path=destination, detail=f"profile_id={profile_id}")


def _apply_file_items(ctx: AppContext, profile_id: str, target_root: Path, items: list[tuple[Path, Path]], installed_paths: list[str], skipped_paths: list[str], action: str, *, dry_run: bool) -> None:
    for source, destination in items:
        relative = destination.relative_to(target_root).as_posix()
        if destination.exists():
            skipped_paths.append(relative)
            continue
        installed_paths.append(relative)
        if dry_run:
            continue
        _copy_text_file(source, destination)
        log_file_update(ctx.logger, action=action, path=destination, detail=f"profile_id={profile_id}")


def _manifest_payload(profile: ProfileSpec) -> dict:
    return {
        "profile_id": profile.id,
        "display_name": profile.display_name,
        "applies_to": profile.applies_to,
        "standards": profile.standards,
        "templates": profile.templates,
        "commands": profile.commands,
        "bootstrap": {"create": profile.bootstrap_create},
    }


def write_profile_manifest(ctx: AppContext, target_root: Path, profile: ProfileSpec) -> Path:
    manifest_path = target_root / PROFILE_MANIFEST_REL
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(render_profile_manifest(profile), encoding="utf-8")
    log_file_update(ctx.logger, action="profile_write_manifest", path=manifest_path, detail=f"profile_id={profile.id}")
    return manifest_path


def render_profile_manifest(profile: ProfileSpec) -> str:
    return json.dumps(_manifest_payload(profile), ensure_ascii=False, indent=2) + "\n"


def read_profile_manifest(target_root: Path) -> dict | None:
    manifest_path = target_root / PROFILE_MANIFEST_REL
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def detect_applied_profile(target_root: Path) -> str | None:
    manifest = read_profile_manifest(target_root)
    if not manifest:
        return None
    profile_id = manifest.get("profile_id")
    return str(profile_id) if profile_id else None


def sync_profile_standards(ctx: AppContext, profile: ProfileSpec, target_root: Path, *, dry_run: bool = False) -> ProfileStandardsSyncResult:
    synced_standards: list[str] = []
    unchanged_standards: list[str] = []
    missing_sources: list[str] = []

    for standard_rel in profile.standards:
        source = ctx.base_dir / standard_rel
        destination = resolve_standard_destination(target_root, standard_rel)
        relative = destination.relative_to(target_root).as_posix()
        if not source.exists():
            missing_sources.append(standard_rel)
            continue
        source_text = _read_text(source)
        if destination.exists() and _read_text(destination) == source_text:
            unchanged_standards.append(relative)
            continue
        synced_standards.append(relative)
        if dry_run:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source_text, encoding="utf-8")
        log_file_update(ctx.logger, action="profile_sync_standard", path=destination, detail=f"profile_id={profile.id}")

    manifest_expected = render_profile_manifest(profile)
    manifest_path = target_root / PROFILE_MANIFEST_REL
    manifest_updated = not manifest_path.exists() or _read_text(manifest_path) != manifest_expected
    if manifest_updated and not dry_run:
        write_profile_manifest(ctx, target_root, profile)

    return ProfileStandardsSyncResult(
        profile_id=profile.id,
        target_root=target_root,
        synced_standards=synced_standards,
        unchanged_standards=unchanged_standards,
        missing_sources=missing_sources,
        manifest_updated=manifest_updated,
        dry_run=dry_run,
    )


def apply_profile(ctx: AppContext, profile: ProfileSpec, target_root: Path, *, dry_run: bool = False) -> ProfileApplyResult:
    created_dirs: list[str] = []
    installed_standards: list[str] = []
    wrote_templates: list[str] = []
    skipped_paths: list[str] = []

    _apply_directory_items(ctx, profile.id, target_root, profile.bootstrap_create, created_dirs, skipped_paths, dry_run=dry_run)

    standard_items = [
        (ctx.base_dir / standard_rel, resolve_standard_destination(target_root, standard_rel))
        for standard_rel in profile.standards
    ]
    template_items = [
        (ctx.base_dir / template_rel, resolve_template_destination(target_root, template_rel))
        for template_rel in profile.templates
    ]

    _apply_file_items(ctx, profile.id, target_root, standard_items, installed_standards, skipped_paths, "profile_install_standard", dry_run=dry_run)
    _apply_file_items(ctx, profile.id, target_root, template_items, wrote_templates, skipped_paths, "profile_write_template", dry_run=dry_run)

    if not dry_run:
        write_profile_manifest(ctx, target_root, profile)

    return ProfileApplyResult(
        profile_id=profile.id,
        target_root=target_root,
        created_dirs=created_dirs,
        installed_standards=installed_standards,
        wrote_templates=wrote_templates,
        skipped_paths=skipped_paths,
        dry_run=dry_run,
    )


def _print_profile(profile: ProfileSpec) -> None:
    print(f"Profile: {profile.id}")
    print(f"Name:    {profile.display_name}")
    print(f"Source:  {profile.source_path}")
    print()
    print(f"Applies To: {', '.join(profile.applies_to) if profile.applies_to else '-'}")
    print("Standards:")
    for item in profile.standards:
        print(f"- {item}")
    print("Templates:")
    for item in profile.templates:
        print(f"- {item}")
    print("Commands:")
    for key, value in profile.commands.items():
        print(f"- {key}: {value}")
    print("Bootstrap:")
    for item in profile.bootstrap_create:
        print(f"- {item}")


def _validate_output_format(output_format: str) -> bool:
    if output_format in {"text", "json"}:
        return True
    print(f"Unsupported format: {output_format}")
    return False


def _print_apply_summary(result: ProfileApplyResult, commands: dict[str, str]) -> None:
    heading = "Profile Diff" if result.dry_run else "Applied Profile"
    print(f"\n=== {heading} ===")
    print(f"Profile: {result.profile_id}")
    print(f"Target:  {result.target_root}")
    print(f"DryRun:  {'yes' if result.dry_run else 'no'}\n")
    print(f"- created dirs: {len(result.created_dirs)}")
    print(f"- installed standards: {len(result.installed_standards)}")
    print(f"- wrote templates: {len(result.wrote_templates)}")
    print(f"- skipped existing: {len(result.skipped_paths)}")

    for title, items in (
        ("Created Dirs", result.created_dirs),
        ("Installed Standards", result.installed_standards),
        ("Wrote Templates", result.wrote_templates),
        ("Skipped Existing", result.skipped_paths),
    ):
        if not items:
            continue
        print(f"\n{title}:")
        for item in items:
            print(f"- {item}")

    if result.dry_run:
        return

    print("\nNext:")
    for command in commands.values():
        print(f"- {command}")


def _print_standards_sync_summary(result: ProfileStandardsSyncResult, commands: dict[str, str]) -> None:
    heading = "Standards Sync Preview" if result.dry_run else "Standards Sync"
    print(f"\n=== {heading} ===")
    print(f"Profile: {result.profile_id}")
    print(f"Target:  {result.target_root}")
    print(f"DryRun:  {'yes' if result.dry_run else 'no'}\n")
    print(f"- synced standards: {len(result.synced_standards)}")
    print(f"- unchanged standards: {len(result.unchanged_standards)}")
    print(f"- missing sources: {len(result.missing_sources)}")
    print(f"- manifest updated: {'yes' if result.manifest_updated else 'no'}")

    for title, items in (
        ("Synced Standards", result.synced_standards),
        ("Unchanged Standards", result.unchanged_standards),
        ("Missing Sources", result.missing_sources),
    ):
        if not items:
            continue
        print(f"\n{title}:")
        for item in items:
            print(f"- {item}")

    if result.dry_run:
        return

    print("\nNext:")
    for command in commands.values():
        print(f"- {command}")


def cmd_profile_list(ctx: AppContext, *, output_format: str = "text") -> int:
    if not _validate_output_format(output_format):
        return 1
    profiles = list_profiles(ctx)
    if output_format == "json":
        print(
            json.dumps(
                [
                    {
                        "id": profile.id,
                        "display_name": profile.display_name,
                        "applies_to": profile.applies_to,
                        "source_path": str(profile.source_path),
                    }
                    for profile in profiles
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print("\n=== Profiles ===\n")
    for profile in profiles:
        print(f"- {profile.id:<18} {profile.display_name}  [{', '.join(profile.applies_to)}]")
    return 0


def cmd_profile_show(ctx: AppContext, profile_id: str, *, output_format: str = "text") -> int:
    if not _validate_output_format(output_format):
        return 1
    profile = load_profile(ctx, profile_id)
    if output_format == "json":
        print(
            json.dumps(
                {
                    "id": profile.id,
                    "display_name": profile.display_name,
                    "applies_to": profile.applies_to,
                    "standards": profile.standards,
                    "templates": profile.templates,
                    "commands": profile.commands,
                    "bootstrap": {"create": profile.bootstrap_create},
                    "source_path": str(profile.source_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    _print_profile(profile)
    return 0


def cmd_profile_apply(ctx: AppContext, profile_id: str, project_id_or_path: str = ".", *, dry_run: bool = False) -> int:
    profile = load_profile(ctx, profile_id)
    target_root = Path(project_id_or_path).expanduser().resolve()
    if not target_root.exists():
        print(f"路径不存在: {target_root}")
        return 1
    if not target_root.is_dir():
        print(f"目标不是目录: {target_root}")
        return 1

    ctx.logger.info("profile_apply_start | profile_id=%s | target_root=%s | dry_run=%s", profile.id, target_root, dry_run)
    result = apply_profile(ctx, profile, target_root, dry_run=dry_run)
    _print_apply_summary(result, profile.commands)
    ctx.logger.info(
        "profile_apply_complete | profile_id=%s | target_root=%s | dry_run=%s | dirs=%s | standards=%s | templates=%s | skipped=%s",
        result.profile_id,
        result.target_root,
        result.dry_run,
        len(result.created_dirs),
        len(result.installed_standards),
        len(result.wrote_templates),
        len(result.skipped_paths),
    )
    return 0


def cmd_standards_sync(ctx: AppContext, project_id_or_path: str = ".", *, profile_id: str | None = None, dry_run: bool = False) -> int:
    target_root = Path(project_id_or_path).expanduser().resolve()
    if not target_root.exists():
        print(f"路径不存在: {target_root}")
        return 1
    if not target_root.is_dir():
        print(f"目标不是目录: {target_root}")
        return 1

    resolved_profile_id = profile_id or detect_applied_profile(target_root)
    if not resolved_profile_id:
        print("未检测到已安装 profile。请先运行 profile-apply，或使用 --profile <id> 显式指定。")
        return 1

    profile = load_profile(ctx, resolved_profile_id)
    ctx.logger.info("standards_sync_start | profile_id=%s | target_root=%s | dry_run=%s", profile.id, target_root, dry_run)
    result = sync_profile_standards(ctx, profile, target_root, dry_run=dry_run)
    _print_standards_sync_summary(result, profile.commands)
    ctx.logger.info(
        "standards_sync_complete | profile_id=%s | target_root=%s | dry_run=%s | synced=%s | unchanged=%s | missing=%s | manifest_updated=%s",
        result.profile_id,
        result.target_root,
        result.dry_run,
        len(result.synced_standards),
        len(result.unchanged_standards),
        len(result.missing_sources),
        result.manifest_updated,
    )
    return 1 if result.missing_sources else 0
