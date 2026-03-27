---
created_at: 2026-03-28
updated_at: 2026-03-28
doc_status: active
description: >
  Project-local overlay generated for the agent-runtime profile.
  Refresh with amem profile-render when runtime layout changes.
applyTo: "**"
---

# Agent Runtime Local Contract

- Active profile: agent-runtime
- Preferred Python executable: python3
- Runtime directory: runtime
- Python project detected: true
- Runtime layout detected: true

## Local Expectations

1. Keep runtime-facing scripts under `runtime` or update the profile variable before rerendering.
2. Use `python3` when documenting local validation or MCP launch commands.
3. Re-run `amem profile-render .` when runtime entrypoints or layout assumptions change.