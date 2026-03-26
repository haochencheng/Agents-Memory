from __future__ import annotations

import os
import sys
from pathlib import Path

from agents_memory.constants import (
	DEFAULT_QDRANT_COLLECTION,
	DEFAULT_QDRANT_HOST,
	DEFAULT_QDRANT_PORT,
	EMBED_DIM,
	VECTOR_THRESHOLD,
)
from agents_memory.runtime import AppContext
from agents_memory.services.records import build_record_text, cmd_search, get_embedding, parse_frontmatter, total_error_count


def qdrant_settings() -> tuple[str, int, str]:
	host = os.getenv("QDRANT_HOST", DEFAULT_QDRANT_HOST)
	port = int(os.getenv("QDRANT_PORT", str(DEFAULT_QDRANT_PORT)))
	collection = os.getenv("QDRANT_COLLECTION", DEFAULT_QDRANT_COLLECTION)
	return host, port, collection


def cmd_embed(ctx: AppContext) -> None:
	try:
		import lancedb
	except ImportError:
		print("请先安装依赖：pip install lancedb openai pyarrow")
		sys.exit(1)

	all_files = sorted(ctx.errors_dir.glob("*.md"))
	if ctx.archive_dir.exists():
		all_files += sorted(ctx.archive_dir.glob("*.md"))
	if not all_files:
		print("No error records to embed.")
		return

	records_raw = [(parse_frontmatter(filepath), filepath) for filepath in all_files if parse_frontmatter(filepath)]
	print(f"Embedding {len(records_raw)} records using text-embedding-3-small...")

	ctx.vector_dir.mkdir(parents=True, exist_ok=True)
	db = lancedb.connect(str(ctx.vector_dir))

	rows = []
	for index, (meta, filepath) in enumerate(records_raw, 1):
		text = build_record_text(meta, filepath)
		vector = get_embedding(text)
		rows.append(
			{
				"id": meta.get("id", filepath.stem),
				"project": meta.get("project", ""),
				"category": meta.get("category", ""),
				"domain": meta.get("domain", ""),
				"severity": meta.get("severity", ""),
				"status": meta.get("status", ""),
				"filepath": str(filepath),
				"text": text,
				"vector": vector,
			}
		)
		print(f"  [{index}/{len(records_raw)}] {meta.get('id', filepath.stem)}")

	if "errors" in db.table_names():
		db.drop_table("errors")
	db.create_table("errors", data=rows)
	print(f"\nVector index built: {len(rows)} records → {ctx.vector_dir}/errors.lance")


def cmd_vsearch(ctx: AppContext, query: str, top_k: int = 5) -> None:
	try:
		import lancedb
	except ImportError:
		print("LanceDB 未安装，回退到关键词搜索。安装：pip install lancedb openai pyarrow")
		cmd_search(ctx, query)
		return

	if not ctx.vector_dir.exists():
		print("向量索引不存在。请先运行：python3 scripts/memory.py embed")
		print("回退到关键词搜索...\n")
		cmd_search(ctx, query)
		return

	db = lancedb.connect(str(ctx.vector_dir))
	if "errors" not in db.table_names():
		print("向量表为空。请先运行：python3 scripts/memory.py embed")
		cmd_search(ctx, query)
		return

	count = total_error_count(ctx)
	if count < VECTOR_THRESHOLD:
		print(f"当前记录数 ({count}) 未达向量搜索阈值 ({VECTOR_THRESHOLD})，使用关键词搜索。\n")
		cmd_search(ctx, query)
		return

	print(f"Semantic search: '{query}'  (top {top_k})\n")
	query_vector = get_embedding(query)
	results = db.open_table("errors").search(query_vector).limit(top_k).to_list()
	if not results:
		print(f"No semantic matches for '{query}'")
		return

	print(f"{'Score':<10} {'ID':<38} {'Project':<20} {'Category':<18} Status")
	print("-" * 100)
	for row in results:
		distance = row.get("_distance", 0.0)
		similarity = max(0.0, 1.0 - distance)
		print(
			f"{similarity:<10.4f} {row['id']:<38} {row['project']:<20} "
			f"{row['category']:<18} {row['status']}"
		)


def cmd_to_qdrant(ctx: AppContext) -> None:
	try:
		import lancedb
		from qdrant_client import QdrantClient
		from qdrant_client.models import Distance, PointStruct, VectorParams
	except ImportError:
		print("请先安装：pip install qdrant-client lancedb")
		sys.exit(1)

	if not ctx.vector_dir.exists():
		print("本地 LanceDB 索引不存在。请先运行：python3 scripts/memory.py embed")
		sys.exit(1)

	db = lancedb.connect(str(ctx.vector_dir))
	if "errors" not in db.table_names():
		print("LanceDB 向量表为空，请先运行 embed。")
		sys.exit(1)

	rows = db.open_table("errors").to_list()
	if not rows:
		print("向量表中没有数据。")
		return

	host, port, collection = qdrant_settings()
	client = QdrantClient(host=host, port=port)
	existing = [item.name for item in client.get_collections().collections]
	if collection in existing:
		print(f"集合 '{collection}' 已存在，删除并重建...")
		client.delete_collection(collection)

	client.create_collection(
		collection_name=collection,
		vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
	)

	points = [
		PointStruct(
			id=index,
			vector=row["vector"],
			payload={key: row[key] for key in ("id", "project", "category", "domain", "severity", "status", "filepath")},
		)
		for index, row in enumerate(rows)
	]
	client.upsert(collection_name=collection, points=points)
	print(f"✅ 迁移完成：{len(points)} 条记录 → Qdrant ({host}:{port}/{collection})")
	print(f"\nQdrant Dashboard: http://{host}:6333/dashboard")

