---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# FE-003: 项目详情页读取了错误的路由参数，导致接入项目详情不可用

**发现时间:** 2026-04-08  
**严重级别:** medium  
**状态:** resolved

## 问题描述

路由定义为 `/projects/:id`，但 `ProjectDetail` 页面使用 `useParams<{ name: string }>()` 读取参数。
结果是页面请求统计时拿到空字符串，接入后的项目详情页无法正确展示真实数据。

## 根因

路由参数命名与页面读取字段在重构过程中发生漂移，导致前端请求 `/api/projects/{id}/stats` 时使用了错误的 project id。

## 修复

- `ProjectDetail` 改为读取 `id`
- wiki 过滤逻辑改为使用返回的 `project` 字段
- 补充 `last_ingest` 展示，便于接入成功验证

## 受影响文件

- `frontend/src/pages/dashboard/ProjectDetail.tsx`