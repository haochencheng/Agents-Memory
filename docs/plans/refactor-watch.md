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

1. [WARN] `agents_memory/mcp_app.py::memory_record_error` line=271 metrics=(lines=45, branches=4, nesting=1, locals=9)
   - token: `hotspot-27d26ab2550d`
   - issues: `lines=45>40, locals=9>8, branches=4, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-27d26ab2550d`
2. [WARN] `agents_memory/services/projects.py::parse_projects` line=12 metrics=(lines=25, branches=8, nesting=3, locals=10)
   - token: `hotspot-37a8abb3045e`
   - issues: `branches=8>5, locals=10>8, nesting=3, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-37a8abb3045e`
3. [WARN] `agents_memory/services/integration_enable.py::cmd_enable` line=383 metrics=(lines=50, branches=5, nesting=1, locals=11)
   - token: `hotspot-765a0d5e3560`
   - issues: `lines=50>40, locals=11>8, branches=5, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-765a0d5e3560`
4. [WARN] `agents_memory/services/integration_enable.py::_preview_enable_actions` line=105 metrics=(lines=52, branches=4, nesting=1, locals=14)
   - token: `hotspot-95b46d4f7dc4`
   - issues: `lines=52>40, locals=14>8, branches=4, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-95b46d4f7dc4`
5. [WARN] `agents_memory/services/profiles.py::sync_profile_standards` line=321 metrics=(lines=42, branches=5, nesting=2, locals=15)
   - token: `hotspot-c57353e7277d`
   - issues: `lines=42>40, locals=15>8, branches=5, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-c57353e7277d`

## Suggested Action

1. Run `amem refactor-bundle .` to materialize the first hotspot into an executable planning bundle.
2. If a hotspot cannot be split yet, add a guiding comment that explains the main decision path and risk boundaries.
3. Re-run `amem doctor .` after the change and confirm `refactor_watch` findings shrink or disappear.
