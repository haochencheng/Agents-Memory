# 接入其他项目

> 把任意项目的 AI Agent 接入 Agents-Memory 共享记忆系统，全程约 2 分钟。

---

## 接入需要做什么？

接入共 3 步，`amem register` **全部自动完成**：

| 步骤 | 做什么 | 效果 |
|------|--------|------|
| 1. **注册** | 写入 `memory/projects.md` | `amem sync` 能向该项目推送规则 |
| 2. **bridge instruction** | 复制协议文件到 `.github/instructions/` | Agent 知道该如何使用记忆系统 |
| 3. **MCP 工具层** | 写入 `.vscode/mcp.json` | Agent 真正能调用 `memory_record_error` 等工具 |

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

所有步骤直接回车确认默认值即可：

```
🔍 检测到项目 ID: my-service  (来源: git remote / 目录名)
Project ID [my-service]: ↵

Instruction 目录 [.github/instructions]: ↵

📂 扫描到 instruction 文件:
   python       → .github/instructions/python.instructions.md
   frontend     → .github/instructions/frontend.instructions.md

🏷  推断的 domains: frontend, python
Domains (逗号分隔) [frontend, python]: ↵

✅ 已写入 memory/projects.md → my-service

自动安装 bridge instruction？[Y/n]: ↵
✅ Bridge instruction installed → .github/instructions/agents-memory-bridge.instructions.md

自动写入 .vscode/mcp.json（VS Code MCP 工具层）？[Y/n]: ↵
  ✅ 已写入 .vscode/mcp.json
```

> **提示**：如果目标项目已有 `.vscode/mcp.json`（含其他 MCP server），命令会**合并写入** `agents-memory` 条目，不覆盖现有配置。

---

## 可选：AGENTS.md 读序注册

如果你的项目有 `AGENTS.md`，把 bridge instruction 加到读序最前，让 Agent 每次 session 自动加载：

```markdown
## Read Order

1. `.github/instructions/agents-memory-bridge.instructions.md`  ← 加在最前
2. `.github/instructions/python.instructions.md`
...
```

---

## 接入后 Agent 的完整工作流

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
  → amem promote <id>  # 重复出现 ≥ 2 次时升级为规则
  → amem sync          # 推送规则到所有注册项目
```

---

## 如何验证接入是否成功？

### 检查 1：注册已写入

```bash
grep -A3 "## my-service" /path/to/Agents-Memory/memory/projects.md
```

输出应包含 `active: true`。

### 检查 2：bridge instruction 存在

```bash
ls .github/instructions/agents-memory-bridge.instructions.md
```

### 检查 3：MCP 配置正确（关键）

```bash
cat .vscode/mcp.json
# 应包含 "agents-memory" 键
```

然后在 **该项目的 VS Code 窗口** Agent/Chat 面板中输入：

```
请调用 memory_get_index 工具，告诉我当前有多少条错误记录。
```

返回 `index.md` 内容则接入完成 ✅

如果提示"找不到工具"，检查：
- `.vscode/mcp.json` 是否存在于该项目根目录
- `python3.12` 是否在 PATH：`which python3.12`
- `mcp` 包是否已装：`python3.12 -c "from mcp.server.fastmcp import FastMCP; print('OK')"`

### 检查 4：sync 能覆盖该项目

```bash
amem sync
# 输出中应出现该项目的 instruction 文件路径
```

---

## 分步手动接入（不用 register 命令时）

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

**步骤 3 — 写入 .vscode/mcp.json：**

```bash
amem mcp-setup my-service   # 按项目 ID
# 或
amem mcp-setup /path/to/my-service  # 按路径
# 或
cd /path/to/my-service && amem mcp-setup  # 当前目录
```

---

## 已注册项目现状

| 项目 | 注册 | bridge 安装 | MCP 配置 |
|------|------|------------|------|
| synapse-network | ✅ | ✅ | ✅ |
| spec2flow | ✅ | ✅ | 运行 `amem mcp-setup spec2flow` |
| agents-memory | ✅ | — | ✅（内置）|
