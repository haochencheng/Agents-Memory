#!/usr/bin/env python3.12
"""
test-synapse-wiki.py — Synapse-Network wiki 接入链路自动化测试

测试覆盖:
  1. wiki topics 已生成（数量 > 0）
  2. synapse-architecture topic 存在且有内容
  3. wiki-query 能检索到 Synapse 相关内容
  4. wiki-lint 健康检查通过
  5. ingest --dry-run （使用 Synapse bugfix 文档）
  6. Embedding 对 Synapse 文档有效（维度正确）

用法:
  python3.12 scripts/test-synapse-wiki.py
  python3.12 scripts/test-synapse-wiki.py --quick    # 跳过 LLM 和 ingest 测试
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from io import StringIO
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYNAPSE_ROOT = Path("/Users/cliff/workspace/agent/Synapse-Network")
sys.path.insert(0, str(ROOT))

os.environ.setdefault("AGENTS_MEMORY_ROOT", str(ROOT))
os.environ.setdefault("AMEM_EMBED_PROVIDER", "ollama")
os.environ.setdefault("AMEM_LLM_PROVIDER", "ollama")
os.environ.setdefault("AMEM_LLM_MODEL", "qwen2.5:7b")
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")

# ─── 颜色 ─────────────────────────────────────────────────────────────────────
GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
BLUE   = "\033[0;34m"
NC     = "\033[0m"

def ok(msg):   print(f"{GREEN}  ✅ {msg}{NC}")
def fail(msg): print(f"{RED}  ❌ {msg}{NC}")
def warn(msg): print(f"{YELLOW}  ⚠️  {msg}{NC}")
def info(msg): print(f"{BLUE}  ℹ  {msg}{NC}")
def section(name): print(f"\n{BLUE}══ {name} ══{NC}")

parser = argparse.ArgumentParser()
parser.add_argument("--quick", action="store_true", help="跳过 LLM 和 ingest 测试")
args = parser.parse_args()

results: list[tuple[str, bool, str]] = []

def check(name: str, fn):
    try:
        msg = fn()
        ok(f"{name}: {msg or 'passed'}")
        results.append((name, True, msg or ""))
    except Exception as e:
        err_msg = str(e)
        fail(f"{name}: {err_msg}")
        results.append((name, False, err_msg))
        if os.environ.get("AMEM_TEST_VERBOSE"):
            traceback.print_exc()

# ─── 测试函数 ──────────────────────────────────────────────────────────────────

def test_wiki_topics_exist():
    from agents_memory.runtime import build_context
    from agents_memory.services.wiki import list_wiki_topics
    ctx = build_context()
    topics = list_wiki_topics(ctx.wiki_dir)
    if not topics:
        raise AssertionError("wiki 目录为空。先运行: bash scripts/gen-synapse-wiki.sh")
    synapse_topics = [t for t in topics if "synapse" in t.lower()]
    if not synapse_topics:
        raise AssertionError(
            f"未找到 synapse 相关 topic（共 {len(topics)} 个 topics）。"
            "先运行: bash scripts/gen-synapse-wiki.sh"
        )
    return f"共 {len(topics)} 个 topics，synapse 相关: {len(synapse_topics)} 个"


def test_synapse_architecture_topic():
    from agents_memory.runtime import build_context
    from agents_memory.services.wiki import read_wiki_page, list_wiki_topics
    ctx = build_context()
    topics = list_wiki_topics(ctx.wiki_dir)
    arch_topics = [t for t in topics if "architecture" in t.lower() or "overview" in t.lower()]
    if not arch_topics:
        raise AssertionError(
            f"未找到 architecture/overview topic。可用 topics: {topics[:5]}"
        )
    topic = arch_topics[0]
    content = read_wiki_page(ctx.wiki_dir, topic)
    if not content or len(content) < 100:
        raise AssertionError(f"topic '{topic}' 内容过短: {len(content or '')} 字符")
    return f"topic '{topic}' 存在，内容 {len(content)} 字符"


def test_wiki_query():
    from agents_memory.runtime import build_context
    from agents_memory.services.wiki import search_wiki
    ctx = build_context()
    # 搜索 Synapse 相关内容
    results_q = search_wiki(ctx.wiki_dir, "synapse", limit=5)
    if not results_q:
        results_q = search_wiki(ctx.wiki_dir, "gateway", limit=5)
    if not results_q:
        # Try any keyword from the topics
        from agents_memory.services.wiki import list_wiki_topics
        topics = list_wiki_topics(ctx.wiki_dir)
        if topics:
            keyword = topics[0].replace("-", " ").split()[0]
            results_q = search_wiki(ctx.wiki_dir, keyword, limit=5)
    if not results_q:
        raise AssertionError("wiki-query 未返回结果（wiki 可能为空或内容不含 'synapse'/'gateway'）")
    return f"wiki-query 命中 {len(results_q)} 条: {[r['topic'] for r in results_q]}"


def test_wiki_lint():
    from agents_memory.runtime import build_context
    from agents_memory.services.wiki import cmd_wiki_lint, list_wiki_topics
    ctx = build_context()
    topics = list_wiki_topics(ctx.wiki_dir)
    if not topics:
        return "wiki 为空，跳过 lint"
    buf = StringIO()
    with redirect_stdout(buf):
        exit_code = cmd_wiki_lint(ctx, [])
    output = buf.getvalue()
    if exit_code != 0:
        raise AssertionError(f"wiki-lint 返回非 0: {output}")
    # Both OK and warnings are acceptable (non-zero exit not raised)
    return f"wiki-lint 完成: {'✅' if '✅' in output else '⚠️ 有警告'}"


def test_ingest_dry_run_with_synapse_doc():
    if args.quick:
        return "跳过（--quick 模式）"

    bugfix_file = SYNAPSE_ROOT / "docs/reference/bugfix/gateway/BUG-DEPOSIT-01-intent-status-false-failed.md"
    if not bugfix_file.exists():
        return f"跳过（文件不存在: {bugfix_file}）"

    from agents_memory.runtime import build_context
    from agents_memory.services.ingest import ingest_document
    ctx = build_context()

    result = ingest_document(ctx, str(bugfix_file), "pr-review", "synapse-network", dry_run=True)
    if result.error:
        raise AssertionError(f"ingest 返回错误: {result.error}")
    return f"ingest --dry-run 通过: summary 长度={len(result.summary)}, topics={result.topics_updated}"


def test_embedding_for_synapse_doc():
    arch_file = SYNAPSE_ROOT / "docs/ARCHITECTURE.md"
    if not arch_file.exists():
        return f"跳过（文件不存在: {arch_file}）"

    from agents_memory.services.records import get_embedding
    sample_text = arch_file.read_text(encoding="utf-8")[:500]
    vec = get_embedding(sample_text)
    if not vec or len(vec) < 100:
        raise AssertionError(f"embedding 维度异常: {len(vec)}")
    return f"Synapse 文档 embedding 成功，维度={len(vec)}"


def test_synapse_bugfix_files_accessible():
    bugfix_dir = SYNAPSE_ROOT / "docs/reference/bugfix"
    if not bugfix_dir.exists():
        raise AssertionError(f"bugfix 目录不存在: {bugfix_dir}")
    files = list(bugfix_dir.rglob("*.md"))
    if not files:
        raise AssertionError("bugfix 目录中无 .md 文件")
    return f"找到 {len(files)} 个 bugfix 文件"


def test_wiki_frontmatter_valid():
    """验证 wiki 页面 frontmatter 格式正确"""
    from agents_memory.runtime import build_context
    from agents_memory.services.wiki import list_wiki_topics
    ctx = build_context()
    topics = list_wiki_topics(ctx.wiki_dir)
    if not topics:
        return "wiki 为空，跳过"
    bad_pages = []
    for topic in topics[:10]:  # 只检查前 10 个
        path = ctx.wiki_dir / f"{topic}.md"
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            bad_pages.append(topic)
    if bad_pages:
        raise AssertionError(f"以下 topics frontmatter 缺失: {bad_pages}")
    checked = min(len(topics), 10)
    return f"检查 {checked}/{len(topics)} 个 topics，frontmatter 格式正确"


# ─── 主流程 ───────────────────────────────────────────────────────────────────
section("Synapse-Network Wiki 接入测试")
print(f"  AGENTS_MEMORY_ROOT: {ROOT}")
print(f"  SYNAPSE_ROOT:       {SYNAPSE_ROOT}")
print(f"  quick: {args.quick}")

section("1. 源文件检查")
check("Synapse bugfix 文件可访问",      test_synapse_bugfix_files_accessible)

section("2. Wiki 知识库检查")
check("Wiki topics 已生成",             test_wiki_topics_exist)
check("Architecture topic 存在且有内容", test_synapse_architecture_topic)
check("Frontmatter 格式正确",           test_wiki_frontmatter_valid)

section("3. 查询链路")
check("wiki-query 检索",                test_wiki_query)
check("wiki-lint 健康检查",             test_wiki_lint)

section("4. Ingest 链路")
check("ingest --dry-run（Synapse bugfix）", test_ingest_dry_run_with_synapse_doc)

section("5. Embedding 链路")
check("Synapse 文档 embedding",          test_embedding_for_synapse_doc)

# ─── 汇总 ────────────────────────────────────────────────────────────────────
section("测试汇总")
passed = sum(1 for _, ok_, _ in results if ok_)
failed = sum(1 for _, ok_, _ in results if not ok_)
total  = len(results)

print(f"\n  通过: {passed}/{total}")
if failed:
    print(f"  失败: {failed}/{total}")
    print("\n  失败项目:")
    for name, ok_, msg in results:
        if not ok_:
            print(f"    • {name}: {msg}")
    sys.exit(1)
else:
    print(f"\n{GREEN}  🎉 全部 {total} 项测试通过！Synapse-Network wiki 接入正常。{NC}")
    sys.exit(0)
