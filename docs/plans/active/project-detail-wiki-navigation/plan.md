---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# Execution Plan

## Scope

- 影响后端：`agents_memory/web/api.py`、`agents_memory/web/models.py`
- 影响前端：`frontend/src/api/useProjects.ts`、`frontend/src/pages/dashboard/ProjectDetail.tsx`
- 新增测试：`tests/test_web_api.py`、前端项目详情页测试
- 影响文档：前端设计、接入指南、maintenance bugfix、active plan bundle

## Design Notes

- 目录树必须由 `source_path` 规则生成，保证稳定、可追溯。
- `Domain` 分组首版使用 deterministic 规则，而不是直接调用 LLM。
- API 直接返回导航索引，避免前端重复实现路径解析和分组逻辑。
- 项目页保留已有统计卡，wiki 浏览区升级为 `Tree / Domain / List` 三种模式。

## Change Set

- 新增项目级 wiki 导航响应模型
- 新增 `/api/projects/{id}/wiki-nav` 接口
- 项目详情页增加视图切换与树形导航渲染
- 补充前后端自动化测试
- 记录 flat list 可用性问题到 frontend maintenance bugfix

## Rollout Notes

- 先以 `Synapse-Network` 作为真实大文档项目验证数据规模
- 规则分组首版先覆盖 `Root Docs / Architecture / Workflow / Guides / Ops / Plans / Other`
- 目录树默认折叠深层节点，减少页面初次渲染负担
- LLM/agent 分组建议仅保留在文档方案层，不在本次代码实现里引入额外依赖