"""Tests for get_embedding() — OpenAI + Ollama provider selection.

All tests are fully offline — no real API calls are made.
Both _get_openai_embedding and _get_ollama_embedding are mocked.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from agents_memory.constants import (
    DEFAULT_OLLAMA_HOST,
    EMBED_PROVIDER_ENV,
    OLLAMA_EMBED_DIM,
    OLLAMA_EMBED_MODEL,
    OLLAMA_HOST_ENV,
)
from agents_memory.services.records import (
    _get_ollama_embedding,
    _get_openai_embedding,
    get_embedding,
)


# ---------------------------------------------------------------------------
# TestGetEmbeddingProviderSelection
# ---------------------------------------------------------------------------


class TestGetEmbeddingProviderSelection(unittest.TestCase):
    """Verify that get_embedding() routes to the correct provider based on env var."""

    def test_default_uses_openai(self):
        env = {k: v for k, v in os.environ.items() if k != EMBED_PROVIDER_ENV}
        with patch.dict(os.environ, env, clear=True):
            with patch("agents_memory.services.records._get_openai_embedding", return_value=[0.1] * 1536) as mock_oa:
                result = get_embedding("test query")
        mock_oa.assert_called_once_with("test query")
        self.assertEqual(len(result), 1536)

    def test_openai_explicit_uses_openai(self):
        with patch.dict(os.environ, {EMBED_PROVIDER_ENV: "openai"}):
            with patch("agents_memory.services.records._get_openai_embedding", return_value=[0.2] * 1536) as mock_oa:
                result = get_embedding("hello")
        mock_oa.assert_called_once_with("hello")
        self.assertEqual(len(result), 1536)

    def test_ollama_provider_uses_ollama(self):
        with patch.dict(os.environ, {EMBED_PROVIDER_ENV: "ollama"}):
            with patch("agents_memory.services.records._get_ollama_embedding", return_value=[0.3] * 768) as mock_ol:
                result = get_embedding("embedding text")
        mock_ol.assert_called_once_with("embedding text")
        self.assertEqual(len(result), 768)

    def test_unknown_provider_falls_through_to_openai(self):
        """Unrecognised provider values should fall back to OpenAI (safe default)."""
        with patch.dict(os.environ, {EMBED_PROVIDER_ENV: "azure"}):
            with patch("agents_memory.services.records._get_openai_embedding", return_value=[0.1] * 1536) as mock_oa:
                get_embedding("text")
        mock_oa.assert_called_once()


# ---------------------------------------------------------------------------
# TestGetOpenAIEmbedding
# ---------------------------------------------------------------------------


class TestGetOpenAIEmbedding(unittest.TestCase):
    def test_calls_openai_api(self):
        mock_openai = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data[0].embedding = [0.5] * 1536
        mock_openai.OpenAI.return_value.embeddings.create.return_value = mock_resp

        with patch.dict(sys.modules, {"openai": mock_openai}):
            result = _get_openai_embedding("test")

        self.assertEqual(result, [0.5] * 1536)
        mock_openai.OpenAI.return_value.embeddings.create.assert_called_once()

    def test_exits_when_openai_not_installed(self):
        with patch.dict(sys.modules, {"openai": None}):
            with self.assertRaises(SystemExit):
                _get_openai_embedding("text")


# ---------------------------------------------------------------------------
# TestGetOllamaEmbedding
# ---------------------------------------------------------------------------


class TestGetOllamaEmbedding(unittest.TestCase):
    def _make_mock_response(self, embedding: list[float]):
        """Build a mock urllib response returning the given embedding."""
        import io
        body = json.dumps({"embedding": embedding}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_returns_embedding_from_ollama(self):
        expected = [0.1] * OLLAMA_EMBED_DIM
        mock_resp = self._make_mock_response(expected)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _get_ollama_embedding("test")
        self.assertEqual(result, expected)
        self.assertEqual(len(result), OLLAMA_EMBED_DIM)

    def test_uses_default_ollama_host(self):
        expected = [0.0] * OLLAMA_EMBED_DIM
        mock_resp = self._make_mock_response(expected)
        calls = []

        def capture_urlopen(req, timeout=None):
            calls.append(req.full_url)
            return mock_resp

        env = {k: v for k, v in os.environ.items() if k != OLLAMA_HOST_ENV}
        with patch.dict(os.environ, env, clear=True):
            with patch("urllib.request.urlopen", side_effect=capture_urlopen):
                _get_ollama_embedding("text")

        self.assertTrue(calls[0].startswith(DEFAULT_OLLAMA_HOST))
        self.assertIn("/api/embeddings", calls[0])

    def test_uses_custom_ollama_host(self):
        expected = [0.0] * OLLAMA_EMBED_DIM
        mock_resp = self._make_mock_response(expected)
        calls = []

        def capture_urlopen(req, timeout=None):
            calls.append(req.full_url)
            return mock_resp

        with patch.dict(os.environ, {OLLAMA_HOST_ENV: "http://custom-host:11434"}):
            with patch("urllib.request.urlopen", side_effect=capture_urlopen):
                _get_ollama_embedding("text")

        self.assertIn("custom-host:11434", calls[0])

    def test_sends_correct_model_in_payload(self):
        expected = [0.0] * OLLAMA_EMBED_DIM
        mock_resp = self._make_mock_response(expected)
        payloads = []

        def capture_urlopen(req, timeout=None):
            payloads.append(json.loads(req.data.decode()))
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
            _get_ollama_embedding("my text")

        self.assertEqual(payloads[0]["model"], OLLAMA_EMBED_MODEL)
        self.assertEqual(payloads[0]["prompt"], "my text")

    def test_exits_when_ollama_unavailable(self):
        with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
            with self.assertRaises(SystemExit):
                _get_ollama_embedding("text")

    def test_strips_trailing_slash_from_host(self):
        expected = [0.0] * OLLAMA_EMBED_DIM
        mock_resp = self._make_mock_response(expected)
        calls = []

        def capture_urlopen(req, timeout=None):
            calls.append(req.full_url)
            return mock_resp

        with patch.dict(os.environ, {OLLAMA_HOST_ENV: "http://localhost:11434/"}):
            with patch("urllib.request.urlopen", side_effect=capture_urlopen):
                _get_ollama_embedding("text")

        # Should not have double slashes
        self.assertNotIn("//api", calls[0])


# ---------------------------------------------------------------------------
# TestEmbedDimConstants
# ---------------------------------------------------------------------------


class TestEmbedDimConstants(unittest.TestCase):
    def test_ollama_dim_is_768(self):
        self.assertEqual(OLLAMA_EMBED_DIM, 768)

    def test_ollama_model_name(self):
        self.assertEqual(OLLAMA_EMBED_MODEL, "nomic-embed-text")

    def test_default_ollama_host(self):
        self.assertEqual(DEFAULT_OLLAMA_HOST, "http://localhost:11434")


if __name__ == "__main__":
    unittest.main()
