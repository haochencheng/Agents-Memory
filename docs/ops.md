# 运维文档

## 日常操作

### MCP 直接读取 refactor hotspots

当 agent 已通过 MCP 接入时，可以直接调用 `memory_get_refactor_hotspots(project_root)` 获取结构化 hotspot 列表，再按序调用 `memory_init_refactor_bundle(project_root, hotspot_index, task_slug, dry_run)` 生成执行 bundle，无需依赖 `docs/plans/refactor-watch.md`。

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
