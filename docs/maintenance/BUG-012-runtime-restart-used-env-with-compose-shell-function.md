---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# BUG-012 runtime restart 把 `compose` shell 函数当成外部命令调用

## 现象

执行：

```bash
sh scripts/runtime/restart.sh
```

会在停止或启动容器阶段失败：

```text
env: compose: No such file or directory
```

## 根因

`scripts/runtime/manage.sh` 里定义了一个 shell 函数 `compose()`，内部再分发到 `docker-compose` 或 `docker compose`。  
但 `start_qdrant` / `start_ollama` / `stop_services` 前面用了：

```bash
env QDRANT_PORT=... compose ...
```

`env` 只能执行外部命令，不能调用 shell 函数，所以 `compose` 被当成不存在的二进制而失败。

## 修复

- 改成 shell 原生的前缀变量赋值：

```bash
QDRANT_PORT=... compose up -d qdrant
OLLAMA_PORT=... compose stop ollama
```

这样既保留了环境覆盖，也能正确调用 shell 函数。

## 回归验证

```bash
sh scripts/runtime/restart.sh
sh scripts/local/runtime.sh status
.venv/bin/python -m unittest tests.test_script_env_config -v
```
