---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# Agents-Memory 架构分析与优化方案

> 参考：Karpathy LLM Wiki（5K+ stars）、Garry Tan GBrain（220 stars）两篇最新 gist，
> 对照当前系统做差距分析，给出可落地的优化路径。

---

## 一、当前系统架构全图

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                            CONSUMERS（消费端）                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  GitHub Copilot          Claude Code           任意 MCP 客户端               ║
║  (via copilot-instr.)   (via AGENTS.md)        (via mcp.json)               ║
║        │                     │                       │                       ║
║        └──────────┬──────────┘                       │                       ║
║                   │                                  │                       ║
║     ┌─────────────▼──────────────┐    ┌─────────────▼──────────────┐        ║
║     │  Bridge Instructions       │    │  MCP Server (FastMCP)      │        ║
║     │  .github/instructions/     │    │  agents_memory/mcp_app.py  │        ║
║     │  agents-memory-bridge.md   │    │  stdio transport           │        ║
║     └─────────────┬──────────────┘    └─────────────┬──────────────┘        ║
║                   │                                  │                       ║
║                   └─────────────┬────────────────────┘                       ║
║                                 │                                             ║
╠═════════════════════════════════▼═════════════════════════════════════════════╣
║                         CLI / Services 层                                    ║
║                                                                              ║
║  scripts/amem (amem CLI)  ←→  agents_memory/app.py                          ║
║                                      │                                       ║
║           ┌──────────────────────────┼─────────────────────────┐            ║
║           │                          │                          │            ║
║    commands/records           commands/vector           commands/wiki        ║
║    commands/planning          commands/profiles         commands/workflows   ║
║    commands/integration       commands/validation                            ║
║           │                          │                          │            ║
║    services/records.py       services/vector.py        services/wiki.py     ║
║    services/planning.py      services/profiles.py      services/validation/ ║
║    services/integration*.py                                                  ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                           存储层（Storage）                                   ║
║                                                                              ║
║   errors/*.md          memory/rules.md        memory/projects.md            ║
║   ─────────────        ──────────────         ──────────────────            ║
║   YAML frontmatter     领域编码规则            注册项目列表                   ║
║   + body text          (by domain)                                           ║
║                                                                              ║
║   memory/wiki/*.md     vector/ (LanceDB)      Qdrant (Docker)               ║
║   ─────────────────    ─────────────────      ─────────────────             ║
║   主题知识页           本地向量索引             多 Agent 共享                 ║
║   (topic + frontmatter) <200条用LanceDB       向量索引                       ║
║                                                                              ║
║   index.md             errors/archive/*.md    profiles/*.yaml               ║
║   ──────────           ───────────────────    ──────────────                ║
║   导航索引              90天归档               项目原型模板                   ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                       集成层（Integration）                                   ║
║                                                                              ║
║  doctor / onboarding-state.json      bridge-install / copilot-setup         ║
║  plan-init / start-task / validate   profile-apply / standards-sync          ║
║  enable / bootstrap / register       refactor-bundle / close-task            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 数据流：错误记录 → 规则提升

```
Agent 遇到问题
    │
    ▼
memory_record_error()  →  errors/AME-xxx.md (YAML frontmatter + body)
    │
    ▼
amem promote <id>  →  memory/rules.md 追加规则条目
    │
    ▼
amem sync  →  把规则写入注册项目的 bridge instructions
    │
    ▼
Agent 下次启动读取 bridge instructions → 规则生效
```

### 数据流：向量搜索

```
amem embed  →  遍历 errors/*.md  →  OpenAI text-embedding-3-small
                                  │
                          <200条 → LanceDB (本地)
                          ≥200条 → Qdrant (Docker, 多 Agent 共享)
                                  │
amem vsearch <query>  →  向量相似度检索  →  返回 Top-K 记录
memory_wiki_query()   →  wiki/*.md 关键词搜索  →  返回摘要
```

---

## 二、与 Karpathy LLM Wiki / GBrain 的对比

| 维度 | Karpathy LLM Wiki | Garry Tan GBrain | Agents-Memory（当前） |
|------|------------------|-----------------|----------------------|
| **核心理念** | LLM 主动维护 Wiki，知识编译一次复用多次 | SQLite 单文件，compiled truth + timeline 分线 | 错误记录驱动规则提升，MCP 提供工具 |
| **存储** | Markdown 文件目录 | SQLite（FTS5 + 向量 BLOB 同库） | Markdown + LanceDB + Qdrant（分散） |
| **全文搜索** | 依赖外部工具（qmd/BM25） | FTS5 内置（SQLite） | 关键词 grep（无 FTS） |
| **向量搜索** | 可选（qmd） | JS cosine，同 SQLite DB | LanceDB / Qdrant（独立）|
| **LLM 主动合成** | ✅ LLM 写 Wiki，ingest/lint/query 全流程 | ✅ LLM 驱动 ingest → compiled truth 更新 | ❌ LLM 只是工具调用方，无主动合成 |
| **Compiled Truth / Timeline 分离** | ❌ 无此概念（但有 index + log） | ✅ 核心设计 | ❌ 无 |
| **交叉引用** | wiki links（`[[Page]]`） | links 表 + backlinks | ❌ 无（wiki 孤岛） |
| **Ingest 流水线** | ✅ 结构化（meeting/article/doc） | ✅ source_type + source_ref 记录 | ❌ 无（只有 wiki-ingest，功能弱）|
| **MCP 支持** | 可选（gbrain serve） | ✅ MCP native | ✅ FastMCP，已接入 |
| **多 Agent 共享** | 文件系统共享 | 单文件 scp/rsync | ✅ Qdrant（Docker）|
| **知识维护（lint）** | ✅ 矛盾检测 + 孤页 + 过期 | ✅ maintain skill | ❌ 无知识健康检查 |
| **Planning/Onboarding** | ❌ | ❌ | ✅（系统独有的亮点）|
| **Profile 项目原型** | ❌ | ❌ | ✅（系统独有的亮点）|

---

## 三、差距分析：我们缺什么

### 3.1 最大缺口：知识是静态的，没有 LLM 主动合成

**现状**：Wiki 页面由人或 agent 手写写入（`wiki-ingest`），没有"LLM 读入源材料 → 主动更新相关页面"的流水线。  
**Karpathy 的核心洞察**：知识必须被"编译"——LLM 不是在查询时重新发现，而是持续维护一份已综合好的 wiki。  
**影响**：错误记录和规则之间的关联是手动的（`promote`），没有自动从错误中提炼 pattern → 更新 wiki。

### 3.2 搜索层：有向量，缺全文（FTS）

**现状**：关键词搜索是 grep（`cmd_search`），无 FTS 索引，大量记录时慢且不精准。  
**GBrain 洞察**：FTS5 + 向量 在同一数据库，单次 query 可并行 fan-out 两种检索再合并排名。

### 3.3 Wiki 是孤岛，无交叉引用

**现状**：`memory/wiki/*.md` 之间没有链接，没有 backlinks，没有关联 errors/rules 的指针。  
**GBrain 洞察**：links 表 + backlinks 命令，知识图谱才能复利增长。

### 3.4 无 Compiled Truth / Timeline 分离

**现状**：错误记录 = YAML frontmatter + body，body 既是 "结论" 也是 "证据"，没有分线。  
**GBrain 洞察**："结论"（compiled_truth）需要被 LLM 重写更新，"时间线"（timeline）append-only。  
**影响**：错误记录随 Agent 推理时间增长不断过时，没有机制强迫 Agent 更新结论。

### 3.5 无 Ingest 流水线

**现状**：只有 `wiki-ingest`（把一个 md 文件导入 wiki），没有结构化 ingest（PR review、meeting notes、决策记录）。  
**副作用**：实际发生的工程决策没有进入记忆系统，knowledge base 增长慢。

---

## 四、优化方案（分优先级）

### P0：LLM 主动合成（最高 ROI）

**新增命令**：`amem wiki-compile [--topic <name>] [--scope errors|rules|all]`

```
流程：
1. 读取最近 N 条 errors（或指定 scope 的源材料）
2. 读取现有相关 wiki 页面（关键词匹配）
3. 调用 LLM（见第五节）：
   - 识别 error pattern → 提炼 rule
   - 更新 wiki 页的 compiled_truth（结论区）
   - append timeline 条目（append-only）
4. 写回 wiki 页面
5. 更新 wiki 向量索引
```

**新增 MCP tool**：`memory_wiki_compile(scope, topic)`

**Wiki 页面格式升级**（借鉴 GBrain）：

```markdown
---
topic: finance-safety
compiled_at: 2026-04-07
confidence: high
sources: [AME-001, AME-007, AME-023]
---

<!-- COMPILED TRUTH: LLM 维护，整体重写 -->
## 结论（Compiled Truth）
> 最新综合评估：...

## 已知 Pattern
- ...

---

<!-- TIMELINE: append-only，人/agent 追加 -->
## 时间线

- **2026-04-07** | AME-023 — 发现 decimals 处理漏洞，触发 finance-safety rule
- **2026-03-20** | AME-007 — 首次记录 USDT 精度问题
```

---

### P1：混合搜索（FTS + 向量）

**现状**：搜索是 grep（O(n) 字符串扫描）。  
**方案 A（轻量）**：引入 Python `whoosh` 库建本地 FTS 索引，与向量搜索结果合并排名。  
**方案 B（推荐，对齐 GBrain）**：迁移错误记录到 SQLite（保留 markdown 导出），用 FTS5 + vector BLOB 同库查询。

```python
# 混合搜索排名公式（对齐 Karpathy query skill）
combined_score = fts_score * 0.4 + vector_similarity * 0.6
# 近期记录加权
if days_since_created < 30:
    combined_score += 0.1
```

**新增命令**：`amem hybrid-search <query> [--limit 10]`  
**升级 MCP tool**：`memory_search()` 统一入口，内部自动路由 FTS / 向量 / 关键词。

---

### P2：Wiki 交叉引用 & 知识图谱

**新增字段**（wiki 页面 frontmatter）：

```yaml
links:
  - topic: smart-contract-errors
    context: "Reentrancy 与 finance-safety 有重叠"
  - topic: python-typing
    context: "类型错误经常导致精度丢失"
```

**新增命令**：
- `amem wiki-link <from-topic> <to-topic> [--context "..."]`
- `amem wiki-backlinks <topic>`
- `amem wiki-lint` — 孤岛页面、过期结论、缺失交叉引用检查

---

### P3：结构化 Ingest 流水线

```
amem ingest <file> [--type pr-review|meeting|decision|code-review] [--project <id>]
```

流程：LLM 读取源文档 → 识别 entity（错误 pattern、决策、规则）→ 更新相关 wiki 页 → 追加 timeline → 记录 ingest_log

---

### P4：知识维护（Lint）

```
amem wiki-maintain [--check contradictions|orphans|stale|missing-links]
```

对齐 Karpathy lint 操作：
- **矛盾检测**：两个 wiki 页对同一 pattern 结论不一致
- **孤岛页面**：无 inbound links 的 wiki 页
- **过期结论**：compiled_truth 最后更新 > 30 天但 errors 有新记录
- **缺失引用**：wiki 页提到 errors ID 但没有 sources 字段

---

## 五、本地 LLM vs 第三方 LLM？

### 结论：**使用第三方 LLM（Claude / GPT-4o），不建议现阶段本地部署**

| 需求 | 本地 LLM（Ollama/llama.cpp） | 第三方 LLM（Claude/GPT-4o） |
|------|----------------------------|---------------------------|
| wiki-compile（主动合成） | ⚠️ 7B 模型质量差，hallucination 多；需 ≥32B | ✅ 高质量，推理能力强 |
| FTS + 向量混合排名 | 不需要 LLM | 不需要 LLM |
| 向量 embedding | ✅ nomic-embed-text（本地，免费） | ✅ text-embedding-3-small（$0.02/1M，极便宜）|
| ingest 解析 | ⚠️ 小模型准确率低 | ✅ 稳定，结构化输出好 |
| 延迟 | ✅ 无网络，低延迟 | ⚠️ API 调用延迟，但 wiki-compile 不是实时场景 |
| 成本 | 硬件成本（GPU/内存） | 极低（wiki-compile 调用次数少，每次 <$0.01）|
| 隐私 | ✅ 完全本地 | ⚠️ 数据出境（代码内容）|

### 推荐策略：**Embedding 本地 + 合成用 Claude API**

```
embedding（高频）:
  → nomic-embed-text via Ollama（本地，免费，1.5B 模型足够）
  → 降低对 OpenAI billing 的依赖

wiki-compile / ingest / lint（低频、高质量要求）:
  → Claude claude-sonnet-4-5 via API（最佳性价比推理）
  → 或 GPT-4o-mini（更便宜，质量略低）

fallback / 离线场景:
  → Qwen2.5-7B-Instruct via Ollama（推理质量在小模型里最强）
  → 仅用于 lint 类简单任务
```

### 配置方案

```python
# agents_memory/constants.py 新增
LLM_SYNTHESIS_MODEL = os.getenv("AMEM_LLM_MODEL", "claude-sonnet-4-5")
LLM_SYNTHESIS_PROVIDER = os.getenv("AMEM_LLM_PROVIDER", "anthropic")  # anthropic | openai | ollama
EMBED_MODEL_LOCAL = "nomic-embed-text"  # Ollama 本地 embedding
EMBED_PROVIDER = os.getenv("AMEM_EMBED_PROVIDER", "openai")  # openai | ollama
```

---

## 六、实施优先级路线图

```
Phase 1（1-2天）: Wiki Compiled Truth 格式升级
  - wiki 页面增加 compiled_truth / timeline 分区
  - wiki-compile 命令（调用 Claude API 合成）
  - memory_wiki_compile MCP tool

Phase 2（2-3天）: 混合搜索
  - 引入 whoosh FTS 本地索引（轻量，纯 Python）
  - hybrid-search 命令 + MCP tool 统一入口
  - Embedding 切换到 nomic-embed-text（Ollama，本地）

Phase 3（1天）: Wiki 交叉引用
  - wiki frontmatter links 字段
  - wiki-link / wiki-backlinks 命令

Phase 4（2天）: Ingest 流水线
  - amem ingest 命令（支持 PR/meeting/decision 类型）
  - 结构化 ingest_log

Phase 5（1天）: Wiki Lint
  - wiki-maintain 命令
  - MCP tool: memory_wiki_lint()
```

---

## 七、系统独有优势（不要丢）

与 GBrain / Karpathy Wiki 相比，Agents-Memory 有两个独特优势：

1. **Planning + Onboarding 流水线**：`plan-init / start-task / close-task / validate` 是其他系统没有的，是真正的"工程 OS"层。
2. **Profile 项目原型系统**：`profiles/*.yaml` + `profile-apply` 可以把组织标准自动安装到新项目，这是团队协作的乘数效应。

**这两块不需要改**，只需在 wiki-compile 流水线里让 LLM 能读取 planning artifacts 作为 ingest 源。

---

## 八、五阶段功能 CLI / MCP 集成矩阵

> Phase 1–5 已全部落地。下表是每个功能的 CLI 命令、MCP 工具、服务实现及测试入口的完整对照。

### Phase 1 — Wiki Compiled Truth / wiki-compile

| 维度 | 实现 |
|------|------|
| **CLI 命令** | `amem wiki-compile <topic> [--scope errors\|rules\|all] [--recent-n N] [--dry-run] [--provider P] [--model M]` |
| **CLI 注册** | `agents_memory/commands/wiki.py` → `wiki-compile` |
| **MCP 工具** | `memory_wiki_compile(topic, scope, recent_n, dry_run)` |
| **服务层** | `agents_memory/services/wiki_compile.py` — `compile_wiki_topic()` |
| **Wiki 页格式** | compiled_truth 区（LLM 重写）+ timeline 区（append-only）用 `---` 分隔 |
| **LLM 路由** | `AMEM_LLM_PROVIDER` 环境变量：`anthropic`（默认）`\|` `openai` `\|` `ollama` |
| **测试文件** | `tests/test_wiki_compile.py`，`tests/test_mcp_phases.py::TestMCPWikiCompile` |

### Phase 2 — 混合搜索（FTS + 向量）

| 维度 | 实现 |
|------|------|
| **CLI 命令 1** | `amem fts-index [--force]` — 构建 / 重建 SQLite FTS5 索引 |
| **CLI 命令 2** | `amem hybrid-search <query> [--limit N] [--fts-only] [--json]` — FTS + 向量混合查询 |
| **CLI 注册** | `agents_memory/commands/search.py` → `fts-index`, `hybrid-search` |
| **MCP 工具** | `memory_search(query, limit, mode)` — mode: `hybrid`（默认）`\|` `fts` `\|` `vector` |
| **服务层** | `agents_memory/services/search.py` — `build_fts_index()`, `search_fts()`, `hybrid_search()` |
| **评分公式** | `combined = fts×0.4 + vec×0.6`；近 30 天 +0.1 boost |
| **FTS 存储** | `vectors/fts.db`（SQLite FTS5 + unicode61 分词器，gitignored）|
| **测试文件** | `tests/test_search_service.py`，`tests/test_mcp_phases.py::TestMCPSearch` |

### Phase 3 — Wiki 交叉引用

| 维度 | 实现 |
|------|------|
| **CLI 命令 1** | `amem wiki-link <from> <to> [--context "说明"]` — 幂等有向链接 |
| **CLI 命令 2** | `amem wiki-backlinks <topic>` — 反向链接查询（O(n)扫描）|
| **CLI 注册** | `agents_memory/commands/wiki.py` → `wiki-link`, `wiki-backlinks` |
| **MCP 工具** | 通过 `memory_wiki_update` 更新 frontmatter links 字段 |
| **服务层** | `agents_memory/services/wiki.py` — `get_wiki_links()`, `set_wiki_links()`, `cmd_wiki_link()`, `cmd_wiki_backlinks()` |
| **存储格式** | frontmatter `links:` YAML list，每项含 `topic`（必须）和 `context`（可选）|
| **测试文件** | `tests/test_wiki_service.py::TestGetWikiLinks`,`TestUpsertLinkEntry` |

### Phase 4 — Ingest 结构化摄取流水线

| 维度 | 实现 |
|------|------|
| **CLI 命令** | `amem ingest <file> --type <type> [--project <id>] [--dry-run] [--log] [--provider P] [--model M]` |
| **CLI 注册** | `agents_memory/commands/ingest.py` → `ingest` |
| **MCP 工具** | `memory_ingest(content, source_type, source_ref, project, dry_run)` |
| **服务层** | `agents_memory/services/ingest.py` — `ingest_document()`, `build_ingest_prompt()`, `read_ingest_log()` |
| **支持类型** | `pr-review`, `meeting`, `decision`, `code-review` |
| **日志格式** | `memory/ingest_log.jsonl`（JSONL，append-only，UTC ISO 8601）|
| **LLM 输出** | `{summary, topics, timeline_entry, compiled_truth_update(可选)}` |
| **测试文件** | `tests/test_ingest_service.py`，`tests/test_mcp_phases.py::TestMCPIngest` |

### Phase 5 — Wiki Lint + MCP 工具完整化

| 维度 | 实现 |
|------|------|
| **CLI 命令** | `amem wiki-lint [--check orphans\|stale\|missing-links\|all]` |
| **CLI 注册** | `agents_memory/commands/wiki.py` → `wiki-lint` |
| **MCP 工具** | `memory_wiki_lint(check)` — 捕获 stdout 并返回 |
| **服务层** | `agents_memory/services/wiki.py` — `cmd_wiki_lint()`, `_lint_orphans()`, `_lint_stale()`, `_lint_missing_links()` |
| **孤立检测** | 入链为 0 的 topic → `[orphan]` |
| **过期检测** | `compiled_at` 超过 30 天 → `[stale]` |
| **缺失链接** | body 提及其他 topic 名但 `links:` 未记录 → `[missing-link]` |
| **返回值** | 始终 exit 0；问题通过 stdout 输出 |
| **测试文件** | `tests/test_wiki_service.py::TestLintOrphans,TestLintStale`，`tests/test_mcp_phases.py::TestMCPWikiLint` |

### MCP 工具总表（截至 Phase 5）

| MCP 工具 | 对应 CLI | Phase |
|----------|---------|-------|
| `memory_get_index` | — | core |
| `memory_get_onboarding_state` | `doctor` | core |
| `memory_get_onboarding_next_action` | `do-next` | core |
| `memory_execute_onboarding_next_action` | `do-next` | core |
| `memory_get_refactor_hotspots` | `doctor` | core |
| `memory_init_refactor_bundle` | `start-task` | core |
| `memory_get_rules` | `list` | core |
| `memory_get_error` | `list` | core |
| `memory_record_error` | `new` | core |
| `memory_increment_repeat` | — | core |
| `memory_list_projects` | `list` | core |
| `memory_sync_stats` | `stats` | core |
| `memory_wiki_list` | `wiki-list` | core |
| `memory_wiki_query` | `wiki-query` | core |
| `memory_wiki_update` | `wiki-ingest` | core |
| `memory_wiki_compile` | `wiki-compile` | Phase 1 |
| `memory_search` | `fts-index` + `hybrid-search` | Phase 2 |
| `memory_wiki_lint` | `wiki-lint` | Phase 5 |
| `memory_ingest` | `ingest` | Phase 4 |

---

## 参考

- [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — 增量知识编译模式
- [Garry Tan GBrain](https://gist.github.com/garrytan/49c88e83cf8d7ae95e087426368809cb) — SQLite + FTS5 + embedding 单文件架构
