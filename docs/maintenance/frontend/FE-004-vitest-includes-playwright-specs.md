---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# FE-004: Vitest 错误扫描 Playwright E2E 文件，导致 `npm test` 失败

**发现时间:** 2026-04-08  
**严重级别:** medium  
**状态:** resolved

## 问题描述

执行 `cd frontend && npm test` 时，Vitest 会把 `tests/e2e/**/*.spec.ts` 也纳入测试收集。
这些文件使用的是 Playwright 的 `test.describe()`，因此 Vitest 运行阶段直接报错。

## 根因

`frontend/vitest.config.ts` 没有限定 unit test 的 include 范围，也没有排除 `tests/e2e/`。

## 修复

- 为 Vitest 增加 `include: ['src/test/**/*.{test,spec}.{ts,tsx}']`
- 显式排除 `tests/e2e/**`

## 受影响文件

- `frontend/vitest.config.ts`