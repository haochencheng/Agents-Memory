---
created_at: 2026-03-27
updated_at: 2026-03-27
doc_status: active
---
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

1. [WARN] `agents_memory/services/profiles.py::_print_profile` line=611 metrics=(lines=40, branches=11, nesting=3, locals=5)
   - token: `hotspot-5ae7cd31a053`
   - issues: `branches=11>5, lines=40, nesting=3, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-5ae7cd31a053`
2. [WARN] `agents_memory/services/profiles.py::cmd_profile_show` line=755 metrics=(lines=52, branches=2, nesting=1, locals=4)
   - token: `hotspot-17c12282c5bd`
   - issues: `lines=52>40, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-17c12282c5bd`
3. [WARN] `agents_memory/services/profiles.py::_match_path_exists_detector` line=239 metrics=(lines=10, branches=0, nesting=0, locals=9)
   - token: `hotspot-ab71e0fcf606`
   - issues: `locals=9>8, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-ab71e0fcf606`
4. [WARN] `agents_memory/services/profiles.py::sync_profile_standards` line=528 metrics=(lines=22, branches=2, nesting=1, locals=9)
   - token: `hotspot-c57353e7277d`
   - issues: `locals=9>8`
   - bundle command: `amem refactor-bundle . --token hotspot-c57353e7277d`
5. [WARN] `agents_memory/services/integration_enable.py::_preview_enable_profile_actions` line=37 metrics=(lines=31, branches=3, nesting=2, locals=8)
   - token: `hotspot-fb859b344646`
   - issues: `lines=31, locals=8, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-fb859b344646`

## Suggested Action

1. Run `amem refactor-bundle .` to materialize the first hotspot into an executable planning bundle.
2. If a hotspot cannot be split yet, add a guiding comment that explains the main decision path and risk boundaries.
3. Re-run `amem doctor .` after the change and confirm `refactor_watch` findings shrink or disappear.
