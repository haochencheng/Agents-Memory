---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# FE-007: Knowledge Graph 页面的焦点节点 state 回写让渲染测试卡住

**发现时间:** 2026-04-13  
**严重级别:** medium  
**状态:** resolved

## 问题描述

在为新的 `Schema / Explore / Table` 图谱页补 `vitest` 测试时，最基础的 schema 渲染用例无法结束，测试进程会卡住。

## 根因

页面初版通过 `useEffect` 把 `explore.focusNode` 反向写回 `selectedId` state。虽然浏览器里看起来可用，但这种“从派生结果再回写 state”的同步方式让测试环境更容易进入持续更新状态。

## 修复

- 去掉 `explore.focusNode -> selectedId` 的 effect 回写
- 让 Explore 焦点优先从 `selectedId || requestedNodeId` 派生
- 只有用户显式点击节点时才更新 `selectedId`
- 补 `KnowledgeGraphPage.test.tsx` 回归测试，覆盖 schema / explore / table 三个视图

## 受影响文件

- `frontend/src/pages/wiki/KnowledgeGraphPage.tsx`
- `frontend/src/test/KnowledgeGraphPage.test.tsx`
