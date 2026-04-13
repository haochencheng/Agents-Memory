---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# BUG-010 web-start status 在 API 接管分支里触发未绑定变量

## Summary

给 `scripts/web-start.sh` 增加“接管兼容 API / 替换旧版 API”逻辑后，`bash scripts/web-start.sh status` 在某条端口占用分支下会直接报 `unbound variable`。

## Trigger

- 运行一个兼容的 `agents_memory.web.api`，但暂时没有 `.web_api.pid`
- 再执行 `bash scripts/web-start.sh status`

## Root Cause

`cmd_status` 在 `set -u` 模式下引用了局部变量 `pid`，而这条分支里的变量处理不够稳健；一旦状态检查命中端口占用分支，脚本会因为未绑定变量直接退出。

## Fix

1. 把该分支里的变量改成更明确的 `port_pid`
2. 统一走 `_port_pid` 解析监听 PID
3. 重新跑 `status` / `api` / `health` 串联验证，确认接管逻辑和状态展示都正常

## Rule

给 `set -u` 的 shell 脚本补状态分支时，不要依赖模糊局部变量；端口探测值应单独命名，并在同一分支内完成赋值和消费。
