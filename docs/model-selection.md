---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# 本地模型选型指南

本项目通过 Ollama 运行本地模型，涉及两类任务：
- **Embedding**：将错误记录 / Wiki 页面编码为向量，用于语义搜索
- **LLM 合成**：`wiki-compile`（提炼 compiled_truth）、`ingest`（从文档提取结构化 JSON）

---

## 一、Embedding 模型

### 当前选型：`nomic-embed-text`

| 属性 | 值 |
|------|-----|
| 维度 | 768 |
| 模型大小 | ~270 MB |
| 语言 | 英 / 中（多语言一般）|
| 上下文窗口 | 8192 tokens |
| 推理速度（M4 Pro）| ~20-40ms |
| Ollama 拉取 | `ollama pull nomic-embed-text` |

**适用场景**：本地开发、无 API Key 环境、延迟敏感场景。  
**弱点**：中文语义质量略低于专门多语言模型；768d 维度低于 OpenAI 1536d。

---

### 候选替代方案

#### ✅ 推荐升级：`EmbeddingGemma`（Google，2025-08）

> Google 官方标注：**"best-in-class open model for on-device embeddings"**

| 属性 | 值 |
|------|-----|
| 维度 | 768 / 1536（取决于变体）|
| 模型大小 | ~200-500 MB |
| 语言 | 多语言（中文质量优于 nomic）|
| 特点 | 基于 Gemma 架构蒸馏，专为嵌入任务优化 |
| Ollama 支持 | 部分变体支持（`ollama pull embeddinggemma`）|
| 适用场景 | 替换 nomic-embed-text，中文记录较多时质量提升明显 |

#### `mxbai-embed-large`

| 属性 | 值 |
|------|-----|
| 维度 | 1024 |
| 模型大小 | ~670 MB |
| 语言 | 英文为主 |
| Ollama 拉取 | `ollama pull mxbai-embed-large` |
| 适用场景 | 英文记录质量更好，中文一般 |

#### `bge-m3`（BAAI）

| 属性 | 值 |
|------|-----|
| 维度 | 1024 |
| 模型大小 | ~1.2 GB |
| 语言 | **多语言最强**（中英日韩均优秀）|
| Ollama 拉取 | `ollama pull bge-m3` |
| 适用场景 | 中文记录较多、对召回质量要求高时首选 |

---

### Embedding 选型矩阵

| 模型 | 维度 | 大小 | 中文质量 | 速度 | 推荐场景 |
|------|------|------|----------|------|----------|
| `nomic-embed-text` | 768 | 270MB | ⭐⭐⭐ | ⚡⚡⚡ | 当前默认，快速开发 |
| `EmbeddingGemma` | 768/1536 | 200-500MB | ⭐⭐⭐⭐ | ⚡⚡⚡ | **推荐升级** |
| `mxbai-embed-large` | 1024 | 670MB | ⭐⭐ | ⚡⚡ | 英文项目 |
| `bge-m3` | 1024 | 1.2GB | ⭐⭐⭐⭐⭐ | ⚡⚡ | 中文记录多时 |
| OpenAI `text-embedding-3-small` | 1536 | 云端 | ⭐⭐⭐⭐ | ⚡（网络延迟）| 生产环境 |

**结论**：当前 `nomic-embed-text` 满足需求；若中文 wiki 内容增多，建议迁移至 `bge-m3` 或 `EmbeddingGemma`。

---

## 二、LLM 合成模型

### 当前选型：`qwen2.5:7b`

| 属性 | 值 |
|------|-----|
| 参数量 | 7B |
| 模型大小 | ~4.7 GB（Q4_K_M 量化）|
| 上下文窗口 | 128K tokens |
| 中文能力 | ⭐⭐⭐⭐⭐（阿里，专为中文优化）|
| 代码能力 | ⭐⭐⭐⭐ |
| 推理速度（M4 Pro）| ~35-50 tokens/s |
| Ollama 拉取 | `ollama pull qwen2.5:7b` |

**适合任务**：
- `wiki-compile`：中文 compiled_truth 合成，需要理解错误摘要后生成结构化 Markdown
- `ingest`：从 PR / 会议记录中提取 `{summary, topics, timeline_entry}` JSON

**弱点**：推理与逻辑能力略弱于同规模的 Gemma / Llama3；JSON 格式输出偶尔需要 `_parse_llm_json` 容错处理。

---

### Google Gemma 系列评估

#### Gemma 4（2026-04，本月发布）

| 变体 | 参数量 | 大小 | 特点 |
|------|--------|------|------|
| `gemma4:e2b` | 2B（MoE）| ~1.5 GB | 移动端 / IoT，极低内存 |
| `gemma4:e4b` | 4B（MoE）| ~2.5 GB | **性价比最高**，推理与代码能力强 |
| `gemma4:26b` | 26B | ~16 GB | 接近 frontier，M4 Pro 64GB 可运行 |
| `gemma4:31b` | 31B | ~20 GB | 桌面端最强开源模型之一 |

**MoE 架构（Mixture of Experts）**说明：`e2b`/`e4b` 虽标称较小参数量，实际推理质量远超同尺寸 Dense 模型，因为每次推理只激活部分专家网络。

#### Gemma 3（2025）

| 变体 | 参数量 | 大小 | 备注 |
|------|--------|------|------|
| `gemma3:270m` | 270M | ~200MB | 超轻量，适合嵌入式 |
| `gemma3:1b` | 1B | ~700MB | 快速分类任务 |
| `gemma3:4b` | 4B | ~2.5GB | 已在 Ollama 广泛使用 |
| `gemma3:9b` | 9B | ~5.5GB | **当前最佳 9B 级开源模型之一** |

---

### LLM 候选方案对比

| 模型 | 大小 | 中文 | JSON 输出 | 推理质量 | 速度（M4 Pro）| 推荐度 |
|------|------|------|-----------|----------|--------------|--------|
| `qwen2.5:7b`（当前）| 4.7GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ~40 t/s | ✅ 现状可用 |
| `gemma4:e4b` | 2.5GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ~60 t/s | 🔥 推荐测试 |
| `gemma3:9b` | 5.5GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ~35 t/s | 🔥 推荐测试 |
| `qwen2.5:14b` | 9GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ~20 t/s | 质量优先时 |
| `llama3.1:8b` | 4.9GB | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ~40 t/s | 英文项目 |
| `phi4:14b` | 8.9GB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ~20 t/s | 代码/推理强 |

---

### Gemma 适合本项目吗？

**适合点：**
- `gemma4:e4b` 在 JSON 结构化输出上表现极佳（GovBench JSON 任务领先），`ingest` 提取成功率更高
- Gemma 4 专门为"agentic workflows"优化 —— 与本项目 MCP 工具场景高度吻合
- Ollama 官方支持：`ollama pull gemma3:4b` / `gemma4:e4b`
- 模型更小（e4b 2.5GB < qwen2.5:7b 4.7GB），冷启动更快

**不足点：**
- **中文质量略弱于 qwen**：Gemma 以英文为主训练，`wiki-compile` 生成的中文 Markdown 可能不如 qwen 流畅
- `qwen2.5:7b` 在中文记忆、总结类任务上仍是 7B 级最强

---

## 三、本机（M4 Pro 64GB）运行能力

| 模型 | 大小 | 内存占用 | 速度 | 可运行 |
|------|------|----------|------|--------|
| nomic-embed-text | 270MB | ~500MB | 20-40ms/次 | ✅ |
| EmbeddingGemma | ~400MB | ~700MB | 20-40ms/次 | ✅ |
| bge-m3 | 1.2GB | ~2GB | 30-60ms/次 | ✅ |
| qwen2.5:7b | 4.7GB | ~6GB | ~40 t/s | ✅ |
| gemma4:e4b | 2.5GB | ~3.5GB | ~60 t/s | ✅ |
| gemma3:9b | 5.5GB | ~7GB | ~35 t/s | ✅ |
| qwen2.5:14b | 9GB | ~11GB | ~20 t/s | ✅ |
| gemma4:26b | 16GB | ~20GB | ~12 t/s | ✅ |
| gemma4:31b | 20GB | ~25GB | ~10 t/s | ✅ |

M4 Pro 统一内存架构（CPU+GPU 共享 64GB）可以流畅运行到 31B 级模型，无需量化也能跑 26B。

---

## 四、推荐选型路径

### 短期（现状维持）
```
Embedding: nomic-embed-text  ← 当前，够用
LLM:       qwen2.5:7b        ← 当前，中文合成质量好
```

### 中期（推荐测试）
```
Embedding: bge-m3             ← 中文 wiki 记录多时
LLM:       gemma4:e4b         ← JSON 结构输出更可靠，体积更小
```

验证方式：
```bash
# 测试 gemma4:e4b 的 ingest JSON 输出质量
export AMEM_LLM_PROVIDER=ollama
export AMEM_LLM_MODEL=gemma4:e4b
amem ingest docs/test-pr.md --type pr-review --dry-run
```

### 长期（质量优先）
```
Embedding: EmbeddingGemma     ← 等 Ollama 官方支持稳定后
LLM:       qwen2.5:14b        ← 中文质量最佳；或 gemma4:26b（综合最强）
```

---

## 五、配置方式

```bash
# 拉取推荐模型
ollama pull bge-m3
ollama pull gemma4:e4b

# 切换配置（.env 或 shell）
export AMEM_EMBED_PROVIDER=ollama
export AMEM_EMBED_MODEL=bge-m3        # 未来扩展，当前硬编码 nomic-embed-text
export AMEM_LLM_PROVIDER=ollama
export AMEM_LLM_MODEL=gemma4:e4b
```

> **注**：当前 `OLLAMA_EMBED_MODEL` 常量硬编码为 `nomic-embed-text`（`constants.py`）。  
> 若要切换 embedding 模型，需修改 `constants.py` 中的 `OLLAMA_EMBED_MODEL` 值，或添加 `AMEM_EMBED_MODEL` 环境变量支持。
