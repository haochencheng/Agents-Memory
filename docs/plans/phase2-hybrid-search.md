---
title: "Phase 2: Hybrid FTS + Vector Search"
status: "completed"
created: 2026-03-28
updated: 2026-03-28
type: plan
---

# Phase 2: Hybrid FTS + Vector Search

## Motivation

The existing search (`cmd_search`) is a simple `grep`-based O(n) scan with no ranking.
The existing vector search (`cmd_vsearch`) requires an active LanceDB index (often cold on first use).
Neither supports a unified, ranked view combining keyword recall with semantic relevance.

This phase implements hybrid search inspired by Karpathy's LLM Wiki query pattern and GBrain's
ranked search approach.

## Design

```
Query
  │
  ├─── SQLite FTS5 (BM25) ─── normalize [0,1] ─── weight × 0.4
  │
  └─── LanceDB cosine sim ─── [0,1] ────────────── weight × 0.6
            │
            └── if unavailable, use FTS weight = 1.0
                                                      │
                                              recent boost +0.1
                                              (created < 30d)
                                                      │
                                              sort by combined_score
                                                      │
                                               top-N results
```

## Hybrid Score Formula

```
combined_score = fts_score * 0.4 + vector_score * 0.6 + recent_boost(0.1)
```

## FTS Implementation

- **Backend**: Python stdlib `sqlite3` with FTS5 virtual table
- **Storage**: `vectors/fts.db` (zero extra dependencies)
- **Tokenizer**: `unicode61` (handles CJK tokenization)
- **Index**: automatic rebuild when file count mismatch detected
- **Schema**: full-text over `id, project, category, domain, content`

## CLI Commands

```bash
amem fts-index [--force]               # Build / rebuild FTS5 index
amem hybrid-search <query>             # Hybrid search (FTS + vector)
  [--limit 10]                         # Result count
  [--fts-only]                         # Skip vector layer
  [--json]                             # Machine-readable output
```

## MCP Tool

```python
memory_search(query, limit=10, mode="hybrid")
# mode: "hybrid" | "fts" | "vector"
```

## Files Changed

- `agents_memory/services/search.py` — NEW: FTS index + hybrid search engine
- `agents_memory/commands/search.py` — NEW: command registration
- `agents_memory/app.py` — registered search commands
- `agents_memory/mcp_app.py` — added `memory_search` MCP tool
- `tests/test_search_service.py` — NEW: 32 tests covering all paths

## Status

✅ Implemented and tested. 276/276 tests green.
