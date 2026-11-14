"""Tests for the provider-neutral LLM client."""

from unittest.mock import Mock

from google import genai
from google.genai import errors

from config import Config
from gateway.llm_client import LLMClient


class GeminiConfig(Config):
    LLM_PROVIDER = "gemini"
    GEMINI_API_KEY = "test-gemini-key"
    GEMINI_MODEL = "gemini-test-model"


def _client_with_response(monkeypatch, response=None, error=None):
    fake_client = Mock()
    fake_client.models.generate_content.return_value = response
    if error is not None:
        fake_client.models.generate_content.side_effect = error
    client_options = {}

    def create_client(**kwargs):
        client_options.update(kwargs)
        return fake_client

    monkeypatch.setattr(genai, "Client", create_client)
    return fake_client, client_options


def test_gemini_request_uses_sdk_key_timeout_and_separate_system_instruction(monkeypatch):
    fake_response = Mock()
    fake_response.text = "  Safe answer.  "
    fake_client, client_options = _client_with_response(monkeypatch, fake_response)
    llm_client = LLMClient(GeminiConfig())

    result = llm_client.generate(
        "Summarize this document.",
        "Document text.",
        timeout=12,
    )

    assert result.success
    assert result.content == "Safe answer."
    assert result.model == "gemini-test-model"
    assert client_options["api_key"] == "test-gemini-key"
    assert client_options["http_options"].timeout == 12000
    request = fake_client.models.generate_content.call_args.kwargs
    assert request["model"] == "gemini-test-model"
    assert request["config"].system_instruction
    assert "UNTRUSTED DOCUMENT CONTENT" in request["contents"]
    fake_client.close.assert_called_once()


def test_gemini_empty_response_is_an_error(monkeypatch):
    fake_response = Mock()
    fake_response.text = None
    _client_with_response(monkeypatch, fake_response)

    result = LLMClient(GeminiConfig()).generate("Explain photosynthesis.")

    assert not result.success
    assert result.content is None
    assert "empty response" in result.error.lower()


def test_gemini_rate_limit_error_is_sanitized(monkeypatch):
    api_error = errors.APIError(
        429,
        {"error": {"message": "quota detail and private request metadata"}},
    )
    _client_with_response(monkeypatch, error=api_error)

    result = LLMClient(GeminiConfig()).generate("Explain photosynthesis.")

    assert not result.success
    assert "rate limit" in result.error.lower()
    assert "private request metadata" not in result.error


def test_gemini_service_error_is_sanitized(monkeypatch):
    api_error = errors.APIError(
        503,
        {"error": {"message": "internal service detail"}},
    )
    _client_with_response(monkeypatch, error=api_error)

    result = LLMClient(GeminiConfig()).generate("Explain photosynthesis.")

    assert not result.success
    assert "temporarily unavailable" in result.error
    assert "internal service detail" not in result.error


def test_missing_gemini_key_does_not_create_sdk_client(monkeypatch):
    class MissingKeyConfig(GeminiConfig):
        GEMINI_API_KEY = ""

    create_client = Mock()
    monkeypatch.setattr(genai, "Client", create_client)

    result = LLMClient(MissingKeyConfig()).generate("Explain photosynthesis.")

    assert not result.success
    assert "GEMINI_API_KEY" in result.error
    create_client.assert_not_called()
