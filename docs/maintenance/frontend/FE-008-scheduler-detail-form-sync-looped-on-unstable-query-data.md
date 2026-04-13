---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# FE-008: SchedulerDetail 的表单同步依赖整个 query 对象会导致渲染循环

**发现时间:** 2026-04-13  
**严重级别:** medium  
**状态:** resolved

## 问题描述

在给 `SchedulerDetail` 新增 `vitest` 详情页测试时，测试进程无法结束；页面渲染后没有报错，但 Vitest 会一直挂住。

## 根因

详情页初版通过 `useEffect(..., [data])` 把 `data.task_group` 回写到本地 `form` state。只要 hook 返回的 `data` 对象引用不稳定，即使字段值没变，也会重复触发 effect，进而持续 `setForm`，形成渲染循环。

## 修复

- 把 effect 依赖从整个 `data` 对象改成稳定字段
- 在 `setForm` 里增加幂等比较；字段未变化时直接返回 `current`
- 补 `SchedulerDetailPage.test.tsx` 回归，覆盖详情渲染和编辑提交流程

## 受影响文件

- `frontend/src/pages/dashboard/SchedulerDetail.tsx`
- `frontend/src/test/SchedulerDetailPage.test.tsx`
