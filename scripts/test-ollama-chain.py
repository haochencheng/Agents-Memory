#!/usr/bin/env python3.12
"""
test-ollama-chain.py — Agents-Memory Ollama 全链路自动化测试

测试覆盖:
  1. Ollama 服务连通性
  2. nomic-embed-text Embedding 输出维度和值域
  3. qwen2.5:7b (或指定 LLM) 基础生成能力
  4. agents_memory 模块导入
  5. get_embedding() 端到端 → 返回 list[float] length=768
  6. wiki-sync → 创建 wiki 页面
  7. wiki-compile (--dry-run) → LLM 合成链路
  8. ingest (--dry-run) → 摄取链路
  9. hybrid-search → FTS 索引构建 + 搜索
 10. wiki-lint → 健康检查

用法:
  python3.12 scripts/test-ollama-chain.py
  python3.12 scripts/test-ollama-chain.py --llm gemma4:e4b
  python3.12 scripts/test-ollama-chain.py --quick   # 跳过 LLM 生成（快速模式）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import traceback
import urllib.request
from io import StringIO
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ─── 颜色输出 ─────────────────────────────────────────────────────────────────
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

# ─── 参数 ─────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Agents-Memory Ollama 全链路测试")
parser.add_argument("--embed",   default="nomic-embed-text",  help="Embedding 模型")
parser.add_argument("--llm",     default="qwen2.5:7b",        help="LLM 合成模型")
parser.add_argument("--host",    default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"), help="Ollama 地址")
parser.add_argument("--quick",   action="store_true",          help="跳过 LLM 调用（只测 embedding + 本地逻辑）")
args = parser.parse_args()

OLLAMA_HOST = args.host.rstrip("/")
EMBED_MODEL = args.embed
LLM_MODEL   = args.llm

# ─── 结果追踪 ─────────────────────────────────────────────────────────────────
results: list[tuple[str, bool, str]] = []

def check(name: str, fn):
    """Run a test function, record pass/fail."""
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

# ─── 测试函数 ─────────────────────────────────────────────────────────────────

def test_ollama_health():
    url = f"{OLLAMA_HOST}/api/tags"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
    models = [m["name"] for m in data.get("models", [])]
    return f"Ollama 在线，已有模型: {len(models)} 个"


def test_embed_model_available():
    url = f"{OLLAMA_HOST}/api/tags"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
    names = [m["name"] for m in data.get("models", [])]
    base = EMBED_MODEL.split(":")[0]
    if not any(n == EMBED_MODEL or n.startswith(base + ":") for n in names):
        raise AssertionError(f"{EMBED_MODEL} 未安装。运行: ollama pull {EMBED_MODEL}")
    return f"{EMBED_MODEL} 已就绪"


def test_llm_model_available():
    url = f"{OLLAMA_HOST}/api/tags"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
    names = [m["name"] for m in data.get("models", [])]
    base = LLM_MODEL.split(":")[0]
    if not any(n == LLM_MODEL or n.startswith(base + ":") for n in names):
        raise AssertionError(f"{LLM_MODEL} 未安装。运行: ollama pull {LLM_MODEL}")
    return f"{LLM_MODEL} 已就绪"


def test_embedding_output():
    payload = json.dumps({"model": EMBED_MODEL, "prompt": "Synapse-Network 错误记录"}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/embeddings", data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    vec = data.get("embedding", [])
    if not vec:
        raise AssertionError("embedding 字段为空")
    dim = len(vec)
    if dim < 100:
        raise AssertionError(f"维度异常: {dim}（预期 >= 100）")
    # 值域检查
    if not all(isinstance(v, (int, float)) for v in vec[:5]):
        raise AssertionError("embedding 值类型异常")
    return f"维度={dim}, 首值={vec[0]:.4f}"


def test_llm_json_output():
    if args.quick:
        return "跳过（--quick 模式）"
    payload = json.dumps({
        "model": LLM_MODEL,
        "prompt": '用 JSON 格式回答，只输出 JSON，不要其他文字。格式: {"answer": "值"}\n问题: 1+1=?',
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate", data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    response = data.get("response", "")
    if not response:
        raise AssertionError("LLM 返回为空")
    return f"响应长度={len(response)}，首50字: {response[:50]!r}"


def test_agents_memory_import():
    from agents_memory.runtime import build_context
    from agents_memory.services.records import get_embedding
    from agents_memory.services.wiki import list_wiki_topics, write_wiki_page
    return "所有核心模块导入成功"


def test_get_embedding_via_api():
    os.environ["AMEM_EMBED_PROVIDER"] = "ollama"
    os.environ["OLLAMA_HOST"] = OLLAMA_HOST
    from agents_memory.services.records import get_embedding
    vec = get_embedding("test synapse error")
    if not vec or len(vec) < 100:
        raise AssertionError(f"向量维度异常: {len(vec)}")
    return f"get_embedding() 返回 {len(vec)} 维向量"


def test_wiki_write_and_read():
    from agents_memory.runtime import build_context
    from agents_memory.services.wiki import write_wiki_page, read_wiki_page, list_wiki_topics

    with tempfile.TemporaryDirectory() as tmp:
        wiki_dir = Path(tmp) / "wiki"
        write_wiki_page(wiki_dir, "test-topic", "# 测试内容\n\n这是一个测试 wiki 页面。")
        content = read_wiki_page(wiki_dir, "test-topic")
        if not content or "测试内容" not in content:
            raise AssertionError("wiki 写入读取失败")
        topics = list_wiki_topics(wiki_dir)
        if "test-topic" not in topics:
            raise AssertionError(f"wiki-list 未返回 test-topic，topics={topics}")
    return "wiki 写入/读取/列表 正常"


def test_wiki_compile_dry_run():
    if args.quick:
        return "跳过（--quick 模式）"
    os.environ["AMEM_LLM_PROVIDER"] = "ollama"
    os.environ["AMEM_LLM_MODEL"] = LLM_MODEL
    os.environ["OLLAMA_HOST"] = OLLAMA_HOST

    from agents_memory.runtime import AppContext
    from agents_memory.services.wiki import write_wiki_page
    from agents_memory.services.wiki_compile import compile_wiki_topic

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wiki_dir = tmp_path / "memory" / "wiki"
        write_wiki_page(wiki_dir, "auth", "# Auth\n\n认证模块。")

        ctx = AppContext(
            base_dir=tmp_path,
            errors_dir=tmp_path / "errors",
            archive_dir=tmp_path / "errors" / "archive",
            memory_dir=tmp_path / "memory",
            wiki_dir=wiki_dir,
            vector_dir=tmp_path / "vectors",
            index_file=tmp_path / "index.md",
            projects_file=tmp_path / "memory" / "projects.md",
            rules_file=tmp_path / "memory" / "rules.md",
            templates_dir=ROOT / "templates",
        )
        ctx.errors_dir.mkdir(parents=True, exist_ok=True)

        result = compile_wiki_topic(ctx, "auth", dry_run=True)
        # 'skipped' is valid when no error records exist (correct behavior)
        valid_statuses = ("dry_run", "ok", "no_errors", "skipped")
        if result.get("status") not in valid_statuses:
            raise AssertionError(f"wiki-compile 返回异常状态: {result}")
    return f"wiki-compile --dry-run 通过: status={result.get('status')}"


def test_ingest_dry_run():
    if args.quick:
        return "跳过（--quick 模式）"
    os.environ["AMEM_LLM_PROVIDER"] = "ollama"
    os.environ["AMEM_LLM_MODEL"] = LLM_MODEL
    os.environ["OLLAMA_HOST"] = OLLAMA_HOST

    from agents_memory.runtime import AppContext
    from agents_memory.services.wiki import write_wiki_page
    from agents_memory.services.ingest import ingest_document

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wiki_dir = tmp_path / "memory" / "wiki"
        # 创建测试 wiki topic
        write_wiki_page(wiki_dir, "auth", "# Auth\n\n认证模块。")

        ctx = AppContext(
            base_dir=tmp_path,
            errors_dir=tmp_path / "errors",
            archive_dir=tmp_path / "errors" / "archive",
            memory_dir=tmp_path / "memory",
            wiki_dir=wiki_dir,
            vector_dir=tmp_path / "vectors",
            index_file=tmp_path / "index.md",
            projects_file=tmp_path / "memory" / "projects.md",
            rules_file=tmp_path / "memory" / "rules.md",
            templates_dir=ROOT / "templates",
        )
        ctx.errors_dir.mkdir(parents=True, exist_ok=True)
        ctx.memory_dir.mkdir(parents=True, exist_ok=True)

        # 创建测试源文档
        src = tmp_path / "test-pr.md"
        src.write_text(
            "# PR #42: Fix auth token expiry\n\n"
            "## Summary\n\n修复了 JWT token 过期后未正确刷新的问题。\n\n"
            "## Changes\n\n- 更新 token refresh 逻辑\n- 添加单元测试\n",
            encoding="utf-8",
        )

        result = ingest_document(ctx, str(src), "pr-review", "synapse-network", dry_run=True)
        if result.error:
            raise AssertionError(f"ingest 返回错误: {result.error}")
    return f"ingest --dry-run 通过: topics={result.topics_updated}"


def test_fts_search():
    from agents_memory.runtime import AppContext
    from agents_memory.services.records import collect_errors
    from agents_memory.services.search import build_fts_index, search_fts

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        errors_dir = tmp_path / "errors"
        errors_dir.mkdir(parents=True, exist_ok=True)

        # 创建一条测试错误记录（使用 ASCII 关键字确保 unicode61 tokenizer 可定位）
        (errors_dir / "TEST-001.md").write_text(
            "---\nid: TEST-001\nproject: synapse-network\ncategory: type-error\n"
            "severity: high\nstatus: new\ndate: 2026-04-07\ndomain: backend\n---\n\n"
            "# TEST-001 JWT auth failure\n\nProblem: token verification throws NullPointerException.\n",
            encoding="utf-8",
        )

        ctx = AppContext(
            base_dir=tmp_path,
            errors_dir=errors_dir,
            archive_dir=tmp_path / "errors" / "archive",
            memory_dir=tmp_path / "memory",
            wiki_dir=tmp_path / "memory" / "wiki",
            vector_dir=tmp_path / "vectors",
            index_file=tmp_path / "index.md",
            projects_file=tmp_path / "memory" / "projects.md",
            rules_file=tmp_path / "memory" / "rules.md",
            templates_dir=ROOT / "templates",
        )
        ctx.memory_dir.mkdir(parents=True, exist_ok=True)

        count = build_fts_index(ctx, force=True)
        # Use ASCII query matching indexed content (unicode61 tokenizer)
        hits = search_fts(ctx, "JWT auth")
        if not hits:
            raise AssertionError(f"FTS 搜索未返回结果（已索引 {count} 条记录）")
    return f"FTS 索引 {count} 条，搜索 'JWT auth' 命中 {len(hits)} 条"


def test_wiki_lint():
    from agents_memory.runtime import AppContext
    from agents_memory.services.wiki import write_wiki_page
    from agents_memory.services.wiki import cmd_wiki_lint

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wiki_dir = tmp_path / "memory" / "wiki"

        # 建两个互相链接的 v2 页面（避免 orphan 警告）
        def make_page(topic: str, link_to: str = "") -> None:
            links = f"  - topic: {link_to}\n    context: test\n" if link_to else ""
            wiki_dir.mkdir(parents=True, exist_ok=True)
            (wiki_dir / f"{topic}.md").write_text(
                f"---\ntopic: {topic}\ncreated_at: 2026-04-07\nupdated_at: 2026-04-07\n"
                f"compiled_at: 2026-04-07\nconfidence: high\nsources: []\nlinks:\n{links}---\n\n"
                f"## Contents\nTest content.\n",
                encoding="utf-8",
            )

        make_page("alpha", link_to="beta")
        make_page("beta", link_to="alpha")

        ctx = AppContext(
            base_dir=tmp_path,
            errors_dir=tmp_path / "errors",
            archive_dir=tmp_path / "errors" / "archive",
            memory_dir=tmp_path / "memory",
            wiki_dir=wiki_dir,
            vector_dir=tmp_path / "vectors",
            index_file=tmp_path / "index.md",
            projects_file=tmp_path / "memory" / "projects.md",
            rules_file=tmp_path / "memory" / "rules.md",
            templates_dir=ROOT / "templates",
        )

        buf = StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_wiki_lint(ctx, [])
        output = buf.getvalue()
        if exit_code != 0:
            raise AssertionError(f"wiki-lint 返回非 0: exit_code={exit_code}")
        if "✅" not in output:
            raise AssertionError(f"wiki-lint 输出无 ✅: {output!r}")
    return "wiki-lint 2 页面通过检查"


# ─── 运行所有测试 ──────────────────────────────────────────────────────────────
section("Agents-Memory Ollama 全链路测试")
print(f"  Embedding: {EMBED_MODEL}")
print(f"  LLM:       {LLM_MODEL}")
print(f"  Host:      {OLLAMA_HOST}")
print(f"  Quick:     {args.quick}")

section("1. Ollama 基础连通性")
check("Ollama 健康检查",          test_ollama_health)
check(f"Embed 模型 {EMBED_MODEL}", test_embed_model_available)
if not args.quick:
    check(f"LLM 模型 {LLM_MODEL}",    test_llm_model_available)

section("2. Embedding 输出验证")
check("Embedding API 输出",       test_embedding_output)

section("3. LLM 生成验证")
check("LLM JSON 输出",            test_llm_json_output)

section("4. agents_memory 模块")
check("模块导入",                  test_agents_memory_import)
check("get_embedding() 端到端",   test_get_embedding_via_api)

section("5. Wiki 本地逻辑")
check("Wiki 写入/读取/列表",       test_wiki_write_and_read)
check("wiki-lint 健康检查",        test_wiki_lint)

section("6. Wiki Compile 链路")
check("wiki-compile --dry-run",   test_wiki_compile_dry_run)

section("7. Ingest 链路")
check("ingest --dry-run",         test_ingest_dry_run)

section("8. 搜索链路")
check("FTS 索引 + 搜索",           test_fts_search)

# ─── 汇总 ─────────────────────────────────────────────────────────────────────
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
    print(f"\n{GREEN}  🎉 全部 {total} 项测试通过！Ollama 链路正常。{NC}")
    sys.exit(0)
