---
created_at: 2026-03-27
updated_at: 2026-03-27
doc_status: active
---
# Bootstrap Checklist

- Project: `agents-memory`
- Root: `/Users/cliff/workspace/Agents-Memory`
- Overall: `READY`

## Checklist
- [x] Core - Core status=HEALTHY (ok=7, warn=0, fail=0, info=0)
- [x] Planning - Planning status=HEALTHY (ok=2, warn=0, fail=0, info=0)
- [x] Integration - Integration status=HEALTHY (ok=1, warn=0, fail=0, info=1)
- [ ] Optional - Optional status=WATCH (ok=1, warn=5, fail=0, info=1)
- [x] Final verification - latest `amem doctor .` already reflects the current healthy state

## Action Sequence
1. Optional (recommended): Refactor flagged functions before adding more behavior, and add a short guiding comment when complex logic must remain in place.
## Group Health
### Core
- Summary: Core status=HEALTHY (ok=7, warn=0, fail=0, info=0)
- [OK] `registry` registered as 'agents-memory'
- [OK] `active` active=true
- [OK] `root` /Users/cliff/workspace/Agents-Memory
- [OK] `python3.12` /opt/homebrew/bin/python3.12
- [OK] `mcp_package` mcp import OK
- [OK] `profile_manifest` applied profile 'agent-runtime'
- [OK] `profile_consistency` profile 'agent-runtime' consistency OK

### Planning
- Summary: Planning status=HEALTHY (ok=2, warn=0, fail=0, info=0)
- [OK] `planning_root` present: /Users/cliff/workspace/Agents-Memory/docs/plans
- [OK] `planning_bundle` 9 planning bundle(s) passed plan-check

### Integration
- Summary: Integration status=HEALTHY (ok=1, warn=0, fail=0, info=1)
- [INFO] `bridge_instruction` bridge not configured for this project
- [OK] `mcp_config` agents-memory server configured -> /Users/cliff/workspace/Agents-Memory/.vscode/mcp.json

### Optional
- Summary: Optional status=WATCH (ok=1, warn=5, fail=0, info=1)
- [OK] `copilot_activation` Agents-Memory activation block present -> /Users/cliff/workspace/Agents-Memory/.github/copilot-instructions.md
- [INFO] `agents_read_order` bridge not configured; AGENTS read order check skipped
- [WARN] `refactor_watch` agents_memory/services/profiles.py::_print_profile high complexity (branches=11>5, lines=40, nesting=3, missing_guiding_comment)
- [WARN] `refactor_watch` agents_memory/services/profiles.py::cmd_profile_show high complexity (lines=52>40, missing_guiding_comment)
- [WARN] `refactor_watch` agents_memory/services/profiles.py::_match_path_exists_detector high complexity (locals=9>8, missing_guiding_comment)
- [WARN] `refactor_watch` agents_memory/services/profiles.py::sync_profile_standards high complexity (locals=9>8)
- [WARN] `refactor_watch` agents_memory/services/integration_enable.py::_preview_enable_profile_actions high complexity (lines=31, locals=8, missing_guiding_comment)
