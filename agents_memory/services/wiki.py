from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from agents_memory.runtime import AppContext


_FRONTMATTER_TEMPLATE = """\
---
topic: {topic}
created_at: {today}
updated_at: {today}
confidence: medium
sources: []
---

"""

# Template for v2 pages with compiled_truth / timeline sections
_COMPILED_FRONTMATTER_TEMPLATE = """\
---
topic: {topic}
created_at: {today}
updated_at: {today}
compiled_at: {today}
confidence: medium
sources: []
links: []
---

"""

# Sentinel comment lines separating compiled_truth from timeline
_TIMELINE_SEPARATOR = "---"
_TIMELINE_HEADER = "## 时间线"


# ---------------------------------------------------------------------------
# Low-level page helpers
# ---------------------------------------------------------------------------


def _frontmatter_end(content: str) -> int:
    """Return the character offset just after the closing --- fence, or 0 if absent."""
    fence_count = 0
    pos = 0
    for line in content.splitlines(keepends=True):
        pos += len(line)
        if line.strip() == "---":
            fence_count += 1
            if fence_count == 2:
                return pos
    return 0


def _refresh_updated_at(content: str, today: str) -> str:
    """Replace the updated_at value inside the frontmatter block."""
    fm_end = _frontmatter_end(content)
    if not fm_end:
        return content
    fm_lines = content[:fm_end].splitlines(keepends=True)
    updated_fm = "".join(
        f"updated_at: {today}\n" if line.startswith("updated_at:") else line
        for line in fm_lines
    )
    return updated_fm + content[fm_end:]


def _format_frontmatter_value(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_format_frontmatter_value(item) for item in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_./-]+", text):
        return text
    return json.dumps(text, ensure_ascii=False)


def _merge_frontmatter_extra(content: str, extra: dict[str, Any]) -> str:
    if not extra:
        return content
    fm_end = _frontmatter_end(content)
    if not fm_end:
        return content
    fm_lines = content[:fm_end].splitlines(keepends=True)
    body = content[fm_end:]
    closing_index = next(
        (idx for idx in range(len(fm_lines) - 1, -1, -1) if fm_lines[idx].strip() == "---"),
        len(fm_lines) - 1,
    )
    updated_lines: list[str] = []
    seen_keys: set[str] = set()
    for line in fm_lines[:closing_index]:
        stripped = line.strip()
        if not stripped or stripped.startswith("-") or ":" not in stripped:
            updated_lines.append(line)
            continue
        key = stripped.split(":", 1)[0].strip()
        if key in extra:
            updated_lines.append(f"{key}: {_format_frontmatter_value(extra[key])}\n")
            seen_keys.add(key)
            continue
        updated_lines.append(line)
    for key, value in extra.items():
        if key in seen_keys:
            continue
        updated_lines.append(f"{key}: {_format_frontmatter_value(value)}\n")
    updated_lines.append(fm_lines[closing_index])
    return "".join(updated_lines) + body


def _excerpt_around(content: str, keyword: str, context_lines: int = 3) -> str:
    """Return a short excerpt centered on the first line that contains *keyword*."""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if keyword in line.lower():
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            return "\n".join(lines[start:end])
    return "\n".join(lines[: min(6, len(lines))])


# ---------------------------------------------------------------------------
# Compiled Truth / Timeline helpers (v2 page format)
# ---------------------------------------------------------------------------


def parse_wiki_sections(content: str) -> dict[str, str]:
    """Split a wiki page into its three logical sections.

    Returns a dict with keys:
    - ``frontmatter_str``: raw frontmatter block (including ``---`` fences)
    - ``compiled_truth``: text above the ``---`` separator (excluding frontmatter)
    - ``timeline``: text below the ``---`` separator + ``## 时间线`` header

    For legacy pages without a ``---`` separator, ``timeline`` is empty and
    ``compiled_truth`` holds the entire body.
    """
    fm_end = _frontmatter_end(content)
    frontmatter_str = content[:fm_end].rstrip("\n") if fm_end else ""
    body = content[fm_end:].lstrip("\n") if fm_end else content

    # Find the first bare "---" line in the body that acts as the section divider.
    lines = body.splitlines(keepends=True)
    separator_idx: int | None = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            separator_idx = i
            break

    if separator_idx is None:
        return {
            "frontmatter_str": frontmatter_str,
            "compiled_truth": body.rstrip("\n"),
            "timeline": "",
        }

    compiled_truth = "".join(lines[:separator_idx]).rstrip("\n")
    timeline_raw = "".join(lines[separator_idx + 1 :]).lstrip("\n")
    # Strip leading "## 时间线" header if present so the stored value is just entries.
    if timeline_raw.startswith(_TIMELINE_HEADER):
        timeline_raw = timeline_raw[len(_TIMELINE_HEADER):].lstrip("\n")
    return {
        "frontmatter_str": frontmatter_str,
        "compiled_truth": compiled_truth.rstrip("\n"),
        "timeline": timeline_raw.rstrip("\n"),
    }


def build_compiled_page(
    topic: str,
    compiled_truth: str,
    timeline: str,
    *,
    fm_extra: dict[str, Any] | None = None,
    existing_frontmatter: str = "",
) -> str:
    """Assemble a v2 wiki page from its three sections.

    If *existing_frontmatter* is provided it is used as-is (with ``updated_at``
    and ``compiled_at`` refreshed).  Otherwise a fresh frontmatter block is
    generated from *topic* and *fm_extra*.
    """
    today = date.today().isoformat()

    if existing_frontmatter:
        # Ensure the frontmatter contains two --- fences; add closing fence if missing.
        fm_raw = existing_frontmatter.strip()
        if fm_raw.count("---") < 2:
            fm_raw = fm_raw + "\n---"
        fm = _refresh_updated_at(fm_raw + "\n", today).rstrip("\n")
        # Also refresh compiled_at
        fm_lines = fm.splitlines(keepends=True)
        fm = "".join(
            f"compiled_at: {today}\n" if line.startswith("compiled_at:") else line
            for line in fm_lines
        ).rstrip("\n")
    else:
        fm = _COMPILED_FRONTMATTER_TEMPLATE.format(topic=topic, today=today).rstrip("\n")
        if fm_extra:
            # Inject extra key-value pairs before the closing ---
            parts = fm.rstrip("\n").rsplit("---", 1)
            extra_lines = "".join(f"{k}: {v}\n" for k, v in fm_extra.items())
            fm = parts[0] + extra_lines + "---"

    body = compiled_truth.strip()
    parts = [fm, "", body]

    if timeline.strip():
        parts += ["", _TIMELINE_SEPARATOR, "", _TIMELINE_HEADER, "", timeline.strip()]

    return "\n".join(parts) + "\n"


def append_timeline_entry(wiki_dir: Path, topic: str, entry: str) -> Path:
    """Append *entry* as the newest item in the timeline section of *topic*.

    Creates the page (and timeline section) if it does not exist.
    The entry is prepended (newest-first convention).
    """
    path = wiki_dir / f"{topic}.md"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    if path.exists():
        sections = parse_wiki_sections(path.read_text(encoding="utf-8"))
        existing_timeline = sections["timeline"]
        new_timeline = entry.strip() + ("\n" + existing_timeline if existing_timeline else "")
        new_content = build_compiled_page(
            topic,
            sections["compiled_truth"],
            new_timeline,
            existing_frontmatter=sections["frontmatter_str"],
        )
    else:
        fm = _COMPILED_FRONTMATTER_TEMPLATE.format(topic=topic, today=today).rstrip("\n")
        new_content = build_compiled_page(topic, "", entry.strip(), existing_frontmatter=fm)

    path.write_text(new_content, encoding="utf-8")
    return path


def update_compiled_truth(wiki_dir: Path, topic: str, new_truth: str) -> Path:
    """Overwrite the compiled_truth section while preserving the timeline."""
    path = wiki_dir / f"{topic}.md"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    if path.exists():
        sections = parse_wiki_sections(path.read_text(encoding="utf-8"))
        new_content = build_compiled_page(
            topic,
            new_truth,
            sections["timeline"],
            existing_frontmatter=sections["frontmatter_str"],
        )
    else:
        fm = _COMPILED_FRONTMATTER_TEMPLATE.format(topic=topic, today=today).rstrip("\n")
        new_content = build_compiled_page(topic, new_truth, "", existing_frontmatter=fm)

    path.write_text(new_content, encoding="utf-8")
    return path


def _parse_fm_links_block(fm_lines: list[str]) -> list[dict[str, str]]:
    """Extract link entries from the raw lines of a frontmatter block.

    Processes the block after the ``links:`` key has been encountered.
    # State machine: "- topic:" starts a new entry; "context:" fills current; other top-level key ends block.
    """
    links: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in fm_lines:
        stripped = line.strip()
        if stripped.startswith("- topic:"):
            if current:
                links.append(current)
            current = {"topic": stripped[len("- topic:"):].strip()}
        elif stripped.startswith("context:") and current:
            current["context"] = stripped[len("context:"):].strip().strip('"').strip("'")
        elif stripped and not stripped.startswith("-") and ":" in stripped:
            # different top-level key — block is over
            if current:
                links.append(current)
                current = {}
            break
    if current:
        links.append(current)
    return links


def get_wiki_links(content: str) -> list[dict[str, str]]:
    """Parse the ``links:`` list from frontmatter and return it as a list of dicts.

    Each dict has at minimum a ``topic`` key and optionally a ``context`` key.
    Returns an empty list when no links are present or frontmatter is absent.
    """
    fm_end = _frontmatter_end(content)
    if not fm_end:
        return []
    fm_lines = content[:fm_end].splitlines()
    try:
        links_start = next(i for i, l in enumerate(fm_lines) if l.strip().startswith("links:"))
    except StopIteration:
        return []
    return _parse_fm_links_block(fm_lines[links_start + 1:])


def _strip_links_from_fm(fm_lines: list[str]) -> list[str]:
    """Remove any existing ``links:`` block from raw frontmatter lines."""
    result: list[str] = []
    in_links = False
    for line in fm_lines:
        stripped = line.strip()
        if stripped.startswith("links:"):
            in_links = True
            continue
        if in_links:
            if stripped.startswith("- ") or stripped == "":
                continue
            in_links = False
        result.append(line)
    return result


def _build_links_yaml(links: list[dict[str, str]]) -> list[str]:
    """Return YAML lines for a links block suitable for frontmatter insertion."""
    lines = ["links:\n"]
    for link in links:
        lines.append(f"  - topic: {link['topic']}\n")
        if link.get("context"):
            lines.append(f"    context: \"{link['context']}\"\n")
    return lines


def set_wiki_links(wiki_dir: Path, topic: str, links: list[dict[str, str]]) -> Path:
    """Write the ``links:`` field in the frontmatter of the wiki page for *topic*.

    Replaces any existing links list entirely.
    """
    path = wiki_dir / f"{topic}.md"
    if not path.exists():
        raise FileNotFoundError(f"Wiki page not found: {path}")
    content = path.read_text(encoding="utf-8")
    fm_end = _frontmatter_end(content)
    if not fm_end:
        return path  # no frontmatter, skip

    fm_lines = _strip_links_from_fm(content[:fm_end].splitlines(keepends=True))
    closing_idx = next(
        (i for i in range(len(fm_lines) - 1, -1, -1) if fm_lines[i].strip() == "---"),
        len(fm_lines) - 1,
    )
    final_fm = fm_lines[:closing_idx] + _build_links_yaml(links) + [fm_lines[closing_idx]]
    new_content = "".join(final_fm) + content[fm_end:]
    new_content = _refresh_updated_at(new_content, date.today().isoformat())
    path.write_text(new_content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Public service API
# ---------------------------------------------------------------------------


def list_wiki_topics(wiki_dir: Path) -> list[str]:
    """Return sorted list of topic stems found in *wiki_dir*."""
    if not wiki_dir.exists():
        return []
    return sorted(p.stem for p in wiki_dir.glob("*.md"))


def read_wiki_page(wiki_dir: Path, topic: str) -> str | None:
    """Return the full text of a wiki page, or None if it does not exist."""
    path = wiki_dir / f"{topic}.md"
    return path.read_text(encoding="utf-8") if path.exists() else None


def write_wiki_page(
    wiki_dir: Path,
    topic: str,
    content: str,
    *,
    source: str = "",
    frontmatter_extra: dict[str, Any] | None = None,
) -> Path:
    """Create or overwrite a wiki page; auto-generates frontmatter when absent.

    Rules:
    - If *content* begins with ``---`` it is treated as a complete page and only
      ``updated_at`` is refreshed.
    - If the page already exists its frontmatter is preserved and the body is
      replaced with *content*.
    - Otherwise a fresh frontmatter block is prepended.
    """
    wiki_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    path = wiki_dir / f"{topic}.md"

    if content.lstrip().startswith("---"):
        final = _refresh_updated_at(content, today)
    elif path.exists():
        existing = path.read_text(encoding="utf-8")
        fm_end = _frontmatter_end(existing)
        if fm_end:
            header = _refresh_updated_at(existing[:fm_end], today)
            final = header + content
        else:
            fm = _FRONTMATTER_TEMPLATE.format(topic=topic, today=today)
            final = fm + content
    else:
        fm = _FRONTMATTER_TEMPLATE.format(topic=topic, today=today)
        if source:
            fm = fm.replace("sources: []", f"sources: [{source}]")
        final = fm + content

    if frontmatter_extra:
        final = _merge_frontmatter_extra(final, frontmatter_extra)

    path.write_text(final, encoding="utf-8")
    return path


def search_wiki(wiki_dir: Path, query: str, limit: int = 5) -> list[dict]:
    """Return up to *limit* wiki pages whose text contains *query* (case-insensitive)."""
    if not wiki_dir.exists():
        return []
    keyword = query.lower()
    matches: list[dict] = []
    for path in sorted(wiki_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        if keyword in content.lower():
            matches.append(
                {
                    "topic": path.stem,
                    "path": str(path),
                    "excerpt": _excerpt_around(content, keyword),
                }
            )
            if len(matches) >= limit:
                break
    return matches


def ingest_file(wiki_dir: Path, source_path: Path, topic: str | None = None) -> Path:
    """Import a Markdown file into the wiki.

    The topic defaults to the lower-cased, hyphen-separated stem of the file name.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    resolved_topic = (topic or source_path.stem).lower().replace(" ", "-")
    content = source_path.read_text(encoding="utf-8")
    return write_wiki_page(wiki_dir, resolved_topic, content, source=source_path.name)


# ---------------------------------------------------------------------------
# CLI command implementations
# ---------------------------------------------------------------------------


def cmd_wiki_list(ctx: AppContext, args: list[str]) -> int:
    """Print all wiki topic names."""
    topics = list_wiki_topics(ctx.wiki_dir)
    if not topics:
        print("Wiki 尚无内容。提示: 运行 amem wiki-ingest <path> 导入文档。")
        return 0
    print(f"Wiki 主题 ({len(topics)} 条):\n")
    for topic in topics:
        print(f"  • {topic}")
    return 0


def _parse_limit_arg(args: list[str], default: int = 5) -> tuple[int, list[str]]:
    """Extract --limit <n> from args; return (limit, remaining_args)."""
    limit = default
    remaining: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return limit, remaining


def _parse_topic_arg(args: list[str]) -> tuple[str | None, list[str]]:
    """Extract --topic <name> from args; return (topic, remaining_args)."""
    topic: str | None = None
    remaining: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--topic" and i + 1 < len(args):
            topic = args[i + 1]
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return topic, remaining


def _resolve_content_input(args: list[str]) -> tuple[str | None, list[str], int | None]:
    """Extract --content <text> or --from-file <path> from args.

    Returns (content_str, remaining_args, error_code).
    *error_code* is non-None when a --from-file path was given but not found.
    """
    content: str | None = None
    error_code: int | None = None
    remaining: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--content" and i + 1 < len(args):
            content = args[i + 1]
            i += 2
        elif args[i] == "--from-file" and i + 1 < len(args):
            file_path = Path(args[i + 1]).expanduser().resolve()
            if not file_path.exists():
                print(f"错误: 文件不存在: {file_path}")
                error_code = 1
            else:
                content = file_path.read_text(encoding="utf-8")
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return content, remaining, error_code


def cmd_wiki_query(ctx: AppContext, args: list[str]) -> int:
    """Search wiki pages by keyword and print matching excerpts."""
    if not args or args[0].startswith("--"):
        print("用法: amem wiki-query <keyword> [--limit <n>]")
        return 1
    query = args[0]
    limit, _ = _parse_limit_arg(args[1:])
    matches = search_wiki(ctx.wiki_dir, query, limit=limit)
    if not matches:
        print(f"Wiki 中未找到匹配 '{query}' 的内容。")
        print(f"Wiki 目录: {ctx.wiki_dir}")
        print("提示: 先运行 amem wiki-ingest <path> 导入文档，或 amem wiki-sync <topic> 写入知识。")
        return 0
    print(f"找到 {len(matches)} 个相关 Wiki 页面 (query: '{query}'):\n")
    for match in matches:
        print(f"─── [{match['topic']}] ───")
        print(match["excerpt"])
        print()
    return 0


def cmd_wiki_ingest(ctx: AppContext, args: list[str]) -> int:
    """Ingest a document file into the wiki."""
    if not args or args[0].startswith("--"):
        print("用法: amem wiki-ingest <path> [--topic <topic-name>]")
        return 1
    source = args[0]
    topic, _ = _parse_topic_arg(args[1:])
    source_path = Path(source).expanduser().resolve()
    try:
        path = ingest_file(ctx.wiki_dir, source_path, topic)
        print(f"✅ 已导入: {source_path.name}  →  {path}")
        return 0
    except FileNotFoundError as exc:
        print(f"错误: {exc}")
        return 1


def cmd_wiki_sync(ctx: AppContext, args: list[str]) -> int:
    """Write or update a wiki page for a topic."""
    if not args or args[0].startswith("--"):
        print("用法: amem wiki-sync <topic> [--content <text>] [--from-file <path>]")
        return 1
    topic = args[0]
    content, _, error_code = _resolve_content_input(args[1:])
    if error_code is not None:
        return error_code
    if content is None:
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            print("错误: 请通过 --content 或 --from-file 提供内容，或通过 stdin 传入。")
            return 1
    path = write_wiki_page(ctx.wiki_dir, topic, content)
    print(f"✅ Wiki 页面已更新: {path}")
    return 0


# ---------------------------------------------------------------------------
# wiki-link  /  wiki-backlinks  /  wiki-lint
# ---------------------------------------------------------------------------


def _upsert_link_entry(links: list[dict[str, str]], to_topic: str, context: str) -> list[dict[str, str]]:
    """Add or update a link to *to_topic* in *links*; returns updated list."""
    for lnk in links:
        if lnk["topic"] == to_topic:
            if context:
                lnk["context"] = context
            return links
    entry: dict[str, str] = {"topic": to_topic}
    if context:
        entry["context"] = context
    links.append(entry)
    return links


def cmd_wiki_link(ctx: AppContext, args: list[str]) -> int:
    """Create a directional link between two wiki topics.

    Usage: amem wiki-link <from-topic> <to-topic> [--context "..."]

    # Validate both topics exist → read existing links → _upsert_link_entry → save.
    """
    if len(args) < 2:
        print("用法: amem wiki-link <from-topic> <to-topic> [--context \"...\"]")
        return 1

    from_topic, to_topic = args[0], args[1]
    context_text = ""
    i = 2
    while i < len(args):
        if args[i] == "--context" and i + 1 < len(args):
            context_text = args[i + 1]
            i += 2
        else:
            i += 1

    for topic_name in (from_topic, to_topic):
        if not (ctx.wiki_dir / f"{topic_name}.md").exists():
            print(f"错误: Wiki 页面不存在: {topic_name}")
            return 1

    content = (ctx.wiki_dir / f"{from_topic}.md").read_text(encoding="utf-8")
    links = _upsert_link_entry(get_wiki_links(content), to_topic, context_text)
    set_wiki_links(ctx.wiki_dir, from_topic, links)
    print(f"✅ 链接已创建: {from_topic} → {to_topic}")
    return 0


def cmd_wiki_backlinks(ctx: AppContext, args: list[str]) -> int:
    """Show all wiki topics that link TO the given topic.

    Usage: amem wiki-backlinks <topic>

    # Scan every wiki page's links block for references to target; collect and print.
    """
    if not args:
        print("用法: amem wiki-backlinks <topic>")
        return 1
    target = args[0]
    if not ctx.wiki_dir.exists():
        print("Wiki 目录不存在，无内容。")
        return 0
    backlinks: list[dict[str, str]] = []
    for path in sorted(ctx.wiki_dir.glob("*.md")):
        if path.stem == target:
            continue
        content = path.read_text(encoding="utf-8")
        for lnk in get_wiki_links(content):
            if lnk["topic"] == target:
                backlinks.append({"from": path.stem, "context": lnk.get("context", "")})
    if not backlinks:
        print(f"没有 Wiki 页面链接到 '{target}'。")
        return 0
    print(f"链接到 '{target}' 的页面 ({len(backlinks)} 条):\n")
    for b in backlinks:
        ctx_str = f"  context: {b['context']}" if b["context"] else ""
        print(f"  • {b['from']}{ctx_str}")
    return 0


def _lint_orphans(ctx: AppContext, topics: list[str]) -> list[str]:
    """Return issue strings for wiki pages with no inbound links."""
    inbound: dict[str, int] = {t: 0 for t in topics}
    for topic in topics:
        content = (ctx.wiki_dir / f"{topic}.md").read_text(encoding="utf-8")
        for lnk in get_wiki_links(content):
            if lnk["topic"] in inbound:
                inbound[lnk["topic"]] += 1
    return [f"[orphan] '{t}' 无入链（无其他页面引用它）" for t, c in inbound.items() if c == 0]


def _lint_stale(ctx: AppContext, topics: list[str]) -> list[str]:
    """Return issue strings for compiled_truth older than 30 days."""
    from datetime import date as _date  # noqa: PLC0415
    issues: list[str] = []
    for topic in topics:
        content = (ctx.wiki_dir / f"{topic}.md").read_text(encoding="utf-8")
        compiled_at = next(
            (line.split(":", 1)[1].strip() for line in content.splitlines() if line.startswith("compiled_at:")),
            "",
        )
        if not compiled_at:
            continue
        try:
            if (_date.today() - _date.fromisoformat(compiled_at)).days > 30:
                issues.append(f"[stale] '{topic}' compiled_truth 已超过 30 天未更新 (compiled_at={compiled_at})")
        except ValueError:
            pass
    return issues


def _lint_missing_links(ctx: AppContext, topics: list[str]) -> list[str]:
    """Return issue strings for topics mentioned in body but not linked."""
    issues: list[str] = []
    for topic in topics:
        content = (ctx.wiki_dir / f"{topic}.md").read_text(encoding="utf-8")
        sections = parse_wiki_sections(content)
        body_text = (sections["compiled_truth"] + " " + sections["timeline"]).lower()
        linked = {lnk["topic"] for lnk in get_wiki_links(content)}
        for other in topics:
            if other == topic or other in linked:
                continue
            if other.replace("-", " ") in body_text or other in body_text:
                issues.append(f"[missing-link] '{topic}' 提及了 '{other}' 但未建立链接")
    return issues


def cmd_wiki_lint(ctx: AppContext, args: list[str]) -> int:
    """Health-check the wiki: detect orphan pages, stale compiled_truth, missing links.

    Usage: amem wiki-lint [--check orphans|stale|missing-links|all]
    Exits 0 even when issues are found; issues are printed to stdout.

    # Dispatch: parse --check flag → call lint sub-functions → aggregate + print.
    """
    check_mode = "all"
    i = 0
    while i < len(args):
        if args[i].startswith("--check="):
            check_mode = args[i].split("=", 1)[1]
            i += 1
        elif args[i] == "--check" and i + 1 < len(args):
            check_mode = args[i + 1]
            i += 2
        else:
            i += 1

    if not ctx.wiki_dir.exists():
        print("Wiki 目录不存在，无内容可检查。")
        return 0

    topics = list_wiki_topics(ctx.wiki_dir)
    if not topics:
        print("Wiki 尚无内容。")
        return 0

    issues: list[str] = []
    if check_mode in ("orphans", "all"):
        issues += _lint_orphans(ctx, topics)
    if check_mode in ("stale", "all"):
        issues += _lint_stale(ctx, topics)
    if check_mode in ("missing-links", "all"):
        issues += _lint_missing_links(ctx, topics)

    if not issues:
        print(f"✅ Wiki 健康检查通过（{len(topics)} 个页面，无问题）")
        return 0

    print(f"⚠️  发现 {len(issues)} 个问题:\n")
    for issue in issues:
        print(f"  • {issue}")
    return 0
