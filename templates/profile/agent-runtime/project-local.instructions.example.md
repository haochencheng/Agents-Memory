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

- Active profile: {{profile.id}}
- Preferred Python executable: {{variable.python_bin}}
- Runtime directory: {{variable.runtime_dir}}
- Python project detected: {{fact.language.python}}
- Runtime layout detected: {{fact.repo_shape.runtime}}

## Local Expectations

1. Keep runtime-facing scripts under `{{variable.runtime_dir}}` or update the profile variable before rerendering.
2. Use `{{variable.python_bin}}` when documenting local validation or MCP launch commands.
3. Re-run `amem profile-render .` when runtime entrypoints or layout assumptions change.