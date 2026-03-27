---
created_at: 2026-03-26
updated_at: 2026-03-27
doc_status: active
---

# 模块化与插件化结构

> 目标：把原来堆在 `scripts/memory.py` 里的所有能力，拆成“共享运行时 + 服务层 + 命令层 + agent adapter 层”，让后续接入 ChatGPT、Claude、其他 IDE Agent 时不再改动核心业务逻辑。

---

## 边界说明

`docs/modular-architecture.md` 负责：

1. 代码目录结构与模块分层。
2. runtime / services / commands / integrations 的职责边界。
3. 插件扩展点和模块装配方式。

`docs/architecture.md` 负责：

1. repo 级技术决策与 ADR。
2. 为什么采用某种实现路线。
3. 某个设计选择带来的后果与权衡。

换句话说：

```text
architecture.md         = 为什么这样实现
modular-architecture.md = 代码如何分层与扩展
```

---

## 新结构

```text
agents_memory/
├── app.py                         # CLI 总入口与命令分发
├── mcp_app.py                     # MCP Server 总入口
├── runtime.py                     # 路径、上下文、logger
├── constants.py                   # 常量与默认配置
├── logging_utils.py               # 统一日志
│
├── commands/
│   ├── records.py                 # list/stats/search/new/promote/archive/update-index
│   ├── vector.py                  # embed/vsearch/to-qdrant
│   └── integration.py             # register/doctor/mcp-setup/agent-setup
│
├── services/
│   ├── records.py                 # 错误记录解析与读写
│   ├── projects.py                # projects.md 注册表解析与目标解析
│   ├── integration.py             # bridge/MCP/doctor/register/sync 业务逻辑
│   └── vector.py                  # 向量索引与 Qdrant 迁移
│
└── integrations/
    └── agents/
        ├── base.py                # AgentAdapter 抽象协议
        ├── registry.py            # adapter 注册表
        ├── github_copilot.py      # 已实现
        ├── chatgpt.py             # scaffold
        └── claude.py              # scaffold

scripts/
├── memory.py                      # thin wrapper → agents_memory.app
├── mcp_server.py                  # thin wrapper → agents_memory.mcp_app
└── amem                           # thin wrapper → agents_memory.app
```

---

## 分层原则

### 1. runtime / constants

这一层只负责：

1. 仓库根目录解析
2. 路径对象构造
3. logger 构造
4. 常量与默认值

业务代码不能再到处自己拼 `BASE_DIR / "errors" / ...`。

### 2. services

这一层只负责业务逻辑，不负责 CLI 参数解析。

例如：

1. `records.py` 负责 frontmatter 解析、错误记录创建、index 更新
2. `projects.py` 负责项目注册表解析与路径解析
3. `integration.py` 负责同步规则、doctor、register、bridge/MCP 安装
4. `vector.py` 负责 LanceDB / Qdrant

这样 MCP server、CLI、将来的 Web UI 都能复用同一套逻辑。

### 3. commands

这一层只做命令分发，把 CLI 参数映射到服务层。

优点是：

1. CLI 入口清晰
2. 新命令只加一个注册点
3. 不会把业务逻辑和交互逻辑重新耦合回去

### 4. integrations/agents

这是新的插件层。

`AgentAdapter` 协议定义两个核心动作：

1. `install(...)`
2. `doctor(...)`

当前内置 adapter：

1. `github-copilot`：已实现，负责仓库级 instructions 安装与校验
2. `chatgpt`：scaffold，占位等待后续 repo-local 集成方案稳定
3. `claude`：scaffold，占位等待后续 repo-local 集成方案稳定

---

## 为什么这是可插拔的

因为新的 agent 接入不再改 `register` 主流程，只需要：

1. 新增一个 adapter 文件
2. 在 `registry.py` 注册
3. 实现 `install()` 和 `doctor()`

`register`、`agent-setup`、`doctor` 直接复用 registry，不需要再写一套 if/else 分支地狱。

---

## 当前默认策略

默认 agent 是 `github-copilot`。

所以：

1. `amem register` 会自动走 GitHub Copilot adapter
2. `amem copilot-setup` 是兼容 alias
3. `amem agent-list` 可以查看当前内置 adapters
4. `amem agent-setup <agent> <target>` 是未来扩展入口

---

## 演进路径

下一步如果要真正试吃 ChatGPT / Claude，不需要再重构核心，只需要补各自 adapter：

1. ChatGPT 的 repo instruction / project memory 装配方式
2. Claude 的 repo instruction / MCP 装配方式
3. 对应 doctor 校验规则

核心的错误记录、规则同步、向量检索、项目注册表都不用再动。

---

## 使用规则

后续新增内容时，遵守下面 3 条：

1. 如果是在解释模块目录、层级职责、adapter 扩展点，写入 `docs/modular-architecture.md`。
2. 如果是在解释某个 repo 级技术决策为什么成立，写入 `docs/architecture.md`。
3. 如果一个段落同时在写“为什么”与“怎么分层”，优先拆开，避免 ADR 和模块设计互相漂移。