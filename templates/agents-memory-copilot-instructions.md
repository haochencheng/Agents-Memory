<!-- agents-memory:start -->
# Agents-Memory Auto-Activation

When working in this repository, treat Agents-Memory as mandatory session context for coding, debugging, code review, refactors, migrations, and docs-sync work.

## Required startup sequence

1. Before any substantial analysis or edits, call `memory_get_index()` if the `agents-memory` MCP server is available.
2. Before touching domain-specific code, call `memory_get_rules(domain)` with the closest matching domain:
   - `python` for Python, FastAPI, backend, repository, or migration work
   - `frontend` for TypeScript, React, Next.js, or UI work
   - `finance` for balance, billing, settlement, ledger, withdraw, refund, or reconciliation work
   - `docs` for README, AGENTS, instruction, contract, workflow, or runbook updates
3. When the task resembles a previous failure pattern, call `memory_search(query)` before writing code.

## Error capture protocol

- Use `project="{{PROJECT_ID}}"` when calling `memory_record_error(...)` for this repository.
- If the same error pattern happens again, prefer `memory_increment_repeat(id)` instead of creating a duplicate record.
- Record a new error after any bug fix that took more than one attempt or exposed a reusable lesson.

## Fallback when MCP is unavailable

Use the CLI directly:

```bash
python3 {{AGENTS_MEMORY_ROOT}}/scripts/memory.py search <keyword>
python3 {{AGENTS_MEMORY_ROOT}}/scripts/memory.py new
```

## Notes

- This file is the strongest repository-wide auto-activation mechanism officially supported by GitHub Copilot custom instructions.
- It improves default tool usage on every repository-scoped request, but it does not hard-enforce MCP tool execution when the platform chooses not to use tools.
<!-- agents-memory:end -->