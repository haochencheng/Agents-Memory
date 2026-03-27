---
created_at: 2026-03-28
updated_at: 2026-03-28
doc_status: active
description: >
  Project-local overlay generated for the frontend-app profile.
  Refresh with amem profile-render when app layout changes.
applyTo: "**"
---

# Frontend App Local Contract

- Active profile: {{profile.id}}
- Preferred package manager: {{variable.package_manager}}
- Primary app root: {{variable.app_root}}
- Node project detected: {{fact.language.node}}
- package.json packageManager declared: {{fact.tooling.package_manager_declared}}
- Frontend framework markers detected: {{fact.framework.frontend_manifest}}
- Frontend layout detected: {{fact.repo_shape.frontend}}

## Local Expectations

1. Use `{{variable.package_manager}}` in repo-local command examples unless the project documents an override.
2. Keep the main application rooted under `{{variable.app_root}}` or update the profile variable before rerendering.
3. Re-run `amem profile-render .` after moving app directories or changing the package manager contract.