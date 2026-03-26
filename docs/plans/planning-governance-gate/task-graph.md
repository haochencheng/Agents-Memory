# Task Graph

## Work Items

1. 在 validation 层新增 planning bundle finding 收集逻辑。
2. 在 CLI validation registry 中注册 `plan-check`。
3. 为 `plan-check` 补齐单测和 docs-check command coverage。
4. 用 `plan-init` 生成并完善当前仓库的 dogfooding planning bundle。
5. 运行全量验证并提交推送。

## Dependencies

- 必须先完成 validation service，CLI 才能接线。
- 文档和测试可以在命令主干稳定后并行补齐。

## Exit Criteria

- `plan-check` 能正确区分 `OK / PARTIAL / FAIL`。
- 仓库内至少有一份真实 planning bundle 可被 `plan-check` 校验。
- `python3 -m unittest discover -s tests -p 'test_*.py'`、`py_compile`、`docs-check` 通过。
