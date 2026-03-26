# 接入其他项目

> 把任意项目的 AI Agent 接入 Agents-Memory 共享记忆系统，全程约 2 分钟。

---

## 接入需要做什么？

接入共 4 步，`amem register` **全部自动完成**：

| 步骤 | 做什么 | 效果 |
|------|--------|------|
| 1. **注册** | 写入 `memory/projects.md` | `amem sync` 能向该项目推送规则 |
| 2. **仓库级 Copilot 激活** | 写入 `.github/copilot-instructions.md` | Copilot 在仓库上下文的每次请求都会默认加载 Agents-Memory 协议 |
| 3. **bridge instruction** | 复制协议文件到 `.github/instructions/` | 文件级/代码变更场景继续补强记忆协议 |
| 4. **MCP 工具层** | 写入 `.vscode/mcp.json` | Agent 真正能调用 `memory_record_error` 等工具 |

> 这是当前 GitHub Copilot 官方能力下的最强自动化组合：仓库级 custom instructions 负责“每次请求默认带上协议”，MCP 负责“真的能调用记忆工具”。平台目前没有公开的硬强制机制能保证每次都先执行某个 MCP tool，所以这里实现的是最强默认，而不是底层强制钩子。

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

自动安装 .github/copilot-instructions.md（仓库级 Copilot 自动激活）？[Y/n]: ↵
  ✅ 已写入 .github/copilot-instructions.md

自动安装 bridge instruction？[Y/n]: ↵
✅ Bridge instruction installed → .github/instructions/agents-memory-bridge.instructions.md

自动写入 .vscode/mcp.json（VS Code MCP 工具层）？[Y/n]: ↵
  ✅ 已写入 .vscode/mcp.json
```

> **提示 1**：如果目标项目已有 `.github/copilot-instructions.md`，命令会只追加或更新 `Agents-Memory` 激活块，不覆盖原有仓库指令。

> **提示 2**：如果目标项目已有 `.vscode/mcp.json`（含其他 MCP server），命令会**合并写入** `agents-memory` 条目，不覆盖现有配置。

> **提示 3**：`register` 当前默认安装的是 `github-copilot` adapter。后续如果你要试吃其他 agent，可先运行 `amem agent-list` 查看内置 adapters，再用 `amem agent-setup <agent> <target>` 单独安装。

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

## 为什么现在要多写一个 `.github/copilot-instructions.md`？

因为这一步才是“只执行一次，以后每次请求默认启用”的关键。

- `.github/copilot-instructions.md` 是 GitHub Copilot 官方支持的**仓库级 custom instructions** 文件。
- 它会在 Copilot 处理当前仓库请求时自动附加到上下文里。
- `agents-memory-bridge.instructions.md` 更像文件级/规则级补强，能帮助 coding agent 在具体代码任务里保持协议一致。
- `.vscode/mcp.json` 只解决“工具是否存在”，不解决“Copilot 会不会默认先想到要用它”。

所以新的接入设计是：

1. 用 `.github/copilot-instructions.md` 把 Agents-Memory 变成仓库默认协议。
2. 用 `.github/instructions/agents-memory-bridge.instructions.md` 继续强化代码变更场景。
3. 用 `.vscode/mcp.json` 提供真实的 MCP tools。

---

## 接入后 Agent 的完整工作流

```
session 开始
  → Agent 先读 .agents-memory/onboarding-state.json
  → 如缺失则运行 amem doctor . --write-state --write-checklist
  → 如 state 提示 bootstrap 未完成，先执行 recommended_next_command
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

### 检查 2：仓库级 Copilot 激活存在

```bash
ls .github/copilot-instructions.md
grep -n "agents-memory:start" .github/copilot-instructions.md
```

### 检查 3：bridge instruction 存在

```bash
ls .github/instructions/agents-memory-bridge.instructions.md
```

### 检查 4：MCP 配置正确（关键）

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

### 检查 5：sync 能覆盖该项目

```bash
amem sync
# 输出中应出现该项目的 instruction 文件路径

# 如需看详细日志
tail -f /path/to/Agents-Memory/logs/agents-memory.log
```

日志里可以直接看到：

1. `register_start` / `register_complete`
2. `install_bridge` 写入了哪个项目的哪个文件
3. `write_mcp_config` 或 `merge_mcp_config` 是否生效
4. 后续 `sync_rule` 是否把规则同步进该项目

### 检查 6：一条命令做全量体检

```bash
amem doctor my-service
```

它会一次检查：

1. 项目是否已注册到 `memory/projects.md`
2. `.github/copilot-instructions.md` 是否包含 Agents-Memory 激活块
3. bridge instruction 是否存在
4. `.vscode/mcp.json` 是否包含 `agents-memory`
5. 当前机器上的 `python3.12` / `mcp` 是否就绪
6. `AGENTS.md` 或 `docs/AGENTS.md` 是否引用了 bridge instruction（可选项）

如果你希望把体检结果直接变成 agent 可执行状态：

```bash
cd /path/to/my-service
amem doctor . --write-state --write-checklist
```

它会额外生成：

1. `.agents-memory/onboarding-state.json`
2. `docs/plans/bootstrap-checklist.md`

其中 `onboarding-state.json` 顶层会直接给出：

1. `project_bootstrap_ready`
2. `recommended_next_command`
3. `recommended_verify_command`
4. `recommended_done_when`

如果 agent 只想拿当前第一步动作，而不是整份 state，可优先调用 MCP tool：

```text
memory_get_onboarding_next_action(project_root=".")
```

如果你想把这个状态直接落成可执行 planning 工件：

```bash
amem onboarding-bundle .
```

它会在 `docs/plans/onboarding-*/` 下生成面向当前接入缺口的 task bundle。
如果 bundle 已存在，重复运行会增量刷新其中受管的 onboarding sections。

---

## 分步手动接入（不用 register 命令时）

**步骤 1 — 编辑 `memory/projects.md`，追加：**

```markdown
## my-service

- **id**: my-service
- **root**: /path/to/my-service
- **instruction_dir**: .github/instructions
- **bridge_instruction**: .github/instructions/agents-memory-bridge.instructions.md
- **active**: true
- **domains**: python, frontend, docs
```

**步骤 2 — 安装仓库级 Copilot 自动激活：**

```bash
amem copilot-setup my-service
```

**步骤 3 — 安装 bridge instruction：**

```bash
amem bridge-install my-service
```

**步骤 4 — 写入 .vscode/mcp.json：**

```bash
amem mcp-setup my-service   # 按项目 ID
# 或
amem mcp-setup /path/to/my-service  # 按路径
# 或
cd /path/to/my-service && amem mcp-setup  # 当前目录
```

---

## 已注册项目现状

| 项目 | 注册 | Copilot 激活 | bridge 安装 | MCP 配置 |
|------|------|---------------|------------|------|
| synapse-network | ✅ | 待补装 | ✅ | ✅ |
| spec2flow | ✅ | 待补装 | ✅ | ✅ |
| agents-memory | ✅ | 内置仓库 | — | ✅（内置）|
