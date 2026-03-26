# Project Registry

Public example template. Your local runtime copy is generated as `memory/projects.md` on first run.
Do not commit private project roots or local absolute paths to a public repository.

---

## example-project

- **id**: example-project
- **root**: /absolute/path/to/example-project
- **instruction_dir**: .github/instructions
- **bridge_instruction**: .github/instructions/agents-memory-bridge.instructions.md
- **active**: false
- **domains**: python, frontend, docs

---

## 注册新项目

在本文件末尾追加如下格式的条目，然后运行：

```bash
python3 scripts/memory.py sync
```

模板：
```text
## <project-id>

- **id**: <project-id>
- **root**: /absolute/path/to/project
- **instruction_dir**: .github/instructions
- **bridge_instruction**: .github/instructions/agents-memory-bridge.instructions.md
- **active**: true
- **domains**: python, frontend, docs
```