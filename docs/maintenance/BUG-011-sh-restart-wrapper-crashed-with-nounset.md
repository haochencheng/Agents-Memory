---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# BUG-011 `sh` 执行 restart wrapper 时在 `set -u` 下触发未绑定变量

## 现象

执行：

```bash
sh scripts/runtime/restart.sh
```

直接报错：

```text
scripts/runtime/restart.sh: line 7: @: unbound variable
```

`scripts/web/restart.sh` 存在相同风险。

## 根因

wrapper 脚本在 `set -euo pipefail` 下使用了 `"${@}"`。  
当脚本被 `sh` 调起且没有任何位置参数时，`dash` 会把 `${@}` 视为未绑定变量，从而在 `-u` 模式下直接退出。

## 修复

- 把 wrapper 里的 `"${@}"` 改成 `"$@"`
- 为 `local / staging / prod` 新增独立目录入口，减少用户直接在杂乱脚本里找环境入口的成本

## 回归验证

```bash
sh scripts/runtime/restart.sh
bash scripts/local/runtime.sh config --json
bash scripts/staging/web.sh config --json
bash scripts/prod/restart.sh
```
