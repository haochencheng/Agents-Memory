#!/usr/bin/env python3
"""
Agents-Memory CLI — 错误记录管理工具

用法:
  python3 memory.py new               # 交互式创建新错误记录
  python3 memory.py list              # 列出所有 new/reviewed 状态的记录
  python3 memory.py stats             # 统计各类别错误数量
  python3 memory.py search <keyword>  # 关键词搜索（< 200 条默认策略）
  python3 memory.py vsearch <query>   # 语义向量搜索（需先运行 embed）
  python3 memory.py embed             # 构建 / 更新本地 LanceDB 向量索引
  python3 memory.py promote <id>      # 将错误记录升级为 instruction 规则
  python3 memory.py archive           # 归档 90 天以上且无重复的记录
  python3 memory.py update-index      # 重新生成 index.md 统计数字
  python3 memory.py to-qdrant         # 迁移向量索引到 Qdrant（多 Agent 共享）

依赖安装:
  基础（关键词搜索）: 无需额外依赖，纯标准库
  向量搜索（本地）:   pip install lancedb openai pyarrow
  Qdrant 迁移:       pip install qdrant-client
"""

import os
import sys
import shutil
from datetime import date, timedelta
from pathlib import Path

# ─── 路径常量 ────────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent.parent
ERRORS_DIR  = BASE_DIR / "errors"
ARCHIVE_DIR = BASE_DIR / "errors" / "archive"
MEMORY_DIR  = BASE_DIR / "memory"
VECTOR_DIR  = BASE_DIR / "vectors"   # LanceDB 本地文件目录（gitignored）
INDEX_FILE  = BASE_DIR / "index.md"

# 超过此数量自动推荐向量搜索
VECTOR_THRESHOLD = 200

# OpenAI embedding 模型（1536 维）
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM   = 1536

# Qdrant 连接（docker-compose 默认）
QDRANT_HOST       = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT       = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "agents-memory")

# ─── 枚举常量 ────────────────────────────────────────────────────────────────

CATEGORIES = [
    "type-error", "logic-error", "finance-safety", "arch-violation",
    "test-failure", "docs-drift", "config-error", "build-error",
    "runtime-error", "security",
]

PROJECTS = [
    "synapse-network", "spec2flow", "provider-service",
    "gateway", "admin-front", "gateway-admin", "other",
]

DOMAINS = ["finance", "frontend", "python", "docs", "config", "infra", "other"]



# ─── 公共工具 ────────────────────────────────────────────────────────────────

def parse_frontmatter(filepath: Path) -> dict:
    """解析 Markdown 文件头部 YAML frontmatter（仅支持 key: value 格式）。"""
    meta: dict = {}
    in_front = False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if line == "---":
                if not in_front:
                    in_front = True
                    continue
                else:
                    break
            if in_front and ": " in line:
                key, _, value = line.partition(": ")
                meta[key.strip()] = value.strip().strip('"')
    return meta


def read_body(filepath: Path) -> str:
    """读取 Markdown 正文（frontmatter 之后的内容）。"""
    lines = filepath.read_text(encoding="utf-8").splitlines()
    body_lines: list[str] = []
    fence_count = 0
    for line in lines:
        if line.strip() == "---":
            fence_count += 1
            continue
        if fence_count >= 2:
            body_lines.append(line)
    return "\n".join(body_lines)


def collect_errors(status_filter: list[str] | None = None) -> list[dict]:
    records = []
    for filepath in sorted(ERRORS_DIR.glob("*.md")):
        meta = parse_frontmatter(filepath)
        if not meta:
            continue
        if status_filter and meta.get("status") not in status_filter:
            continue
        meta["_file"] = str(filepath)
        records.append(meta)
    return records


def total_error_count() -> int:
    return len(list(ERRORS_DIR.glob("*.md")))


# ─── 基础命令 ────────────────────────────────────────────────────────────────

def cmd_list():
    records = collect_errors(status_filter=["new", "reviewed"])
    if not records:
        print("No active error records found.")
        return
    print(f"\n{'ID':<38} {'Project':<20} {'Category':<18} {'Sev':<10} Status")
    print("-" * 98)
    for r in records:
        print(
            f"{r.get('id',''):<38} {r.get('project',''):<20} "
            f"{r.get('category',''):<18} {r.get('severity',''):<10} {r.get('status','')}"
        )
    print(f"\nTotal: {len(records)} active records")


def cmd_stats():
    records = collect_errors()
    if not records:
        print("No records found.")
        return
    from collections import Counter
    cats     = Counter(r.get("category", "unknown") for r in records)
    projs    = Counter(r.get("project",  "unknown") for r in records)
    statuses = Counter(r.get("status",   "unknown") for r in records)
    print("\n=== By Category ===")
    for cat, count in cats.most_common():
        print(f"  {cat:<22} {count}")
    print("\n=== By Project ===")
    for proj, count in projs.most_common():
        print(f"  {proj:<22} {count}")
    print("\n=== By Status ===")
    for status, count in statuses.most_common():
        print(f"  {status:<22} {count}")
    count = total_error_count()
    print(f"\nTotal records: {count}")
    if count >= VECTOR_THRESHOLD:
        print(f"\n⚡ 记录数已超过 {VECTOR_THRESHOLD}，建议切换到向量搜索：")
        print("   python3 scripts/memory.py embed")
        print("   python3 scripts/memory.py vsearch <query>")


def cmd_search(keyword: str):
    """关键词全文搜索（< 200 条的默认策略）。"""
    keyword = keyword.lower()
    matches = []
    for filepath in sorted(ERRORS_DIR.glob("*.md")):
        content = filepath.read_text(encoding="utf-8").lower()
        if keyword in content:
            meta = parse_frontmatter(filepath)
            matches.append((filepath.name, meta))
    if not matches:
        print(f"No records matching '{keyword}'")
        return
    print(f"\nFound {len(matches)} match(es) for '{keyword}':\n")
    for fname, meta in matches:
        print(f"  {fname}")
        print(f"    project={meta.get('project','')}  category={meta.get('category','')}  status={meta.get('status','')}")


def cmd_promote(record_id: str):
    matched = None
    for filepath in ERRORS_DIR.glob("*.md"):
        meta = parse_frontmatter(filepath)
        if meta.get("id") == record_id:
            matched = filepath
            break
    if not matched:
        print(f"Record '{record_id}' not found.")
        return
    instruction_path = input(
        "Write instruction file path (e.g., .github/instructions/python.instructions.md): "
    ).strip()
    content = matched.read_text(encoding="utf-8")
    content = content.replace("status: reviewed", "status: promoted")
    content = content.replace('promoted_to: ""', f'promoted_to: "{instruction_path}"')
    matched.write_text(content, encoding="utf-8")
    print(f"Promoted {record_id} → {instruction_path}")
    cmd_update_index()


def cmd_archive():
    cutoff = date.today() - timedelta(days=90)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archived = 0
    for filepath in list(ERRORS_DIR.glob("*.md")):
        meta = parse_frontmatter(filepath)
        if meta.get("status") not in ("reviewed", "promoted"):
            continue
        try:
            record_date = date.fromisoformat(meta.get("date", ""))
        except ValueError:
            continue
        if record_date < cutoff and int(meta.get("repeat_count", "1")) <= 1:
            shutil.move(str(filepath), str(ARCHIVE_DIR / filepath.name))
            archived += 1
            print(f"  Archived: {filepath.name}")
    print(f"\n{archived} record(s) archived.")
    if archived:
        cmd_update_index()


def cmd_update_index():
    active   = collect_errors(status_filter=["new", "reviewed"])
    promoted = collect_errors(status_filter=["promoted"])
    total    = total_error_count()

    from collections import Counter
    cats      = Counter(r.get("category", "") for r in active)
    top3_cats = cats.most_common(3)
    recent_promoted = sorted(promoted, key=lambda r: r.get("date", ""), reverse=True)[:3]

    top3_cats_str = "\n".join(
        f"| `{cat}` | {count} |" for cat, count in top3_cats
    ) or "| _暂无_ | - |"

    recent_rules_str = "\n".join(
        f"- **{r.get('id','')}**: {r.get('promoted_to','')}"
        for r in recent_promoted
    ) or "_暂无_"

    vector_hint = ""
    if total >= VECTOR_THRESHOLD:
        vector_hint = (
            f"\n> ⚡ 记录数 ({total}) 已超过 {VECTOR_THRESHOLD}，"
            f"已启用向量语义搜索。运行 `python3 scripts/memory.py embed` 更新索引。\n"
        )

    search_cmd = "vsearch" if total >= VECTOR_THRESHOLD else "search "

    index_content = f"""# Agent Memory Index — Hot Tier

> 这是 Agent 每次启动时**必须加载**的唯一文件，严格控制在 400 tokens 以内。
> 其余所有内容通过 semantic search 或按需读取。
{vector_hint}
## 当前活跃规则总数

| 类别 | 数量 | 文件 |
|------|------|------|
| 错误模式 (errors) | {total} | `errors/` |
| 升级规则 (promoted) | {len(promoted)} | `memory/rules.md` |

## 最近升级的规则（Top 3）

{recent_rules_str}

## 最高频错误类别（Top 3）

| Category | Count |
|----------|-------|
{top3_cats_str}

## 检索指引

- 写代码前：查 `memory/rules.md` 匹配项目领域规则
- 代码出错后：`python3 scripts/memory.py {search_cmd} <keyword>`
- 写 Finance 代码：额外加载 `memory/rules.md`（Finance 段）
- 做文档变更：检查 docs-drift 类别的错误记录

## 快速提交新错误

```
errors/YYYY-MM-DD-<project>-<sequence>.md
```

格式见 `schema/error-record.md`
"""
    INDEX_FILE.write_text(index_content, encoding="utf-8")
    print("index.md updated.")


def cmd_new():
    print("\n=== New Error Record ===\n")
    today = date.today().isoformat()
    print(f"Projects: {', '.join(PROJECTS)}")
    project = input("Project: ").strip() or "other"
    existing = list(ERRORS_DIR.glob(f"{today}-{project}-*.md"))
    seq = str(len(existing) + 1).zfill(3)
    record_id = f"{today}-{project}-{seq}"
    filename = ERRORS_DIR / f"{record_id}.md"
    print(f"\nCategories: {', '.join(CATEGORIES)}")
    category = input("Category: ").strip() or "runtime-error"
    print(f"\nDomains: {', '.join(DOMAINS)}")
    domain   = input("Domain: ").strip() or "other"
    severity = input("Severity (critical/warning/info) [warning]: ").strip() or "warning"
    task       = input("What were you trying to do? (1 line): ").strip()
    error_desc = input("What went wrong? (1 line): ").strip()
    root_cause = input("Why did it happen? (1 line): ").strip()
    fix        = input("How was it fixed? (1 line): ").strip()
    rule       = input("Prevention rule (1-2 sentences): ").strip()
    content = f"""---
id: {record_id}
date: {today}
project: {project}
domain: {domain}
category: {category}
severity: {severity}
status: new
promoted_to: ""
repeat_count: 1
tags: []
---

## 错误上下文

**任务目标：**
{task}

**出错文件 / 位置：**
<!-- 填写文件路径 -->

## 错误描述

{error_desc}

## 根因分析

{root_cause}

## 修复方案

{fix}

## 提炼规则

{rule}

## 关联

<!-- 关联记录 ID 或 instruction 文件 -->
"""
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    filename.write_text(content, encoding="utf-8")
    print(f"\nCreated: {filename}")
    cmd_update_index()


# ─── 向量搜索 — LanceDB（本地，无服务端）──────────────────────────────────────

def _build_record_text(meta: dict, filepath: Path) -> str:
    """把 frontmatter + 正文拼成 embedding 用的文本，截断到 3000 字符。"""
    header = " ".join(filter(None, [
        meta.get("category", ""),
        meta.get("project", ""),
        meta.get("domain", ""),
        meta.get("severity", ""),
    ]))
    body = read_body(filepath)
    return f"{header}\n{body}"[:3000]


def get_embedding(text: str) -> list[float]:
    """调用 OpenAI text-embedding-3-small。需要 OPENAI_API_KEY 环境变量。"""
    try:
        import openai
    except ImportError:
        print("请先安装 openai: pip install openai")
        sys.exit(1)
    client = openai.OpenAI()
    response = client.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding


def cmd_embed():
    """构建 / 更新本地 LanceDB 向量索引。需要：pip install lancedb openai pyarrow"""
    try:
        import lancedb
    except ImportError:
        print("请先安装依赖：pip install lancedb openai pyarrow")
        sys.exit(1)

    all_files = sorted(ERRORS_DIR.glob("*.md"))
    if ARCHIVE_DIR.exists():
        all_files += sorted(ARCHIVE_DIR.glob("*.md"))

    if not all_files:
        print("No error records to embed.")
        return

    records_raw = [(parse_frontmatter(f), f) for f in all_files if parse_frontmatter(f)]
    print(f"Embedding {len(records_raw)} records using {EMBED_MODEL}...")

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(VECTOR_DIR))

    rows = []
    for i, (meta, filepath) in enumerate(records_raw, 1):
        text   = _build_record_text(meta, filepath)
        vector = get_embedding(text)
        rows.append({
            "id":       meta.get("id", filepath.stem),
            "project":  meta.get("project", ""),
            "category": meta.get("category", ""),
            "domain":   meta.get("domain", ""),
            "severity": meta.get("severity", ""),
            "status":   meta.get("status", ""),
            "filepath": str(filepath),
            "text":     text,
            "vector":   vector,
        })
        print(f"  [{i}/{len(records_raw)}] {meta.get('id', filepath.stem)}")

    # 全量重建
    if "errors" in db.table_names():
        db.drop_table("errors")
    db.create_table("errors", data=rows)
    print(f"\nVector index built: {len(rows)} records → {VECTOR_DIR}/errors.lance")
    cmd_update_index()


def cmd_vsearch(query: str, top_k: int = 5):
    """
    语义向量搜索。
    - 若 LanceDB 不可用或索引未建立，自动回退到关键词搜索。
    - 记录数 < VECTOR_THRESHOLD 时提示使用 search 命令。
    """
    try:
        import lancedb
    except ImportError:
        print("LanceDB 未安装，回退到关键词搜索。安装：pip install lancedb openai pyarrow")
        cmd_search(query)
        return

    if not VECTOR_DIR.exists():
        print("向量索引不存在。请先运行：python3 scripts/memory.py embed")
        print("回退到关键词搜索...\n")
        cmd_search(query)
        return

    db = lancedb.connect(str(VECTOR_DIR))
    if "errors" not in db.table_names():
        print("向量表为空。请先运行：python3 scripts/memory.py embed")
        cmd_search(query)
        return

    count = total_error_count()
    if count < VECTOR_THRESHOLD:
        print(f"当前记录数 ({count}) 未达向量搜索阈值 ({VECTOR_THRESHOLD})，使用关键词搜索。\n")
        cmd_search(query)
        return

    print(f"Semantic search: '{query}'  (top {top_k})\n")
    query_vector = get_embedding(query)
    results = db.open_table("errors").search(query_vector).limit(top_k).to_list()

    if not results:
        print(f"No semantic matches for '{query}'")
        return

    print(f"{'Score':<10} {'ID':<38} {'Project':<20} {'Category':<18} Status")
    print("-" * 100)
    for r in results:
        dist = r.get("_distance", 0.0)
        sim  = max(0.0, 1.0 - dist)
        print(
            f"{sim:<10.4f} {r['id']:<38} {r['project']:<20} "
            f"{r['category']:<18} {r['status']}"
        )


# ─── Qdrant 迁移（多 Agent 共享记忆）─────────────────────────────────────────

def cmd_to_qdrant():
    """
    把本地 LanceDB 向量索引迁移到 Qdrant。
    前提：
      1. 已运行 `python3 scripts/memory.py embed`
      2. Qdrant 已通过 docker/docker-compose.yml 启动
      3. pip install qdrant-client
    """
    try:
        import lancedb
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
    except ImportError:
        print("请先安装：pip install qdrant-client lancedb")
        sys.exit(1)

    if not VECTOR_DIR.exists():
        print("本地 LanceDB 索引不存在。请先运行：python3 scripts/memory.py embed")
        sys.exit(1)

    db = lancedb.connect(str(VECTOR_DIR))
    if "errors" not in db.table_names():
        print("LanceDB 向量表为空，请先运行 embed。")
        sys.exit(1)

    rows = db.open_table("errors").to_list()
    if not rows:
        print("向量表中没有数据。")
        return

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    existing = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION in existing:
        print(f"集合 '{QDRANT_COLLECTION}' 已存在，删除并重建...")
        client.delete_collection(QDRANT_COLLECTION)

    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )

    points = [
        PointStruct(
            id=i,
            vector=row["vector"],
            payload={k: row[k] for k in ("id", "project", "category", "domain", "severity", "status", "filepath")},
        )
        for i, row in enumerate(rows)
    ]

    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"✅ 迁移完成：{len(points)} 条记录 → Qdrant ({QDRANT_HOST}:{QDRANT_PORT}/{QDRANT_COLLECTION})")
    print(f"\nQdrant Dashboard: http://{QDRANT_HOST}:6333/dashboard")


# ─── 入口 ────────────────────────────────────────────────────────────────────

def main():
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    args = sys.argv[1:]

    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "stats":
        cmd_stats()
    elif args[0] == "search":
        cmd_search(" ".join(args[1:]) if len(args) > 1 else "")
    elif args[0] == "vsearch":
        if len(args) < 2:
            print("用法: python3 memory.py vsearch <query>")
        else:
            top_k = int(args[-1]) if args[-1].isdigit() else 5
            query = " ".join(args[1:]) if not args[-1].isdigit() else " ".join(args[1:-1])
            cmd_vsearch(query, top_k)
    elif args[0] == "embed":
        cmd_embed()
    elif args[0] == "to-qdrant":
        cmd_to_qdrant()
    elif args[0] == "promote":
        cmd_promote(args[1]) if len(args) > 1 else print("用法: python3 memory.py promote <id>")
    elif args[0] == "archive":
        cmd_archive()
    elif args[0] == "update-index":
        cmd_update_index()
    elif args[0] == "new":
        cmd_new()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
