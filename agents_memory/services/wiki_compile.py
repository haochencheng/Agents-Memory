"""wiki_compile — LLM-driven wiki synthesis (Phase 1 / P0 optimisation).

Reads recent error records, finds relevant wiki pages, calls an LLM to
synthesise a compiled-truth update, and writes the result back.

Providers supported via environment or explicit argument:
  anthropic  — ANTHROPIC_API_KEY
  openai     — OPENAI_API_KEY
  ollama     — local Ollama server (OLLAMA_HOST, default http://localhost:11434)

The function is intentionally free of side-effects when ``dry_run=True``
so that unit tests can exercise prompt construction and diff generation
without making real API calls.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

from agents_memory.runtime import AppContext
from agents_memory.services.wiki import (
    append_timeline_entry,
    list_wiki_topics,
    parse_wiki_sections,
    read_wiki_page,
    search_wiki,
    update_compiled_truth,
)
from agents_memory.services.records import collect_errors, read_body

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PROVIDER = os.getenv("AMEM_LLM_PROVIDER", "anthropic")
DEFAULT_MODEL_BY_PROVIDER: dict[str, str] = {
    "anthropic": os.getenv("AMEM_LLM_MODEL", "claude-sonnet-4-5"),
    "openai": os.getenv("AMEM_LLM_MODEL", "gpt-4o-mini"),
    "ollama": os.getenv("AMEM_LLM_MODEL", "qwen2.5:7b"),
}

_COMPILE_SYSTEM_PROMPT = """\
You are an engineering knowledge curator for the Agents-Memory system.
Your job is to synthesise error records into a concise, actionable wiki page section.

Rules:
1. Write the compiled_truth section in Chinese (中文), clear and concise.
2. The compiled_truth should contain:
   - A one-paragraph executive summary (blockquote `>`).
   - A "已知 Pattern" bullet list with concrete, actionable rules.
3. Do NOT include timeline entries — those are handled separately.
4. Do NOT hallucinate error IDs or dates not present in the input.
5. Return ONLY the compiled_truth markdown text, no frontmatter, no `---` separators.
"""

_COMPILE_USER_TEMPLATE = """\
# Wiki Topic: {topic}

## Current compiled_truth (may be empty for new pages)

{current_truth}

## Recent error records to synthesise

{error_summaries}

## Task

Produce an updated compiled_truth section for the wiki page "{topic}".
Include an executive summary and actionable patterns based on the errors above.
"""


# ---------------------------------------------------------------------------
# LLM client helpers
# ---------------------------------------------------------------------------


def _call_llm_anthropic(prompt: str, model: str) -> str:
    try:
        import anthropic  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("anthropic 包未安装。运行: pip install anthropic") from exc
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        system=_COMPILE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _call_llm_openai(prompt: str, model: str) -> str:
    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("openai 包未安装。运行: pip install openai") from exc
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _COMPILE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2048,
    )
    return (response.choices[0].message.content or "").strip()


def _call_llm_ollama(prompt: str, model: str) -> str:
    import urllib.request
    import json

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    url = f"{host}/api/generate"
    full_prompt = _COMPILE_SYSTEM_PROMPT + "\n\n" + prompt
    payload = json.dumps({"model": model, "prompt": full_prompt, "stream": False}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    return data.get("response", "").strip()


def _call_llm(prompt: str, *, provider: str, model: str) -> str:
    """Dispatch to the appropriate LLM provider."""
    dispatch = {
        "anthropic": _call_llm_anthropic,
        "openai": _call_llm_openai,
        "ollama": _call_llm_ollama,
    }
    if provider not in dispatch:
        raise ValueError(f"未知 LLM provider: {provider}. 支持: {list(dispatch)}")
    return dispatch[provider](prompt, model)


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def _build_error_summaries(records: list[dict], ctx: AppContext, max_records: int) -> str:
    """Build a text block summarising the most recent *max_records* errors."""
    lines: list[str] = []
    for rec in records[:max_records]:
        rec_id = rec.get("id", "?")
        category = rec.get("category", "")
        project = rec.get("project", "")
        filepath_str = rec.get("_file", "")
        body = ""
        if filepath_str:
            try:
                body = read_body(Path(filepath_str))[:400]
            except Exception:
                pass
        lines.append(f"### [{rec_id}] {category} / {project}")
        if body:
            lines.append(body.strip())
        lines.append("")
    return "\n".join(lines) if lines else "（无错误记录）"


def build_compile_prompt(topic: str, current_truth: str, error_summaries: str) -> str:
    """Public helper — builds the LLM prompt for compile.  Exposed for testing."""
    return _COMPILE_USER_TEMPLATE.format(
        topic=topic,
        current_truth=current_truth.strip() or "（尚无内容）",
        error_summaries=error_summaries.strip() or "（无相关错误记录）",
    )


# ---------------------------------------------------------------------------
# Core compile function
# ---------------------------------------------------------------------------


def compile_wiki_topic(
    ctx: AppContext,
    topic: str,
    *,
    recent_n: int = 20,
    scope: str = "errors",
    provider: str | None = None,
    model: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Synthesise a wiki page's compiled_truth from recent error records.

    Returns a result dict:
    {
        "topic": str,
        "status": "ok" | "skipped" | "dry_run",
        "new_compiled_truth": str,
        "timeline_entry": str,
        "error_count": int,
        "dry_run": bool,
        "path": str | None,
    }
    """
    resolved_provider = provider or DEFAULT_PROVIDER
    resolved_model = model or DEFAULT_MODEL_BY_PROVIDER.get(resolved_provider, "gpt-4o-mini")

    # 1. Gather source errors relevant to this topic
    all_errors = collect_errors(ctx)
    relevant_errors: list[dict] = []
    if scope == "errors" or scope == "all":
        keyword = topic.lower().replace("-", " ")
        for rec in all_errors:
            rec_text = " ".join(str(v) for v in rec.values()).lower()
            if keyword in rec_text or any(
                part in rec_text for part in keyword.split()
            ):
                relevant_errors.append(rec)
        if not relevant_errors:
            # Fall back to most recent N regardless of topic match
            relevant_errors = all_errors[:recent_n]

    if not relevant_errors:
        return {
            "topic": topic,
            "status": "skipped",
            "reason": "no error records found",
            "new_compiled_truth": "",
            "timeline_entry": "",
            "error_count": 0,
            "dry_run": dry_run,
            "path": None,
        }

    relevant_errors = relevant_errors[:recent_n]

    # 2. Read current wiki page
    current_page = read_wiki_page(ctx.wiki_dir, topic)
    current_sections = parse_wiki_sections(current_page) if current_page else {
        "frontmatter_str": "",
        "compiled_truth": "",
        "timeline": "",
    }
    current_truth = current_sections["compiled_truth"]

    # 3. Build prompt + call LLM
    error_summaries = _build_error_summaries(relevant_errors, ctx, len(relevant_errors))
    prompt = build_compile_prompt(topic, current_truth, error_summaries)

    if dry_run:
        new_truth = f"[dry-run] Would synthesise from {len(relevant_errors)} errors for topic '{topic}'."
        timeline_entry = ""
        path = None
    else:
        new_truth = _call_llm(prompt, provider=resolved_provider, model=resolved_model)

        # 4. Append timeline entry
        error_ids = [r.get("id", "?") for r in relevant_errors]
        timeline_entry = (
            f"- **{date.today().isoformat()}** | wiki-compile "
            f"— 从 {len(relevant_errors)} 条错误记录合成 compiled_truth "
            f"(errors: {', '.join(error_ids[:5])}{'...' if len(error_ids) > 5 else ''})"
        )

        # 5. Write back
        path_obj = update_compiled_truth(ctx.wiki_dir, topic, new_truth)
        append_timeline_entry(ctx.wiki_dir, topic, timeline_entry)
        path = str(path_obj)

    return {
        "topic": topic,
        "status": "dry_run" if dry_run else "ok",
        "new_compiled_truth": new_truth,
        "timeline_entry": timeline_entry if not dry_run else "",
        "error_count": len(relevant_errors),
        "dry_run": dry_run,
        "path": path,
    }


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


def _parse_compile_args(args: list[str]) -> dict[str, Any]:
    """Parse args for wiki-compile command."""
    parsed: dict[str, Any] = {
        "topic": None,
        "scope": "errors",
        "recent_n": 20,
        "provider": None,
        "model": None,
        "dry_run": False,
    }
    i = 0
    while i < len(args):
        if args[i] == "--topic" and i + 1 < len(args):
            parsed["topic"] = args[i + 1]; i += 2
        elif args[i] == "--scope" and i + 1 < len(args):
            parsed["scope"] = args[i + 1]; i += 2
        elif args[i] == "--recent-n" and i + 1 < len(args):
            try:
                parsed["recent_n"] = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == "--provider" and i + 1 < len(args):
            parsed["provider"] = args[i + 1]; i += 2
        elif args[i] == "--model" and i + 1 < len(args):
            parsed["model"] = args[i + 1]; i += 2
        elif args[i] == "--dry-run":
            parsed["dry_run"] = True; i += 1
        elif not args[i].startswith("--"):
            if parsed["topic"] is None:
                parsed["topic"] = args[i]
            i += 1
        else:
            i += 1
    return parsed


def cmd_wiki_compile(ctx: AppContext, args: list[str]) -> int:
    """CLI: amem wiki-compile <topic> [--scope errors|all] [--recent-n 20]
           [--provider anthropic|openai|ollama] [--model <name>] [--dry-run]
    """
    if not args:
        print("用法: amem wiki-compile <topic> [--scope errors|all] [--recent-n 20]")
        print("      [--provider anthropic|openai|ollama] [--model <name>] [--dry-run]")
        return 1

    parsed = _parse_compile_args(args)
    topic = parsed["topic"]
    if not topic:
        print("错误: 请提供 topic 名称。")
        return 1

    print(f"🔄 Wiki Compile: topic={topic}, scope={parsed['scope']}, "
          f"recent_n={parsed['recent_n']}, dry_run={parsed['dry_run']}")

    try:
        result = compile_wiki_topic(
            ctx,
            topic,
            recent_n=parsed["recent_n"],
            scope=parsed["scope"],
            provider=parsed["provider"],
            model=parsed["model"],
            dry_run=parsed["dry_run"],
        )
    except RuntimeError as exc:
        print(f"❌ LLM 调用失败: {exc}")
        return 1

    if result["status"] == "skipped":
        print(f"⏭️  跳过: {result.get('reason', '无相关记录')}")
        return 0

    if result["dry_run"]:
        print(f"\n[dry-run] 预览 — 将从 {result['error_count']} 条错误记录合成 '{topic}'")
        print("\n--- compiled_truth 预览 ---")
        print(result["new_compiled_truth"])
        return 0

    print(f"✅ 已更新 wiki/{topic}.md (来源: {result['error_count']} 条错误记录)")
    return 0
