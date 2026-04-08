---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# FE-006: 项目 Wiki 的 Domain 分组错误把 `docs/` 根文件按文件名拆成脏分类

**发现时间:** 2026-04-08  
**严重级别:** medium  
**状态:** resolved

## 问题描述

在真实 `Synapse-Network` 验证中，`/api/projects/synapse-network/wiki-nav` 返回了 `Agents.Md`、`Readme.Md`、`Architecture.Md` 这类不合理的 Domain 分组。

## 根因

首版 `source_group` 规则把 `docs/<file>.md` 的第二段路径直接当作“文档域”，导致 `docs/AGENTS.md`、`docs/README.md` 这类位于 `docs/` 根目录的文件被错误地按文件名生成分组。

## 修复

- 为 `docs/<file>.md` 增加专门规则，统一归入 `Docs Root`
- 同步将其 `document_role` 标记为 `docs-root`
- 重跑 live API 与页面截图验证，确认脏分组消失

## 受影响文件

- `agents_memory/web/api.py`