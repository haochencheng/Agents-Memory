---
created_at: 2026-03-26
updated_at: 2026-03-27
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
# 关键词搜索（< 200 条记录时）
python3 scripts/memory.py search pydantic

# 语义搜索（≥ 200 条后）
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

---

## 向量搜索启用（记录达到 200 条后）

### 1. 安装依赖

```bash
pip install lancedb openai pyarrow
```

### 2. 设置 OpenAI Key

```bash
export OPENAI_API_KEY=sk-...
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
| `OPENAI_API_KEY` | — | embed 命令必须 |

---

## 与已有 PostgreSQL 的关系

本项目的 PostgreSQL（已在 Docker 中运行）**不用于**向量存储。

| 用途 | 存储方式 |
|------|----------|
| 错误记录（结构化文本）| `errors/*.md`（本地运行数据，默认不进入公开仓库）|
| 向量索引（本地）| `vectors/` LanceDB（gitignored）|
| 向量索引（共享）| Qdrant（单独容器）|
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
