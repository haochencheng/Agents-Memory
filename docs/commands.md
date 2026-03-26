# CLI Commands

> Agents-Memory CLI 全量命令总表。默认推荐从 `amem enable .` 开始接入项目。

## Recommended Entry

### `amem enable .`

默认模式的一键接入命令。自动完成当前项目的基础 Shared Engineering Brain 接入：


适合首次接入项目，目标是最小成本启用可运行链路。

### `amem enable . --dry-run`

预览模式。只展示当前项目将启用哪些能力、将写哪些文件，不落任何文件。

适合在正式接入前先检查影响面。

### `amem enable . --full`

全量模式的一键接入命令。在默认模式基础上继续：
- 把 refactor follow-up 写回 onboarding state

适合希望一次性把 Shared Engineering Brain 核心能力全部打开的项目。

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

展示某个 profile 的标准、模板和 bootstrap 信息。

### `amem profile-apply <profile-id> [path]`

把 profile 安装到目标项目。

### `amem profile-diff <profile-id> [path]`

预览 profile 将写入哪些文件。

### `amem standards-sync [path]`

同步 profile 管理的组织标准文件。

### `amem profile-check [path]`

校验已安装 profile 的一致性。

### `amem docs-check [path]`

校验仓库文档入口、命令说明和 contract/test/policy 漂移。