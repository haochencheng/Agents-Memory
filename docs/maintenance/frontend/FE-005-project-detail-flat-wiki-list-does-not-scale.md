---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# FE-005: 项目详情页的纯平铺 Wiki 列表在大项目下不可扩展

**发现时间:** 2026-04-08  
**严重级别:** medium  
**状态:** resolved

## 问题描述

当单项目 wiki 页面数量上升到 100+ 时，`/projects/:id` 继续把所有 wiki 页面直接平铺成卡片列表，会导致页面滚动距离过长、定位成本过高、结构关系不可见。

## 根因

前端虽然已经拿到了 wiki 页面的 `source_path` 元数据，但项目详情页没有把这层路径信息转换为可浏览的目录树或分组导航，导致数据规模一上来就退化成长列表。

## 修复

- 新增项目级 wiki 导航索引接口
- 项目详情页增加 `Tree / Domain / List` 三种浏览视图
- 默认优先展示结构化导航，而不是单一平铺列表

## 受影响文件

- `agents_memory/web/api.py`
- `agents_memory/web/models.py`
- `frontend/src/api/useProjects.ts`
- `frontend/src/pages/dashboard/ProjectDetail.tsx`