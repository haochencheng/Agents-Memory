from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

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


def _excerpt_around(content: str, keyword: str, context_lines: int = 3) -> str:
    """Return a short excerpt centred on the first line that contains *keyword*."""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if keyword in line.lower():
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            return "\n".join(lines[start:end])
    return "\n".join(lines[: min(6, len(lines))])


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


def write_wiki_page(wiki_dir: Path, topic: str, content: str, *, source: str = "") -> Path:
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
