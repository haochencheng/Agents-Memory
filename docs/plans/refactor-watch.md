# Refactor Watch

- Project: `agents-memory`
- Root: `/Users/cliff/workspace/Agents-Memory`

## Purpose

Track Python functions that are already high-complexity or are approaching the configured refactor thresholds.

## Thresholds

- Hard gate: more than 40 effective lines, more than 5 control-flow branches, nesting depth >= 4, or more than 8 local variables.
- Watch zone: around 30 effective lines, 4 branches, nesting depth 3, or 6 local variables.
- Complex logic should include a short guiding comment when it cannot be cleanly decomposed yet.

## Workflow Entry

- Primary command: `amem refactor-bundle .`
- Prefer stable targeting with: `amem refactor-bundle . --token <hotspot-token>`
- Fallback positional targeting: `amem refactor-bundle . --index <n>`
- The command creates or refreshes `docs/plans/refactor-<slug>/` using the first current hotspot as execution context.

## Hotspots

1. [WARN] `agents_memory/services/integration.py::cmd_sync` line=208 metrics=(lines=57, branches=11, nesting=3, locals=15)
   - token: `hotspot-b963d3c1470f`
   - issues: `lines=57>40, branches=11>5, locals=15>8, nesting=3`
   - bundle command: `amem refactor-bundle . --token hotspot-b963d3c1470f`
2. [WARN] `agents_memory/services/integration.py::cmd_register` line=1707 metrics=(lines=56, branches=7, nesting=2, locals=14)
   - token: `hotspot-1c511b0626bb`
   - issues: `lines=56>40, branches=7>5, locals=14>8`
   - bundle command: `amem refactor-bundle . --token hotspot-1c511b0626bb`
3. [WARN] `agents_memory/services/integration.py::execute_onboarding_next_action` line=1397 metrics=(lines=114, branches=7, nesting=2, locals=16)
   - token: `hotspot-bd33eb374bd5`
   - issues: `lines=114>40, branches=7>5, locals=16>8`
   - bundle command: `amem refactor-bundle . --token hotspot-bd33eb374bd5`
4. [WARN] `agents_memory/services/integration.py::_doctor_runbook_steps` line=586 metrics=(lines=37, branches=7, nesting=3, locals=12)
   - token: `hotspot-ec7f7678d0f7`
   - issues: `branches=7>5, locals=12>8, lines=37, nesting=3, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-ec7f7678d0f7`
5. [WARN] `agents_memory/services/integration.py::_doctor_checklist_markdown` line=738 metrics=(lines=49, branches=5, nesting=2, locals=9)
   - token: `hotspot-124776bc8f37`
   - issues: `lines=49>40, locals=9>8, branches=5, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-124776bc8f37`

## Suggested Action

1. Run `amem refactor-bundle .` to materialize the first hotspot into an executable planning bundle.
2. If a hotspot cannot be split yet, add a guiding comment that explains the main decision path and risk boundaries.
3. Re-run `amem doctor .` after the change and confirm `refactor_watch` findings shrink or disappear.
