---
created_at: 2026-03-28
updated_at: 2026-04-07
doc_status: active
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