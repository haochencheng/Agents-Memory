---
created_at: 2026-03-26
updated_at: 2026-03-27
doc_status: active
---

# Standards Check Rules

1. 新 Python 逻辑是否遵守 commands / services / integrations / runtime 分层
2. 是否违反 DRY，重复实现同类逻辑
3. 是否新增无法测试的关键业务逻辑
4. 是否把本应进入 standards 的规则散落到 README 临时说明中