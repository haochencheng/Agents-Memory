from __future__ import annotations

import unittest

from agents_memory.services.wiki_knowledge import (
    build_concept_graph_context,
    extract_page_concepts,
    graph_boost_for_search_record,
    graph_rerank_explanation_for_search_record,
    infer_concept_type,
    score_query_concepts,
)


class WikiKnowledgeTests(unittest.TestCase):
    def test_infer_concept_type_detects_error_pattern(self) -> None:
        concept_type = infer_concept_type("Bug Frontend 404 Routes Failed", page_doc_type="maintenance")
        self.assertEqual(concept_type, "error_pattern")

    def test_extract_page_concepts_prefers_title_then_headings(self) -> None:
        page = {
            "topic": "auth-migration-decision",
            "title": "Auth Migration Decision",
            "doc_type": "architecture",
            "project": "synapse-network",
            "tags": ["architecture", "auth", "redis"],
            "raw": "# Auth Migration Decision\n\n## Redis Cache\n\n## JWT Refresh\n\nUse `AuthService` and `RedisTokenStore`.\n",
        }
        concepts = extract_page_concepts(page)
        ids = [concept["id"] for concept in concepts]
        self.assertEqual(ids[0], "decision:auth-migration-decision")
        self.assertIn("module:redis-cache", ids)
        self.assertTrue(any(concept["title"] == "AuthService" for concept in concepts))

    def test_query_scores_propagate_across_concept_graph(self) -> None:
        catalog = {
            "auth-design": {
                "topic": "auth-design",
                "title": "Auth Design",
                "doc_type": "architecture",
                "project": "synapse-network",
                "tags": ["auth", "jwt"],
                "raw": "# Auth Design\n\n## JWT Refresh\nUse `AuthService`.\n",
                "word_count": 120,
            },
            "billing-recharge": {
                "topic": "billing-recharge",
                "title": "Billing Recharge",
                "doc_type": "guide",
                "project": "synapse-network",
                "tags": ["billing", "recharge"],
                "raw": "# Billing Recharge\n\nReferences auth settlement.\n",
                "word_count": 80,
            },
        }
        page_edges = [
            {"source": "auth-design", "target": "billing-recharge", "type": "explicit", "weight": 3.0},
        ]
        context = build_concept_graph_context(catalog, page_edges)
        scores = score_query_concepts("jwt", context)

        self.assertGreater(scores.get("decision:auth-design", 0.0), 0.0)
        self.assertGreater(scores.get("module:billing-recharge", 0.0), 0.0)

    def test_graph_boost_can_rerank_related_workflow_record(self) -> None:
        catalog = {
            "auth-design": {
                "topic": "auth-design",
                "title": "Auth Design",
                "doc_type": "architecture",
                "project": "synapse-network",
                "tags": ["auth", "jwt"],
                "raw": "# Auth Design\n\n## JWT Refresh\nUse `AuthService`.\n",
                "word_count": 120,
            },
        }
        context = build_concept_graph_context(catalog, [])
        scores = score_query_concepts("jwt", context)
        workflow_boost = graph_boost_for_search_record(
            {
                "type": "workflow",
                "id": "TASK-42",
                "title": "Implement JWT Refresh flow",
                "snippet": "Update AuthService and RedisTokenStore handling.",
                "project": "synapse-network",
                "source_type": "task_completion",
            },
            query="jwt",
            context=context,
            concept_scores=scores,
        )

        self.assertGreater(workflow_boost, 0.0)

    def test_graph_rerank_explanation_returns_reasons(self) -> None:
        catalog = {
            "auth-design": {
                "topic": "auth-design",
                "title": "Auth Design",
                "doc_type": "architecture",
                "project": "synapse-network",
                "tags": ["auth", "jwt"],
                "raw": "# Auth Design\n\n## JWT Refresh\nUse `AuthService`.\n",
                "word_count": 120,
            },
        }
        context = build_concept_graph_context(catalog, [])
        explanation = graph_rerank_explanation_for_search_record(
            {
                "type": "workflow",
                "id": "TASK-99",
                "title": "JWT Refresh rollout",
                "snippet": "Touch AuthService and auth gateway.",
                "project": "synapse-network",
                "source_type": "task_completion",
            },
            query="jwt",
            context=context,
        )

        self.assertGreater(explanation["boost"], 0.0)
        self.assertTrue(explanation["reasons"])
        self.assertTrue(explanation["matched_concepts"])
        self.assertEqual(explanation["matched_concepts"][0]["primary_topic"], "auth-design")
