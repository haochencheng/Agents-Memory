"""services/search.py — Hybrid FTS + vector search for Agents-Memory.

Implements a two-layer search pipeline:
  1. SQLite FTS5 full-text search (zero external deps, stdlib sqlite3)
  2. Vector similarity search (LanceDB, optional)
  3. Hybrid merge with configurable score weights

FTS index is stored in vector_dir/fts.db (a small SQLite file).
It is rebuilt automatically when stale (based on file count mismatch).

Hybrid score formula (aligned with Karpathy query skill):
  combined = fts_rank * 0.4 + vector_similarity * 0.6
  recent_boost (+0.1 if created within 30 days)
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from agents_memory.runtime import AppContext
from agents_memory.services.records import collect_errors, parse_frontmatter, read_body


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FTS_DB_NAME = "fts.db"
FTS_SCORE_WEIGHT = 0.4
VECTOR_SCORE_WEIGHT = 0.6
RECENT_BOOST = 0.1
RECENT_DAYS = 30


# ---------------------------------------------------------------------------
# FTS index management
# ---------------------------------------------------------------------------


def _fts_db_path(ctx: AppContext) -> Path:
    ctx.vector_dir.mkdir(parents=True, exist_ok=True)
    return ctx.vector_dir / FTS_DB_NAME


def _open_fts_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _create_fts_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS docs (
            id      TEXT PRIMARY KEY,
            project TEXT,
            category TEXT,
            domain  TEXT,
            severity TEXT,
            status  TEXT,
            date_str TEXT,
            filepath TEXT,
            content TEXT
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
            id, project, category, domain, content,
            content='docs',
            content_rowid='rowid',
            tokenize='unicode61'
        );
        CREATE TABLE IF NOT EXISTS fts_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()


def _fts_doc_count(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute("SELECT COUNT(*) FROM docs").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def _fts_file_to_row(filepath: Path) -> tuple | None:
    """Parse one error record file into an insertable FTS row tuple, or None to skip."""
    meta = parse_frontmatter(filepath)
    if not meta:
        return None
    body = read_body(filepath)
    content = " ".join([
        meta.get("id", ""), meta.get("category", ""), meta.get("project", ""),
        meta.get("domain", ""), meta.get("severity", ""), body,
    ])
    return (
        meta.get("id", filepath.stem), meta.get("project", ""), meta.get("category", ""),
        meta.get("domain", ""), meta.get("severity", ""), meta.get("status", ""),
        meta.get("date", ""), str(filepath), content,
    )


def _fts_full_rebuild(conn: sqlite3.Connection, all_files: list[Path]) -> int:
    """Wipe and repopulate the FTS index from *all_files*. Returns indexed count."""
    conn.execute("DELETE FROM docs")
    conn.execute("DELETE FROM docs_fts")
    conn.commit()
    rows = [r for f in all_files if (r := _fts_file_to_row(f)) is not None]
    conn.executemany(
        "INSERT OR REPLACE INTO docs (id, project, category, domain, severity, status, date_str, filepath, content) VALUES (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.execute("INSERT INTO docs_fts(docs_fts) VALUES('rebuild')")
    conn.execute("INSERT OR REPLACE INTO fts_meta(key,value) VALUES('built_at', ?)", (date.today().isoformat(),))
    conn.commit()
    return len(rows)


def build_fts_index(ctx: AppContext, force: bool = False) -> int:
    """(Re)build the FTS5 index from all error records.

    Returns the number of documents indexed.
    Skips rebuild if the doc count matches current file count and ``force`` is False.
    """
    db_path = _fts_db_path(ctx)
    all_files = sorted(ctx.errors_dir.glob("*.md"))
    if ctx.archive_dir.exists():
        all_files += sorted(ctx.archive_dir.glob("*.md"))

    conn = _open_fts_db(db_path)
    _create_fts_schema(conn)

    if not force and _fts_doc_count(conn) == len(all_files):
        conn.close()
        return len(all_files)

    count = _fts_full_rebuild(conn, all_files)
    conn.close()
    return count


def search_fts(ctx: AppContext, query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Full-text search over error records using SQLite FTS5.

    Automatically rebuilds the index if stale.
    Returns a list of result dicts with keys: id, project, category, domain,
    severity, status, date_str, filepath, fts_score.
    """
    db_path = _fts_db_path(ctx)
    if not db_path.exists():
        build_fts_index(ctx)

    conn = _open_fts_db(db_path)
    _create_fts_schema(conn)

    # Auto-rebuild when stale
    current_count = len(list(ctx.errors_dir.glob("*.md")))
    if _fts_doc_count(conn) != current_count:
        conn.close()
        build_fts_index(ctx, force=True)
        conn = _open_fts_db(db_path)

    # FTS5 uses negative BM25 scores (lower = better match)
    # Normalize to [0, 1] range
    try:
        rows = conn.execute(
            """
            SELECT d.id, d.project, d.category, d.domain, d.severity,
                   d.status, d.date_str, d.filepath,
                   -bm25(docs_fts) AS raw_score
            FROM docs_fts
            JOIN docs d ON docs_fts.rowid = d.rowid
            WHERE docs_fts MATCH ?
            ORDER BY raw_score DESC
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []

    if not rows:
        conn.close()
        return []

    max_score = max(r["raw_score"] for r in rows) or 1.0
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "project": r["project"],
            "category": r["category"],
            "domain": r["domain"],
            "severity": r["severity"],
            "status": r["status"],
            "date_str": r["date_str"],
            "filepath": r["filepath"],
            "fts_score": r["raw_score"] / max_score,
        })
    conn.close()
    return results


# ---------------------------------------------------------------------------
# Hybrid search
# ---------------------------------------------------------------------------


def _is_recent(date_str: str) -> bool:
    if not date_str:
        return False
    try:
        d = date.fromisoformat(date_str)
        return (date.today() - d).days <= RECENT_DAYS
    except ValueError:
        return False


def _get_vector_scores(ctx: AppContext, query: str, limit: int) -> dict[str, float]:
    """Return {doc_id: similarity_score} from the LanceDB vector index.

    Returns an empty dict when LanceDB is unavailable or not initialised.
    """
    vector_by_id: dict[str, float] = {}
    try:
        import lancedb  # type: ignore[import-untyped]
        from agents_memory.services.records import get_embedding  # noqa: PLC0415
        if not ctx.vector_dir.exists():
            return vector_by_id
        db = lancedb.connect(str(ctx.vector_dir))
        if "errors" not in db.table_names():
            return vector_by_id
        q_vec = get_embedding(query)
        for row in db.open_table("errors").search(q_vec).limit(limit).to_list():
            distance = row.get("_distance", 1.0)
            vector_by_id[row["id"]] = max(0.0, 1.0 - float(distance))
    except Exception:
        pass
    return vector_by_id


def _merge_search_results(
    fts_by_id: dict[str, dict],
    vector_by_id: dict[str, float],
    fts_weight: float,
    vector_weight: float,
) -> list[dict[str, Any]]:
    """Merge FTS and vector result maps into a single scored list."""
    merged: list[dict[str, Any]] = []
    for doc_id in set(fts_by_id) | set(vector_by_id):
        fts_score = fts_by_id.get(doc_id, {}).get("fts_score", 0.0)
        vec_score = vector_by_id.get(doc_id, 0.0)

        if fts_score > 0 and vec_score > 0:
            combined = fts_score * fts_weight + vec_score * vector_weight
        elif fts_score > 0:
            combined = fts_score
        else:
            combined = vec_score

        if doc_id in fts_by_id and _is_recent(fts_by_id[doc_id].get("date_str", "")):
            combined += RECENT_BOOST

        base = fts_by_id.get(doc_id, {})
        merged.append({
            "id": doc_id,
            "project": base.get("project", ""),
            "category": base.get("category", ""),
            "domain": base.get("domain", ""),
            "severity": base.get("severity", ""),
            "status": base.get("status", ""),
            "date_str": base.get("date_str", ""),
            "filepath": base.get("filepath", ""),
            "fts_score": round(fts_score, 4),
            "vector_score": round(vec_score, 4),
            "combined_score": round(combined, 4),
        })
    return merged


def hybrid_search(
    ctx: AppContext,
    query: str,
    limit: int = 10,
    fts_weight: float = FTS_SCORE_WEIGHT,
    vector_weight: float = VECTOR_SCORE_WEIGHT,
) -> list[dict[str, Any]]:
    """Merge FTS and vector search results with weighted scoring.

    Falls back gracefully: if LanceDB is unavailable, returns FTS-only results.
    If FTS index is empty, returns vector-only results.
    """
    fts_results = search_fts(ctx, query, limit=limit * 2)
    fts_by_id: dict[str, dict] = {r["id"]: r for r in fts_results}
    vector_by_id = _get_vector_scores(ctx, query, limit=limit * 2)

    merged = _merge_search_results(fts_by_id, vector_by_id, fts_weight, vector_weight)
    merged.sort(key=lambda x: x["combined_score"], reverse=True)
    return merged[:limit]


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_fts_index(ctx: AppContext, args: list[str]) -> int:
    """Build or rebuild the FTS index.

    Usage: amem fts-index [--force]
    """
    force = "--force" in args
    count = build_fts_index(ctx, force=force)
    print(f"✅ FTS 索引{'重新' if force else ''}构建完成: {count} 条记录")
    return 0


def _parse_search_args(args: list[str]) -> dict:
    """Parse CLI flags for cmd_hybrid_search into a flat dict of options."""
    parsed = {"query": args[0], "limit": 10, "fts_only": False, "output_json": False}
    i = 1
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            try:
                parsed["limit"] = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == "--fts-only":
            parsed["fts_only"] = True
            i += 1
        elif args[i] == "--json":
            parsed["output_json"] = True
            i += 1
        else:
            i += 1
    return parsed


def cmd_hybrid_search(ctx: AppContext, args: list[str]) -> int:
    """Hybrid FTS + vector search.

    Usage: amem hybrid-search <query> [--limit 10] [--fts-only] [--json]

    # Dispatch: parse args → run FTS or hybrid → print table or JSON.
    """
    if not args or args[0].startswith("--"):
        print("用法: amem hybrid-search <query> [--limit 10] [--fts-only] [--json]")
        return 1

    opts = _parse_search_args(args)

    if opts["fts_only"]:
        results = search_fts(ctx, opts["query"], limit=opts["limit"])
    else:
        results = hybrid_search(ctx, opts["query"], limit=opts["limit"])

    if not results:
        print(f"未找到匹配 '{opts['query']}' 的记录。")
        print("提示: 先运行 amem fts-index 构建索引，或 amem embed 构建向量索引。")
        return 0

    if opts["output_json"]:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    mode = "FTS-only" if opts["fts_only"] else "Hybrid FTS+Vector"
    print(f"\n{mode} 搜索结果: '{opts['query']}'  ({len(results)} 条)\n")
    print(f"{'Score':<8} {'ID':<36} {'Project':<20} {'Category':<18} Status")
    print("-" * 96)
    for r in results:
        score = r.get("combined_score", r.get("fts_score", 0.0))
        print(
            f"{score:<8.4f} {r['id']:<36} {r['project']:<20} "
            f"{r['category']:<18} {r['status']}"
        )
    return 0
