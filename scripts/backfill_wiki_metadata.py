from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents_memory.runtime import build_context
from agents_memory.services.wiki_backfill import backfill_wiki_metadata_and_links


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill wiki metadata and candidate links.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of topics processed")
    parser.add_argument("--project", type=str, default=None, help="Only process one normalized project id")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    ctx = build_context(reference_file=__file__)
    result = backfill_wiki_metadata_and_links(
        ctx,
        dry_run=args.dry_run,
        limit=args.limit,
        project=args.project,
    )
    if args.json:
        print(json.dumps({
            "updated": result.updated,
            "skipped": result.skipped,
            "items": [
                {
                    "topic": item.topic,
                    "project": item.project,
                    "source_path": item.source_path,
                    "doc_type": item.doc_type,
                    "changed_fields": item.changed_fields,
                    "added_links": item.added_links,
                    "updated": item.updated,
                }
                for item in result.items
            ],
        }, ensure_ascii=False, indent=2))
        return 0

    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"[{mode}] updated={result.updated} skipped={result.skipped}")
    for item in result.items:
        if not item.updated:
            continue
        changes = ", ".join(item.changed_fields) if item.changed_fields else "links"
        links = f" | links: {', '.join(item.added_links)}" if item.added_links else ""
        print(f"- {item.topic} | {item.doc_type} | {changes}{links}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
