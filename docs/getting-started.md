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

CLI 的 `new / list / stats / search / register / sync / bridge-install` 命令使用纯标准库，**无需任何额外 pip 安装**。直接运行：

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
```

---

## 6. 启动 MCP Server（VS Code 集成）

MCP Server 是 AI Agent 调用共享记忆的核心接口。在 VS Code 中使用 GitHub Copilot / Claude 时，它会以 `stdio` 子进程方式自动启动。

### 配置文件（已内置）

`.vscode/mcp.json` 已存在于仓库根目录：

```json
{
  "servers": {
    "agents-memory": {
      "type": "stdio",
      "command": "python3.12",
      "args": ["/Users/cliff/workspace/Agents-Memory/scripts/mcp_server.py"],
      "env": {}
    }
  }
}
```

> **注意**：`args` 中的路径是绝对路径，克隆到其他位置后需同步修改。

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

## 5. 日常运维命令速查

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

## 6. 目录结构说明

```
Agents-Memory/
├── index.md          ← 热区：每次 Session 必加载，≤ 400 tokens
├── memory/
│   ├── rules.md      ← 温区：已提炼的防范规则
│   └── projects.md   ← 已注册的跨项目注册表
├── errors/           ← 冷区：所有错误记录文件
│   └── archive/      ← 90 天以上的归档记录
├── templates/        ← bridge instruction 模板
├── scripts/
│   ├── memory.py     ← CLI 主工具（12 命令）
│   └── mcp_server.py ← MCP Server（7 个 Agent 工具）
└── .vscode/
    └── mcp.json      ← VS Code MCP 集成配置
```

---

## 7. 常见问题

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
      "args": ["/Users/cliff/workspace/Agents-Memory/scripts/mcp_server.py"]
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
