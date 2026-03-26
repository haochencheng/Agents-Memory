# Project Registry

每个条目描述一个使用 Agents-Memory 共享记忆的项目。
`sync` 命令会用此文件把提炼的规则推送到对应项目的 instruction 文件中。

---

## synapse-network

- **id**: synapse-network
- **root**: /Users/cliff/workspace/Synapse-Network
- **instruction_dir**: .github/instructions
- **bridge_instruction**: .github/instructions/agents-memory-bridge.instructions.md
- **active**: true
- **domains**: finance, python, frontend, docs, config, infra
- **instruction_files**:
  - finance:   .github/instructions/finance-backend.instructions.md
  - python:    .github/instructions/python.instructions.md
  - frontend:  .github/instructions/frontend.instructions.md
  - docs:      .github/instructions/docs-sync.instructions.md
  - admin:     .github/instructions/finance-admin.instructions.md
  - admin-console: .github/instructions/admin-console.instructions.md

---

## spec2flow

- **id**: spec2flow
- **root**: /Users/cliff/workspace/Spec2Flow
- **instruction_dir**: .github/instructions
- **bridge_instruction**: .github/instructions/agents-memory-bridge.instructions.md
- **active**: true
- **domains**: frontend, python, docs

---

## agents-memory

- **id**: agents-memory
- **root**: /Users/cliff/workspace/Agents-Memory
- **instruction_dir**: .github/instructions
- **bridge_instruction**: ""
- **active**: true
- **domains**: python
- **note**: Self-referential — this repo records errors about itself.

---

## 注册新项目

在本文件末尾追加如下格式的条目，然后运行：

```bash
python3 scripts/memory.py sync
```

模板：
```
## <project-id>

- **id**: <project-id>
- **root**: /absolute/path/to/project
- **instruction_dir**: .github/instructions
- **bridge_instruction**: .github/instructions/agents-memory-bridge.instructions.md
- **active**: true
- **domains**: python, frontend, docs
```
