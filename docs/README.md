---
created_at: 2026-03-26
updated_at: 2026-03-27
doc_status: active
---

# Agents-Memory 项目文档

> Shared Engineering Brain for AI coding agents：Memory + Standards + Planning + Validation。

## 文档边界

- [AI Engineering Operating System](ai-engineering-operating-system.md)：产品定位、系统基线、顶层 workflow、状态机、实施状态。
- [架构决策](architecture.md)：repo 级实现决策与技术取舍，不重复产品定位和系统总设计。
- [模块化与插件化结构](modular-architecture.md)：代码目录结构、模块分层、插件扩展点，不重复 ADR 技术取舍。
- [接入其他项目](integration.md)：目标项目如何接入、验证、排错，不重复仓库内部代码分层。
- [CLI 命令总表](commands.md)：命令签名、参数与按域分组参考，不展开接入步骤。
- [本地启动指南](getting-started.md)：本仓库如何首次安装、启动、做基础验证，不展开日常运维与目标项目接入流程。
- [运维与故障处理](ops.md)：日志、索引、Qdrant、备份、恢复与日常排障，不重复首次安装与目标项目接入。

## 目录

- [功能概述](#功能概述)
- [快速开始](#快速开始)
- [三层记忆架构](#三层记忆架构)
- [CLI 命令参考](#cli-命令参考)
- [自我进化闭环](#自我进化闭环)
- [向量搜索扩展](#向量搜索扩展)
- [本地启动与运维](getting-started.md)
- [运维与故障处理](ops.md)
- [CLI 命令总表](commands.md)
- [接入其他项目](integration.md)
- [Copilot 自动激活设计](copilot-auto-activation.md)
- [模块化与插件化结构](modular-architecture.md)
- [AI Engineering Operating System](ai-engineering-operating-system.md)
- [Planning Bundle Example](plans/planning-governance-gate/README.md)
- [Onboarding Bundle Example](plans/onboarding-copilot-activation/README.md)
- [Foundation Hardening Plan](foundation-hardening.md)
- [Stale Cleanup Inventory](stale-cleanup.md)
- [Top-Level Command Model](ai-engineering-operating-system.md#顶层命令模型)
- [State Machine Design](ai-engineering-operating-system.md#状态机设计)
- [Artifact Model](ai-engineering-operating-system.md#工件模型)
- [System Architecture](ai-engineering-operating-system.md#系统架构图)
- [Repo Implementation Plan](ai-engineering-operating-system.md#repo-级实施方案)
- [架构决策（Repo ADR）](architecture.md)
