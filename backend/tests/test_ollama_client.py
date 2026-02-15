"""Tests for the Ollama client with mocked HTTP responses."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.detector import DetectedEntity
from app.services.ollama_client import OllamaClient


@pytest.fixture
def sample_entities():
    """Sample entities for verification tests."""
    return [
        DetectedEntity("John Smith", "PERSON", 0, 10, 0.90, "spacy"),
        DetectedEntity("Acme Corp", "ORG", 20, 29, 0.85, "spacy"),
        DetectedEntity("john@example.com", "EMAIL", 40, 56, 0.95, "regex"),
    ]


class TestIsAvailable:
    """Tests for Ollama availability checking."""

    def test_available_when_running(self):
        client = OllamaClient(url="http://localhost:11434")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client._client, "get", return_value=mock_response):
            assert client.is_available() is True

    def test_unavailable_when_connection_refused(self):
        client = OllamaClient(url="http://localhost:99999")
        with patch.object(
            client._client, "get", side_effect=httpx.ConnectError("refused")
        ):
            assert client.is_available() is False

    def test_unavailable_on_timeout(self):
        client = OllamaClient(url="http://localhost:11434")
        with patch.object(
            client._client, "get", side_effect=httpx.TimeoutException("timeout")
        ):
            assert client.is_available() is False


class TestVerifyEntities:
    """Tests for entity verification with mocked LLM responses."""

    def test_all_valid(self, sample_entities):
        client = OllamaClient()
        llm_response = json.dumps([
            {"text": "John Smith", "is_valid": True, "entity_type": "PERSON"},
            {"text": "Acme Corp", "is_valid": True, "entity_type": "ORG"},
            {"text": "john@example.com", "is_valid": True, "entity_type": "EMAIL"},
        ])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": llm_response}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_response):
            result = client.verify_entities("some text", sample_entities)
            assert len(result) == 3

    def test_filters_invalid(self, sample_entities):
        client = OllamaClient()
        llm_response = json.dumps([
            {"text": "John Smith", "is_valid": True, "entity_type": "PERSON"},
            {"text": "Acme Corp", "is_valid": False, "entity_type": "ORG"},
            {"text": "john@example.com", "is_valid": True, "entity_type": "EMAIL"},
        ])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": llm_response}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_response):
            result = client.verify_entities("some text", sample_entities)
            assert len(result) == 2
            assert all(e.text != "Acme Corp" for e in result)

    def test_empty_entities_returns_empty(self):
        client = OllamaClient()
        result = client.verify_entities("some text", [])
        assert result == []

    def test_fallback_on_http_error(self, sample_entities):
        client = OllamaClient()
        with patch.object(
            client._client,
            "post",
            side_effect=httpx.ConnectError("connection failed"),
        ):
            result = client.verify_entities("some text", sample_entities)
            # Should return originals on error
            assert len(result) == 3

    def test_fallback_on_invalid_json(self, sample_entities):
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "This is not valid JSON at all"
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_response):
            result = client.verify_entities("some text", sample_entities)
            # Should fallback to originals
            assert len(result) == 3

    def test_handles_markdown_wrapped_json(self, sample_entities):
        client = OllamaClient()
        llm_response = '```json\n[\n{"text": "John Smith", "is_valid": true, "entity_type": "PERSON"}\n]\n```'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": llm_response}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_response):
            result = client.verify_entities("some text", sample_entities)
            assert len(result) == 1
            assert result[0].text == "John Smith"


class TestOllamaConfig:
    """Tests for configuration handling."""

    def test_default_config(self):
        client = OllamaClient()
        assert "localhost" in client._url
        assert "11434" in client._url

    def test_custom_config(self):
        client = OllamaClient(url="http://myserver:8080", model="custom-model")
        assert client._url == "http://myserver:8080"
        assert client._model == "custom-model"

    def test_env_config(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_URL", "http://env-server:9090")
        monkeypatch.setenv("OLLAMA_MODEL", "env-model")
        client = OllamaClient()
        assert client._url == "http://env-server:9090"
        assert client._model == "env-model"
