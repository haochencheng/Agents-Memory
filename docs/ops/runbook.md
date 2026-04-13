---
created_at: 2026-03-26
updated_at: 2026-04-13
doc_status: active
---

# 运维与故障处理

---

## 边界说明

`docs/ops.md` 负责：

1. 日常运维命令和例行维护。
2. 日志、索引、Qdrant、备份、排障。
3. 运行期问题的定位、恢复与清理。

`docs/getting-started.md` 负责：

1. 本仓库如何首次安装与启动。
2. 本地依赖如何准备。
3. 本地 CLI、MCP、日志、Qdrant 如何做首次验证。

`docs/integration.md` 负责：

1. 目标项目如何接入。
2. 用户执行哪些命令完成接入。
3. 接入后如何验证是否生效。

`docs/commands.md` 负责：

1. 命令签名与参数形态。
2. 所有 CLI 的总表与分组参考。

换句话说：

```text
ops.md              = 日常运维与故障处理
getting-started.md  = 本仓库首次安装与启动
integration.md      = 外部项目接入流程
commands.md         = 命令参考
```

---

## 日常操作

### 调试日志

所有关键操作默认都会写到：

```bash
tail -f logs/agents-memory.log
```

重点会记录：
- `amem register` 的项目接入过程
- `.github/instructions/*` 或 `.vscode/mcp.json` 的文件写入
- `amem sync` 对其他项目的规则同步结果
- MCP tools 调用和错误记录写入

如果需要把日志同时打印到终端：

```bash
export AGENTS_MEMORY_LOG_STDERR=1
export AGENTS_MEMORY_LOG_LEVEL=DEBUG
```

### MCP 直接读取 refactor hotspots

当 agent 已通过 MCP 接入时，可以直接调用 `memory_get_refactor_hotspots(project_root)` 获取结构化 hotspot 列表；每个 hotspot 都会返回稳定的 `rank_token`。随后优先调用 `memory_init_refactor_bundle(project_root, hotspot_index, hotspot_token, task_slug, dry_run)` 并传入 `hotspot_token` 生成执行 bundle，无需依赖 `docs/plans/refactor-watch.md`，也不会因为 hotspot 排序变化而指向漂移。

### 记录新错误

```bash
cd /path/to/Agents-Memory
python3 scripts/memory.py new
```

交互式填写项目、类别、根因、修复、提炼规则。完成后自动更新 `index.md`。

### 查看活跃错误

```bash
python3 scripts/memory.py list
```

### 统计分布

```bash
python3 scripts/memory.py stats
```

### 搜索错误

```bash
# 1. 关键词搜索（< 200 条，零依赖）
python3 scripts/memory.py search pydantic

# 2. 混合搜索 — FTS BM25 + 向量相似度（推荐，零额外依赖）
python3 scripts/memory.py fts-index          # 首次构建 FTS 索引（stale 时自动重建）
python3 scripts/memory.py hybrid-search "TypeScript 类型收窄失效"
python3 scripts/memory.py hybrid-search "timeout" --limit 5 --fts-only  # 仅 FTS
python3 scripts/memory.py hybrid-search "oom" --json                     # JSON 输出

# 3. 纯向量搜索（需先 embed，≥ 200 条后）
python3 scripts/memory.py vsearch "TypeScript 类型收窄失效"
```

### 将错误升级为 instruction 规则

```bash
python3 scripts/memory.py promote 2026-03-26-spec2flow-001
# 输入目标 instruction 文件路径，然后手动把 "提炼规则" 节内容追加到该文件的 Gotchas 段
```

### 归档旧记录

```bash
# 归档 90 天以上且 repeat_count=1 的 reviewed/promoted 记录
python3 scripts/memory.py archive
```

### Ingest 文档摄取

将 PR 描述、会议记录、架构决策记录等结构化写入记忆系统：

```bash
# Ingest PR 描述
python3 scripts/memory.py ingest docs/pr-123.md --type pr-review --project synapse-network

# Ingest 会议记录
python3 scripts/memory.py ingest docs/meeting-2026-04-07.md --type meeting

# Ingest 架构决策
python3 scripts/memory.py ingest docs/adr-042.md --type decision --project backend

# 预览（不写入）
python3 scripts/memory.py ingest docs/pr.md --type pr-review --dry-run

# 查看摄取日志
python3 scripts/memory.py ingest dummy --log
```

支持类型：`pr-review`、`meeting`、`decision`、`code-review`
摄取日志存储于：`memory/ingest_log.jsonl`

### Legacy Workflow 迁移

当旧版本把 `task_completion` / `requirement_completion` 错写进 `errors/` 后，可用一次性迁移脚本把它们物理搬到 `memory/workflow_records/`：

```bash
# 先预览本次会迁哪些文件
python3 scripts/migrate_workflow_records.py --dry-run

# 正式迁移全部 legacy workflow records
python3 scripts/migrate_workflow_records.py

# 只迁前 20 条，适合分批处理
python3 scripts/migrate_workflow_records.py --limit 20
```

说明：
- 只会处理 `source_type` 属于 workflow 的 legacy 文件
- 真正的 `error_record` 不会被移动
- 重复执行是安全的；已迁过的记录会自动跳过

### Wiki 维护

```bash
# Wiki 结构与交叉链接检查
python3 scripts/memory.py wiki-lint

# 生成 wiki 合成摘要（调用 LLM）
python3 scripts/memory.py wiki-compile python --dry-run

# 为历史 wiki 页面补 metadata / candidate links
python3 scripts/backfill_wiki_metadata.py --dry-run
python3 scripts/backfill_wiki_metadata.py --project synapse-network
python3 scripts/backfill_wiki_metadata.py --json
```

说明：
- backfill 会补齐 `project / source_path / doc_type / tags / links`
- 历史页面若存在旧 frontmatter `sources:`，会优先复用它推断 `source_path`
- backfill / onboarding 现在还会解析正文中的显式 Markdown 文档引用，并把它们补成 `links`
- 重复执行是安全的；已经具备 metadata 且无新增 links 的页面会自动跳过

### Scheduler 运行与恢复

Scheduler 现在已经从“平铺 3 条任务”升级成“任务组 + 批次日志”模型，并会把配置和执行结果写到本地磁盘：

```text
memory/scheduler_tasks.json   # 任务组定义（task_groups）
memory/scheduler_runs.jsonl   # 每次调度触发的 batch + steps
memory/check_runs.jsonl       # 兼容旧索引的 checks 数据
memory/workflow_records/*.md  # scheduler_check workflow 记录
```

行为说明：
- API 服务启动时会自动恢复 `memory/scheduler_tasks.json`
- 后台 runtime 会扫描到期任务组，并按顺序执行 `docs` / `profile` / `plan`
- 一次 cron 触发会生成一个 batch，batch 下面固定有 3 个 step
- 每个任务组只保留最近 200 次 batch；workflow 审计记录不受这个上限影响
- `/api/scheduler/task-groups` 是主接口，`/api/scheduler/tasks` 只保留兼容映射
- 每次执行同时写入 checks 与 workflow

排障时可直接查看：

```bash
cat memory/scheduler_tasks.json
tail -n 20 memory/scheduler_runs.jsonl
tail -n 20 memory/check_runs.jsonl
rg -n "source_type: scheduler_check" memory/workflow_records
```

如果任务创建成功但一直不执行，优先检查：
- 项目是否仍在 `memory/projects.md` 里注册
- `cron_expr` 是否是合法的 5 段 cron
- 注册项目根目录是否仍然存在
- 任务组是否被暂停，或 `next_run_at` 是否为空
- 最近的 `scheduler_runs.jsonl` 是否持续写入新 batch

Scheduler 表单里会直接显示常用 cron 示例。快速参考：

```text
分钟 小时 日 月 星期
5 * * * *       每小时第 5 分钟
0 * * * *       每小时整点
0 2 * * *       每天凌晨 2 点
30 9 * * 1-5    工作日 09:30
0 8 * * 1       每周一 08:00
```

`bash scripts/web-start.sh api` 现在还会校验运行中的 API 合同：
- 发现 `10100` 上已是兼容的 Agents-Memory API 时，会直接复用并写回 `.web_api.pid`
- 发现端口上是旧版 `agents_memory.web.api`，但缺少 `/api/scheduler/task-groups` 时，会自动替换旧进程
- 如果端口被其他非 Agents-Memory 进程占用，脚本会停止并提示人工处理，避免误杀别的服务

---

## 向量搜索启用（记录达到 200 条后）

### 1. 安装依赖

```bash
pip install lancedb openai pyarrow
```

### 2. Embedding 提供方选择

| 提供方 | 命令 | 说明 |
|--------|------|------|
| OpenAI（默认） | `export AMEM_EMBED_PROVIDER=openai` | 需要 `OPENAI_API_KEY`，1536d |
| Ollama（本地） | `export AMEM_EMBED_PROVIDER=ollama` | 本地运行，免费，768d |

**使用 OpenAI：**

```bash
export AMEM_EMBED_PROVIDER=openai   # 或省略（默认）
export OPENAI_API_KEY=sk-...
pip install lancedb openai pyarrow
```

**使用 Ollama nomic-embed-text（推荐本地）：**

```bash
# 启动 Ollama 并拉取模型（见下文 Ollama Docker 章节）
export AMEM_EMBED_PROVIDER=ollama
export OLLAMA_HOST=http://localhost:11434   # 默认，可省略
pip install lancedb pyarrow                # 无需 openai
```

### 3. 构建本地向量索引

```bash
python3 scripts/memory.py embed
# 全量 embed 所有 errors/*.md，写入 vectors/ 目录（gitignored）
```

### 4. 使用语义搜索

```bash
python3 scripts/memory.py vsearch "balance 并发扣款死锁"
python3 scripts/memory.py vsearch "filter type guard typescript" 10   # 返回 top 10
```

---

## Ollama Docker — 本地 LLM + Embedding

### 首次启动

```bash
cd /path/to/Agents-Memory/docker
mkdir -p data/ollama
docker-compose up -d ollama
```

验证启动：

```bash
curl http://localhost:11434/api/tags
# → {"models":[...]}
```

### 拉取模型

```bash
# Embedding 模型（必须，274MB）
docker exec -it agents-memory-ollama ollama pull nomic-embed-text

# LLM 用于 wiki-compile / ingest 合成（可选）
docker exec -it agents-memory-ollama ollama pull qwen2.5:7b   # 4.7GB，推荐
docker exec -it agents-memory-ollama ollama pull llama3.2     # 2GB，轻量
```

或通过 REST API 拉取（适合脚本化）：

```bash
curl http://localhost:11434/api/pull -d '{"name":"nomic-embed-text"}'
```

### 验证 Embedding

```bash
export AMEM_EMBED_PROVIDER=ollama
python3.12 -c "from agents_memory.services.records import get_embedding; v=get_embedding('hello'); print(len(v))"
# → 768
```

### 停止 / 清理

```bash
docker-compose stop ollama           # 停止但保留模型数据
docker-compose down                  # 停容器，保留 volume 数据
docker-compose down -v               # 清除所有数据（包括已拉取的模型！）
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AMEM_EMBED_PROVIDER` | `openai` | `openai` \| `ollama` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API 地址 |
| `OLLAMA_PORT` | `11434` | docker-compose 端口 |

---

## 向量数据库（Qdrant Docker）— 多 Agent 共享场景

### 首次启动

```bash
cd /path/to/Agents-Memory/docker
mkdir -p data/qdrant
cp .env.example .env
docker-compose up -d
```

验证启动：

```bash
curl http://localhost:6333/readyz
# → {"status":"ok"}
```

Web Dashboard：[http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### 迁移本地 LanceDB → Qdrant

```bash
pip install qdrant-client
python3 scripts/memory.py to-qdrant
```

输出示例：

```
✅ 迁移完成：47 条记录 → Qdrant (localhost:6333/agents-memory)
Qdrant Dashboard: http://localhost:6333/dashboard
```

### 停止 / 数据清除

```bash
cd docker
docker-compose down           # 保留数据
docker-compose down -v        # 清除所有向量数据（危险！）
```

### 环境变量（覆盖默认值）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `QDRANT_HOST` | `localhost` | Qdrant 主机地址 |
| `QDRANT_PORT` | `6333` | Qdrant REST 端口 |
| `QDRANT_COLLECTION` | `agents-memory` | 集合名称 |
| `OPENAI_API_KEY` | — | OpenAI embed 模式必须 |
| `AMEM_EMBED_PROVIDER` | `openai` | 切换 `ollama` > 使用本地 embedding |

---

## 与已有 PostgreSQL 的关系

本项目的 PostgreSQL（已在 Docker 中运行）**不用于**向量存储。

| 用途 | 存储方式 |
|------|----------|
| 错误记录（结构化文本）| `errors/*.md`（本地运行数据，默认不进入公开仓库）|
| Workflow 记录 | `memory/workflow_records/*.md`（完成 task / requirement 的执行证据）|
| Wiki 知识库 | `memory/wiki/*.md`（编译真相 + 时间线）|
| 向量索引（本地）| `vectors/` LanceDB（gitignored）|
| FTS 全文索引 | `vectors/fts.db` SQLite（自动维护）|
| 摄取日志 | `memory/ingest_log.jsonl`（追加写，gitignored）|
| 向量索引（共享）| Qdrant（单独容器）|
| 本地 LLM + Embedding | Ollama（单独容器，可选）|
| 业务数据库 | 已有 PostgreSQL（无需改动）|

两个 Docker 容器互不干扰，网络隔离。

---

## 备份策略

| 数据 | 备份方式 | 频率 |
|------|---------|------|
| `errors/` | 私有备份 / 私有仓库 / 本地磁盘快照 | 每次新增记录后 |
| `memory/rules.md` | 私有备份 / 私有仓库 | 每次 promote 后 |
| `vectors/` | 不备份（可从 errors/ 重新 embed）| — |
| Qdrant `data/qdrant/` | 本地目录挂载，自动持久化 | Docker volume |

重建向量索引只需：

```bash
python3 scripts/memory.py embed
python3 scripts/memory.py to-qdrant   # 如果使用 Qdrant
```

---

## 常见问题

**Q: embed 命令花费多少钱？**  
A: 按 `text-embedding-3-small` 定价 $0.02/1M tokens。200 条记录（每条约 1000 tokens）= 约 $0.004，基本可以忽略。

**Q: 向量索引需要每次 AI 启动时重建吗？**  
A: 不需要。`vectors/` 目录持久化在本地。只有新增记录后运行一次 `embed` 增量更新即可。当前版本是全量重建，如需增量更新可在 LanceDB 表上做 `upsert`。

**Q: LanceDB 和 Qdrant 同时维护会不会不一致？**  
A: `to-qdrant` 是单向迁移命令，从 LanceDB 推送到 Qdrant。建议选择一个作为主索引：  
- 单机开发 → 只用 LanceDB  
- 多人协作 → 迁移到 Qdrant，废弃 LanceDB

**Q: 搜索结果 Score 代表什么？**  
A: LanceDB 返回 `_distance`（余弦距离），脚本转换为 `1 - distance` 作为相似度。Score = 1.0 表示完全匹配，Score < 0.5 表示相关性较低。

---

## 使用规则

后续新增内容时，遵守下面 4 条：

1. 如果是在说明本仓库如何首次安装、启动、首次验证，写入 `docs/getting-started.md`。
2. 如果是在说明日常维护、日志排查、索引修复、Qdrant 生命周期、备份恢复，写入 `docs/ops.md`。
3. 如果是在说明目标项目如何接入与验证，写入 `docs/integration.md`。
4. 如果是在列命令签名、参数、输出形态，写入 `docs/commands.md`。
