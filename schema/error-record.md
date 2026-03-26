# Error Record Schema

每个错误记录是一个独立的 Markdown 文件，放在 `errors/` 目录下。
命名格式：`YYYY-MM-DD-<project>-<error-type>.md`

---

## 文件模板

```markdown
---
id: <YYYY-MM-DD>-<project>-<sequence>
date: <YYYY-MM-DD>
project: <project-name>        # synapse-network | spec2flow | provider-service | gateway | admin-front
domain: <domain>               # finance | frontend | python | docs | config | infra
category: <category>           # 见下方 Category 枚举
severity: <critical|warning|info>
status: <new|reviewed|promoted|archived>
promoted_to: ""                # 升级后填写 instruction 文件路径
repeat_count: 1
tags: []
---

## 错误上下文

**任务目标：**
<!-- 当时在做什么 -->

**出错文件 / 位置：**
<!-- 文件路径 + 行号 (如适用) -->

## 错误描述

<!-- 具体出了什么错，粘贴报错信息或描述 -->

## 根因分析

<!-- 为什么会出这个错，原因层面的分析 -->

## 修复方案

<!-- 怎么修的 -->

## 提炼规则

<!-- 从这个错误提炼出来的防范规则，用 1-2 句话表达 -->
<!-- 这条规则将来升级为 instruction 文件的 Gotcha 段 -->

## 关联

<!-- 关联的其他错误记录 ID 或 instruction 文件 -->
```

---

## Category 枚举

| Category | 描述 |
|----------|------|
| `type-error` | TypeScript / Python 类型错误 |
| `logic-error` | 业务逻辑错误（如 TOCTOU、条件判断错误）|
| `finance-safety` | 金融安全违反（float、无幂等、无锁）|
| `arch-violation` | 架构分层违反（SQL 在 router、service 跨边界）|
| `test-failure` | 测试覆盖缺失或测试断言错误 |
| `docs-drift` | 代码与文档不同步 |
| `config-error` | 环境变量、配置项错误 |
| `build-error` | 构建 / 编译 / 打包错误 |
| `runtime-error` | 运行时异常（非类型）|
| `security` | 安全漏洞（注入、越权、泄漏）|

## Severity 定义

- `critical`：阻塞发布或有数据安全风险
- `warning`：功能受损但可 workaround
- `info`：代码质量 / 一致性问题，不影响功能

## Status 流转

```
new → reviewed → promoted → archived
               ↘ archived
```

- `new`：刚记录，未经复盘
- `reviewed`：已理解根因，提炼了规则
- `promoted`：规则已写入 instruction 文件的 Gotcha 段
- `archived`：超过 90 天且无重复，归档到 `errors/archive/`
