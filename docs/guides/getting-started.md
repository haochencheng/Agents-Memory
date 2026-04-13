---
created_at: 2026-03-26
updated_at: 2026-04-13
doc_status: active
---

# 本地启动指南

> 从零搭建 Agents-Memory 本地环境，5 分钟内完成。

---

## 边界说明

`docs/getting-started.md` 负责：

1. 本仓库如何克隆、安装、启动。
2. 本地依赖如何准备。
3. 本地 CLI、MCP、日志、Qdrant 如何验证。

`docs/integration.md` 负责：

1. 目标项目如何接入 Agents-Memory。
2. `amem enable` / `register` / `doctor` 的接入路径。
3. 接入后如何验证是否真正生效。

`docs/commands.md` 负责：

1. 所有 CLI 命令的总表与参数参考。

`docs/ops.md` 负责：

1. 日常运维命令和故障处理。
2. 日志、索引、Qdrant、备份与恢复。

换句话说：

```text
getting-started.md  = 本仓库首次安装与启动
integration.md      = 外部项目接入流程
commands.md         = 命令总表
ops.md              = 日常运维与故障处理
```

## 前置条件

| 依赖 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.10+ | MCP Server 要求；推荐 Python 3.12 |
| Git | 任意 | 必须 |
| VS Code | 1.90+ | 使用 MCP 工具集成时必须 |

---

## 1. 克隆仓库

```bash
git clone https://github.com/haochencheng/Agents-Memory.git
cd Agents-Memory
```

---

## 2. 安装 `amem` 全局命令

`amem` 是 Agents-Memory 的全局 CLI，安装后在任意目录可用（无需 cd 到仓库、无需 Python 环境配置）：

```bash
bash scripts/install-cli.sh
```

脚本会自动创建符号链接到 `/opt/homebrew/bin/amem`（macOS）或 `~/.local/bin/amem`（Linux）。

验证安装：
```bash
amem stats
# 输出: 各类别错误数量统计（无需在仓库目录下）
```

> **已安装则跳过此步**。如果 `which amem` 有输出说明已安装。

---

## 3. 安装依赖

### 最小安装（CLI 基础功能，零依赖）

CLI 的 `new / list / stats / search / register / enable / bootstrap / do-next / validate / start-task / copilot-setup / agent-list / agent-setup / bridge-install / mcp-setup / doctor / plan-init / onboarding-bundle / refactor-bundle / plan-check / profile-list / profile-show / profile-apply / profile-diff / standards-sync / profile-check / docs-check / sync / archive / update-index` 命令使用纯标准库，**无需任何额外 pip 安装**。直接运行：

```bash
python3 scripts/memory.py list
```

### MCP Server（让 AI Agent 用工具调用记忆系统）

```bash
# macOS 系统 Python 3.12（推荐）
python3.12 -m pip install mcp --break-system-packages

# 或者使用 venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install mcp
```

验证安装：

```bash
python3.12 -c "from mcp.server.fastmcp import FastMCP; print('OK')"
```

### 向量搜索 — OpenAI（云端，需 API Key）

```bash
pip install lancedb openai pyarrow
export OPENAI_API_KEY=sk-...
```

### 向量搜索 — Ollama nomic-embed-text（本地，免费，推荐）

```bash
# 1. 启动 Ollama（通过 Docker）
mkdir -p docker/data/ollama
cd docker && docker-compose up -d ollama

# 2. 拉取 nomic-embed-text 模型（768 维，体积约 274MB）
docker exec -it agents-memory-ollama ollama pull nomic-embed-text

# 3. 设置 Agents-Memory 使用 Ollama 作为 Embedding 提供方
export AMEM_EMBED_PROVIDER=ollama
# 可选：自定义 Ollama 地址（默认 http://localhost:11434）
# export OLLAMA_HOST=http://localhost:11434

# 4. 验证 Embedding 工作正常
python3.12 -c "from agents_memory.services.records import get_embedding; v=get_embedding('test'); print(len(v), v[:3])"
# 输出: 768 [0.xxx, 0.xxx, 0.xxx]
```

> **本地嵌入 vs 云端嵌入**
> | | nomic-embed-text (Ollama) | text-embedding-3-small (OpenAI) |
> |---|---|---|
> | 费用 | 免费 | $0.02/1M tokens |
> | 维度 | 768d | 1536d |
> | 需要联网 | 否 | 是 |
> | 设置 | `AMEM_EMBED_PROVIDER=ollama` | `OPENAI_API_KEY=...` |

### Qdrant 多 Agent 共享（可选）

```bash
pip install qdrant-client
mkdir -p docker/data/qdrant
cd docker && docker-compose up -d qdrant
```

---

---

## 4. 一键启动（推荐）

```bash
bash scripts/start.sh               # 检查依赖 + 启动 Qdrant + 打印验证提示
bash scripts/start.sh status        # 检查所有服务运行状态
bash scripts/start.sh stop          # 停止 Qdrant / Ollama（MCP Server 由 VS Code 管理）
bash scripts/start.sh restart       # 重启 runtime 服务
bash scripts/start.sh --qdrant      # 只启动 Qdrant
bash scripts/start.sh --ollama      # 只启动 Ollama
bash scripts/start.sh --with-ollama # 启动 Qdrant + Ollama
bash scripts/start.sh --mcp         # 前台调试 MCP Server（stdio 交互模式）
bash scripts/start.sh config        # 查看当前环境配置
bash scripts/start.sh --env staging config --json
```

`start.sh` 会自动完成：
- 检查 Python 3.12 和 `mcp` 包是否就绪（缺失自动安装）
- 创建 `docker/data/qdrant/` 目录并启动 Qdrant 容器
- 等待 Qdrant 健康检查通过
- 打印 VS Code 验证指引

默认启动路径不会再顺带拉起 Ollama，避免在 Docker 代理配置异常时因为 `ollama/ollama` 镜像拉取失败而阻塞 Qdrant。只有显式传入 `--ollama` 或 `--with-ollama` 时才会启动本地 LLM 容器。

脚本现在已经按职责归类：

```text
scripts/runtime/manage.sh   # runtime 主入口
scripts/runtime/restart.sh  # runtime 重启入口
scripts/web/manage.sh       # web 主入口
scripts/web/restart.sh      # web 重启入口
scripts/start.sh            # 兼容旧命令，转发到 runtime/manage.sh
scripts/web-start.sh        # 兼容旧命令，转发到 web/manage.sh
```

环境按 `local / staging / prod` 分层，配置文件位于：

```text
config/environments/local.env
config/environments/staging.env
config/environments/prod.env
```

例如：

```bash
bash scripts/web/manage.sh --env local restart
bash scripts/web/manage.sh --env staging config
bash scripts/runtime/manage.sh --env prod config --json
```

---

## 5. 验证基础 CLI

```bash
python3 scripts/memory.py stats
# 输出: 各类别错误数量统计

python3 scripts/memory.py list
# 输出: 所有 new/reviewed 状态的记录

python3 scripts/memory.py search pydantic
# 输出: 包含 "pydantic" 的所有错误记录

python3 scripts/memory.py fts-index
# 输出: 构建 SQLite FTS5 全文检索索引（零依赖，自动维护）

python3 scripts/memory.py hybrid-search "type guard"
# 输出: 混合搜索（FTS+向量，综合评分排序）

python3 scripts/memory.py embed
# 输出: 构建 / 更新本地 LanceDB 向量索引

python3 scripts/memory.py vsearch "type guard"
# 输出: 语义搜索结果（需先 embed）

python3 scripts/memory.py doctor .
# 输出: 当前仓库的健康检查（按 Core / Planning / Integration / Optional 分组）
# 提示: 如果你是在给“其他项目”做接入验证，完整链路请看 docs/integration.md

python3 scripts/memory.py enable .
# 输出: 命令可执行性 smoke test；目标项目接入链路说明请看 docs/integration.md

python3 scripts/memory.py bootstrap . --dry-run
# 输出: 按顶层 workflow 语义预览接入影响面

python3 scripts/memory.py enable . --dry-run
# 输出: 命令可执行性 smoke test；详细接入预览语义请看 docs/integration.md

python3 scripts/memory.py enable . --full --dry-run --json
# 输出: 命令可执行性 smoke test；agent/CI 接入路径请看 docs/integration.md

python3 scripts/memory.py enable . --full
# 输出: 命令可执行性 smoke test；完整接入行为说明请看 docs/integration.md

python3 scripts/memory.py enable .
# 输出: 本地验证命令存在且可运行；具体接入后副作用请看 docs/integration.md

python3 scripts/memory.py doctor . --write-checklist --write-state
# 输出: 导出本地 health/onboarding 工件；如果你是在接入目标项目，完整解释请看 docs/integration.md

python3 scripts/memory.py onboarding-execute .
# 输出: 本地命令 smoke test；完整 onboarding 接入语义请看 docs/integration.md

python3 scripts/memory.py do-next .
# 输出: 当前 onboarding 的下一步动作、验证命令和后续动作

python3 scripts/memory.py onboarding-bundle .
# 输出: 本地命令 smoke test；bundle 语义请结合 planning 文档阅读

python3 scripts/memory.py refactor-bundle .
# 输出: 本地命令 smoke test；hotspot/refactor 细节见相关 planning 文档

代码规范补充：
1. `standards/python/base.instructions.md` 现在内置“高复杂度必须重构”的评判标准
2. 命中任一硬性条件，或命中三条及以上软性条件，应优先重构后再扩展功能
3. 复杂逻辑如果暂时不能继续拆分，必须补解释性注释，说明关键决策和风险边界

python3 scripts/memory.py plan-init "shared engineering brain task" .
# 输出: 在 docs/plans/<slug>/ 生成 spec / plan / task-graph / validation bundle

python3 scripts/memory.py start-task "shared engineering brain task" .
# 输出: 顶层 workflow 入口；生成 bundle 后会把 active_task 写入 onboarding state

python3 scripts/memory.py plan-check .
# 输出: 校验 docs/plans/ 下 planning bundle 的完整性和关键语义

python3 scripts/memory.py validate .
# 输出: 聚合 docs / profile / planning / doctor 的统一交付门

python3 scripts/memory.py close-task . --slug shared-engineering-brain-task
# 输出: gate 通过后回写 bundle 完成标记，并把 completed task 写回 onboarding state

python3 scripts/memory.py profile-list
# 输出: 当前内置 profile 列表

python3 scripts/memory.py profile-show python-service
# 输出: python-service profile 的 standards / templates / bootstrap / variables / detectors / overlays 详情

python3 scripts/memory.py profile-apply python-service . --dry-run
# 输出: profile 将创建的目录、标准文件和模板写入预览

python3 scripts/memory.py profile-render . --dry-run
# 输出: 基于当前 project facts 预览将被渲染或移除的 project-local overlays

python3 scripts/memory.py standards-sync .
# 输出: 将 profile 管理的组织标准文件、project facts 和 active overlays 同步到当前项目

# 说明: 如果项目已经通过 profile-apply 或 enable --full 安装过 profile，重新执行 enable 也会自动完成同一轮标准刷新

python3 scripts/memory.py profile-check .
# 输出: 当前项目已安装 profile 的 manifest / standards / facts / overlays 一致性检查结果

python3 scripts/memory.py docs-check .
# 输出: 文档入口、contract/test/policy 漂移、明显过期表述检查

python3 scripts/memory.py docs-touch .
# 输出: 自动刷新受管 Markdown 文档的 updated_at，必要时补齐 front matter

python3 scripts/memory.py docs-touch docs/ --dry-run
# 输出: 仅预览 docs/ 目录下哪些文档会被刷新

python3 scripts/memory.py to-qdrant
# 输出: 把本地向量索引迁移到共享 Qdrant（可选）
```

## 使用规则

后续新增内容时，遵守下面 3 条：

1. 如果是在说明本仓库如何首次安装、启动、验证，写入 `docs/getting-started.md`。
2. 如果是在说明目标项目如何接入与排错，写入 `docs/integration.md`。
3. 如果是在说明日志、索引、Qdrant、备份、恢复或日常故障处理，写入 `docs/ops.md`。

---

## 6. 启动 MCP Server（VS Code 集成）

MCP Server 是 AI Agent 调用共享记忆的核心接口。在 VS Code 中使用 GitHub Copilot / Claude 时，它会以 `stdio` 子进程方式自动启动。

### 配置文件（公开示例）

公开仓库提供示例文件 `templates/mcp.example.json`。实际使用时请复制为本地 `.vscode/mcp.json`，或直接对目标项目运行 `amem mcp-setup <project>`：

```json
{
  "servers": {
    "agents-memory": {
      "type": "stdio",
      "command": "python3.12",
      "args": ["/path/to/Agents-Memory/scripts/mcp_server.py"],
      "env": {}
    }
  }
}
```

> **注意**：`args` 中的路径必须改成你的本机绝对路径。

### 验证 MCP Server 启动

在 VS Code 的 Agent / Chat 面板中，输入：

```
调用 memory_get_index() 工具，返回当前 index.md 内容
```

或在终端手动测试（会话模式）：

```bash
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python3.12 scripts/mcp_server.py
```

正常输出应包含 `memory_get_index`, `memory_record_error` 等工具名。

---

## 7. 后续运维入口

完成首次启动后，下面这些内容统一转到 `docs/ops.md`：

1. 调试日志查看与日志级别切换。
2. `new / promote / sync / archive / update-index` 等日常运维命令。
3. 向量索引维护、Qdrant 生命周期管理、备份与恢复。
4. 日常故障处理和运行期 FAQ。

---

## 8. 目录结构说明

```
Agents-Memory/
├── index.md          ← 本地生成的热区摘要，gitignored
├── memory/
│   ├── rules.md      ← 本地生成的温区规则，gitignored
│   └── projects.md   ← 本地生成的项目注册表，gitignored
├── errors/           ← 冷区目录；错误记录文件 `*.md` gitignored
│   └── archive/      ← 90 天以上的归档记录
├── logs/             ← 统一调试日志（agents-memory.log）
├── agents_memory/    ← Python package 主体（app / mcp_app / commands / services / integrations）
├── templates/        ← bridge / copilot / public example 模板
├── scripts/
│   ├── memory.py     ← thin wrapper → agents_memory.app
│   └── mcp_server.py ← thin wrapper → agents_memory.mcp_app
└── .vscode/
  └── mcp.json      ← 本地 VS Code MCP 配置，gitignored
```

首次运行 CLI 时，如果 `index.md`、`memory/projects.md`、`memory/rules.md` 不存在，会自动从 `templates/*.example.*` 生成本地默认文件。

---

## 9. 常见问题

**Q: Python 3.12 不在 PATH 怎么办？**

```bash
# macOS 用 Homebrew 安装
brew install python@3.12
which python3.12  # 应输出 /opt/homebrew/bin/python3.12
```

**Q: MCP Server 在 Claude Desktop 中使用**

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "agents-memory": {
      "command": "python3.12",
      "args": ["/path/to/Agents-Memory/scripts/mcp_server.py"]
    }
  }
}
```

**Q: 运行期日志、索引或搜索问题去哪看？**

A: 这些都属于日常运维与排障，统一见 `docs/ops.md`。
