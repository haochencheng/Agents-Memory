# Spec

## Task

Refactor hotspot: agents_memory/services/integration.py::cmd_enable

## Problem

- `cmd_enable` 同时承担参数校验、头部输出、dry-run 渲染、profile 应用、doctor 导出、refactor follow-up 写回，认知负担过高。
- `enable --dry-run` 的结构化预览刚扩展过，如果继续把新分支堆在主函数里，后续维护成本会继续上升。

## Goal

- 将 `cmd_enable` 按执行阶段拆成更小 helper。
- 保持 `enable` 默认模式、全量模式、dry-run、JSON 输出的行为完全不变。
- 让 `amem doctor .` 不再把 `cmd_enable` 识别为首个 refactor hotspot。

## Non-Goals

- 这次不重构 `cmd_doctor`、`cmd_onboarding_execute`、`_doctor_state_payload`。
- 这次不改变 `enable` 的外部命令行 contract。

## Acceptance Criteria

- [x] `cmd_enable` 的校验、预览渲染、profile 应用、full-mode follow-up 写回被拆分到 helper。
- [x] `python3 -m unittest tests.test_integration_service` 通过。
- [x] `python3 -m py_compile agents_memory/services/integration.py tests/test_integration_service.py` 通过。
- [x] `amem doctor .` 不再报告 `agents_memory/services/integration.py::cmd_enable` 为热点。
