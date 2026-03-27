# 接入其他项目

> 把任意项目的 AI Agent 接入 Agents-Memory Shared Engineering Brain，全程约 2 分钟。

---

## 接入需要做什么？

接入共 4 步，推荐通过 `amem enable .` 一次编排完成：

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
amem enable .
```

如果你想先看影响面，不立刻写文件：

```bash
amem enable . --dry-run
```

它会输出三组预览信息：

1. `Capabilities`
2. `Planned Writes`
3. `Skipped Existing`

如果你想把 profile、Copilot 激活和第一条 refactor follow-up 也一起打开：

```bash
amem enable . --full
```

如果你希望把全量预览交给 agent 或 CI 直接消费：

```bash
amem enable . --full --dry-run --json
```

默认模式会自动完成：

1. 注册项目
2. 安装 bridge instruction
3. 写入 `.vscode/mcp.json`
4. 如果项目已安装 profile，则刷新 profile 管理的 standards
5. 导出 `doctor` state/checklist
6. 生成 onboarding bundle

`--full` 会继续：

1. 自动应用推荐 profile
2. 后续再次执行 `amem enable .` 时，会继续自动同步该 profile 管理的标准文件
3. 安装或更新 `.github/copilot-instructions.md`
4. 安全补齐现有 planning bundle 缺失的受管文件
5. 为第一条 refactor hotspot 生成 bundle，并把 follow-up 写回 onboarding state

如果你仍然想逐项确认或手动控制每一步，也可以继续使用交互式 `amem register`：

```bash
amem register
```

交互式 `register` 中，所有步骤直接回车确认默认值即可：

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

> **提示 3**：`enable` 默认模式不会自动写 `.github/copilot-instructions.md`；如果你要连同 repo-wide Copilot 激活一起接上，请用 `amem enable . --full`。

> **提示 4**：`enable --dry-run` 不会写任何文件，适合先评估将要启用的能力和目标路径。

> **提示 5**：当前目标项目里的 agent 读取入口是 `.github/copilot-instructions.md`、`.github/instructions/agents-memory-bridge.instructions.md`、`.github/instructions/agents-memory/standards/*`、根目录 `AGENTS.md` 中的受管 read-order block，以及 `.vscode/mcp.json`。这条接入链路不要求目标项目额外生成 `llms.txt` 才能生效；`llms.txt` 仍主要用于 Agents-Memory 仓库自身的机器可读地图。

> **提示 6**：这里的自动修复目前只覆盖安全、模板化的 planning bundle 缺失文件修复。像 refactor hotspot 这类需要代码判断的项，仍会保留为 runbook / bundle，交给后续人工或 agent 按计划处理。

---

## 受管：AGENTS.md 读序路由

对 profile-managed 项目，`profile-apply` 和 `enable --full` 现在都会在项目根目录生成或更新一个最小 `AGENTS.md` 受管 block，用来路由 read order：

```markdown
## Agents-Memory Read Order

1. `.github/instructions/agents-memory-bridge.instructions.md`  ← 加在最前
2. `.github/instructions/agents-memory/standards/...`
```

如果项目本来已经有自己的 `AGENTS.md`，Agents-Memory 只会更新自己的受管 block，不覆盖其他项目说明。

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
6. 根目录 `AGENTS.md` 的受管 block 是否引用了最新 bridge instruction 和 profile-managed standards

如果你希望把体检结果直接变成 agent 可执行状态：

```bash
cd /path/to/my-service
amem doctor . --write-state --write-checklist
```

它会额外生成：

1. `.agents-memory/onboarding-state.json`
2. `docs/plans/bootstrap-checklist.md`
3. `docs/plans/refactor-watch.md`

其中 `onboarding-state.json` 顶层会直接给出：

1. `project_bootstrap_ready`
2. `recommended_next_command`
3. `recommended_verify_command`
4. `recommended_done_when`
5. `recommended_next_safe_to_auto_execute`
6. `recommended_next_approval_required`
7. `recommended_next_approval_reason`
8. `execution_history`
9. `last_executed_action`
10. `last_verified_action`

如果 agent 只想拿当前第一步动作，而不是整份 state，可优先调用 MCP tool：

```text
memory_get_onboarding_next_action(project_root=".")
```

如果 agent 希望直接执行第一步 onboarding action，并把执行/验证结果回写到 state，可调用：

```text
memory_execute_onboarding_next_action(project_root=".", verify=true, approve_unsafe=false)
```

CLI 对应命令：

```bash
amem onboarding-execute .
```

如果 state 或 next-action payload 表明 `approval_required=true`，则默认不执行。此时应由人类明确批准，再运行：

```bash
amem onboarding-execute . --approve-unsafe
```

此外，`amem doctor .` 现在会输出 `refactor_watch`，扫描当前项目 Python 函数是否逼近复杂度门槛。
它不会阻塞 bootstrap readiness，但会提示哪些函数应先重构，哪些复杂逻辑还缺少解释性注释；当你使用 `--write-checklist` 时，这些热点还会沉淀到 `docs/plans/refactor-watch.md`。

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
