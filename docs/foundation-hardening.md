# Foundation Hardening Plan

> 目标：先把 Agents-Memory 的地基搭好，再继续往 AI Engineering Operating System 演进。

---

## 1. 当前项目需要优化的地方

根据 Harness Engineering 的核心原则，当前仓库的主要问题不是“功能不够”，而是“支撑结构还不够强”。

### 1.1 记录系统不完整

当前仓库已经具备：

1. Memory 核心闭环
2. MCP 接入
3. agent adapter 插件层
4. 产品方向文档

但缺少下面这些会直接影响长期可维护性的基础设施：

1. 组织级 `standards/` 标准库
2. 统一 `docs-check` 规则
3. 统一测试策略与最小验证矩阵
4. 统一规划模板与执行计划模板
5. 针对过期文档 / 过期代码的持续清理机制

### 1.2 文档易漂移

当前问题：

1. README、docs、产品方向文档之间已经开始分层，但还没有机械校验
2. 行为变更是否同步 docs，仍主要依赖人工自觉
3. 没有统一的术语表和废弃文档治理规则

如果不加约束，文档会出现：

1. 入口地图和真实实现脱节
2. 示例命令与代码行为不一致
3. 同一个概念在不同文档里命名漂移

### 1.3 代码复杂度会自然膨胀

当前仓库已经做了模块化拆分，但还缺少正式的工程约束：

1. TDD 规则没有写成标准文件
2. DRY / 代码复用 / 插件化只是设计偏好，不是强规则
3. 没有文件大小、职责边界、依赖方向的校验规则
4. 没有结构测试或复杂度预算

### 1.4 验证层明显不足

当前实际可用验证主要还是：

1. `py_compile`
2. 手工 smoke test

缺失：

1. 单元测试目录和基础测试 harness
2. 文档校验命令
3. 契约校验 / policy 校验
4. 文档、代码、测试同步更新的机械门禁

---

## 2. Harness Engineering 对当前仓库的直接要求

结合 OpenAI Harness Engineering 文章，当前仓库应优先补齐下面几条能力。

### 2.1 把仓库变成真正的记录系统

要求：

1. 短入口文档只做地图
2. 深层文档放到结构化目录
3. 计划、标准、验证规则都作为版本化工件进入仓库

对 Agents-Memory 的直接含义：

1. `docs/` 继续保留为记录系统主入口
2. `standards/` 成为组织级规范源
3. `profiles/` 成为项目装配源
4. `tests/` 成为机械验证源

### 2.2 让智能体可读，而不是让说明书越来越大

要求：

1. 不要把所有规则塞进一个大文件
2. 用分层目录和明确职责保持渐进披露
3. 把高频约束做成可检查规则，而不是长段叙述

对 Agents-Memory 的直接含义：

1. 保持 `README` / `docs/README` 作为目录地图
2. 具体规范拆进 `standards/`
3. 具体验证拆进 `validation` 规则和测试

### 2.3 用机械约束防止熵扩散

要求：

1. 通过 lint、结构测试、文档检查来强制不变量
2. 人的偏好要尽量编码成工具，而不是只留在 review 评论里

对 Agents-Memory 的直接含义：

1. 加 `docs-check`
2. 加单元测试
3. 加结构约束
4. 加“过期文档 / 过期代码”清理清单

---

## 3. 实现方案

### 3.1 文档防漂移方案

建立三层机制。

#### Layer A. 结构化来源分层

1. `README.md`：对外介绍 + 快速入口
2. `docs/README.md`：完整文档目录
3. `docs/*.md`：架构、集成、运维、产品、治理
4. `standards/docs/*`：组织级文档规范与校验规则

#### Layer B. 同步原则

任何行为变更都必须同步更新：

1. 对应代码
2. 对应 docs
3. 对应单元测试或验证脚本

最低规则：

1. 改 CLI 行为，必须改 README / docs/getting-started / llms.txt 中相关命令说明
2. 改模板或项目接入行为，必须改 integration / doctor / 相关示例
3. 改产品定位，必须改产品文档和 docs 入口

#### Layer C. 文档校验命令

第一版 `docs-check` 应校验：

1. 必需入口文件存在
2. `docs/README.md` 中的链接文件存在
3. 关键命令在 README 与 docs 中没有明显冲突
4. 废弃文档列表为空，或被明确标注 deprecated
5. 绝对路径、私有路径、过时结构引用被标记

### 3.2 代码复杂度防膨胀方案

建立四条强规则。

#### Rule 1. TDD

1. Bug fix 必须有对应回归测试，或在同一变更中补上
2. 新命令 / 新服务逻辑必须至少有最小单元测试覆盖
3. 包装层薄脚本可少测，但核心 services 必测

#### Rule 2. DRY

1. 公共逻辑优先收敛到 `services/` 或共享工具模块
2. 不允许多个命令层各自复制解析、路径、同步逻辑
3. 同类模板生成逻辑必须抽成统一 helper

#### Rule 3. 模块化

1. CLI dispatch 只在 `commands/`
2. 业务逻辑只在 `services/`
3. agent 集成只在 `integrations/agents/`
4. 运行时路径、logger、bootstrap 只在 `runtime.py`

#### Rule 4. 插件化

1. 新 agent 不改主流程 if/else，必须走 registry
2. 新 profile 不改核心常量分支，必须走 profile schema
3. 新 validation 不直接散落在命令里，必须进入验证层

### 3.3 文档、代码、单元测试同步更新方案

定义统一变更契约：

```text
Behavior change
  => code change
  => docs change
  => test or validation change
```

具体要求：

1. 代码新增命令：更新 README、docs/getting-started、llms.txt、tests/
2. 代码改行为：更新对应 docs，并补或改测试
3. 文档新增规范：如果可机械化，必须补校验规则或测试
4. 废弃能力：同时删代码、删 docs、删测试，不允许只删其中一层

### 3.4 删除过期或不符合新产品定义的内容

删除策略分两步。

#### Step 1. 标记

建立待清理清单，标出：

1. 仅把项目定义成 shared error memory 的过期表述
2. 引用了旧目录结构的文档
3. 已被 example/bootstrap 机制取代的说明
4. 已无对应代码实现的说明项

#### Step 2. 清理

每次清理必须同步删掉：

1. 对应文档
2. 对应代码或死路径引用
3. 对应测试 / 示例 / README 片段

---

## 4. 验证方案

### 4.1 文档验证

建议新增：

1. `amem docs-check`
2. `tests/test_docs_check.py`

第一版校验内容：

1. docs 索引可达性
2. 命令示例存在性
3. 关键文件链接一致性
4. 过期文档标记检查
5. glossary / 命名一致性检查

### 4.2 代码验证

建议新增：

1. `tests/test_runtime_bootstrap.py`
2. `tests/test_projects_service.py`
3. `tests/test_records_service.py`
4. `tests/test_integration_service.py`

最小验证矩阵：

1. runtime bootstrap 正常生成本地默认文件
2. 项目注册表解析正确
3. 错误记录创建 / 搜索 / index 更新正确
4. doctor / bridge / mcp merge 行为正确

### 4.3 单元测试

测试规则：

1. 以 `services/` 为主测对象
2. 以纯函数和文件系统 side effect 为主要断言点
3. 命令层只做薄测试
4. `scripts/` wrapper 只做 smoke 级验证

### 4.4 同步门禁

最终应形成统一验证入口：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/memory.py doctor .
python3 scripts/memory.py docs-check .
python3 -m py_compile $(find agents_memory scripts -name '*.py' -print)
```

---

## 5. 第一批必须落地的基础设施

### 优先级 P0

1. `standards/` 目录
2. `tests/` 目录
3. `docs-check` 命令
4. Python / TDD / DRY / docs-sync 标准文件
5. 过期文档清理清单

### 优先级 P1

1. `profiles/` 目录
2. `profile-apply` 命令
3. 结构测试 / policy-check
4. contract-check / test-check / standards-check

---

## 6. 当前建议删除或收敛的内容类型

不是立即盲删，而是优先识别这三类：

1. 只描述旧 memory-only 定位、与 Shared Engineering Brain 新目标冲突的表述
2. 引用旧运行文件入库方式、但已被 bootstrap 模式取代的表述
3. 存在说明但没有实现、会误导 agent 的“未来能力”描述

这些内容要么：

1. 改写为 roadmap
2. 标为 planned
3. 直接删除

---

## 7. 代码规范基线

第一版规范明确加入下面这些要求：

1. TDD
2. DRY
3. 代码复用优先
4. 可插拔优先
5. 模块化边界清晰
6. 文档、代码、测试同步更新
7. 删除过期代码与过期文档
8. 行为变更必须绑定验证

---

## 8. 近期执行顺序

建议按下面顺序落地，而不是并行扩散：

1. 新增 `standards/` 首批文件
2. 新增 `tests/` 和最小单元测试
3. 实现 `docs-check`
4. 清理过期文档表述
5. 再进入 `profiles/` 与 `profile-apply`

这是当前最稳的“先打地基，再扩系统”路线。