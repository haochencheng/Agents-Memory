---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# BUG-013 web restart 遇到兼容但未托管的 Vite 进程时不会接管或替换

## 现象

执行：

```bash
sh scripts/local/web.sh restart
```

如果 `10000` 端口已经被本仓库自己的 Vite dev server 占用，但没有写入 `.web_ui.local.pid`，脚本只会提示：

```text
端口 10000 已被占用（可能已有前端运行）
```

然后停止在半托管状态，既不会接管 PID，也不会在 `restart` 时真正重启前端。

## 根因

`scripts/web/manage.sh` 只对 API 端口做了“兼容进程识别 / 接管 / 替换旧进程”逻辑；UI 端口仍然只有简单的“检测到占用就跳过”分支。

## 修复

- 新增 `_is_agents_memory_ui_pid`
- 新增 `_ensure_expected_ui_on_port`
- `start_ui` 现在会识别本仓库自己的 Vite 进程并接管 PID
- `restart` 路径会显式替换兼容但未托管的旧 UI 进程

## 回归验证

```bash
sh scripts/local/web.sh restart
sh scripts/local/web.sh status
```
