---
created_at: 2026-03-26
updated_at: 2026-03-28
doc_status: active
---

# CLI Commands

> Agents-Memory CLI 全量命令总表。默认推荐从 `amem bootstrap .` 开始走顶层 workflow。

---

## 边界说明

`docs/commands.md` 负责：

1. 命令签名与参数形态。
2. 每条命令的简短用途说明。
3. 命令按能力域分组后的总表。

`docs/integration.md` 负责：

1. 目标项目如何接入。
2. 推荐按什么顺序执行接入命令。
3. 接入后如何验证与排错。

`docs/getting-started.md` 负责：

1. 本仓库如何本地安装与启动。
2. 本地依赖、MCP、Qdrant、日志、CLI 自检。

换句话说：

```text
commands.md         = 命令参考
integration.md      = 外部项目接入流程
getting-started.md  = 本仓库本地启动与运维
```

## Recommended Entry

### `amem bootstrap .`

顶层 workflow 入口。

适合首次接入项目，希望按“用户意图”而不是内部模块名来理解命令。当前语义等价于 `amem enable .`，但文档与后续产品演进都以 `bootstrap` 作为主入口。

### `amem start-task "<task>" .`

顶层 workflow 入口。

适合把新需求快速收敛成标准 planning bundle。当前语义等价于 `amem plan-init "<task>" .`。

### `amem do-next .`

顶层 workflow 入口。

适合让 agent 直接读取当前 onboarding state，输出当前阻塞项、推荐动作、验证命令和下一步命令，而不是自己猜测。

### `amem validate .`

顶层 workflow 入口。

聚合 `docs-check`、`profile-check`、`plan-check` 与 `doctor`，形成一个统一交付门。`--strict` 会把 `WARN/PARTIAL` 也视为失败退出。

### `amem close-task .`

顶层 workflow 入口。

在统一 gate 通过后，把当前 task bundle 的完成状态回写到 `README.md`、`task-graph.md`、`validation.md`，并把完成记录写回 `.agents-memory/onboarding-state.json`。如果当前项目有多个任务 bundle，建议显式传 `--slug <task-slug>`。

### `amem enable .`

兼容层入口，一键接入命令。

适合已有用户继续沿用现有命令。具体接入顺序、受管文件和验证步骤统一见 `docs/integration.md`。

### `amem enable . --dry-run`

预览模式。只展示当前项目将启用哪些能力、将写哪些文件，以及哪些项目工件会被复用，不落任何文件。

适合在正式接入前先检查影响面。它是命令参考的一部分，不展开完整接入流程。

默认分组输出：

- `Capabilities`
- `Planned Writes`
- `Skipped Existing`

### `amem enable . --full --dry-run --json`

结构化 JSON 预览模式。适合 agent、脚本或 CI 直接消费。

输出字段包括：

- `project_id`
- `project_root`
- `mode`
- `dry_run`
- `capabilities`
- `planned_writes`
- `skipped_existing`

### `amem enable . --full`

全量模式的一键接入命令。在默认模式基础上继续：
- 把 refactor follow-up 写回 onboarding state

适合希望一次性把 Shared Engineering Brain 核心能力全部打开的项目。完整接入说明见 `docs/integration.md`。

---

## Workflow Commands

### `amem bootstrap [path] [--full] [--dry-run] [--json]`

按用户意图组织的一键 bootstrap 入口。当前委托给 `enable` 实现，参数语义保持一致。

### `amem start-task <task-name> [path] [--slug <task-slug>] [--dry-run]`

按用户意图组织的 task 启动入口。当前委托给 `plan-init` 实现，生成 `spec / plan / task-graph / validation`。

### `amem do-next [path] [--format text|json]`

输出当前 onboarding 下一步动作。如果项目还没准备好，会给出推荐命令；如果 onboarding 已完成，会提示继续正常实现或开启下一个 task。

### `amem validate [path] [--strict] [--format text|json]`

统一交付门。输出 `docs / profile / planning / doctor` 四组结果，并给出统一退出码。

### `amem close-task [path] [--slug <task-slug>] [--strict] [--format text|json]`

任务关闭入口。会先跑统一 gate，再原子化回写 task bundle 的完成标记和 onboarding state 中的任务闭环状态。

---

## 使用规则

后续新增内容时，遵守下面 3 条：

1. 如果是在列命令、参数、输出形态，写入 `docs/commands.md`。
2. 如果是在说明目标项目如何按步骤接入，写入 `docs/integration.md`。
3. 如果是在说明本仓库如何安装、启动、调试，写入 `docs/getting-started.md`。

## Memory

### `amem new`

交互式创建新的错误记录。

### `amem list`

列出当前 `new` / `reviewed` 状态的错误记录。

### `amem stats`

统计错误记录分布。

### `amem search <keyword>`

按关键词全文搜索错误记录。

### `amem embed`

构建或更新本地 LanceDB 向量索引。

### `amem vsearch <query>`

使用向量索引做语义搜索。

### `amem promote <id>`

把错误记录升级为可同步的规则。

### `amem sync`

将已升级规则同步到所有注册项目的 instruction 文件。

### `amem archive`

归档旧错误记录。

### `amem update-index`

刷新 `index.md` 的统计与摘要。

### `amem to-qdrant`

把向量索引迁移到共享 Qdrant。

## Integration

### `amem register [path]`

交互式注册项目，写入项目 registry，并引导后续接入动作。

### `amem bridge-install <project-id>`

为目标项目安装 bridge instruction。

### `amem mcp-setup [project-id|path]`

写入或合并 `.vscode/mcp.json`，启用 Agents-Memory MCP server。

### `amem copilot-setup [project-id|path]`

安装 GitHub Copilot 仓库级激活块。

### `amem doctor [project-id|path] [--write-checklist] [--write-state]`

运行完整接入健康检查，并可导出 checklist/state 工件。

### `amem onboarding-execute [path] [--approve-unsafe] [--no-verify]`

执行 onboarding state 中当前第一条动作，并回写执行/验证结果。

### `amem agent-list`

列出内置 agent adapter。

### `amem agent-setup <agent> [path]`

为目标项目安装指定 agent adapter。

## Planning

### `amem plan-init <task-name> [path] [--slug <task-slug>] [--dry-run]`

初始化一个 planning bundle：`spec / plan / task-graph / validation`。

### `amem onboarding-bundle [path] [--slug <task-slug>] [--dry-run]`

根据 onboarding state 生成 onboarding planning bundle。

### `amem refactor-bundle [path] [--token <hotspot-token>] [--index <n>] [--slug <task-slug>] [--dry-run]`

根据 refactor hotspot 生成 refactor planning bundle。优先使用稳定的 `--token`，避免 hotspot 排序变化导致目标漂移。

### `amem plan-check [path]`

校验 `docs/plans/` 下 planning bundles 的完整性和关键语义。

## Profiles And Standards

### `amem profile-list`

列出内置 profile。

### `amem profile-show <profile-id>`

展示某个 profile 的标准、模板、bootstrap，以及 schema 中的 `variables / detectors / overlays`。

### `amem profile-apply <profile-id> [path]`

把 profile 安装到目标项目。

### `amem profile-diff <profile-id> [path]`

预览 profile 将写入哪些文件。

### `amem profile-render [path] [--profile <id>] [--dry-run]`

根据当前 `project-facts.json` 对 active overlays 做重渲染，并清理已经失活的 project-local overlay 文件。

### `amem standards-sync [path]`

同步 profile 管理的组织标准文件，同时刷新 `project-facts.json` 和 active overlays。

### `amem profile-check [path]`

校验已安装 profile 的一致性，包括 manifest、standards、facts、overlays 和 AGENTS 路由。

### `amem docs-check [path]`

校验仓库文档入口、命令说明和 contract/test/policy 漂移。

### `amem docs-touch [path] [--date YYYY-MM-DD] [--dry-run] [--format text|json]`

自动刷新受管 Markdown 文档的 `updated_at`。如果目标文档缺少 front matter，会顺带补齐 `created_at / updated_at / doc_status`。

适用场景：

- 代码改动后批量同步文档最后修改时间
- 新增文档元数据契约后补齐旧文档头部
- 在 CI 或脚本里先用 `--dry-run` 预览将改动哪些文档