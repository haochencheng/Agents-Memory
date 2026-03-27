---
created_at: 2026-03-28
updated_at: 2026-03-28
doc_status: active
description: >
  Project-local overlay generated for the fullstack-product profile.
  Refresh with amem profile-render when workspace layout changes.
applyTo: "**"
---

# Fullstack Product Local Contract

- Active profile: {{profile.id}}
- Preferred package manager: {{variable.package_manager}}
- Workspace root: {{variable.workspace_root}}
- Node project detected: {{fact.language.node}}
- Workspace manifest declared: {{fact.repo_shape.workspace_manifest}}
- Workspace tooling markers detected: {{fact.tooling.workspace_stack}}
- Monorepo layout detected: {{fact.repo_shape.monorepo}}

## Local Expectations

1. Use `{{variable.package_manager}}` for workspace-level command examples unless repo docs say otherwise.
2. Keep application packages grouped under `{{variable.workspace_root}}` or rerender after changing the workspace contract.
3. Re-run `amem profile-render .` after moving apps/packages or changing workspace structure.