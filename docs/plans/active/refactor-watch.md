---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---
# Refactor Watch

- Project: `agents-memory`
- Root: `/Users/cliff/workspace/agent/Agents-Memory`

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

1. [WARN] `agents_memory/services/ingest.py::cmd_ingest` line=312 metrics=(lines=79, branches=16, nesting=7, locals=11)
   - token: `hotspot-0e832c6afc58`
   - issues: `lines=79>40, branches=16>5, nesting=7>=4, locals=11>8, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-0e832c6afc58`
2. [WARN] `agents_memory/services/search.py::cmd_hybrid_search` line=320 metrics=(lines=49, branches=10, nesting=4, locals=9)
   - token: `hotspot-714e7e37f08b`
   - issues: `lines=49>40, branches=10>5, nesting=4>=4, locals=9>8, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-714e7e37f08b`
3. [WARN] `agents_memory/ui/streamlit_app.py::page_ingest` line=254 metrics=(lines=48, branches=9, nesting=4, locals=13)
   - token: `hotspot-dd482a657b60`
   - issues: `lines=48>40, branches=9>5, nesting=4>=4, locals=13>8, missing_guiding_comment`
   - bundle command: `amem refactor-bundle . --token hotspot-dd482a657b60`
4. [WARN] `agents_memory/web/api.py::search` line=339 metrics=(lines=64, branches=15, nesting=7, locals=12)
   - token: `hotspot-4d403be2b3c8`
   - issues: `lines=64>40, branches=15>5, nesting=7>=4, locals=12>8`
   - bundle command: `amem refactor-bundle . --token hotspot-4d403be2b3c8`
5. [WARN] `agents_memory/services/search.py::hybrid_search` line=233 metrics=(lines=57, branches=8, nesting=4, locals=17)
   - token: `hotspot-5e218138cbd5`
   - issues: `lines=57>40, branches=8>5, nesting=4>=4, locals=17>8`
   - bundle command: `amem refactor-bundle . --token hotspot-5e218138cbd5`

## Suggested Action

1. Run `amem refactor-bundle .` to materialize the first hotspot into an executable planning bundle.
2. If a hotspot cannot be split yet, add a guiding comment that explains the main decision path and risk boundaries.
3. Re-run `amem doctor .` after the change and confirm `refactor_watch` findings shrink or disappear.
