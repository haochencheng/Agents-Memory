# Validation Rules

文档验证：

1. docs entrypoint 完整
2. 关键命令文档一致
3. deprecated 内容已删除或显式标记

代码验证：

1. `py_compile` 通过
2. 核心 services 有单元测试
3. 关键 CLI 流程至少有 smoke test

同步验证：

1. 行为变更必须同时看到 code diff、docs diff、test diff 中至少两层联动