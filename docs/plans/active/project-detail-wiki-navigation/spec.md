---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# Spec

## Task

把 `http://localhost:10000/projects/synapse-network` 上过多的 wiki 页面，升级为适合大仓库浏览的结构化导航。

## Problem

- 当前项目详情页把该项目全部 wiki 页面平铺为卡片列表。
- 当项目 wiki 页面增长到 100+ 时，用户必须长距离滚动才能定位目标文档。
- 现有页面虽然有 `source_path` 元数据，但没有把它转换成可浏览的目录树或知识分组。

## Goal

- 保留现有 wiki 页面与 `source_path` 真源，不引入会漂移的“虚构目录”。
- 新增稳定的目录树导航，帮助用户按真实文档位置浏览。
- 新增规则驱动的 `Domain` 分组，让用户按知识域而不是物理路径浏览。
- 为后续 LLM / agent 提供可扩展的索引层，但不让模型成为结构真源。

## Non-Goals

- 本次不把文档物理移动到新的仓库目录。
- 本次不实现完全自动的 LLM 目录重写器。
- 本次不替换已有 `Knowledge Graph` 页面。

## Acceptance Criteria

- [x] API 可返回单项目导航索引，至少包含 `items / tree / groups`
- [x] 前端项目详情页默认展示结构化导航，而不是纯平铺长列表
- [x] `Tree` 视图按 `source_path` 展开并可看到叶子 wiki 页面
- [x] `Domain` 视图按规则分组展示 `Root Docs / Architecture / Ops / Plans / ...`
- [x] 自动化测试覆盖新接口与主要前端交互
- [x] `Synapse-Network` 实跑截图可见结构化导航结果