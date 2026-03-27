# Support

## Best Entry Point

Choose the path that matches your need:

1. Bug or reproducible defect: use `.github/ISSUE_TEMPLATE/bug_report.md`.
2. Feature or workflow improvement: use `.github/ISSUE_TEMPLATE/feature_request.md`.
3. Security-sensitive problem: use `SECURITY.md` and keep the report private.
4. Contribution expectations: read `CONTRIBUTING.md` before opening a PR.

## Before Opening An Issue

1. Reproduce on the latest `main` branch or latest published package when possible.
2. Run `python3 scripts/memory.py docs-check .` if your change touches docs or templates.
3. Include the exact command, relevant logs, and expected behavior.

## Project Boundaries

This repository is an open-source engineering runtime. Support is best effort. Maintainers may redirect requests that depend on private project context, local-only data, or organization-specific infrastructure.

## What Maintainers Need

1. OS and Python version.
2. Install mode and command path.
3. Relevant validation output.
4. Minimal reproduction or failing workflow.