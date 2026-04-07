---
created_at: 2026-03-26
updated_at: 2026-04-08
doc_status: active
---

# Docs Check Rules

第一版文档校验至少应覆盖：

1. docs 入口文件存在性
2. `docs/README.md` 中引用的文件存在性
3. README 与 getting-started 中命令列表的一致性
4. `llms.txt` 中的 repo map 与真实路径一致性
5. 过期结构或私有绝对路径引用告警

通过标准：

1. 无缺失文件引用
2. 无关键命令文档漂移
3. 无明显已废弃但未标记的结构说明

## 计划管理规则

6. `docs/plans/` 下必须存在 `active/` 和 `archive/` 两个子目录
7. 已完成计划须移入 `archive/`，进行中保留在 `active/`
8. `docs/plans/README.md` 须反映当前 active/archive 分类状态

## 前端文档规则

9. E2E 测试计划须存放于 `docs/test/frontend/`
10. 前端端口约定：dev server `:10000`，API proxy → `:10100`