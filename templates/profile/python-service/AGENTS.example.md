# Project AGENTS

## Read Order

1. `.agents-memory/onboarding-state.json` if present
2. `.github/instructions/agents-memory/standards/python/base.instructions.md`
3. `.github/instructions/agents-memory/standards/python/tdd.instructions.md`
4. `.github/instructions/agents-memory/standards/python/dry.instructions.md`
5. `.github/instructions/agents-memory/standards/docs/docs-sync.instructions.md`
6. `.github/instructions/agents-memory/standards/planning/harness-engineering.md`
7. `docs/plans/README.md`

## Onboarding State

1. If `.agents-memory/onboarding-state.json` exists, read `recommended_next_command` before deep implementation.
2. If the file is missing, run `amem doctor . --write-state --write-checklist`.
3. If `project_bootstrap_ready` is `false`, finish the first runbook step before large edits.
4. If only `project_bootstrap_complete` is `false`, treat the first step as recommended follow-up work.

## Validation

1. `amem plan-check .`
2. `amem docs-check .`
3. `amem doctor . --write-state --write-checklist`
