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

Shared Engineering Brain for AI coding agents.

面向 AI coding agents 的共享工程运行层，统一 Memory、Standards、Planning、Validation。

README 是开源仓库首页，不展开完整教程正文。

Start here: [docs/getting-started.md](docs/getting-started.md) | [docs/integration.md](docs/integration.md) | [docs/commands.md](docs/commands.md) | [docs/ops.md](docs/ops.md)

Read in: [English](#en) | [简体中文](#zh)

## Product Snapshot / 产品摘要

1. Shared engineering runtime for AI coding agents / 面向 AI coding agents 的共享工程运行层。
2. Unifies memory, standards, planning, and validation / 统一 Memory、Standards、Planning、Validation。
3. Designed for real repositories, not isolated prompt snippets / 面向真实仓库交付，而不是零散 prompt 片段。
4. Turns repeated project lessons into reusable workflow protection / 把项目经验升级成可复用的流程保护。

## Why It Exists / 为什么存在

1. The same engineering mistakes repeat across repos / 相同工程错误会在不同仓库重复出现。
2. Standards, planning, and delivery checks often drift apart / 标准、规划和交付门禁常常彼此漂移。
3. Agents need workflow structure, not only tool access / Agent 需要工作流结构，而不只是工具访问权限。

## What You Get / 你会得到什么

1. Memory: capture failures, retrospectives, rules, and reusable patterns / 记录错误、复盘、规则和复用模式。
2. Standards: installable engineering defaults for docs, planning, validation, and Python / 提供可安装的工程默认约束。
3. Planning: spec, plan, task graph, and validation bundles / 生成 spec、plan、task graph、validation 工件。
4. Validation: docs-check, profile-check, plan-check, doctor, and delivery gates / 提供文档、profile、plan 与交付门禁。

## Why Teams Install Agents-Memory

| Operational Memory | Workflow Discipline | Safer Delivery |
| --- | --- | --- |
| Capture repeated failures, promote rules, and carry engineering context across repos. | Turn freeform requests into bootstrap, planning bundles, and validation-first execution. | Gate changes with docs-check, profile-check, plan-check, CI, and release discipline. |

| 团队记忆沉淀 | 工作流约束 | 更稳的交付 |
| --- | --- | --- |
| 记录重复错误、升级规则，把工程上下文跨仓库复用。 | 把自由需求收敛成 bootstrap、planning bundle 和 validation-first 执行路径。 | 用 docs-check、profile-check、plan-check、CI 和 release discipline 约束交付。 |

## Workflow / 工作流

```text
connect project
	-> bootstrap engineering context
	-> create task bundle
	-> implement with shared standards
	-> run delivery gates
	-> promote lessons back into shared defaults
```

最新架构设计见 docs/ai-engineering-operating-system.md。
安装与启动细节见 docs/getting-started.md。
接入其他项目见 docs/integration.md。
CLI 命令总表见 docs/commands.md。
日常运维与排障见 docs/ops.md。

## Quick Start / 快速开始

```bash
git clone https://github.com/haochencheng/Agents-Memory.git
cd Agents-Memory
python3 -m pip install -e .
amem list
python3 scripts/memory.py docs-check .
python3.12 -m unittest discover -s tests -p 'test_*.py'
```

## Trust Signals / 可信信号

1. [CI](https://github.com/haochencheng/Agents-Memory/actions/workflows/ci.yml) is public and mirrors the local install, compile, test, and docs-check path / CI 公开且与本地安装、编译、测试、docs-check 路径一致。
2. CI is split into `tests` and `docs` jobs for clearer branch protection / CI 已拆分为 `tests` 和 `docs`，便于单独要求通过。
3. [CHANGELOG.md](CHANGELOG.md) and [docs/release-checklist.md](docs/release-checklist.md) govern public release execution / CHANGELOG 与 release checklist 共同约束对外发布流程。
4. [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md), and [CONTRIBUTING.md](CONTRIBUTING.md) define collaboration paths up front / 安全、支持和贡献路径在首页即可追溯。

## Documentation / 文档入口

1. [docs/getting-started.md](docs/getting-started.md): local install, startup, and baseline verification / 本仓库首次安装、启动、基础验证。
2. [docs/integration.md](docs/integration.md): how another repo integrates Agents-Memory / 目标项目如何接入 Agents-Memory。
3. [docs/commands.md](docs/commands.md): CLI command map and parameter reference / CLI 命令总表与参数参考。
4. [docs/ops.md](docs/ops.md): operations, recovery, and troubleshooting / 日常运维、恢复与排障。

Full documentation map / 完整文档地图: [docs/README.md](docs/README.md)

## Open-Source Boundary / 开源边界

Public repository content is limited to code, templates, standards, profiles, and docs. The following are local runtime artifacts and should normally stay uncommitted:

```text
index.md
memory/projects.md
memory/rules.md
errors/*.md
.vscode/mcp.json
logs/
vectors/
```

The repository uses public examples under `templates/` so real project context, private paths, and runtime data do not leak into the open-source tree.

## Contributing / 贡献

Before shipping behavior changes, update code, matching docs, and matching tests or validation scripts together.

Contribution guidance lives in [CONTRIBUTING.md](CONTRIBUTING.md). Pull requests should follow [PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md). Community expectations live in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Security issues should follow [SECURITY.md](SECURITY.md). Support paths are listed in [SUPPORT.md](SUPPORT.md). Releases should update [CHANGELOG.md](CHANGELOG.md) and [docs/release-checklist.md](docs/release-checklist.md).

<a id="en"></a>

## English Snapshot

1. For teams using Copilot or MCP-capable coding agents in real software projects.
2. Core architecture: shared memory, standards, planning bundles, and validation gates.
3. Product baseline: [docs/ai-engineering-operating-system.md](docs/ai-engineering-operating-system.md).
4. Contribution and release flow: [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), and [docs/release-checklist.md](docs/release-checklist.md).

[Back to top](#top)

<a id="zh"></a>

## 中文摘要

1. 适合在真实软件项目里使用 Copilot 或 MCP coding agent 的团队。
2. 核心结构是共享记忆、工程标准、planning bundle 和 validation gate。
3. 最新产品基线见 [docs/ai-engineering-operating-system.md](docs/ai-engineering-operating-system.md)。
4. 贡献与发布流程见 [CONTRIBUTING.md](CONTRIBUTING.md)、[CHANGELOG.md](CHANGELOG.md)、[docs/release-checklist.md](docs/release-checklist.md)。

[返回顶部](#top)

## License / 许可证

This project is released under the MIT License.

本项目采用 MIT License。
