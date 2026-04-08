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
from datetime import UTC, date, datetime
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


def _apply_wiki_updates(
    ctx: AppContext,
    topics: list[str],
    ingest_type: str,
    timeline_entry_text: str,
    compiled_truth_update: str,
) -> tuple[list[str], int]:
    """Write timeline entries and compiled_truth update; return (topics_updated, timeline_count)."""
    timeline_count = 0
    for topic in topics:
        if timeline_entry_text:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            entry = f"{timestamp} [{ingest_type}] {timeline_entry_text}"
            append_timeline_entry(ctx.wiki_dir, topic, entry)
            timeline_count += 1
    topics_updated: list[str] = []
    if topics and compiled_truth_update:
        update_compiled_truth(ctx.wiki_dir, topics[0], compiled_truth_update)
        topics_updated.append(topics[0])
    return topics_updated, timeline_count


def _run_ingest_llm(
    source_path: str,
    ingest_type: str,
    project: str,
    prov: str,
    mdl: str,
    known_topics: list[str],
) -> dict:
    """Read source file, call LLM, and return the parsed JSON dict.

    Returns an empty dict on file-read or JSON-parse failure.
    Raises OSError when the source file cannot be opened (caller converts to IngestResult error).
    """
    content = Path(source_path).read_text(encoding="utf-8")
    system_prompt, user_prompt = build_ingest_prompt(
        ingest_type, source_path, content, project, known_topics
    )
    raw_response = _call_llm(f"{system_prompt}\n\n---\n\n{user_prompt}", provider=prov, model=mdl)
    return _parse_llm_json(raw_response)


def ingest_document(
    ctx: AppContext,
    source_path: str,
    ingest_type: str,
    project: str = "",
    provider: str | None = None,
    model: str | None = None,
    dry_run: bool = False,
) -> "IngestResult":
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

    # Pipeline: validate type → _run_ingest_llm → _apply_wiki_updates → log.
    """
    if ingest_type not in INGEST_TYPES:
        raise ValueError(f"Unsupported ingest type '{ingest_type}'. Valid: {INGEST_TYPES}")

    prov = provider or DEFAULT_PROVIDER
    mdl = model or DEFAULT_MODEL_BY_PROVIDER.get(prov, "")

    try:
        parsed = _run_ingest_llm(source_path, ingest_type, project, prov, mdl, list_wiki_topics(ctx.wiki_dir))
    except OSError as exc:
        return IngestResult(ingest_type=ingest_type, source_path=source_path, project=project, summary="", error=str(exc))

    summary = parsed.get("summary", "")
    topics = [t for t in parsed.get("topics", []) if t in list_wiki_topics(ctx.wiki_dir)]
    log_entry = _build_log_entry(
        ingest_type=ingest_type, source_path=source_path, project=project,
        summary=summary, topics=topics, provider=prov, model=mdl,
    )

    if not dry_run:
        topics_updated, timeline_count = _apply_wiki_updates(
            ctx, topics, ingest_type, parsed.get("timeline_entry", ""), parsed.get("compiled_truth_update", "")
        )
        _append_ingest_log(ctx, log_entry)
    else:
        topics_updated = topics
        timeline_count = 0
        log_entry["dry_run"] = True

    return IngestResult(
        ingest_type=ingest_type, source_path=source_path, project=project,
        summary=summary, topics_updated=topics_updated,
        timeline_entries_added=timeline_count, log_entry=log_entry, dry_run=dry_run,
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
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
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


def _parse_ingest_args(args: list[str]) -> dict:
    """Parse CLI flags for cmd_ingest into a flat dict of options."""
    parsed = {
        "source_path": args[0],
        "ingest_type": "",
        "project": "",
        "provider": None,
        "model": None,
        "dry_run": False,
        "show_log": False,
    }
    i = 1
    _flag_with_value = {"--type": "ingest_type", "--project": "project",
                        "--provider": "provider", "--model": "model"}
    while i < len(args):
        flag = args[i]
        if flag in _flag_with_value and i + 1 < len(args):
            parsed[_flag_with_value[flag]] = args[i + 1]
            i += 2
        elif flag == "--dry-run":
            parsed["dry_run"] = True
            i += 1
        elif flag == "--log":
            parsed["show_log"] = True
            i += 1
        else:
            i += 1
    return parsed


def _print_ingest_result(result: "IngestResult", dry_run: bool, ctx: AppContext) -> None:
    """Print ingest outcome to stdout."""
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


def _validate_ingest_options(opts: dict[str, Any]) -> bool:
    """Validate parsed ingest CLI options and print user-facing errors."""
    ingest_type = opts["ingest_type"]
    if not ingest_type:
        print("错误: 必须指定 --type 参数")
        _print_ingest_usage()
        return False

    if ingest_type not in INGEST_TYPES:
        print(f"错误: 不支持的类型 '{ingest_type}'。支持: {', '.join(INGEST_TYPES)}")
        return False

    return True


def _execute_ingest(ctx: AppContext, opts: dict[str, Any]) -> int:
    """Run ingest_document from parsed CLI options and print the final outcome."""
    try:
        result = ingest_document(
            ctx,
            source_path=opts["source_path"],
            ingest_type=opts["ingest_type"],
            project=opts["project"],
            provider=opts["provider"],
            model=opts["model"],
            dry_run=opts["dry_run"],
        )
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 摄取失败: {exc}")
        return 1

    if result.error:
        print(f"❌ 错误: {result.error}")
        return 1

    _print_ingest_result(result, opts["dry_run"], ctx)
    return 0


def cmd_ingest(ctx: AppContext, args: list[str]) -> int:
    """Ingest a document into the memory system.

    Usage: amem ingest <file> --type <type> [--project <id>] [--provider anthropic|openai|ollama]
                              [--model <name>] [--dry-run] [--log]

    Types: pr-review, meeting, decision, code-review

    # Dispatch: --log → show log; else parse type + call ingest_document + print result.
    """
    # Keep the command surface simple: usage gate, log mode, validation, then execute.
    if not args or args[0].startswith("--"):
        _print_ingest_usage()
        return 1

    opts = _parse_ingest_args(args)

    if opts["show_log"]:
        _cmd_show_log(ctx)
        return 0

    if not _validate_ingest_options(opts):
        return 1

    return _execute_ingest(ctx, opts)


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
