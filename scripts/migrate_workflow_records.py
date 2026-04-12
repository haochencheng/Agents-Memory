#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents_memory.runtime import build_context
from agents_memory.services.workflow_records import migrate_legacy_workflow_records


def _parse_args(argv: list[str]) -> tuple[bool, int | None]:
    dry_run = False
    limit: int | None = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--dry-run":
            dry_run = True
            index += 1
            continue
        if token == "--limit" and index + 1 < len(argv):
            try:
                limit = max(1, int(argv[index + 1]))
            except ValueError as exc:
                raise SystemExit(f"Invalid --limit value: {argv[index + 1]}") from exc
            index += 2
            continue
        raise SystemExit("Usage: python3 scripts/migrate_workflow_records.py [--dry-run] [--limit N]")
    return dry_run, limit


def main(argv: list[str] | None = None) -> int:
    dry_run, limit = _parse_args(list(sys.argv[1:] if argv is None else argv))
    ctx = build_context(reference_file=__file__)
    result = migrate_legacy_workflow_records(ctx, dry_run=dry_run, limit=limit)

    mode_label = "DRY-RUN" if dry_run else "APPLY"
    print(f"[{mode_label}] migrated={result.migrated_count} skipped={result.skipped_count}")
    for item in result.migrated:
        print(f"- {Path(item.source_path).name} -> {Path(item.target_path).name} ({item.source_type})")
    for item in result.skipped:
        print(f"! {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
