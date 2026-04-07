---
created_at: 2026-03-26
updated_at: 2026-04-07
doc_status: active
---

# Agents-Memory 项目文档

> Shared Engineering Brain for AI coding agents：Memory + Standards + Planning + Validation。

## 文档目录结构

```
docs/
├── README.md                            ← 本文档（导航总览）
├── product/                             ← 产品愿景与系统定位
│   └── ai-engineering-operating-system.md
├── architecture/                        ← 架构决策与分析（ADR）
│   ├── overview.md                      ← 仓库级 ADR 与技术取舍
│   ├── modular.md                       ← 代码分层与插件扩展点
│   └── analysis.md                      ← 架构分析与优化报告
├── guides/                              ← 使用指南（How-to）
│   ├── getting-started.md               ← 首次安装与启动
│   ├── integration.md                   ← 目标项目接入流程
│   ├── commands.md                      ← CLI 命令总表
│   ├── model-selection.md               ← 本地模型选型
│   └── copilot-auto-activation.md       ← Copilot 自动激活设计
├── ops/                                 ← 运维与发布
│   ├── runbook.md                       ← 日常运维与故障处理
│   ├── release-checklist.md             ← 发版检查清单
│   ├── foundation-hardening.md          ← 工程约束与强化规则
│   └── stale-cleanup.md                 ← 过期内容清理
├── frontend/                            ← 前端设计文档
│   ├── 00-ui-design.md                  ← 前端 UI 设计方案
│   └── 01~08-*.md                       ← 技术栈、架构、API、计划等
├── plans/                               ← 开发计划与任务追踪
│   └── phase1~5-*.md / [task-slug]/
└── maintenance/                         ← 维护记录
    ├── BUG-*.md
    └── frontend/
```

## 文档分类说明

| 目录 | 用途 | 受众 |
|------|------|------|
| `product/` | 产品愿景、系统定位、实施状态 | 产品 + 工程 |
| `architecture/` | 为什么这样设计（ADR） | 工程 |
| `guides/` | 如何使用（How-to） | 开发者 |
| `ops/` | 如何运维（Runbook） | 运维 + 工程 |
| `frontend/` | 前端产品与技术设计 | 前端工程 |
| `plans/` | 需求规划与任务追踪 | 工程 |
| `maintenance/` | Bug 修复与重构记录 | 工程 |

## 快速入口

- [产品定位与系统基线](product/ai-engineering-operating-system.md)
- [首次安装与启动](guides/getting-started.md)
- [接入其他项目](guides/integration.md)
- [CLI 命令总表](guides/commands.md)
- [运维手册](ops/runbook.md)
- [发布检查清单](ops/release-checklist.md)
- [架构决策（ADR）](architecture/overview.md)
- [模块化结构](architecture/modular.md)
- [前端产品设计](frontend/08-product-frontend-design.md)
- [Planning Bundle Example](plans/planning-governance-gate/README.md)
- [Onboarding Bundle Example](plans/onboarding-copilot-activation/README.md)
