# 本地启动与运维指南

> 从零搭建 Agents-Memory 本地环境，5 分钟内完成。

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

CLI 的 `new / list / stats / search / register / copilot-setup / agent-list / agent-setup / bridge-install / mcp-setup / doctor / plan-init / plan-check / profile-list / profile-show / profile-apply / profile-diff / standards-sync / profile-check / docs-check / sync / archive / update-index` 命令使用纯标准库，**无需任何额外 pip 安装**。直接运行：

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

### 向量搜索（≥ 200 条记录时可选）

```bash
pip install lancedb openai pyarrow
export OPENAI_API_KEY=sk-...
```

### Qdrant 多 Agent 共享（可选）

```bash
pip install qdrant-client
cd docker && docker-compose up -d
```

---

---

## 4. 一键启动（推荐）

```bash
bash scripts/start.sh          # 检查依赖 + 启动 Qdrant + 打印验证提示
bash scripts/start.sh status   # 检查所有服务运行状态
bash scripts/start.sh stop     # 停止 Qdrant（MCP Server 由 VS Code 管理）
bash scripts/start.sh --qdrant # 只启动 Qdrant
bash scripts/start.sh --mcp    # 前台调试 MCP Server（stdio 交互模式）
```

`start.sh` 会自动完成：
- 检查 Python 3.12 和 `mcp` 包是否就绪（缺失自动安装）
- 创建 `docker/data/qdrant/` 目录并启动 Qdrant 容器
- 等待 Qdrant 健康检查通过
- 打印 VS Code 验证指引

---

## 5. 验证基础 CLI

```bash
python3 scripts/memory.py stats
# 输出: 各类别错误数量统计

python3 scripts/memory.py list
# 输出: 所有 new/reviewed 状态的记录

python3 scripts/memory.py search pydantic
# 输出: 包含 "pydantic" 的所有错误记录

python3 scripts/memory.py embed
# 输出: 构建 / 更新本地 LanceDB 向量索引

python3 scripts/memory.py vsearch "type guard"
# 输出: 语义搜索结果（需先 embed）

python3 scripts/memory.py doctor .
# 输出: 当前项目的接入健康检查（按 Core / Planning / Integration / Optional 分组，并附带 Summary / Remediation / Action Sequence / Onboarding Runbook / Project Bootstrap Checklist）

python3 scripts/memory.py doctor . --write-checklist --write-state
# 输出: 在 docs/plans/bootstrap-checklist.md 和 .agents-memory/onboarding-state.json 导出 onboarding 工件
# 提示: agent 可优先读取 onboarding-state.json 中的 recommended_next_command / recommended_verify_command

python3 scripts/memory.py onboarding-execute .
# 输出: 执行当前第一条 onboarding action，随后验证并把 execution_history / last_verified_action 回写到 onboarding-state.json

python3 scripts/memory.py onboarding-bundle .
# 输出: 根据 onboarding-state.json 生成 docs/plans/onboarding-*/ onboarding task bundle
# 提示: 重复运行会增量刷新 bundle 里的受管 onboarding sections

python3 scripts/memory.py plan-init "shared engineering brain task" .
# 输出: 在 docs/plans/<slug>/ 生成 spec / plan / task-graph / validation bundle

python3 scripts/memory.py plan-check .
# 输出: 校验 docs/plans/ 下 planning bundle 的完整性和关键语义

python3 scripts/memory.py profile-list
# 输出: 当前内置 profile 列表

python3 scripts/memory.py profile-show python-service
# 输出: python-service profile 的 standards / templates / bootstrap 详情

python3 scripts/memory.py profile-apply python-service . --dry-run
# 输出: profile 将创建的目录、标准文件和模板写入预览

python3 scripts/memory.py standards-sync .
# 输出: 将 profile 管理的组织标准文件同步到当前项目

python3 scripts/memory.py profile-check .
# 输出: 当前项目已安装 profile 的一致性检查结果

python3 scripts/memory.py docs-check .
# 输出: 文档入口、contract/test/policy 漂移、明显过期表述检查

python3 scripts/memory.py to-qdrant
# 输出: 把本地向量索引迁移到共享 Qdrant（可选）
```

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

## 7. 日常运维命令速查

### 记录新错误（交互式）

```bash
python3 scripts/memory.py new
```

### 升级为规则（重复出现 ≥ 2 次时）

```bash
python3 scripts/memory.py promote 2026-03-26-synapse-001
# 交互输入目标 instruction 文件路径
```

### 将规则同步到所有已注册项目

```bash
python3 scripts/memory.py sync
# 幂等——已同步的规则会自动跳过
```

### 归档旧记录

```bash
python3 scripts/memory.py archive
# 归档 90 天以上且 repeat_count=1 的 reviewed/promoted 记录
```

### 重新生成 index.md（热区摘要）

```bash
python3 scripts/memory.py update-index
```

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

**Q: 修改了错误记录后 index.md 没更新？**

```bash
python3 scripts/memory.py update-index
```

**Q: 搜索无结果但我确定有相关记录？**

记录数 < 200 时使用关键词搜索，需用文件中实际出现的词汇：

```bash
python3 scripts/memory.py search alias    # 而不是 "别名"
python3 scripts/memory.py search Pydantic
```
