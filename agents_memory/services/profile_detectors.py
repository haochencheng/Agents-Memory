from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Protocol

if TYPE_CHECKING:
    from agents_memory.services.profiles import ProfileDetectorSpec


DetectorMatch = tuple[bool, list[str]]


class DetectorAdapter(Protocol):
    kind: str

    def match(self, project_root: Path, config: dict[str, object]) -> DetectorMatch:
        ...


def _to_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def _match_detector_groups(
    any_of: list[str],
    all_of: list[str],
    none_of: list[str],
    *,
    predicate: Callable[[str], bool],
) -> DetectorMatch:
    matched_any = [item for item in any_of if predicate(item)]
    matched_all = [item for item in all_of if predicate(item)]
    blocked = [item for item in none_of if predicate(item)]
    matched = (not any_of or bool(matched_any)) and len(matched_all) == len(all_of) and not blocked
    matched_items = list(dict.fromkeys([*matched_any, *matched_all]))
    return matched, matched_items


def _detector_group_config(config: dict[str, object]) -> tuple[list[str], list[str], list[str]]:
    return (
        _to_string_list(config.get("any_of", [])),
        _to_string_list(config.get("all_of", [])),
        _to_string_list(config.get("none_of", [])),
    )


def _collect_group_matches(
    config: dict[str, object],
    *,
    predicate: Callable[[str], bool],
) -> DetectorMatch:
    any_of, all_of, none_of = _detector_group_config(config)
    return _match_detector_groups(any_of, all_of, none_of, predicate=predicate)


def _read_detector_file(project_root: Path, config: dict[str, object]) -> tuple[str, Path] | None:
    relative_path = str(config.get("path", "")).strip()
    if not relative_path:
        return None
    file_path = project_root / relative_path
    if not file_path.exists() or not file_path.is_file():
        return None
    return file_path.read_text(encoding="utf-8"), file_path


def _resolve_json_key_path(payload: object, dotted_path: str) -> bool:
    current = payload
    for segment in dotted_path.split("."):
        if isinstance(current, dict):
            if segment not in current:
                return False
            current = current[segment]
            continue
        if isinstance(current, list) and segment.isdigit():
            index = int(segment)
            if index < 0 or index >= len(current):
                return False
            current = current[index]
            continue
        return False
    return True


def _relative_matches(project_root: Path, file_path: Path, matched_items: list[str]) -> list[str]:
    relative = file_path.relative_to(project_root).as_posix()
    return [f"{relative}:{item}" for item in matched_items]


@dataclass(frozen=True)
class PathExistsAdapter:
    kind: str = "path_exists"

    def match(self, project_root: Path, config: dict[str, object]) -> DetectorMatch:
        return _collect_group_matches(config, predicate=lambda item: (project_root / item).exists())


@dataclass(frozen=True)
class FileContainsAdapter:
    kind: str = "file_contains"

    def match(self, project_root: Path, config: dict[str, object]) -> DetectorMatch:
        file_state = _read_detector_file(project_root, config)
        if file_state is None:
            return False, []
        file_text, file_path = file_state
        matched, matched_items = _collect_group_matches(config, predicate=lambda item: item in file_text)
        return matched, _relative_matches(project_root, file_path, matched_items)


@dataclass(frozen=True)
class JsonKeyExistsAdapter:
    kind: str = "json_key_exists"

    def match(self, project_root: Path, config: dict[str, object]) -> DetectorMatch:
        file_state = _read_detector_file(project_root, config)
        if file_state is None:
            return False, []
        file_text, file_path = file_state
        try:
            payload = json.loads(file_text)
        except json.JSONDecodeError:
            return False, []
        matched, matched_items = _collect_group_matches(config, predicate=lambda item: _resolve_json_key_path(payload, item))
        return matched, _relative_matches(project_root, file_path, matched_items)


@dataclass(frozen=True)
class CommandAvailableAdapter:
    kind: str = "command_available"

    def match(self, project_root: Path, config: dict[str, object]) -> DetectorMatch:
        del project_root
        return _collect_group_matches(config, predicate=lambda item: shutil.which(item) is not None)


# Registry is explicit so adding a detector kind means adding one adapter object, not another branch ladder.
DETECTOR_ADAPTERS: dict[str, DetectorAdapter] = {
    adapter.kind: adapter
    for adapter in (
        PathExistsAdapter(),
        FileContainsAdapter(),
        JsonKeyExistsAdapter(),
        CommandAvailableAdapter(),
    )
}


def resolve_detector_adapter(kind: str) -> DetectorAdapter | None:
    return DETECTOR_ADAPTERS.get(kind)


def run_profile_detector(project_root: Path, detector: ProfileDetectorSpec) -> dict[str, object]:
    adapter = resolve_detector_adapter(detector.kind)
    matched, matched_paths = adapter.match(project_root, detector.config) if adapter else (False, [])
    return {
        "id": detector.id,
        "kind": detector.kind,
        "output": detector.output,
        "matched": matched,
        "matched_paths": matched_paths,
        "config": detector.config,
    }


def build_project_facts_payload(
    profile_id: str,
    variables: dict[str, str | None],
    detectors: list[ProfileDetectorSpec],
    target_root: Path,
) -> dict[str, object]:
    detector_results = [run_profile_detector(target_root, detector) for detector in detectors]
    facts = {str(result["output"]): bool(result["matched"]) for result in detector_results}
    return {
        "profile_id": profile_id,
        "variables": variables,
        "facts": facts,
        "detectors": detector_results,
    }


def render_project_facts_json(
    profile_id: str,
    variables: dict[str, str | None],
    detectors: list[ProfileDetectorSpec],
    target_root: Path,
) -> str:
    payload = build_project_facts_payload(profile_id, variables, detectors, target_root)
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"