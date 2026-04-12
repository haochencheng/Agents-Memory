from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import re
from typing import Any


_GENERIC_HEADINGS = {
    "时间线",
    "timeline",
    "结论",
    "compiled truth",
    "known pattern",
    "task status",
    "close-out summary",
    "problem",
    "root cause",
    "fix",
    "context",
    "背景",
    "实现",
    "关联",
    "summary",
}

_DECISION_HINTS = {
    "decision",
    "adr",
    "architecture",
    "tradeoff",
    "plan",
    "spec",
    "validation",
    "roadmap",
    "design",
    "方案",
    "决策",
    "架构",
}

_ERROR_HINTS = {
    "bug",
    "error",
    "failure",
    "failed",
    "incident",
    "exception",
    "timeout",
    "regression",
    "404",
    "500",
    "故障",
    "异常",
    "失败",
    "错误",
}

_MODULE_HINTS = {
    "api",
    "service",
    "module",
    "workflow",
    "auth",
    "billing",
    "recharge",
    "refund",
    "frontend",
    "backend",
    "provider",
    "gateway",
    "scheduler",
    "search",
    "memory",
    "ingest",
    "profile",
    "token",
    "redis",
    "jwt",
}

_EDGE_PROPAGATION_WEIGHTS = {
    "explicit": 0.34,
    "inferred": 0.24,
    "mentions": 0.16,
    "contains": 0.1,
}


@dataclass(frozen=True)
class ConceptGraphContext:
    nodes_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[dict[str, Any]] = field(default_factory=list)
    primary_concept_by_topic: dict[str, str] = field(default_factory=dict)
    topic_concepts: dict[str, list[str]] = field(default_factory=dict)
    adjacency: dict[str, list[tuple[str, str, float]]] = field(default_factory=dict)


def _slugify_label(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "unknown"


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip())


def _tokenize_search_text(value: str) -> list[str]:
    return re.findall(r"[a-z0-9\u4e00-\u9fff]{2,}", value.lower())


def _heading_candidates(raw: str) -> list[str]:
    headings: list[str] = []
    for match in re.finditer(r"^#{1,3}\s+(.+)$", raw, flags=re.MULTILINE):
        heading = _normalize_label(match.group(1))
        if not heading or heading.lower() in _GENERIC_HEADINGS:
            continue
        headings.append(heading)
    return headings[:6]


def _inline_candidates(raw: str) -> list[str]:
    inline: list[str] = []
    for match in re.finditer(r"`([^`\n]{3,48})`", raw):
        candidate = _normalize_label(match.group(1))
        if candidate:
            inline.append(candidate)
    for match in re.finditer(r"\b[A-Z][A-Za-z0-9]{3,}\b|\b[a-z]+(?:_[a-z0-9]+){1,3}\b", raw):
        candidate = _normalize_label(match.group(0))
        if candidate:
            inline.append(candidate)
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in inline:
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped[:8]


def infer_concept_type(label: str, *, page_doc_type: str = "", raw: str = "", tags: list[str] | None = None) -> str:
    lowered = label.lower()
    body = raw.lower()
    tag_set = {tag.lower() for tag in (tags or [])}
    if any(hint in lowered for hint in _ERROR_HINTS) or any(hint in tag_set for hint in _ERROR_HINTS):
        return "error_pattern"
    if any(hint in lowered for hint in _DECISION_HINTS):
        return "decision"
    if any(hint in lowered for hint in _MODULE_HINTS) or re.search(r"[A-Z][A-Za-z0-9]{3,}", label):
        return "module"
    if page_doc_type in {"architecture", "plan", "product", "ops"}:
        return "decision"
    if any(hint in body for hint in _ERROR_HINTS) and "error" in lowered:
        return "error_pattern"
    return "entity"


def extract_page_concepts(page: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    title = _normalize_label(str(page.get("title", "") or page.get("topic", "")))
    raw = str(page.get("raw", ""))
    doc_type = str(page.get("doc_type", ""))
    tags = [str(tag) for tag in page.get("tags", []) if str(tag)]
    topic = str(page.get("topic", ""))
    project = str(page.get("project", ""))

    candidates: list[tuple[float, str]] = []
    if title:
        candidates.append((3.0, title))
    for heading in _heading_candidates(raw):
        candidates.append((2.4, heading))
    for tag in tags:
        if tag == project or tag == doc_type:
            continue
        candidates.append((1.4, tag.replace("-", " ")))
    for inline in _inline_candidates(raw):
        candidates.append((1.8, inline))

    concepts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for score, label in sorted(candidates, key=lambda item: (-item[0], item[1].lower())):
        normalized_label = _normalize_label(label)
        if len(normalized_label) < 3:
            continue
        node_type = infer_concept_type(normalized_label, page_doc_type=doc_type, raw=raw, tags=tags)
        concept_id = f"{node_type}:{_slugify_label(normalized_label)}"
        if concept_id in seen_ids:
            continue
        seen_ids.add(concept_id)
        concepts.append(
            {
                "id": concept_id,
                "title": normalized_label,
                "node_type": node_type,
                "score": round(score, 2),
                "primary_topic": topic,
                "project": project,
                "tags": tags,
            }
        )
        if len(concepts) >= limit:
            break
    if not concepts:
        concepts.append(
            {
                "id": f"entity:{_slugify_label(topic)}",
                "title": title or topic,
                "node_type": "entity",
                "score": 1.0,
                "primary_topic": topic,
                "project": project,
                "tags": tags,
            }
        )
    return concepts


def build_concept_graph_context(
    catalog: dict[str, dict[str, Any]],
    page_edges: list[Any],
) -> ConceptGraphContext:
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    primary_concept_by_topic: dict[str, str] = {}
    topic_concepts: dict[str, list[str]] = {}

    def merge_node(node: dict[str, Any]) -> None:
        existing = nodes_by_id.get(str(node["id"]))
        if existing is None:
            nodes_by_id[str(node["id"])] = dict(node)
            return
        merged_tags = sorted(set(existing.get("tags", [])) | set(node.get("tags", [])))
        nodes_by_id[str(node["id"])] = {
            "id": existing["id"],
            "title": existing["title"],
            "node_type": existing["node_type"],
            "project": existing.get("project") or node.get("project", ""),
            "word_count": max(int(existing.get("word_count", 0)), int(node.get("word_count", 0))),
            "tags": merged_tags,
            "primary_topic": existing.get("primary_topic") or node.get("primary_topic", ""),
            "topic_count": int(existing.get("topic_count", 0)) + int(node.get("topic_count", 0)),
        }

    def add_edge(source: str, target: str, edge_type: str, weight: float) -> None:
        edge_key = (source, target, edge_type)
        if edge_key in seen_edges:
            return
        seen_edges.add(edge_key)
        edges.append(
            {
                "source": source,
                "target": target,
                "type": edge_type,
                "weight": round(float(weight), 2),
            }
        )

    for topic, page in catalog.items():
        concepts = extract_page_concepts(page)
        concept_ids = [str(concept["id"]) for concept in concepts]
        if not concept_ids:
            continue
        primary_concept_by_topic[topic] = concept_ids[0]
        topic_concepts[topic] = concept_ids

        for index, concept in enumerate(concepts):
            merge_node(
                {
                    "id": str(concept["id"]),
                    "title": str(concept["title"]),
                    "node_type": str(concept["node_type"]),
                    "project": str(page.get("project", "")),
                    "word_count": int(page.get("word_count", 0)),
                    "tags": [str(tag) for tag in page.get("tags", []) if str(tag)],
                    "primary_topic": topic,
                    "topic_count": 1,
                }
            )
            if index > 0:
                add_edge(concept_ids[0], concept_ids[index], "mentions", float(concept["score"]))

        project = str(page.get("project", ""))
        if project:
            entity_id = f"entity:{project}"
            merge_node(
                {
                    "id": entity_id,
                    "title": project,
                    "node_type": "entity",
                    "project": project,
                    "word_count": 0,
                    "tags": [project],
                    "primary_topic": "",
                    "topic_count": 0,
                }
            )
            add_edge(entity_id, concept_ids[0], "contains", 1.0)

    for edge in page_edges:
        source_topic = str(getattr(edge, "source", "") or edge.get("source", ""))
        target_topic = str(getattr(edge, "target", "") or edge.get("target", ""))
        source_id = primary_concept_by_topic.get(source_topic)
        target_id = primary_concept_by_topic.get(target_topic)
        if not source_id or not target_id:
            continue
        edge_type = str(getattr(edge, "type", "") or edge.get("type", ""))
        weight = float(getattr(edge, "weight", 0.0) or edge.get("weight", 0.0) or 0.0)
        add_edge(source_id, target_id, edge_type, weight)

    adjacency: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        edge_type = str(edge["type"])
        weight = float(edge["weight"])
        adjacency[source].append((target, edge_type, weight))
        adjacency[target].append((source, edge_type, weight))

    return ConceptGraphContext(
        nodes_by_id=nodes_by_id,
        edges=edges,
        primary_concept_by_topic=primary_concept_by_topic,
        topic_concepts=topic_concepts,
        adjacency=dict(adjacency),
    )


def score_query_concepts(query: str, context: ConceptGraphContext) -> dict[str, float]:
    query_tokens = set(_tokenize_search_text(query))
    if not query_tokens:
        return {}
    lowered_query = query.strip().lower()
    direct_scores: dict[str, float] = {}
    for node_id, node in context.nodes_by_id.items():
        title = str(node.get("title", ""))
        tags = [str(tag) for tag in node.get("tags", []) if str(tag)]
        title_tokens = set(_tokenize_search_text(title))
        tag_tokens = set(_tokenize_search_text(" ".join(tags)))
        score = 0.0
        shared_title = query_tokens & title_tokens
        if shared_title:
            score += min(len(shared_title), 3) * 0.8
        if lowered_query and lowered_query in title.lower():
            score += 0.55
        shared_tags = query_tokens & tag_tokens
        if shared_tags:
            score += min(len(shared_tags), 2) * 0.25
        primary_topic = str(node.get("primary_topic", ""))
        if lowered_query and primary_topic and lowered_query.replace(" ", "-") in primary_topic.lower():
            score += 0.2
        if score > 0:
            direct_scores[node_id] = round(score, 4)

    concept_scores = dict(direct_scores)
    for node_id, base_score in direct_scores.items():
        for neighbor_id, edge_type, edge_weight in context.adjacency.get(node_id, []):
            propagated = base_score * _EDGE_PROPAGATION_WEIGHTS.get(edge_type, 0.08) * max(0.5, min(edge_weight, 3.0))
            if propagated <= concept_scores.get(neighbor_id, 0.0):
                continue
            concept_scores[neighbor_id] = round(propagated, 4)
    return concept_scores


def extract_record_concept_ids(record: dict[str, Any], context: ConceptGraphContext) -> list[str]:
    topic = str(record.get("topic", "") or record.get("id", ""))
    if topic in context.topic_concepts:
        return list(context.topic_concepts[topic])

    title = str(record.get("title", "") or topic)
    snippet = str(record.get("snippet", ""))
    project = str(record.get("project", ""))
    doc_type = str(record.get("doc_type", "") or record.get("source_type", "") or record.get("type", ""))
    tags = [
        value
        for value in [project, doc_type, str(record.get("source_type", "")), str(record.get("type", ""))]
        if value
    ]
    pseudo_page = {
        "topic": topic,
        "title": title,
        "raw": f"{title}\n\n{snippet}",
        "doc_type": doc_type,
        "project": project,
        "tags": tags,
    }
    concept_ids = [
        str(concept["id"])
        for concept in extract_page_concepts(pseudo_page, limit=4)
        if str(concept["id"]) in context.nodes_by_id
    ]
    if project:
        entity_id = f"entity:{project}"
        if entity_id in context.nodes_by_id:
            concept_ids.append(entity_id)
    deduped: list[str] = []
    seen: set[str] = set()
    for concept_id in concept_ids:
        if concept_id in seen:
            continue
        seen.add(concept_id)
        deduped.append(concept_id)
    return deduped


def graph_boost_for_search_record(
    record: dict[str, Any],
    *,
    query: str,
    context: ConceptGraphContext,
    concept_scores: dict[str, float] | None = None,
) -> float:
    explanation = graph_rerank_explanation_for_search_record(
        record,
        query=query,
        context=context,
        concept_scores=concept_scores,
    )
    return float(explanation["boost"])


def graph_rerank_explanation_for_search_record(
    record: dict[str, Any],
    *,
    query: str,
    context: ConceptGraphContext,
    concept_scores: dict[str, float] | None = None,
) -> dict[str, Any]:
    scores = concept_scores or score_query_concepts(query, context)
    concept_ids = extract_record_concept_ids(record, context)
    if not concept_ids:
        return {"boost": 0.0, "reasons": [], "matched_concepts": []}
    matched_scores = [scores.get(concept_id, 0.0) for concept_id in concept_ids if scores.get(concept_id, 0.0) > 0]
    if not matched_scores:
        return {"boost": 0.0, "reasons": [], "matched_concepts": []}
    boost = max(matched_scores)
    if len(matched_scores) > 1:
        boost += min(0.12, 0.04 * (len(matched_scores) - 1))
    matched_concepts = [
        {
            "id": concept_id,
            "title": str(context.nodes_by_id.get(concept_id, {}).get("title", concept_id)),
            "node_type": str(context.nodes_by_id.get(concept_id, {}).get("node_type", "")),
            "score": round(scores.get(concept_id, 0.0), 4),
            "primary_topic": str(context.nodes_by_id.get(concept_id, {}).get("primary_topic", "")),
            "project": str(context.nodes_by_id.get(concept_id, {}).get("project", "")),
        }
        for concept_id in concept_ids
        if scores.get(concept_id, 0.0) > 0
    ]
    matched_concepts.sort(key=lambda item: (-float(item["score"]), str(item["title"]).lower()))
    reasons = [
        f"命中概念: {item['title']}"
        for item in matched_concepts[:2]
    ]
    if len(matched_concepts) > 1:
        reasons.append(f"图谱关联放大 +{min(0.12, 0.04 * (len(matched_concepts) - 1)):.2f}")
    return {
        "boost": round(min(boost, 0.95), 4),
        "reasons": reasons,
        "matched_concepts": matched_concepts[:3],
    }
