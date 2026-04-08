---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# Plan Bundle

## Task

为大文档项目的 Project Detail 页面提供可扩展的 wiki 导航结构。

## Outcome

- `ProjectDetail` 从单一平铺卡片列表升级为适合 100+ 文档浏览的知识导航页。
- 导航同时支持稳定的物理目录树与更易读的规范分组视图。
- 首版不依赖 LLM 才能工作，但为后续 agent / LLM 生成分组建议预留数据结构。

## Scope

- Backend：新增单项目 wiki 导航索引接口
- Frontend：在项目详情页增加 `Tree / Domain / List` 视图切换
- Docs：补充产品设计、接入策略、维护记录与验证证据
- Validation：后端 API 测试、前端组件测试、真实页面截图验证

## Acceptance Criteria

- [x] `/api/projects/{id}/wiki-nav` 返回单项目的导航索引数据
- [x] `ProjectDetail` 默认不再只渲染平铺 wiki 卡片列表
- [x] 页面支持 `Tree` 与 `Domain` 两种结构化浏览方式
- [x] `Synapse-Network` 项目页可稳定展示 127 篇 wiki 的结构化视图
- [x] 自动化测试与截图验证覆盖新导航能力