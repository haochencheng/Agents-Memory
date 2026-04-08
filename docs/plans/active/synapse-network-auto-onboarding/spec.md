---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# Spec

## Task

为外部项目提供可验证的一键接入路径，并使用 `Synapse-Network` 作为真实案例。

## Problem

- 现有 `amem bootstrap .` 已能完成基础纳管，但尚未把“项目知识导入 wiki”纳入同一条自动化链路。
- 前端 `/wiki/ingest` 当前只支持文本内容摄入，不能直接基于项目路径执行自动接入与项目文档导入。
- 项目列表 / 项目详情页对 wiki 与 ingest 的统计仍偏向全局视图，无法稳定反映单个项目的接入完成度。

## Goal

- 提供一条面向真实仓库的自动接入工作流：注册项目、应用 profile / standards、生成 onboarding 工件、自动导入项目知识源。
- 暴露 CLI 与 API 两个入口，使自动接入既能在终端完成，也能从前端页面触发。
- 让前端首页、项目页、wiki ingest 页都能直接反映接入成功状态。

## Non-Goals

- 不在本次实现中引入新的向量索引或远程知识库依赖。
- 不自动修改目标项目业务代码，仅写入接入所需配置与 Agents-Memory 工件。
- 不把任意非 Markdown 资产纳入首版项目知识导入范围。

## Acceptance Criteria

- [ ] `amem bootstrap <path> --full --ingest-wiki` 可完成一键接入与项目文档摄取
- [ ] API 提供项目路径驱动的自动接入入口，供前端 `/wiki/ingest` 使用
- [ ] wiki 页面 frontmatter 带有 `project` 与 `source_path` 元数据，项目页可按项目过滤展示
- [ ] `/api/projects`、`/api/projects/{id}/stats`、`/api/wiki` 返回的统计和元数据可支撑前端接入成功展示
- [ ] `Synapse-Network` 实跑后能在 dashboard / projects / wiki ingest 页面看到接入结果