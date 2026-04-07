---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# FE-002: `datetime.utcnow()` deprecated in Python 3.12

**发现时间:** 2026-04-07  
**严重级别:** low (deprecation warning, not runtime failure)  
**状态:** resolved

## 问题描述

`agents_memory/web/api.py` 在 ingest 端点中调用 `datetime.utcnow()`：

```
DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled 
for removal in a future version.
```

## 根因

Python 3.12 将 `datetime.utcnow()` 标为 deprecated，推荐使用 timezone-aware 对象。

## 修复

```python
# Before
"ts": datetime.utcnow().isoformat() + "Z",
# After
from datetime import datetime, timezone
"ts": datetime.now(timezone.utc).isoformat(),
```

## 防止复发

- **约束（已添加到 rules.md）:** 所有新代码使用 `datetime.now(timezone.utc)` 而非 `datetime.utcnow()`。

## 受影响文件

- `agents_memory/web/api.py` — `ingest()` 函数
