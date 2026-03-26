# Agents-Memory

**目标**：让 AI Agent 在构建代码时能持续自我进化——通过结构化错误记录 → 规则提炼 → instruction 写入，形成闭环升级机制。

---

## 设计背景：三个核心问题

### Q1：记录错误会造成每次读取消耗大量 token 吗？

**会，如果你用单文件方案**。解法是分层架构：

```
index.md          ← 热区，始终加载，严格 ≤ 400 tokens
memory/rules.md   ← 温区，按项目领域按需加载
errors/*.md       ← 冷区，通过关键词/语义检索按需加载
```

Agent 每次只加载 `index.md`（400 tokens）。需要时才拉取具体错误记录。
**不是压缩问题，是架构问题**。

---

### Q2：需要引入向量数据库吗？

**取决于规模**：

| 规模 | 方案 | 理由 |
|------|------|------|
| < 200 条记录（当前阶段） | 关键词搜索 + 目录分类 | 零依赖，`python scripts/memory.py search <keyword>` 即可 |
| 200–2000 条 | [LanceDB](https://lancedb.github.io/lancedb/) 本地向量库 | 纯 Python、无服务端、支持语义搜索，嵌入 `text-embedding-3-small` |
| > 2000 条 / 多 Agent 共享 | [Qdrant](https://qdrant.tech/) 或 [Chroma](https://www.trychroma.com/) | 有 HTTP API，支持多进程并发读写 |

**当前无需引入向量数据库**，关键词搜索已经够用。规模到 200 条再迁移，迁移成本极低（结构已设计好）。

---

### Q3：Google TurboQuant 向量压缩适用吗？

**不适用于这个场景**。

TurboQuant（ICLR 2026）解决的是**LLM 推理时 KV Cache 的服务端压缩**：
- 将模型内部的高维 KV 向量从 32bit 压缩到 3bit，不损失精度
- 在 H100 GPU 上实现 8× 注意力计算加速
- 这是 Anthropic/Google 在服务器端运行的底层算法

它**不能**减少你发给 API 的 prompt token 数量。

**真正能帮你减少 token 消耗的方法**：
1. 分层架构（本系统已实现）
2. 把高频规则升级写入 instruction 文件（不需要每次作为 context 传入）
3. 只在需要时通过 `search` 拉取具体错误记录

---

## 目录结构

```
Agents-Memory/
├── index.md                    # 热区：始终加载，≤ 400 tokens
├── schema/
│   └── error-record.md         # 错误记录格式规范
├── errors/
│   ├── YYYY-MM-DD-<project>-<seq>.md   # 错误记录
│   └── archive/                # 90天+无重复的归档记录
├── memory/
│   └── rules.md                # 已升级为规则的提炼内容（温区）
└── scripts/
    └── memory.py               # CLI 管理工具
```

---

## 自我进化闭环

```
AI 写错代码
    ↓
记录到 errors/*.md (status: new)
    ↓
复盘 → 提炼规则 (status: reviewed)
    ↓
repeat_count ≥ 2 或 severity=critical
    ↓
规则写入 .github/instructions/*/Gotchas 段 (status: promoted)
    ↓
下次 AI 写同类代码时 instruction 自动加载
    ↓
错误不再重复
```

这才是真正的"自我进化"——不是靠模型本身学习，而是靠**错误 → 规则 → instruction** 的显式升级机制。

---

## 快速使用

```bash
# 记录一个新错误
python scripts/memory.py new

# 列出所有活跃错误记录
python scripts/memory.py list

# 搜索关键词
python scripts/memory.py search "pydantic"

# 统计错误分布
python scripts/memory.py stats

# 将错误标记为已升级到 instruction
python scripts/memory.py promote 2026-03-26-spec2flow-001

# 归档 90 天以上无重复的记录
python scripts/memory.py archive

# 重新生成 index.md 统计
python scripts/memory.py update-index
```

---

## 未来扩展路径（不需要现在做）

当错误记录超过 200 条后，可以引入本地向量搜索：

```python
# 届时只需加这一层
import lancedb
db = lancedb.connect("./vectors")
table = db.open_table("errors")
results = table.search(query_embedding).limit(5).to_pandas()
```

错误记录的 schema 已经设计好，迁移时只需：
1. `pip install lancedb openai`
2. 跑一次 embedding 脚本把 `errors/*.md` 向量化写入 LanceDB
3. 替换 `cmd_search()` 的实现

现有的所有错误记录文件**不需要改**。
