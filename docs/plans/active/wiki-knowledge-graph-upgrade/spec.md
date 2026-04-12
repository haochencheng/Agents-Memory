---
created_at: 2026-04-12
updated_at: 2026-04-12
doc_status: active
---

# Spec

## Problem

当前 wiki 存在三个核心短板：

1. 页面元数据不稳定，很多页面缺 `tags / doc_type / links`
2. 搜索仍然混合了大量简单全文扫描，图关系没有进入检索排序
3. 知识图谱直接把页面当节点，导致大规模时不可读，也不利于结构化推理

## Desired Outcome

系统应提供：

1. 每个接入页面都具备稳定 frontmatter 元数据
2. onboarding/ingest 时自动补出第一批候选 links
3. 搜索结果同时吸收 FTS/BM25、向量相似度和图关系信号
4. 图谱节点以“概念层”为主，页面退到阅读载体层

## Non-Goals

1. 本轮不引入 Neo4j 等外部图数据库
2. 本轮不做复杂 LLM 实体抽取流水线
3. 本轮优先做 deterministic / low-risk 结构化升级
