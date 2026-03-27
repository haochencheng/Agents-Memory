---
created_at: 2026-03-26
updated_at: 2026-03-27
doc_status: active
---

# Stale Cleanup Inventory

> 目的：持续识别并清理不符合 Shared Engineering Brain 新产品定义的旧文档、旧表述和误导性说明。

---

## 已完成的第一批清理

1. `llms.txt` 中把 `scripts/memory.py` 从“CLI 主入口（所有命令）”纠正为 thin wrapper 语义
2. README 中删除了过于随意的“未来扩展路径（不需要现在做）”标题，避免把 roadmap 误写成当前主结构
3. README / getting-started / llms 将公开仓库与本地运行文件的边界明确化

---

## 待清理类别

### 1. 旧定位表述

需要持续识别：

1. 把系统只定义为 shared error memory 的表述
2. 与 `Shared Engineering Brain` 最终目标冲突的旧定位文案

### 2. 旧结构说明

需要持续识别：

1. 仍把本地运行文件写成公开仓库主结构的一部分
2. 把 wrapper 脚本描述成真实业务入口

### 3. 未来能力误导

需要持续识别：

1. 文档里写成“已有能力”，但其实只是设计方案的部分
2. 没有命令、没有测试、没有代码实现的功能描述

---

## 清理原则

1. 先标记再删除
2. 说明与实现不一致时，优先修正文档
3. 已无实现计划的说明直接删除
4. 仍计划实现但尚未落地的内容，统一标注为 roadmap / planned