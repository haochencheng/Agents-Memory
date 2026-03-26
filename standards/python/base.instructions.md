# Python Baseline

适用范围：所有 Python 模块、CLI、services、runtime、MCP 相关代码。

## 目标

1. 保持可读性优先
2. 保持 agent 可理解性优先
3. 保持边界清晰、职责稳定

## 基线规则

1. Python 版本基线：3.10+
2. 新逻辑优先写在 `agents_memory/services/`，而不是 `scripts/` 包装层
3. 命令分发逻辑只放在 `agents_memory/commands/`
4. 路径解析、logger、bootstrap 只放在 `agents_memory/runtime.py`
5. 不允许把复杂业务逻辑重新塞回 `scripts/*.py`
6. 模块职责必须单一，优先小文件而不是大杂烩

## 可维护性要求

1. 优先显式数据流，避免隐式全局状态
2. 优先命名清晰的 helper，而不是堆叠长函数
3. I/O 与纯逻辑尽量分离，便于单元测试
4. 公共行为抽到共享函数，不复制粘贴逻辑