---
created_at: 2026-03-28
updated_at: 2026-03-28
doc_status: active
description: >
  Project-local overlay generated for the python-service profile.
  Keep repo-specific workflow notes here and regenerate with amem profile-render.
applyTo: "**"
---

# Python Service Local Contract

- Active profile: {{profile.id}}
- Preferred Python executable: {{variable.python_bin}}
- Preferred tests directory: {{variable.tests_dir}}
- Python project detected: {{fact.language.python}}
- Pytest-style config detected: {{fact.testing.pytest_configured}}
- Tests layout detected: {{fact.testing.layout}}

## Local Expectations

1. Use `{{variable.python_bin}}` for repo-local verification examples.
2. Keep automated tests rooted under `{{variable.tests_dir}}` unless the repo has a stronger existing contract.
3. Re-run `amem profile-render .` after changing project structure that affects profile detectors.