"""services/ingest.py — Structured document ingest pipeline for Agents-Memory.

Reads a source document (PR description, meeting notes, decision log, code review),
calls an LLM to extract structured insights, then:
  - Updates relevant wiki pages (compiled_truth + timeline)
  - Appends a log entry to memory/ingest_log.jsonl

Supported ingest types:
  pr-review     Pull request description / review
  meeting       Meeting notes or standup summary
  decision      Architecture decision record (ADR)
  code-review   Code review feedback

Usage (CLI):
  amem ingest <file> --type pr-review [--project myproj] [--dry-run]
  amem ingest <file> --type meeting [--project myproj]

The ingest_log is append-only JSONL at memory/ingest_log.jsonl.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from agents_memory.runtime import AppContext
from agents_memory.services.wiki import (
    append_timeline_entry,
    list_wiki_topics,
    read_wiki_page,
    update_compiled_truth,
)
from agents_memory.services.wiki_compile import (
    DEFAULT_MODEL_BY_PROVIDER,
    DEFAULT_PROVIDER,
    _call_llm,  # noqa: PLC2701 — private reuse
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INGEST_TYPES = ("pr-review", "meeting", "decision", "code-review")

INGEST_LOG_NAME = "ingest_log.jsonl"

_SYSTEM_PROMPT_TEMPLATE = """\
You are an engineering knowledge assistant for the Agents-Memory system.
You are processing a {ingest_type} document.
Extract structured insights in JSON format.
"""

_USER_PROMPT_TEMPLATE = """\
# Document type: {ingest_type}
# Project: {project}
# Source: {source_path}
# Date: {today}

## Source content

{content}

## Task

Analyse the above {ingest_type} document and return a JSON object with:
{{
  "summary": "<one-paragraph summary in Chinese>",
  "topics": ["<wiki topic 1>", "<wiki topic 2>"],
  "timeline_entry": "<single-line timeline entry in Chinese, max 120 chars>",
  "compiled_truth_update": "<updated compiled-truth markdown for the FIRST topic, optional>"
}}

Rules:
- "topics" must be existing wiki topics from the list below, or leave empty list.
- "timeline_entry" must be concise and actionable.
- "compiled_truth_update" is optional — only provide if meaningful insights found.
- Return ONLY valid JSON. No markdown fences.

Known wiki topics: {known_topics}
"""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class IngestResult:
    ingest_type: str
    source_path: str
    project: str
    summary: str
    topics_updated: list[str] = field(default_factory=list)
    timeline_entries_added: int = 0
    log_entry: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    error: str = ""


# ---------------------------------------------------------------------------
# Core ingest logic
# ---------------------------------------------------------------------------


def build_ingest_prompt(
    ingest_type: str,
    source_path: str,
    content: str,
    project: str,
    known_topics: list[str],
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the ingest LLM call."""
    system = _SYSTEM_PROMPT_TEMPLATE.format(ingest_type=ingest_type)
    user = _USER_PROMPT_TEMPLATE.format(
        ingest_type=ingest_type,
        project=project or "(unspecified)",
        source_path=source_path,
        today=date.today().isoformat(),
        content=content[:6000],  # guard against massive docs
        known_topics=", ".join(known_topics) if known_topics else "(none)",
    )
    return system, user


def _parse_llm_json(raw: str) -> dict[str, Any]:
    """Best-effort JSON extraction from LLM output — strip markdown fences."""
    text = raw.strip()
    # Strip ```json ... ``` fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def ingest_document(
    ctx: AppContext,
    source_path: str,
    ingest_type: str,
    project: str = "",
    provider: str | None = None,
    model: str | None = None,
    dry_run: bool = False,
) -> IngestResult:
    """Ingest a document and update wiki + ingest_log.

    Parameters
    ----------
    ctx:          App context (runtime paths).
    source_path:  Path to the source file.
    ingest_type:  One of INGEST_TYPES.
    project:      Optional project tag.
    provider:     LLM provider (anthropic | openai | ollama).
    model:        LLM model name.
    dry_run:      If True, skip file writes (preview mode).

    Returns
    -------
    IngestResult with populated fields.
    """
    if ingest_type not in INGEST_TYPES:
        raise ValueError(f"Unsupported ingest type '{ingest_type}'. Valid: {INGEST_TYPES}")

    prov = provider or DEFAULT_PROVIDER
    mdl = model or DEFAULT_MODEL_BY_PROVIDER.get(prov, "")

    # Read source content
    try:
        content = Path(source_path).read_text(encoding="utf-8")
    except OSError as exc:
        return IngestResult(
            ingest_type=ingest_type,
            source_path=source_path,
            project=project,
            summary="",
            error=str(exc),
        )

    known_topics = list_wiki_topics(ctx.wiki_dir)
    system_prompt, user_prompt = build_ingest_prompt(
        ingest_type, source_path, content, project, known_topics
    )
    combined_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

    raw_response = _call_llm(combined_prompt, provider=prov, model=mdl)
    parsed = _parse_llm_json(raw_response)

    summary = parsed.get("summary", "")
    topics = [t for t in parsed.get("topics", []) if t in known_topics]
    timeline_entry_text = parsed.get("timeline_entry", "")
    compiled_truth_update = parsed.get("compiled_truth_update", "")

    topics_updated: list[str] = []
    timeline_count = 0

    if not dry_run:
        # Update wiki pages
        for topic in topics:
            if timeline_entry_text:
                timestamp = datetime.now().strftime("%Y-%m-%d")
                entry = f"{timestamp} [{ingest_type}] {timeline_entry_text}"
                append_timeline_entry(ctx.wiki_dir, topic, entry)
                timeline_count += 1

        if topics and compiled_truth_update:
            first_topic = topics[0]
            update_compiled_truth(ctx.wiki_dir, first_topic, compiled_truth_update)
            topics_updated.append(first_topic)

        # Write ingest log
        log_entry = _build_log_entry(
            ingest_type=ingest_type,
            source_path=source_path,
            project=project,
            summary=summary,
            topics=topics,
            provider=prov,
            model=mdl,
        )
        _append_ingest_log(ctx, log_entry)
    else:
        log_entry = _build_log_entry(
            ingest_type=ingest_type,
            source_path=source_path,
            project=project,
            summary=summary,
            topics=topics,
            provider=prov,
            model=mdl,
        )
        log_entry["dry_run"] = True

    return IngestResult(
        ingest_type=ingest_type,
        source_path=source_path,
        project=project,
        summary=summary,
        topics_updated=topics_updated if not dry_run else topics,
        timeline_entries_added=timeline_count,
        log_entry=log_entry,
        dry_run=dry_run,
    )


# ---------------------------------------------------------------------------
# Ingest log helpers
# ---------------------------------------------------------------------------


def _build_log_entry(
    *,
    ingest_type: str,
    source_path: str,
    project: str,
    summary: str,
    topics: list[str],
    provider: str,
    model: str,
) -> dict[str, Any]:
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "ingest_type": ingest_type,
        "source_path": source_path,
        "project": project,
        "summary": summary,
        "topics": topics,
        "provider": provider,
        "model": model,
    }


def _ingest_log_path(ctx: AppContext) -> Path:
    ctx.memory_dir.mkdir(parents=True, exist_ok=True)
    return ctx.memory_dir / INGEST_LOG_NAME


def _append_ingest_log(ctx: AppContext, entry: dict[str, Any]) -> None:
    log_path = _ingest_log_path(ctx)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_ingest_log(ctx: AppContext) -> list[dict[str, Any]]:
    """Read all entries from the ingest log.  Returns [] if log doesn't exist."""
    log_path = _ingest_log_path(ctx)
    if not log_path.exists():
        return []
    entries = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


def cmd_ingest(ctx: AppContext, args: list[str]) -> int:
    """Ingest a document into the memory system.

    Usage: amem ingest <file> --type <type> [--project <id>] [--provider anthropic|openai|ollama]
                              [--model <name>] [--dry-run] [--log]

    Types: pr-review, meeting, decision, code-review
    """
    if not args or args[0].startswith("--"):
        _print_ingest_usage()
        return 1

    source_path = args[0]
    ingest_type = ""
    project = ""
    provider: str | None = None
    model: str | None = None
    dry_run = False
    show_log = False

    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--type" and i + 1 < len(args):
            ingest_type = args[i + 1]
            i += 2
        elif arg == "--project" and i + 1 < len(args):
            project = args[i + 1]
            i += 2
        elif arg == "--provider" and i + 1 < len(args):
            provider = args[i + 1]
            i += 2
        elif arg == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 2
        elif arg == "--dry-run":
            dry_run = True
            i += 1
        elif arg == "--log":
            show_log = True
            i += 1
        else:
            i += 1

    if show_log:
        _cmd_show_log(ctx)
        return 0

    if not ingest_type:
        print("错误: 必须指定 --type 参数")
        _print_ingest_usage()
        return 1

    if ingest_type not in INGEST_TYPES:
        print(f"错误: 不支持的类型 '{ingest_type}'。支持: {', '.join(INGEST_TYPES)}")
        return 1

    try:
        result = ingest_document(
            ctx,
            source_path=source_path,
            ingest_type=ingest_type,
            project=project,
            provider=provider,
            model=model,
            dry_run=dry_run,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 摄取失败: {exc}")
        return 1

    if result.error:
        print(f"❌ 错误: {result.error}")
        return 1

    prefix = "🔍 [DRY-RUN] " if dry_run else "✅ "
    print(f"{prefix}文档摄取完成")
    print(f"   类型: {result.ingest_type}")
    print(f"   来源: {result.source_path}")
    if result.project:
        print(f"   项目: {result.project}")
    print(f"   摘要: {result.summary[:200]}")
    if result.topics_updated:
        print(f"   Wiki: {', '.join(result.topics_updated)} ({result.timeline_entries_added} 条时间线)")
    else:
        print("   Wiki: 未匹配到已有 Topic")
    if not dry_run:
        print(f"   日志: {_ingest_log_path(ctx)}")
    return 0


def _print_ingest_usage() -> None:
    print("用法: amem ingest <file> --type <type> [--project <id>] [--dry-run] [--log]")
    print(f"      type: {', '.join(INGEST_TYPES)}")
    print("      --log: 显示摄取日志")


def _cmd_show_log(ctx: AppContext) -> None:
    entries = read_ingest_log(ctx)
    if not entries:
        print("摄取日志为空。")
        return
    print(f"\n摄取日志 ({len(entries)} 条)\n")
    print(f"{'时间':<22} {'类型':<14} {'项目':<16} 来源")
    print("-" * 80)
    for e in entries[-20:]:  # show last 20
        ts = e.get("timestamp", "")[:19]
        print(
            f"{ts:<22} {e.get('ingest_type',''):<14} "
            f"{e.get('project',''):<16} {e.get('source_path','')}"
        )
