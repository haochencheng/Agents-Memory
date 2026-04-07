---
created_at: 2026-03-26
updated_at: 2026-04-07
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

Read in: [English](#en) | [简体中文](#zh)

---

<a id="en"></a>

## English

Agents-Memory is a **Shared Engineering Brain** for AI coding agents. It gives teams a reusable runtime for engineering memory, standards, planning bundles, and validation gates across real repositories.

### Why Teams Install Agents-Memory

| Operational Memory | Workflow Discipline | Safer Delivery |
| --- | --- | --- |
| Capture repeated failures, promote rules, and carry engineering context across repos. | Turn freeform requests into bootstrap, planning bundles, and validation-first execution. | Gate changes with docs-check, profile-check, plan-check, CI, and release discipline. |

### System Architecture

```mermaid
%%{init: {"theme": "default", "flowchart": {"nodeSpacing": 80, "rankSpacing": 100}} }%%
flowchart LR
  U[User / Product Team] --> B[amem bootstrap]
  U --> T[amem start-task]
  A[AI Agent] --> S1[index.md]
  A --> S2[standards]
  A --> S3[profile-managed instructions]
  A --> S4[onboarding-state.json]
  A --> S5[task bundle]

  B --> R[Project Registration]
  B --> P[Profile Install / Refresh]
  B --> I[Bridge and MCP Setup]
  B --> D[Doctor and Onboarding Export]

  P --> PM[profile-manifest.json]
  D --> OS[.agents-memory/onboarding-state.json]
  D --> BC[docs/plans/bootstrap-checklist.md]
  D --> RW[docs/plans/refactor-watch.md]

  T --> TB[docs/plans/task-slug/]
  TB --> SPEC[spec.md]
  TB --> PLAN[plan.md]
  TB --> GRAPH[task-graph.md]
  TB --> VAL[validation.md]

  A --> NX[amem do-next]
  NX --> OS
  NX --> TB

  A --> V[amem validate]
  V --> DC[docs-check]
  V --> PC[profile-check]
  V --> PLC[plan-check]
  V --> TG[focused test gate]
  V --> CG[complexity gate]

  A --> C[amem close-task]
  C --> BG[bundle exit gate]
  C --> GG[global validate gate]
  BG --> TB
  GG --> OS

  A --> L[amem promote-learning]
  L --> ERR[errors]
  L --> RULES[memory/rules.md]
  L --> STD[standards]
  L --> VG[validation rules]
  L --> EVAL[workflow and eval tests]

  classDef user fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a
  classDef agent fill:#ede9fe,stroke:#7c3aed,color:#2e1065
  classDef cmd fill:#d1fae5,stroke:#059669,color:#064e3b
  classDef file fill:#fef3c7,stroke:#d97706,color:#78350f
  classDef gate fill:#fee2e2,stroke:#dc2626,color:#7f1d1d

  class U user
  class A agent
  class B,T,NX,V,C,L cmd
  class S1,S2,S3,S4,S5,PM,OS,BC,RW,TB,SPEC,PLAN,GRAPH,VAL,ERR,RULES,STD,VG,EVAL file
  class R,P,I,D,DC,PC,PLC,TG,CG,BG,GG gate
```

**Five layers inside the Brain:**

| Layer | Responsibility |
| --- | --- |
| **Memory** | Tiered hot / warm / cold error records; keyword + vector hybrid search |
| **Standards** | Shared Python, docs, planning, validation standards; profile-managed instructions |
| **Planning** | spec → plan → task graph → validation bundle; `start-task` / `do-next` / `close-task` |
| **Validation** | Unified delivery gate: docs-check, profile-check, plan-check, test gate, complexity gate |
| **Learning Bus** | Promote errors and good practices to standards, validation rules, and eval cases |

### Knowledge Layer (Wiki) Architecture

The Memory layer includes a structured wiki knowledge graph. This is a **zoom-in on the Memory layer**, not a separate system.

```mermaid
flowchart TD
  subgraph Sources["Sources"]
    E[errors/*.md]
    PR[PR reviews / meeting notes]
    DEC[decision records]
  end

  subgraph Ingest["Ingest Pipeline"]
    ING["amem ingest --type pr-review / decision / meeting"]
    WC[amem wiki-compile --topic X --scope errors]
  end

  subgraph Wiki["memory/wiki/*.md — Knowledge Graph"]
    WP["Wiki Page: topic / compiled_truth / timeline"]
  end

  subgraph Search["Hybrid Search"]
    FTS[FTS index]
    VEC[vector index / LanceDB]
    HS["amem hybrid-search: fts x0.4 + vec x0.6"]
  end

  subgraph Lint["Wiki Lint"]
    L1[orphan pages]
    L2[stale compiled_truth]
    L3[missing cross-links]
  end

  E --> ING
  PR --> ING
  DEC --> ING
  ING --> WC
  WC -- LLM synthesises --> WP
  WP --> FTS
  WP --> VEC
  FTS --> HS
  VEC --> HS
  WP --> L1
  WP --> L2
  WP --> L3

  style Sources fill:#fef3c7,stroke:#d97706
  style Ingest fill:#d1fae5,stroke:#059669
  style Wiki fill:#ede9fe,stroke:#7c3aed
  style Search fill:#dbeafe,stroke:#3b82f6
  style Lint fill:#fee2e2,stroke:#dc2626
```

**Wiki page anatomy** (compiled_truth + append-only timeline):

```markdown
---
topic: finance-safety
compiled_at: 2026-04-07
confidence: high
sources: [AME-001, AME-007]
links:
  - topic: smart-contract-errors
    context: "Reentrancy overlaps with precision rules"
---

## Compiled Truth        ← LLM rewrites on each wiki-compile run
> Consolidated finding: use Decimal, never float for on-chain values.

## Known Patterns
- AME-001: USDT precision loss on transfer

---

## Timeline             ← append-only, never rewritten
- **2026-04-07** | wiki-compile — synthesised from 7 error records
- **2026-03-20** | AME-007 — first recorded precision failure
```

**Wiki commands:**

| Command | Purpose |
| --- | --- |
| `amem wiki-compile --topic X` | LLM synthesises compiled_truth from latest errors |
| `amem wiki-link <from> <to>` | Add cross-reference between topics |
| `amem wiki-backlinks <topic>` | Show all pages linking to this topic |
| `amem wiki-lint` | Detect orphans, stale truths, missing links |
| `amem ingest <file> --type ...` | Structured ingest of PR / meeting / decision records |

**Code layout:**

```text
agents_memory/
├── app.py            # CLI entry point
├── mcp_app.py        # MCP Server entry point
├── runtime.py        # AppContext, path resolution
├── commands/         # CLI dispatch → services
├── services/         # Business logic (records, search, wiki, planning, …)
├── integrations/     # Agent adapters (GitHub Copilot, ChatGPT, Claude)
└── web/              # FastAPI REST API + Streamlit UI (ports 10100 / 10000)
```

### Workflow

```text
connect project
  -> amem bootstrap .          # register + profile + MCP + doctor
  -> amem start-task "<task>"  # spec + plan + task graph + validation bundle
  -> implement with shared standards
  -> amem validate .           # docs + profile + plan + tests + complexity
  -> amem close-task .         # gate + bundle close + onboarding state update
  -> amem promote-learning .   # promote errors / good practices to global defaults
```

### Quick Start

```bash
git clone https://github.com/haochencheng/Agents-Memory.git
cd Agents-Memory
python3 -m pip install -e .

# Verify installation
amem bootstrap . --dry-run
amem validate .

# Run tests
python3.12 -m unittest discover -s tests -p 'test_*.py'

# Start web UI (optional)
bash scripts/web-start.sh start   # FastAPI :10100, Streamlit :10000
```

### Trust Signals

1. [CI](https://github.com/haochencheng/Agents-Memory/actions/workflows/ci.yml) is public and mirrors the local install, compile, test, and docs-check path.
2. CI is split into `tests` and `docs` jobs for clearer branch protection.
3. [CHANGELOG.md](CHANGELOG.md) and [docs/release-checklist.md](docs/release-checklist.md) govern public release execution.
4. [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md), and [CONTRIBUTING.md](CONTRIBUTING.md) define collaboration paths up front.

### Documentation

| Doc | Purpose |
| --- | --- |
| [docs/getting-started.md](docs/getting-started.md) | Local install, startup, and baseline verification |
| [docs/integration.md](docs/integration.md) | How another repo integrates Agents-Memory |
| [docs/commands.md](docs/commands.md) | CLI command map and parameter reference |
| [docs/ops.md](docs/ops.md) | Operations, recovery, and troubleshooting |
| [docs/architecture.md](docs/architecture.md) | Repo-level ADRs and technical decisions |
| [docs/modular-architecture.md](docs/modular-architecture.md) | Code layering, agent adapters, extension points |
| [docs/ai-engineering-operating-system.md](docs/ai-engineering-operating-system.md) | Full product baseline and implementation status |

Full documentation map: [docs/README.md](docs/README.md)

### Open-Source Boundary

Public repository content is limited to code, templates, standards, profiles, and docs. The following are local runtime artifacts and should **not** be committed:

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

### Contributing

Before shipping behavior changes, update code, matching docs, and matching tests or validation scripts together.

Contribution guidance lives in [CONTRIBUTING.md](CONTRIBUTING.md). Pull requests should follow [PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md). Community expectations live in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Security issues should follow [SECURITY.md](SECURITY.md). Support paths are listed in [SUPPORT.md](SUPPORT.md). Releases should update [CHANGELOG.md](CHANGELOG.md) and [docs/release-checklist.md](docs/release-checklist.md).

[Back to top](#top)

---

<a id="zh"></a>

## 简体中文

Agents-Memory 是面向 AI coding agents 的 **Shared Engineering Brain**。它把工程记忆、工程标准、planning bundle 和 validation gate 收敛成可复用的共享运行层，服务真实仓库而不是零散 prompt 片段。

### 为什么团队会安装 Agents-Memory

| 团队记忆沉淀 | 工作流约束 | 更稳的交付 |
| --- | --- | --- |
| 记录重复错误、升级规则，把工程上下文跨仓库复用。 | 把自由需求收敛成 bootstrap、planning bundle 和 validation-first 执行路径。 | 用 docs-check、profile-check、plan-check、CI 和 release discipline 约束交付。 |

### 系统架构全图

```mermaid
%%{init: {"theme": "default", "flowchart": {"nodeSpacing": 80, "rankSpacing": 100}} }%%
flowchart LR
  U[用户 / 产品团队] --> B[amem bootstrap]
  U --> T[amem start-task]
  A[AI Agent] --> S1[index.md]
  A --> S2[standards 工程标准]
  A --> S3[profile 受管 instructions]
  A --> S4[onboarding-state.json]
  A --> S5[task bundle 任务工件]

  B --> R[项目注册]
  B --> P[Profile 安装 / 刷新]
  B --> I[Bridge 与 MCP 安装]
  B --> D[Doctor 与 Onboarding 导出]

  P --> PM[profile-manifest.json]
  D --> OS[.agents-memory/onboarding-state.json]
  D --> BC[docs/plans/bootstrap-checklist.md]
  D --> RW[docs/plans/refactor-watch.md]

  T --> TB[docs/plans/task-slug/]
  TB --> SPEC[spec.md]
  TB --> PLAN[plan.md]
  TB --> GRAPH[task-graph.md]
  TB --> VAL[validation.md]

  A --> NX[amem do-next]
  NX --> OS
  NX --> TB

  A --> V[amem validate]
  V --> DC[docs-check]
  V --> PC[profile-check]
  V --> PLC[plan-check]
  V --> TG[focused test gate]
  V --> CG[complexity gate]

  A --> C[amem close-task]
  C --> BG[bundle exit gate]
  C --> GG[global validate gate]
  BG --> TB
  GG --> OS

  A --> L[amem promote-learning]
  L --> ERR[errors 错误记录]
  L --> RULES[memory/rules.md]
  L --> STD[standards 工程标准]
  L --> VG[validation rules]
  L --> EVAL[workflow & eval tests]

  classDef user fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a
  classDef agent fill:#ede9fe,stroke:#7c3aed,color:#2e1065
  classDef cmd fill:#d1fae5,stroke:#059669,color:#064e3b
  classDef file fill:#fef3c7,stroke:#d97706,color:#78350f
  classDef gate fill:#fee2e2,stroke:#dc2626,color:#7f1d1d

  class U user
  class A agent
  class B,T,NX,V,C,L cmd
  class S1,S2,S3,S4,S5,PM,OS,BC,RW,TB,SPEC,PLAN,GRAPH,VAL,ERR,RULES,STD,VG,EVAL file
  class R,P,I,D,DC,PC,PLC,TG,CG,BG,GG gate
```

**五层核心能力：**

| 层级 | 职责 |
| --- | --- |
| **Memory** | 三层分级记忆（热 / 温 / 冷）；关键词 + 向量混合搜索 |
| **Standards** | 共享 Python、docs、planning、validation 标准；profile 受管 instructions |
| **Planning** | spec → plan → task graph → validation bundle；start-task / do-next / close-task |
| **Validation** | 统一交付门禁：docs-check、profile-check、plan-check、test gate、complexity gate |
| **Learning Bus** | 把错误和最佳实践升级为跨项目 standards、validation rules、eval cases |

### 知识层（Wiki）架构

Memory 层内置结构化 Wiki 知识图谱，是对上方系统架构图中 Memory 层的纵向展开，**不是独立系统**。

```mermaid
flowchart TD
  subgraph Sources["输入源"]
    E[errors/*.md 错误记录]
    PR[PR review / 会议记录]
    DEC[决策记录]
  end

  subgraph Ingest["Ingest 流水线"]
    ING["amem ingest --type pr-review / decision / meeting"]
    WC[amem wiki-compile --topic X --scope errors]
  end

  subgraph Wiki["memory/wiki/*.md — 知识图谱"]
    WP["Wiki 页面: topic / compiled_truth / timeline"]
  end

  subgraph Search["混合搜索"]
    FTS[FTS 全文索引]
    VEC[向量索引 / LanceDB]
    HS["amem hybrid-search: fts x0.4 + vec x0.6"]
  end

  subgraph Lint["Wiki 健康检查"]
    L1[孤岛页面检测]
    L2[过期结论检测]
    L3[缺失交叉引用检测]
  end

  E --> ING
  PR --> ING
  DEC --> ING
  ING --> WC
  WC -- LLM合成 --> WP
  WP --> FTS
  WP --> VEC
  FTS --> HS
  VEC --> HS
  WP --> L1
  WP --> L2
  WP --> L3

  style Sources fill:#fef3c7,stroke:#d97706
  style Ingest fill:#d1fae5,stroke:#059669
  style Wiki fill:#ede9fe,stroke:#7c3aed
  style Search fill:#dbeafe,stroke:#3b82f6
  style Lint fill:#fee2e2,stroke:#dc2626
```

**Wiki 页面结构**（compiled_truth 结论区 + append-only 时间线）：

```markdown
---
topic: finance-safety
compiled_at: 2026-04-07
confidence: high
sources: [AME-001, AME-007]
links:
  - topic: smart-contract-errors
    context: "Reentrancy 与精度规则有重叠"
---

## 结论（Compiled Truth）        ← LLM 每次 wiki-compile 时整体重写
> 综合评估：链上金额运算必须用 Decimal，禁止使用 float。

## 已知 Pattern
- AME-001：USDT transfer 精度丢失

---

## 时间线                        ← 只追加，永不改写
- **2026-04-07** | wiki-compile — 从 7 条错误记录合成
- **2026-03-20** | AME-007 — 首次记录精度问题
```

**Wiki 命令：**

| 命令 | 作用 |
| --- | --- |
| `amem wiki-compile --topic X` | LLM 从最近错误合成 compiled_truth |
| `amem wiki-link <from> <to>` | 建立 topic 之间的交叉引用 |
| `amem wiki-backlinks <topic>` | 查看哪些页面引用了当前 topic |
| `amem wiki-lint` | 检测孤岛页、过期结论、缺失链接 |
| `amem ingest <file> --type ...` | 结构化导入 PR / 会议记录 / 决策文档 |

**代码分层：**

```text
agents_memory/
├── app.py            # CLI 总入口
├── mcp_app.py        # MCP Server 总入口
├── runtime.py        # AppContext，路径解析
├── commands/         # CLI 分发 → services
├── services/         # 业务逻辑（records、search、wiki、planning 等）
├── integrations/     # Agent adapters（GitHub Copilot、ChatGPT、Claude）
└── web/              # FastAPI REST API + Streamlit UI（端口 10100 / 10000）
```

### 工作流

```text
连接项目
  -> amem bootstrap .          # 注册 + profile + MCP + doctor
  -> amem start-task "<task>"  # spec + plan + task graph + validation bundle
  -> 按共享标准实现
  -> amem validate .           # docs + profile + plan + tests + complexity
  -> amem close-task .         # gate + bundle 关闭 + onboarding state 更新
  -> amem promote-learning .   # 把错误 / 最佳实践升级到全局默认
```

### 快速开始

```bash
git clone https://github.com/haochencheng/Agents-Memory.git
cd Agents-Memory
python3 -m pip install -e .

# 验证安装
amem bootstrap . --dry-run
amem validate .

# 运行测试
python3.12 -m unittest discover -s tests -p 'test_*.py'

# 启动 Web UI（可选）
bash scripts/web-start.sh start   # FastAPI :10100，Streamlit :10000
```

### 可信信号

1. [CI](https://github.com/haochencheng/Agents-Memory/actions/workflows/ci.yml) 是公开的，执行的就是本地会跑的安装、编译、测试和 `docs-check`。
2. CI 已拆成独立的 `tests` 和 `docs` jobs，便于 branch protection 单独要求通过。
3. [CHANGELOG.md](CHANGELOG.md) 和 [docs/release-checklist.md](docs/release-checklist.md) 共同约束公开发版流程。
4. [SECURITY.md](SECURITY.md)、[SUPPORT.md](SUPPORT.md) 和 [CONTRIBUTING.md](CONTRIBUTING.md) 让协作路径在首页即可追溯。

### 文档入口

| 文档 | 说明 |
| --- | --- |
| [docs/getting-started.md](docs/getting-started.md) | 首次安装、启动、基础验证 |
| [docs/integration.md](docs/integration.md) | 目标项目如何接入 Agents-Memory |
| [docs/commands.md](docs/commands.md) | CLI 命令总表与参数参考 |
| [docs/ops.md](docs/ops.md) | 日常运维、恢复与排障 |
| [docs/architecture.md](docs/architecture.md) | 仓库级 ADR 与技术决策 |
| [docs/modular-architecture.md](docs/modular-architecture.md) | 代码分层、agent adapter 扩展点 |
| [docs/ai-engineering-operating-system.md](docs/ai-engineering-operating-system.md) | 完整产品基线与实施状态矩阵 |

完整文档地图见 [docs/README.md](docs/README.md)。

最新架构设计见 docs/ai-engineering-operating-system.md。
安装与启动细节见 docs/getting-started.md。
接入其他项目见 docs/integration.md。

公开仓库只包含代码、模板、标准、profiles 和文档。以下内容属于本地运行数据，**默认不应提交**：

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

### 贡献

提交行为变更前，请同步更新代码、对应文档以及对应测试或验证脚本。

贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。提交合并请求时请按 [PULL_REQUEST_TEMPLATE.md](PULL_REQUEST_TEMPLATE.md) 补齐验证信息；协作行为遵循 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)；安全问题请按 [SECURITY.md](SECURITY.md) 私下报告；支持入口见 [SUPPORT.md](SUPPORT.md)；发布时同步维护 [CHANGELOG.md](CHANGELOG.md) 和 [docs/release-checklist.md](docs/release-checklist.md)。

[返回顶部](#top)

---

## License / 许可证

This project is released under the [MIT License](LICENSE).

本项目采用 [MIT License](LICENSE)。
