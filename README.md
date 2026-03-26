# Agents-Memory

**目标**：让 所有AI Agent 在构建代码时能持续自我进化——通过结构化错误记录 → 规则提炼 → instruction 写入，形成闭环升级机制，所有agent共享记忆。

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

## 开源仓库与本地运行数据

公开仓库只提交代码、模板和文档；下面这些是真实运行时数据，默认不再提交：

```text
index.md
memory/projects.md
memory/rules.md
errors/*.md
.vscode/mcp.json
logs/
vectors/
```

首次运行 CLI 时，会自动从 `templates/` 生成公开安全的本地默认文件：

```text
templates/index.example.md
templates/projects.example.md
templates/rules.example.md
templates/mcp.example.json
```

---

## 目录结构

```
Agents-Memory/
├── index.md                     # 本地生成，gitignored
├── memory/
│   ├── projects.md              # 本地生成，gitignored
│   └── rules.md                 # 本地生成，gitignored
├── errors/                      # 本地错误记录目录，*.md gitignored
├── templates/
├── scripts/                    # thin wrappers
└── agents_memory/              # 真正的运行时与业务逻辑
    ├── app.py                  # CLI 总入口
    ├── mcp_app.py              # MCP Server 总入口
    ├── runtime.py              # 上下文与路径解析
    ├── commands/               # 命令分发层
    ├── services/               # 业务服务层
    └── integrations/agents/    # agent adapter 插件层
```

详细拆分见 `docs/modular-architecture.md`。

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

# 检查某个项目是否完整接入 Agents-Memory
python scripts/memory.py doctor spec2flow

# 给已注册项目补装仓库级 Copilot 自动激活
python scripts/memory.py copilot-setup spec2flow

# 将错误标记为已升级到 instruction
python scripts/memory.py promote 2026-03-26-spec2flow-001

# 检查文档入口、命令漂移和明显过期内容
python scripts/memory.py docs-check .

# 归档 90 天以上无重复的记录
python scripts/memory.py archive

# 重新生成 index.md 统计
python scripts/memory.py update-index
```

---

## 调试日志

项目现在会把关键操作写入统一日志文件：

```text
logs/agents-memory.log
```

默认会记录：

1. CLI 命令开始 / 结束
2. `register` 新项目接入
3. `bridge-install` 写入 bridge instruction
4. `mcp-setup` 写入或合并 `.vscode/mcp.json`
5. `sync` 向其他项目同步规则时的跳过 / 写入结果
6. MCP tools 调用，如 `memory_get_index`、`memory_record_error`、`memory_increment_repeat`
7. 所有关键文件更新动作（错误记录文件、项目注册表、index、目标 instruction 文件）

常用查看方式：

```bash
tail -f logs/agents-memory.log
grep "sync_rule" logs/agents-memory.log
grep "project_id=synapse-network" logs/agents-memory.log
```

可选环境变量：

```bash
export AGENTS_MEMORY_LOG_LEVEL=DEBUG
export AGENTS_MEMORY_LOG_STDERR=1
```

`AGENTS_MEMORY_LOG_STDERR=1` 会在保留文件日志的同时，把同样内容打印到 stderr，方便本地调试 CLI / MCP server。

如果你准备开源，请不要把 `logs/`、`index.md`、`memory/*.md`、`errors/*.md`、`.vscode/mcp.json` 推到公开仓库。

## Copilot 自动激活

`amem register` 现在会同时安装三层接入：

1. `.github/copilot-instructions.md`：仓库级默认协议
2. `.github/instructions/agents-memory-bridge.instructions.md`：代码任务补强协议
3. `.vscode/mcp.json`：MCP 工具执行层

设计说明见 `docs/copilot-auto-activation.md`。

## 多 Agent 插件架构

项目现在已经从单文件 CLI 重构成插件式结构：

1. `github-copilot` adapter：已实现
2. `chatgpt` adapter：scaffold
3. `claude` adapter：scaffold

可用命令：

```bash
python scripts/memory.py agent-list
python scripts/memory.py agent-setup github-copilot /path/to/project
```

这层设计让后续扩展新 agent 时，不需要再把 `register`、`doctor`、MCP、错误记录逻辑重新拆一遍。

## Foundation Hardening

项目当前已经开始进入“先打地基，再扩系统”的阶段。基础治理方案见：

1. `docs/ai-engineering-operating-system.md`
2. `docs/foundation-hardening.md`
3. `standards/`

第一批正式纳入仓库的代码规范包括：

1. TDD
2. DRY
3. 代码复用优先
4. 可插拔优先
5. 模块化边界清晰
6. 文档、代码、测试同步更新

当前最小验证入口：

```bash
python3.12 -m unittest discover -s tests -p 'test_*.py'
python3.12 -m py_compile $(find agents_memory scripts -name '*.py' -print)
```

---

## Search Backend Roadmap

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
