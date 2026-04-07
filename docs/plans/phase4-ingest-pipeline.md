---
title: "Phase 4: Structured Ingest Pipeline"
status: "completed"
created: 2026-03-28
updated: 2026-03-28
type: plan
---

# Phase 4: Structured Ingest Pipeline

## Motivation

The current system only reads error records manually created via `amem new`.
There is no path for ingesting existing documents (PR descriptions, meeting notes,
architecture decisions, code review comments) into the structured memory.

This phase adds a `amem ingest` pipeline that reads a source document, calls an LLM
to extract structured insights, and automatically updates wiki pages + ingest log.

## Design

```
Source Document (PR / meeting / decision / code-review)
    │
    ▼
  _call_llm (provider-agnostic: anthropic | openai | ollama)
    │
    ▼
  JSON extraction:
    ├── summary       → IngestResult.summary
    ├── topics        → matched against existing wiki topics
    ├── timeline_entry → appended to wiki pages (newest-first)
    └── compiled_truth_update → optional wiki page update
    │
    ├─── wiki/<topic>.md — append_timeline_entry
    ├─── wiki/<topic>.md — update_compiled_truth (first topic, if provided)
    └─── memory/ingest_log.jsonl — append log entry
```

## Ingest Types

| Type         | Use Case                                |
|--------------|------------------------------------------|
| `pr-review`  | Pull request description / review       |
| `meeting`    | Meeting notes or standup summary        |
| `decision`   | Architecture decision record (ADR)      |
| `code-review`| Code review feedback                    |

## Ingest Log Format

JSONL file at `memory/ingest_log.jsonl`. Each line is a JSON object:

```json
{
  "timestamp": "2026-03-28T09:15:00Z",
  "ingest_type": "pr-review",
  "source_path": "/path/to/pr.md",
  "project": "myproject",
  "summary": "修复了认证失败问题...",
  "topics": ["auth", "backend"],
  "provider": "anthropic",
  "model": "claude-sonnet-4-5"
}
```

## CLI Commands

```bash
amem ingest <file> --type pr-review [--project myproj] [--dry-run]
amem ingest <file> --type meeting
amem ingest <file> --type decision [--provider ollama] [--model qwen2.5:7b]
amem ingest dummy --log           # Show last 20 ingest log entries
```

## MCP Tool

```python
memory_ingest(content, source_type, source_ref="", project="", dry_run=False)
```

## Files Changed

- `agents_memory/services/ingest.py` — NEW: ingest pipeline
- `agents_memory/commands/ingest.py` — NEW: command registration
- `agents_memory/app.py` — registered ingest command
- `agents_memory/mcp_app.py` — added `memory_ingest` MCP tool
- `tests/test_ingest_service.py` — NEW: 33 tests covering all paths

## Bug Fixed

**BUG-002**: `list_wiki_topics(ctx)` was called with `AppContext` instead of `ctx.wiki_dir`.
Fixed: `list_wiki_topics(ctx.wiki_dir)`, `append_timeline_entry(ctx.wiki_dir, ...)`,
`update_compiled_truth(ctx.wiki_dir, ...)`.
See: `docs/bugfix/BUG-002.md`

## Status

✅ Implemented and tested. 276/276 tests green.
