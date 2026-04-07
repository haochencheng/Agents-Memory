---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# REFACTOR-001 — Remaining `refactor_watch` Hotspots

## Summary

After a systematic refactor pass on 2026-04-07 (15 functions refactored across 5 files),
`amem doctor .` reports `Overall: READY` but flagged 5 residual Optional WARNs.

These represent inherent algorithmic complexity that cannot be reduced by simple extraction —
all are parser state-machines, arg-dispatch loops, or long setup pipelines.

## Affected Functions

| # | File | Function | Issues |
|---|------|----------|--------|
| 1 | `scripts/web-health.py` | `suite_api` | lines=86>40, locals=15>8, branches=5 |
| 2 | `agents_memory/services/wiki_compile.py` | `_parse_compile_args` | branches=6>5, nesting=5>=4, lines=35 |
| 3 | `agents_memory/services/ingest.py` | `ingest_document` | lines=51>40, locals=9>8 |
| 4 | `agents_memory/services/wiki.py` | `_parse_fm_links_block` | branches=7>5, nesting=5>=4 |
| 5 | `agents_memory/services/wiki.py` | `cmd_wiki_backlinks` | branches=8>5, nesting=3, locals=7 |

## Root Cause

- `suite_api`: Integration health check that calls 12 API endpoints sequentially — splitting further
  would require breaking the coherent check flow.
- `_parse_compile_args`: `--flag value` dispatch with 6 argument keys — can only be reduced
  by replacing the while-loop parser with a library (e.g. argparse) which is out of scope.
- `ingest_document`: Pipeline orchestrator (validate → LLM → wiki update → log); locals=9 vs limit=8.
- `_parse_fm_links_block`: YAML state machine with entry/continuation/exit states — three branches
  per state is irreducible.
- `cmd_wiki_backlinks`: Needs a guiding comment; branches come from per-topic loop + backlink logic.

## Status

- `amem doctor .` → `Overall: READY`
- These WARNs are in the `Optional` category and do not block any release
- No functional bugs — all 365 tests pass

## Action Plan

- [ ] Add `# guiding_comment` to `cmd_wiki_backlinks` to resolve the `missing_guiding_comment` flag
- [ ] Consider migrating `_parse_compile_args` to `argparse` in a future CLI refactor
- [ ] `suite_api`: out of scope for now — acceptable for a health-check script
