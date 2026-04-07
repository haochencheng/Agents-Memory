---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# Embed — Ollama 本地向量嵌入

## 设计目标

原有系统强依赖 OpenAI `text-embedding-3-small`，开发测试需要消耗 API Token。本特性添加 Ollama `nomic-embed-text` 作为本地可选 embedding 提供商：

- 零 API Key：纯本地推理，适合离线开发
- Docker 一键启动：`docker-compose up -d ollama`
- 通过环境变量切换，不改任何业务代码

---

## 架构设计

```
AMEM_EMBED_PROVIDER=openai (default)
    └─→ _get_openai_embedding()
            openai.OpenAI().embeddings.create(model="text-embedding-3-small")
            1536 维向量

AMEM_EMBED_PROVIDER=ollama
    └─→ _get_ollama_embedding()
            urllib.request.urlopen → {OLLAMA_HOST}/api/embeddings
            model: nomic-embed-text
            768 维向量
```

---

## 提供商对比

| 属性 | OpenAI | Ollama nomic-embed-text |
|------|--------|------------------------|
| 维度 | 1536 | 768 |
| 费用 | $0.02 / 1M tokens | 免费（本地）|
| 延迟 | ~100ms（网络）| ~50ms（本地 CPU）|
| 依赖 | `openai` SDK + API Key | Ollama 服务在本地运行 |
| 适用场景 | 生产环境 | 本地开发 / CI |

---

## 关键常量（constants.py）

```python
EMBED_PROVIDER_ENV = "AMEM_EMBED_PROVIDER"    # 环境变量名
OLLAMA_EMBED_MODEL = "nomic-embed-text"        # Ollama 使用的模型
OLLAMA_EMBED_DIM   = 768                       # 向量维度
OLLAMA_HOST_ENV    = "OLLAMA_HOST"             # 指向 Ollama API 的环境变量
DEFAULT_OLLAMA_HOST = "http://localhost:11434"  # 默认地址
```

---

## API（records.py）

```python
def get_embedding(text: str) -> list[float]:
    """Return embedding vector.
    
    AMEM_EMBED_PROVIDER=openai (default) → OpenAI 1536d
    AMEM_EMBED_PROVIDER=ollama           → Ollama nomic-embed-text 768d
    """

def _get_openai_embedding(text: str) -> list[float]:
    """OpenAI text-embedding-3-small via openai SDK."""

def _get_ollama_embedding(text: str) -> list[float]:
    """POST {OLLAMA_HOST}/api/embeddings with nomic-embed-text.
    
    Uses stdlib urllib.request only (zero extra dependencies).
    Calls sys.exit(1) if Ollama is unreachable.
    """
```

### Ollama API 调用细节

```python
url = f"{host}/api/embeddings"
payload = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
request = urllib.request.Request(
    url, data=payload, method="POST",
    headers={"Content-Type": "application/json"},
)
# timeout=30s；失败 → 打印错误 → sys.exit(1)
data = json.loads(response.read())
return data["embedding"]   # list[float], len=768
```

---

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `AMEM_EMBED_PROVIDER` | `openai` | `openai` 或 `ollama` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama 服务地址 |
| `OPENAI_API_KEY` | — | `openai` provider 必须 |

---

## Docker 服务（docker/docker-compose.yml）

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: agents-memory-ollama
  ports:
    - "${OLLAMA_PORT:-11434}:11434"
  volumes:
    - ollama_models:/root/.ollama
  environment:
    - OLLAMA_HOST=0.0.0.0
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
    interval: 15s
    timeout: 10s
    retries: 5
    start_period: 30s
```

---

## 快速启动

```bash
# 1. 启动 Ollama 容器
cd docker && docker-compose up -d ollama

# 2. 拉取模型（首次使用）
docker exec -it agents-memory-ollama ollama pull nomic-embed-text

# 3. 切换到 Ollama embedding
export AMEM_EMBED_PROVIDER=ollama

# 4. 验证
python3 -c "
from agents_memory.services.records import get_embedding
v = get_embedding('test')
print(len(v))  # 预期: 768
"
```

---

## 测试覆盖

文件：`tests/test_ollama_embedding.py`（15 个测试）

| 测试类 | 覆盖内容 |
|--------|----------|
| `TestGetEmbeddingProviderSelection` | `AMEM_EMBED_PROVIDER` 未设置→调用 OpenAI；设置 `ollama`→调用 Ollama；大小写；无效 provider |
| `TestGetOpenAIEmbedding` | openai SDK 调用验证；返回 list[float] |
| `TestGetOllamaEmbedding` | 正常返回 768d；Ollama 不可达→sys.exit(1)；超时；payload 格式；URL 构建；自定义 OLLAMA_HOST |
| `TestEmbedDimConstants` | `OLLAMA_EMBED_DIM == 768`；`OLLAMA_EMBED_MODEL == "nomic-embed-text"`；`DEFAULT_OLLAMA_HOST` 格式 |

---

## 状态

✅ 已实现并测试通过。291 个全局测试 OK。
