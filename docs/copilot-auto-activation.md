---
created_at: 2026-03-26
updated_at: 2026-04-07
doc_status: active
---

# Copilot 自动激活设计

> 目标：让用户只执行一次 `amem register`，后续 GitHub Copilot 在该仓库上下文里默认先走 Agents-Memory 协议。

---

## 结论先说

当前 GitHub Copilot 官方能力里，**最强可落地方案**不是“硬强制每次先调用某个 MCP tool”，而是下面这组三件套：

1. `.github/copilot-instructions.md`
2. `.github/instructions/agents-memory-bridge.instructions.md`
3. `.vscode/mcp.json`

`amem register` 现在会把这三层一起接上。

---

## 为什么不能做成硬强制？

根据 GitHub Copilot how-to 文档，当前公开能力提供的是：

1. **仓库级 custom instructions**：通过 `.github/copilot-instructions.md` 自动附加仓库级指令。
2. **路径/文件级 instructions**：通过 `.github/instructions/*.instructions.md` 在代码任务里提供更细粒度规则。
3. **MCP tools**：通过 MCP server 把外部工具暴露给 Copilot Chat / Agent。

但 GitHub 没有提供一个官方钩子，允许仓库管理员声明：

> “每一个请求，无条件先执行 `memory_get_index()`，否则不许继续。”

所以平台层面不存在真正的 `beforeEachPrompt()` 强制拦截器。

---

## 新设计

### 第 1 层：仓库级默认协议

文件：`.github/copilot-instructions.md`

作用：让 Copilot 在当前仓库上下文请求里，默认把 Agents-Memory 当成启动协议。

这里写入的内容会明确要求：

1. 先调用 `memory_get_index()`
2. 再按领域调用 `memory_get_rules(domain)`
3. 遇到相似错误模式先 `memory_search(query)`
4. 修完 bug 后调用 `memory_record_error(...)`

这一步解决的是：

- “Copilot 每次进这个仓库，都先想到 Agents-Memory”

---

### 第 2 层：代码任务补强协议

文件：`.github/instructions/agents-memory-bridge.instructions.md`

作用：在代码编辑、文件匹配、Agent 编码场景里，继续补强同一套流程。

这一步解决的是：

- “即使进入具体文件或具体语言规则阶段，Agents-Memory 协议也不会丢”

---

### 第 3 层：真实工具能力

文件：`.vscode/mcp.json`

作用：把 `scripts/mcp_server.py` 暴露给 Copilot，让上面提到的协议不是一句空话，而是真能调工具。

这一步解决的是：

- “Copilot 想调用 `memory_get_index()` 时，工具真的存在”

---

## 为什么这已经是最强默认？

因为三层分别覆盖了三个不同问题：

1. `.github/copilot-instructions.md` 解决“默认意识”
2. `agents-memory-bridge.instructions.md` 解决“代码任务持续约束”
3. `.vscode/mcp.json` 解决“工具执行能力”

单独只有 `.vscode/mcp.json` 不够，因为那只是“工具可用”；Copilot 不一定默认先用。

单独只有 bridge instruction 也不够，因为它更偏具体代码场景，不是仓库级请求入口。

只有把三层一起装上，才最接近“用户只接一次，之后每次都默认走 Agents-Memory”。

---

## register 新行为

`amem register` 现在变成：

1. 注册项目到 `memory/projects.md`
2. 安装或更新 `.github/copilot-instructions.md` 中的 Agents-Memory 激活块
3. 安装 `agents-memory-bridge.instructions.md`
4. 写入或合并 `.vscode/mcp.json`

其中第 2 步使用带标记块的 merge 策略：

- 文件不存在：直接创建
- 文件已存在且已有 Agents-Memory 块：原地更新
- 文件已存在但没有 Agents-Memory 块：追加，不覆盖原有仓库指令

---

## 为什么不用 prompt file 或个人设置？

因为目标是“用户在仓库里执行一次命令就完成接入”，而不是要求每个开发者再做一轮个人侧配置。

- prompt file 需要用户显式选用，不满足“每次默认启用”
- personal settings 是用户级，不适合仓库一键接入
- organization instructions 不是本仓库 CLI 能可靠接管的范围

所以仓库级 `copilot-instructions.md` 才是最合适的控制点。

---

## 验证方式

执行：

```bash
amem doctor <project>
```

它现在会额外检查：

1. `.github/copilot-instructions.md` 是否存在
2. 是否包含 `Agents-Memory` 激活块

然后在该仓库的 Copilot Chat / Agent 面板中输入：

```text
先调用 memory_get_index()，再告诉我当前热区中最重要的规则。
```

如果能正常读到 `index.md`，说明自动激活链路已经打通。

---

## 边界说明

这套设计实现的是：

- **默认前置**
- **高概率稳定触发**
- **仓库级一次接入**

它没有实现的是：

- 平台底层不可绕过的强制执行钩子

如果未来 GitHub Copilot 官方开放更强的仓库策略控制接口，再把第 1 层从“默认协议”升级成“强制前置钩子”即可。