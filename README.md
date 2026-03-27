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

### What It Solves

1. Repeated engineering mistakes across projects.
2. Missing shared standards, planning workflow, and delivery checks for agents.
3. Drift between docs, rules, templates, and real implementation.

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

### Contribution / Roadmap

Contributions are welcome in three directions:

1. Better agent workflows: bootstrap, task execution, validation, and learning loops.
2. Stronger open-source readiness: CI, issue templates, release discipline, and repo health gates.
3. More reusable engineering assets: standards, profiles, planning bundles, and validation policies.

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

## 贡献

欢迎把它当作一个正在演进的工程操作系统来贡献。

提交行为变更前，请至少同步更新：

1. 代码
2. 对应文档
3. 对应测试或验证脚本

贡献说明见 CONTRIBUTING.md。

## License

本项目采用 MIT License。
