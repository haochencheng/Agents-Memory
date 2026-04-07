---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---
# Bootstrap Checklist

- Project: `agents-memory`
- Root: `/Users/cliff/workspace/agent/Agents-Memory`
- Overall: `PARTIAL`

## Checklist
- [ ] Core - Core status=ATTENTION (ok=4, warn=0, fail=2, info=0)
- [x] Planning - Planning status=HEALTHY (ok=2, warn=0, fail=0, info=0)
- [ ] Integration - Integration status=ATTENTION (ok=1, warn=0, fail=1, info=0)
- [ ] Optional - Optional status=WATCH (ok=1, warn=6, fail=0, info=0)
- [ ] Final verification - re-run `amem doctor .` and confirm no remaining WARN / FAIL steps

## Action Sequence
1. Core (required): Register the project in memory/projects.md or re-run `amem register`.; Re-run `amem profile-check .` and repair the missing profile-managed files.
2. Integration (required): Install the bridge with `amem bridge-install <project-id>` if this repo should use bridge-based startup context.
3. Optional (recommended): Re-run `amem standards-sync .` or `amem enable . --full` so AGENTS.md references the current bridge and managed standards.; Refactor flagged functions before adding more behavior, and add a short guiding comment when complex logic must remain in place.

## Onboarding Runbook
### Step 1: Core / registry
- Priority: `required`
- Trigger: project is not registered in memory/projects.md
- Action: Register the repository into the shared project registry so sync and doctor can reason about it.
- Command: `amem register .`
- Verify with: `amem doctor .`
- Next command: `amem profile-check .`
- Safe To Auto Execute: `False`
- Approval Required: `True`
- Approval Reason: registration mutates shared project registry state and may install multiple integration files
- Done when: `amem doctor .` shows `[OK] registry` for this project.

### Step 2: Core / profile_consistency
- Priority: `required`
- Trigger: missing required file: runtime
- Action: Repair missing or drifted profile-managed files before continuing onboarding.
- Command: `amem profile-check .`
- Verify with: `amem profile-check .`
- Next command: `amem bridge-install <project-id>`
- Safe To Auto Execute: `False`
- Approval Required: `True`
- Approval Reason: this step diagnoses drift but manual repair choices still require a human decision
- Done when: `amem doctor .` shows `[OK] profile_consistency`.

### Step 3: Integration / bridge_instruction
- Priority: `required`
- Trigger: /Users/cliff/workspace/agent/Agents-Memory/.github/instructions/agents-memory-bridge.instructions.md
- Action: Install the bridge instruction so agents can load shared startup context automatically.
- Command: `amem bridge-install <project-id>`
- Verify with: `amem doctor .`
- Next command: `amem standards-sync .`
- Safe To Auto Execute: `False`
- Approval Required: `True`
- Approval Reason: bridge installation writes tracked repository instructions and may require project-specific review
- Done when: `amem doctor .` shows `[OK] bridge_instruction`.

### Step 4: Optional / agents_read_order
- Priority: `recommended`
- Trigger: AGENTS.md missing managed references: .github/instructions/agents-memory-bridge.instructions.md
- Action: Refresh the managed AGENTS.md read-order block so it references the current bridge instruction and profile-managed standards.
- Command: `amem standards-sync .`
- Verify with: `amem doctor .`
- Next command: `amem doctor .`
- Safe To Auto Execute: `False`
- Approval Required: `True`
- Approval Reason: refreshing AGENTS.md updates tracked repository instructions and should be reviewed before commit
- Done when: `amem doctor .` shows `[OK] agents_read_order`.

## Group Health
### Core
- Summary: Core status=ATTENTION (ok=4, warn=0, fail=2, info=0)
- [FAIL] `registry` project is not registered in memory/projects.md
- [OK] `root` /Users/cliff/workspace/agent/Agents-Memory
- [OK] `python3.12` /opt/homebrew/bin/python3.12
- [OK] `mcp_package` mcp import OK
- [OK] `profile_manifest` applied profile 'agent-runtime'
- [FAIL] `profile_consistency` missing required file: runtime

### Planning
- Summary: Planning status=HEALTHY (ok=2, warn=0, fail=0, info=0)
- [OK] `planning_root` present: /Users/cliff/workspace/agent/Agents-Memory/docs/plans
- [OK] `planning_bundle` 10 planning bundle(s) passed plan-check

### Integration
- Summary: Integration status=ATTENTION (ok=1, warn=0, fail=1, info=0)
- [FAIL] `bridge_instruction` /Users/cliff/workspace/agent/Agents-Memory/.github/instructions/agents-memory-bridge.instructions.md
- [OK] `mcp_config` agents-memory server configured -> /Users/cliff/workspace/agent/Agents-Memory/.vscode/mcp.json

### Optional
- Summary: Optional status=WATCH (ok=1, warn=6, fail=0, info=0)
- [OK] `copilot_activation` Agents-Memory activation block present -> /Users/cliff/workspace/agent/Agents-Memory/.github/copilot-instructions.md
- [WARN] `agents_read_order` AGENTS.md missing managed references: .github/instructions/agents-memory-bridge.instructions.md
- [WARN] `refactor_watch` agents_memory/services/ingest.py::cmd_ingest high complexity (lines=79>40, branches=16>5, nesting=7>=4, locals=11>8, missing_guiding_comment)
- [WARN] `refactor_watch` agents_memory/services/search.py::cmd_hybrid_search high complexity (lines=49>40, branches=10>5, nesting=4>=4, locals=9>8, missing_guiding_comment)
- [WARN] `refactor_watch` agents_memory/ui/streamlit_app.py::page_ingest high complexity (lines=48>40, branches=9>5, nesting=4>=4, locals=13>8, missing_guiding_comment)
- [WARN] `refactor_watch` agents_memory/web/api.py::search high complexity (lines=64>40, branches=15>5, nesting=7>=4, locals=12>8)
- [WARN] `refactor_watch` agents_memory/services/search.py::hybrid_search high complexity (lines=57>40, branches=8>5, nesting=4>=4, locals=17>8)
