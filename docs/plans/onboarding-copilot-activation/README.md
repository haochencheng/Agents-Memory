# Optional onboarding: copilot_activation

这是当前任务的 planning bundle。

建议使用顺序：

1. 先写 `spec.md`
2. 再补 `plan.md`
3. 再确认 `task-graph.md`
4. 最后在 `validation.md` 里写最小验证路线

## Onboarding State
- state file: `.agents-memory/onboarding-state.json`
- bootstrap ready: `yes`
- bootstrap complete: `no`
- next group: `Optional`
- next key: `copilot_activation`
- next command: `amem copilot-setup .`
- verify with: `amem doctor .`
- done when: `amem doctor .` shows `[OK] copilot_activation`.
