---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# FE-009 SchedulerDetail 分页后在 loading → loaded 切换时触发 Hook 顺序错误

## 现象

打开：

```text
/scheduler/:id
```

页面直接白屏，浏览器控制台报：

```text
Rendered more hooks than during the previous render.
```

## 根因

`SchedulerDetail.tsx` 在新增执行历史分页后，把 `useMemo(...)` 放在了：

```tsx
if (isLoading) return ...
if (error || !data?.task_group) return ...
```

之后。

首次渲染如果走 `loading` 分支，后续加载完成后再执行到 `useMemo`，就会导致同一个组件在不同渲染阶段调用的 Hook 数量不一致，React 直接抛错并中断渲染。

## 修复

- 去掉这个不必要的 `useMemo`
- 在 early return 之前统一计算 `resolvedTaskGroup / runs / runPageNumbers`
- 补一个“先 loading 再 loaded”的前端回归测试

## 回归验证

```bash
npm exec vitest run src/test/SchedulerDetailPage.test.tsx
node scripts/... 打开 /scheduler/:id 不再白屏
```
