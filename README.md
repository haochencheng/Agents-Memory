---
created_at: 2026-03-26
updated_at: 2026-03-28
doc_status: active
---

# Agents-Memory

<a id="top"></a>

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![MCP](https://img.shields.io/badge/MCP-enabled-black)
![Docs Check](https://img.shields.io/badge/docs--check-governed-orange)

[![Release](https://img.shields.io/github/v/release/haochencheng/Agents-Memory)](https://github.com/haochencheng/Agents-Memory/releases)
[![CI](https://github.com/haochencheng/Agents-Memory/actions/workflows/ci.yml/badge.svg)](https://github.com/haochencheng/Agents-Memory/actions/workflows/ci.yml)
[![Changelog](https://img.shields.io/badge/changelog-managed-0A7EA4)](CHANGELOG.md)
[![Release Checklist](https://img.shields.io/badge/release-checklist-reviewed-2F855A)](docs/release-checklist.md)
[![Contributors](https://img.shields.io/github/contributors/haochencheng/Agents-Memory)](https://github.com/haochencheng/Agents-Memory/graphs/contributors)
[![Last Commit](https://img.shields.io/github/last-commit/haochencheng/Agents-Memory)](https://github.com/haochencheng/Agents-Memory/commits/main)
[![Repo Size](https://img.shields.io/github/repo-size/haochencheng/Agents-Memory)](https://github.com/haochencheng/Agents-Memory)

中文 | [English](#english)

开源的 Shared Engineering Brain for AI coding agents。它把 Memory、Standards、Planning、Validation 组合成一个可安装、可验证、可持续演进的工程运行层，而不是一组松散的脚本。

> README 是开源仓库首页，不展开完整教程正文。

关键词：AI coding agent、shared engineering brain、engineering memory、agent runtime、prompt memory、standards sync、planning workflow、validation gate、MCP server、developer tooling

<a id="english"></a>

## English

[中文](#top) | English

Agents-Memory is an open-source Shared Engineering Brain for AI coding agents. It combines Memory, Standards, Planning, and Validation into an installable and verifiable engineering runtime instead of a loose collection of scripts.

Keywords: AI coding agents, engineering memory, agent runtime, prompt memory, standards sync, planning workflow, validation gate, MCP server, developer tooling, reusable engineering context

### Trust Signals

1. [CI](https://github.com/haochencheng/Agents-Memory/actions/workflows/ci.yml) is public and tied to the same install, compile, test, and docs-check flow contributors run locally.
2. [Releases](https://github.com/haochencheng/Agents-Memory/releases) are backed by a checked-in [CHANGELOG.md](CHANGELOG.md), not only by ad-hoc GitHub release text.
3. [docs/release-checklist.md](docs/release-checklist.md) defines how tags and releases are prepared, verified, and checked after publishing.
4. [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md), and [CONTRIBUTING.md](CONTRIBUTING.md) make the collaboration path explicit before someone opens an issue or a pull request.

### What It Solves

1. Repeated engineering mistakes across projects.
2. Missing shared standards, planning workflow, and delivery checks for agents.
3. Drift between docs, rules, templates, and real implementation.

### Who It's For

1. Teams using Copilot or MCP-capable coding agents in real software projects.
2. Engineers who want reusable standards, task scaffolds, and validation gates across repos.
3. Builders creating an internal engineering runtime instead of isolated prompt snippets.
4. Maintainers who need a cleaner bridge between AI assistance and real delivery discipline.

### Architecture Snapshot

1. Agents consume not only memory, but also standards, profiles, onboarding state, and task bundles.
2. Project bootstrap is a unified workflow around register, profile, bridge, doctor, and planning root.
3. Delivery is gated by docs, plans, profiles, tests, and complexity checks.
4. Project experience should be promoted into shared standards, validation rules, and reusable workflow defaults.

### Quick Start

```bash
git clone https://github.com/haochencheng/Agents-Memory.git
cd Agents-Memory
python3 -m pip install -e .
amem list
python3 scripts/memory.py docs-check .
python3.12 -m unittest discover -s tests -p 'test_*.py'
```

### Use Cases

1. Give coding agents persistent engineering memory across multiple repositories.
2. Install reusable standards, profiles, and task workflows into a new project bootstrap.
3. Add docs, planning, profile, and validation gates around AI-assisted delivery.
4. Turn repeated implementation mistakes into reusable rules and workflow protection.
5. Build an MCP-backed engineering runtime for Copilot or other coding agents.

### Docs

1. Setup and first local run: docs/getting-started.md
2. Integrate into another repo: docs/integration.md
3. Operations and troubleshooting: docs/ops.md
4. CLI reference: docs/commands.md
5. Product architecture baseline: docs/ai-engineering-operating-system.md
6. Repo ADRs: docs/architecture.md
7. Modular code structure: docs/modular-architecture.md
8. Release checklist: docs/release-checklist.md

### Quality Gates

1. Every pull request is gated by `.github/workflows/ci.yml` for install, compile, unit tests, and `docs-check`.
2. Public release history is tracked in [CHANGELOG.md](CHANGELOG.md), not only in GitHub release text.
3. Release execution is governed by [docs/release-checklist.md](docs/release-checklist.md), including CI confirmation, version check, tag, and GitHub Release.
4. Open-source surface drift is checked by `docs-check`, including collaboration entrypoints, CI workflow semantics, and release checklist semantics.

### Contribution / Roadmap

Contributions are welcome in three directions:

1. Better agent workflows: bootstrap, task execution, validation, and learning loops.
2. Stronger open-source readiness: CI, issue templates, release discipline, and repo health gates.
3. More reusable engineering assets: standards, profiles, planning bundles, and validation policies.

Contribution flow is documented in [CONTRIBUTING.md](CONTRIBUTING.md). Community expectations live in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), issue / PR intake goes through the repository templates, security reporting follows [SECURITY.md](SECURITY.md), support paths are listed in [SUPPORT.md](SUPPORT.md), sponsorship metadata lives in `.github/FUNDING.yml`, pull requests are gated by `.github/workflows/ci.yml`, and releases should update [CHANGELOG.md](CHANGELOG.md) and [docs/release-checklist.md](docs/release-checklist.md).

Near-term roadmap:

1. Converge more top-level workflows into clearer user-facing commands.
2. Strengthen delivery gates across docs, plans, profiles, tests, and maintainability checks.
3. Improve profile distribution, conflict handling, and cross-project standards sync.

<a id="中文"></a>

## 中文

[English](#english) | 中文

## 它解决什么问题

多数 AI coding agent 的问题不是“不会生成代码”，而是缺少稳定工程上下文：

1. 相同错误在不同项目里反复出现。
2. 工程标准、任务规划和交付验证没有统一入口。
3. 文档、规则、模板和实际实现容易漂移。

## 适合谁

1. 在真实软件项目里使用 Copilot 或其他 MCP coding agent 的团队。
2. 希望把工程标准、任务脚手架和验证门禁复用到多个仓库的工程师。
3. 想构建内部 engineering runtime，而不是只堆 prompt 片段的建设者。
4. 需要把 AI 辅助开发和真实交付纪律更稳地接起来的维护者。

## 可信信号

1. [CI](https://github.com/haochencheng/Agents-Memory/actions/workflows/ci.yml) 是公开的，而且执行的就是贡献者本地会跑的安装、编译、测试和 `docs-check`。
2. [Releases](https://github.com/haochencheng/Agents-Memory/releases) 对应到仓库内的 [CHANGELOG.md](CHANGELOG.md)，不是只依赖 GitHub 页面上的临时说明。
3. [docs/release-checklist.md](docs/release-checklist.md) 明确约束了发版前检查、tag、GitHub Release 和发布后核对动作。
4. [SECURITY.md](SECURITY.md)、[SUPPORT.md](SUPPORT.md)、[CONTRIBUTING.md](CONTRIBUTING.md) 让安全披露、支持路径和贡献入口在首页即可追溯。

Agents-Memory 的目标是把这些能力放进同一个共享层：

```text
Shared Engineering Brain
├── Memory      记录错误、复盘、规则升级
├── Standards   下发工程规范与默认约束
├── Planning    沉淀 spec / plan / task graph workflow
├── Validation  把 docs / profile / doctor 等检查做成 gate
└── Learning Bus 把项目经验升级为跨项目默认保护
```

## 最新架构摘要

项目当前的产品方向已经从“共享错误记忆系统”收敛为面向 agent 的工程 Harness。

当前的架构判断是：

1. Agent 读取的不只是错误记忆，还包括标准、profile、onboarding state 和任务工件。
2. 项目接入不只是 MCP 配置，而是 register、profile、bridge、doctor、planning root 的统一 bootstrap。
3. 交付不只看代码 diff，而要通过 docs、plan、profile、tests、complexity 的统一 gate。
4. 项目经验不只进入 `errors/`，还应升级到 `standards/`、`validation`、profile 和 workflow。

最新架构设计见 docs/ai-engineering-operating-system.md。
Repo 级实现取舍见 docs/architecture.md。
代码分层与模块边界见 docs/modular-architecture.md。

### 当前实现状态

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| Memory 记录、搜索、promote、sync | done | 已具备热区/温区/冷区记忆和规则升级基础链路 |
| Standards 与 profile 受管文件 | partial | 已可同步与安装，但发行和冲突策略仍在继续收敛 |
| Planning bundle 与 onboarding/refactor bundle | done | 已可生成 spec / plan / task graph / validation 工件 |
| Validation gate | partial | 单项检查器已到位，统一 validate workflow 仍在演进 |
| Learning Bus | partial | error promote / sync 已有，跨项目默认保护仍在继续沉淀 |

## 快速开始

如果你只是想本地跑起来并验证仓库：

```bash
git clone https://github.com/haochencheng/Agents-Memory.git
cd Agents-Memory
python3 -m pip install -e .
amem list
python3 scripts/memory.py docs-check .
python3.12 -m unittest discover -s tests -p 'test_*.py'
```

安装与启动细节见 docs/getting-started.md。
接入其他项目见 docs/integration.md。
CLI 命令总表见 docs/commands.md。
日常运维与排障见 docs/ops.md。

## 核心能力

### Memory

1. 结构化错误记录、关键词搜索、向量搜索。
2. `promote` 和 `sync`，把经验升级为共享规则。
3. MCP tools，用于在 agent 会话中拉取记忆、规则和搜索结果。

### Standards And Profiles

1. `standards/` 提供 Python、docs、planning、validation 的组织级标准。
2. `profiles/` 提供项目级工程契约安装与刷新。
3. `enable` / `profile-apply` / `standards-sync` 负责把标准真正安装进目标项目。

### Planning And Validation

1. `plan-init`、`onboarding-bundle`、`refactor-bundle` 生成标准工件。
2. `docs-check`、`profile-check`、`plan-check`、`doctor` 负责门禁和健康检查。
3. onboarding state 与 refactor hotspot 让 agent 能继续执行下一步动作，而不是只看控制台输出。

## 开源边界

公开仓库只包含代码、模板、标准、profiles 和文档。以下内容属于本地运行数据，默认不应提交：

```text
index.md
memory/projects.md
memory/rules.md
errors/*.md
.vscode/mcp.json
logs/
vectors/
```

仓库使用 `templates/` 下的公开样例初始化本地文件，以避免把真实项目上下文、私有路径或运行时数据带进开源仓库。

## 仓库结构

```text
Agents-Memory/
├── agents_memory/    CLI、MCP、services、agent adapters
├── standards/        组织级工程标准与校验规则
├── profiles/         可安装的项目工程契约
├── templates/        bridge / copilot / bootstrap 模板
├── docs/             架构、接入、启动、运维文档
├── tests/            services 与 docs-check 最小测试矩阵
├── llms.txt          机器可读项目地图
└── README.md         开源入口页
```

## 文档导航

1. docs/getting-started.md: 本仓库首次安装、启动、基础验证
2. docs/integration.md: 目标项目如何接入 Agents-Memory
3. docs/ops.md: 日常运维、日志、索引、Qdrant、恢复与排障
4. docs/commands.md: CLI 命令总表与参数参考
5. docs/ai-engineering-operating-system.md: 最新产品基线与目标命令模型
6. docs/architecture.md: repo 级 ADR 与实现取舍
7. docs/modular-architecture.md: 代码目录结构、模块职责与扩展点
8. docs/README.md: 完整文档地图
9. docs/release-checklist.md: 发版前后检查项、tag 与 GitHub Release 流程

## 质量门禁与发布纪律

1. 每个 PR 都会经过 `.github/workflows/ci.yml`，执行安装、编译、单元测试和 `docs-check`。
2. 对外版本历史记录在 [CHANGELOG.md](CHANGELOG.md)，而不是只留在 GitHub Release 页面。
3. 发布动作由 [docs/release-checklist.md](docs/release-checklist.md) 约束，覆盖 CI 结果、版本确认、Git tag 和 GitHub Release。
4. 开源协作入口、CI 语义和 release checklist 语义都已经纳入 `docs-check`，减少首页和真实流程之间的漂移。
9. docs/release-checklist.md: 版本发布前后检查项与 changelog 流程

## 贡献

欢迎把它当作一个正在演进的工程操作系统来贡献。

提交行为变更前，请至少同步更新：

1. 代码
2. 对应文档
3. 对应测试或验证脚本

贡献说明见 CONTRIBUTING.md。
问题反馈与能力建议请使用仓库内置 issue 模板；提交合并请求时请按 PULL_REQUEST_TEMPLATE.md 补齐验证信息；协作行为遵循 CODE_OF_CONDUCT.md；安全问题请按 SECURITY.md 私下报告；使用与协作支持入口见 SUPPORT.md；赞助配置见 `.github/FUNDING.yml`；PR 门禁见 `.github/workflows/ci.yml`；发布时同步维护 CHANGELOG.md 和 docs/release-checklist.md。

## License

本项目采用 MIT License。
