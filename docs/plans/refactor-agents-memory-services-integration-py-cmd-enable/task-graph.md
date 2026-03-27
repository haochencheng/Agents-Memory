---
created_at: 2026-03-27
updated_at: 2026-03-27
doc_status: active
---

# Task Graph

## Work Items

1. 读清 `cmd_enable` 的分支和状态写回路径
2. 拆出 dry-run / profile / follow-up helper
3. 回归验证 `enable` 相关测试
4. 补 planning bundle 与最终校验

## Dependencies

- 先完成 helper 提取，再跑行为测试
- planning bundle 可以在代码稳定后补写

## Exit Criteria

- `cmd_enable` 不再是 `doctor` 的首要热点
- 现有 `enable` 行为测试全部通过
- planning bundle 文件完整

## Refactor Work Items
```json
[
  {
    "step": 1,
    "title": "Extract preview and validation helpers",
    "done_when": "cmd_enable no longer contains preview rendering and request validation details."
  },
  {
    "step": 2,
    "title": "Extract full-mode follow-up persistence",
    "done_when": "Refactor bundle persistence and onboarding-state writes are encapsulated behind a helper."
  },
  {
    "step": 3,
    "title": "Re-run validation",
    "done_when": "Focused tests and doctor confirm no behavior regression and cmd_enable leaves refactor_watch."
  }
]
```
