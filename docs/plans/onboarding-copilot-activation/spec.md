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
    "summary": "Core status=HEALTHY (ok=5, warn=0, fail=0, info=1)",
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
        "status": "INFO",
        "key": "profile_manifest",
        "detail": "no applied profile manifest found"
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
        "detail": "1 planning bundle(s) passed plan-check"
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
    "summary": "Optional status=WATCH (ok=0, warn=1, fail=0, info=1)",
    "checks": [
      {
        "status": "WARN",
        "key": "copilot_activation",
        "detail": "missing ./.github/copilot-instructions.md (recommended for repo-wide auto-activation)"
      },
      {
        "status": "INFO",
        "key": "agents_read_order",
        "detail": "bridge not configured; AGENTS read order check skipped"
      }
    ]
  }
]
```
