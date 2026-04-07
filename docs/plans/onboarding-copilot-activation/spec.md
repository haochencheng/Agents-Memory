---
created_at: 2026-03-26
updated_at: 2026-04-07
doc_status: active
---

# Spec

## Task

Optional onboarding: copilot_activation

## Problem

- 当前问题是什么？

## Goal

- 这次变更要达成什么结果？

## Non-Goals

- 这次不解决什么？

## Acceptance Criteria

- [ ] 有明确可验证的功能结果
- [ ] 有对应 docs / code / tests 同步要求
- [ ] 验收标准可被测试或命令验证

## Onboarding Inputs
- state file: `.agents-memory/onboarding-state.json`

```json
[
  {
    "name": "Core",
    "status": "HEALTHY",
    "summary": "Core status=HEALTHY (ok=7, warn=0, fail=0, info=0)",
    "checks": [
      {
        "status": "OK",
        "key": "registry",
        "detail": "registered as 'agents-memory'"
      },
      {
        "status": "OK",
        "key": "active",
        "detail": "active=true"
      },
      {
        "status": "OK",
        "key": "root",
        "detail": "."
      },
      {
        "status": "OK",
        "key": "python3.12",
        "detail": "/opt/homebrew/bin/python3.12"
      },
      {
        "status": "OK",
        "key": "mcp_package",
        "detail": "mcp import OK"
      },
      {
        "status": "OK",
        "key": "profile_manifest",
        "detail": "applied profile 'agent-runtime'"
      },
      {
        "status": "OK",
        "key": "profile_consistency",
        "detail": "profile 'agent-runtime' consistency OK"
      }
    ]
  },
  {
    "name": "Planning",
    "status": "HEALTHY",
    "summary": "Planning status=HEALTHY (ok=2, warn=0, fail=0, info=0)",
    "checks": [
      {
        "status": "OK",
        "key": "planning_root",
        "detail": "present: ./docs/plans"
      },
      {
        "status": "OK",
        "key": "planning_bundle",
        "detail": "9 planning bundle(s) passed plan-check"
      }
    ]
  },
  {
    "name": "Integration",
    "status": "HEALTHY",
    "summary": "Integration status=HEALTHY (ok=1, warn=0, fail=0, info=1)",
    "checks": [
      {
        "status": "INFO",
        "key": "bridge_instruction",
        "detail": "bridge not configured for this project"
      },
      {
        "status": "OK",
        "key": "mcp_config",
        "detail": "agents-memory server configured -> ./.vscode/mcp.json"
      }
    ]
  },
  {
    "name": "Optional",
    "status": "WATCH",
    "summary": "Optional status=WATCH (ok=1, warn=5, fail=0, info=1)",
    "checks": [
      {
        "status": "OK",
        "key": "copilot_activation",
        "detail": "Agents-Memory activation block present -> ./.github/copilot-instructions.md"
      },
      {
        "status": "INFO",
        "key": "agents_read_order",
        "detail": "bridge not configured; AGENTS read order check skipped"
      },
      {
        "status": "WARN",
        "key": "refactor_watch",
        "detail": "agents_memory/services/profiles.py::_print_profile high complexity (branches=11>5, lines=40, nesting=3, missing_guiding_comment)"
      },
      {
        "status": "WARN",
        "key": "refactor_watch",
        "detail": "agents_memory/services/profiles.py::cmd_profile_show high complexity (lines=52>40, missing_guiding_comment)"
      },
      {
        "status": "WARN",
        "key": "refactor_watch",
        "detail": "agents_memory/services/profiles.py::_match_path_exists_detector high complexity (locals=9>8, missing_guiding_comment)"
      },
      {
        "status": "WARN",
        "key": "refactor_watch",
        "detail": "agents_memory/services/profiles.py::sync_profile_standards high complexity (locals=9>8)"
      },
      {
        "status": "WARN",
        "key": "refactor_watch",
        "detail": "agents_memory/services/integration_enable.py::_preview_enable_profile_actions high complexity (lines=31, locals=8, missing_guiding_comment)"
      }
    ]
  }
]
```
