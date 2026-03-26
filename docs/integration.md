# 接入其他项目

> 把任意项目的 AI Agent 接入 Agents-Memory 共享记忆系统，全程约 2 分钟。

---

## 接入需要做什么？

接入分两层：

| 层 | 做什么 | 效果 |
|----|--------|------|
| **注册层** | 把项目写入 `memory/projects.md` | `sync` 命令能向该项目推送规则 |
| **工具层** | VS Code 的 MCP 配置 | Agent 能调用 `memory_record_error` 等工具 |

**两层都完成后，Agent 才能全自动使用共享记忆。** 只做注册层，Agent 仍需手动跑 CLI。

---

## 一键接入（推荐）

### 前置：安装 `amem` 全局命令（只需一次）

```bash
# 克隆 Agents-Memory（如果还没有）
git clone https://github.com/haochencheng/Agents-Memory.git

# 安装 amem 到系统 PATH（创建符号链接到 /opt/homebrew/bin/amem）
bash Agents-Memory/scripts/install-cli.sh
```

安装后 `amem` 在任意目录全局可用，无需 Python 环境配置、无需 pip。

### 在目标项目根目录运行

```bash
cd /path/to/your-project
amem register
```

命令会依次完成：
1. 从 git remote 自动识别项目 ID
2. 扫描 `.github/instructions/` 推断 domains 和 instruction 文件映射
3. 写入 `memory/projects.md`（幂等，不重复写）
4. 询问是否安装 bridge instruction → 自动复制模板到 `.github/instructions/agents-memory-bridge.instructions.md`

示例输出：

```
🔍 检测到项目 ID: my-service  (来源: git remote / 目录名)
Project ID [my-service]:

Instruction 目录 [.github/instructions]:

📂 扫描到 instruction 文件:
   python       → .github/instructions/python.instructions.md
   frontend     → .github/instructions/frontend.instructions.md

🏷  推断的 domains: frontend, python
Domains (逗号分隔) [frontend, python]:

✅ 已写入 memory/projects.md → my-service

自动安装 bridge instruction？[Y/n]: y
✅ Bridge instruction installed → .github/instructions/agents-memory-bridge.instructions.md
```

---

## 还需要哪些配置？

### 必须：VS Code MCP 配置

`register` 命令安装的 bridge instruction 是**文字协议**，告诉 Agent 该怎么用记忆系统。但 Agent 真正执行工具调用，需要 VS Code 知道 MCP Server 在哪里。

**在你的项目根目录**创建 `.vscode/mcp.json`（或追加到现有文件）：

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

> **路径说明**：`args` 必须是 `mcp_server.py` 的绝对路径，指向 Agents-Memory 仓库位置。

### 可选：AGENTS.md 读序注册

如果你的项目有 `AGENTS.md` 或 `docs/AGENTS.md`，把 bridge instruction 加入读序，让 Agent 在每次 session 开始时自动加载：

```markdown
## Read Order

1. `.github/instructions/agents-memory-bridge.instructions.md`  ← 加在最前
2. `.github/instructions/python.instructions.md`
...
```

---

## 接入后 Agent 的完整工作流

配置完成后，Agent 在该项目中的行为变为：

```
session 开始
  → Agent 读 bridge instruction
  → 调用 memory_get_index()         # 加载 index.md 热区（≤ 400 tokens）
  → 调用 memory_get_rules("python") # 加载领域规则

coding 过程中发现 bug
  → 调用 memory_search("pydantic")  # 查历史是否有相同错误
  → 修复后调用 memory_record_error(
      project="my-service",
      domain="python",
      category="type-error",
      ...
    )                                # 自动写入 errors/*.md

session 结束（人工）
  → python3 memory.py promote <id>  # 重复出现 ≥ 2 次时升级为规则
  → python3 memory.py sync          # 推送规则到所有注册项目
```

---

## 如何验证接入是否成功？

### 检查 1：注册已写入

```bash
grep "my-service" /Users/cliff/workspace/Agents-Memory/memory/projects.md
```

输出应包含：
```
## my-service
- **id**: my-service
- **active**: true
```

### 检查 2：bridge instruction 存在

```bash
ls /path/to/my-project/.github/instructions/agents-memory-bridge.instructions.md
```

### 检查 3：MCP Server 可用（关键）

在 **目标项目的 VS Code 窗口**打开 Agent/Chat 面板，输入：

```
请调用 memory_get_index 工具，告诉我当前有多少条错误记录。
```

如果工具调用成功并返回 `index.md` 内容，接入完成 ✅

如果提示"找不到工具"或 MCP 错误，检查：
- `.vscode/mcp.json` 是否存在于该项目根目录
- `python3.12` 是否在 PATH（`which python3.12`）
- `mcp` 包是否安装在 python3.12 上（`python3.12 -c "import mcp; print(mcp.__version__)"`）

### 检查 4：sync 能覆盖该项目

```bash
python3 /Users/cliff/workspace/Agents-Memory/scripts/memory.py sync
```

如果输出中出现该项目的 instruction 文件路径，说明规则推送链路正常。

---

## 分步手动接入（不用 register 命令时）

如果不想用交互式 `register`，也可以手动完成：

**步骤 1 — 编辑 `memory/projects.md`，追加：**

```markdown
## my-service

- **id**: my-service
- **root**: /absolute/path/to/my-service
- **instruction_dir**: .github/instructions
- **bridge_instruction**: .github/instructions/agents-memory-bridge.instructions.md
- **active**: true
- **domains**: python, frontend, docs
```

**步骤 2 — 安装 bridge instruction：**

```bash
amem bridge-install my-service
```

**步骤 3 — 添加 `.vscode/mcp.json`（同上）**

---

## Spec2Flow / 其他已注册项目的现状

| 项目 | 注册 | bridge 安装 | MCP 配置 |
|------|------|------------|---------|
| synapse-network | ✅ | ✅ | 需手动添加 `.vscode/mcp.json` |
| spec2flow | ✅ | ✅ | 需手动添加 `.vscode/mcp.json` |
| agents-memory | ✅ | — | ✅（内置）|
