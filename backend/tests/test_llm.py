import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest
from httpx2 import AsyncClient, MockTransport, Response

from app import llm

CLAUDE_ADAPTIVE_MIN_TOKENS = 4096


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for setting in (
        "SCENTFOLIO_LLM_PROVIDER",
        "SCENTFOLIO_LLM_MODEL",
        "SCENTFOLIO_LLM_API_KEY",
        "SCENTFOLIO_LLM_BASE_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_CUSTOM_HEADERS",
        "OPENAI_API_KEY",
        "OPENAI_CUSTOM_HEADERS",
        "OPENAI_ORG_ID",
        "OPENAI_PROJECT_ID",
    ):
        monkeypatch.delenv(setting, raising=False)


@pytest.fixture
def model_http(monkeypatch):
    requests = []
    respond = Mock()

    def handle(request):
        requests.append(request)
        return respond(request)

    def client(**options):
        return AsyncClient(transport=MockTransport(handle), **options)

    monkeypatch.setattr(llm, "AsyncClient", client)
    return requests, respond


def _anthropic_response(*, model="claude-opus-5-5", citations=()):
    return Response(
        200,
        json={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": model,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "content": [
                {"type": "thinking", "thinking": "", "signature": "test"},
                {"type": "text", "text": "Model response", "citations": citations},
            ],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
    )


def _chat_response():
    return Response(
        200,
        json={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1,
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Model response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )


def _responses_response(*, annotations=()):
    return Response(
        200,
        json={
            "id": "resp_test",
            "object": "response",
            "created_at": 1,
            "status": "completed",
            "model": "gpt-5",
            "output": [
                {
                    "id": "msg_test",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"name":"Test","source_urls":["https://unverified.example"]}',
                            "annotations": annotations,
                        }
                    ],
                }
            ],
            "usage": {
                "input_tokens": 10,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": 5,
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": 15,
            },
        },
    )


def _openai_annotation(url):
    return {
        "type": "url_citation",
        "start_index": 0,
        "end_index": 4,
        "url": url,
        "title": "A source",
    }


def test_anthropic_default_uses_legacy_key_and_native_search(monkeypatch, model_http):
    requests, respond = model_http
    monkeypatch.setenv("ANTHROPIC_API_KEY", "legacy-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://ignored.example")
    monkeypatch.setenv("ANTHROPIC_CUSTOM_HEADERS", "X-Official-Header: retained")
    respond.side_effect = lambda _: _anthropic_response(
        citations=[
            {
                "type": "web_search_result_location",
                "url": "https://perfume.example/product",
                "title": "Perfume",
                "encrypted_index": "test",
                "cited_text": "Model response",
            }
        ]
    )

    assert llm.complete(
        "System", "User", max_tokens=50, task="lookup", search="Research the perfume."
    ) == ("Model response", ["https://perfume.example/product"])

    (call,) = requests
    assert str(call.url).startswith("https://api.anthropic.com/v1/messages")
    assert call.headers["authorization"] == "Bearer legacy-key"
    assert call.headers["x-official-header"] == "retained"
    body = json.loads(call.content)
    assert body["model"] == "claude-opus-5-5"
    assert body["max_tokens"] == CLAUDE_ADAPTIVE_MIN_TOKENS
    assert body["output_config"]["effort"] == "low"
    assert body["tools"][0]["type"].startswith("web_search_")
    assert "Research the perfume." in str(body)


def test_anthropic_gateway_uses_only_explicit_credentials(monkeypatch, model_http):
    requests, respond = model_http
    monkeypatch.setenv("SCENTFOLIO_LLM_BASE_URL", "https://proxy.example/anthropic")
    monkeypatch.setenv("SCENTFOLIO_LLM_API_KEY", "gateway-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ambient-key")
    monkeypatch.setenv(
        "ANTHROPIC_CUSTOM_HEADERS",
        "wrong line\n  aUthOriZAtion : Bearer ambient-override\n"
        "X-App-Secret: token:with:colons\n X-Api-Key: ambient-key",
    )
    respond.side_effect = lambda _: _anthropic_response()

    assert llm.complete(
        "System", "User", max_tokens=50, task="lookup", search="Research."
    ) == ("Model response", [])

    (call,) = requests
    assert str(call.url) == "https://proxy.example/anthropic/v1/messages"
    assert call.headers["Authorization"] == "Bearer gateway-key"
    assert "X-App-Secret" not in call.headers
    assert "X-Api-Key" not in call.headers
    assert call.headers["Anthropic-Version"]
    assert json.loads(call.content)["tools"]


def test_anthropic_enrichment_preserves_default_model_without_search(
    monkeypatch, model_http
):
    requests, respond = model_http
    monkeypatch.setenv("SCENTFOLIO_LLM_API_KEY", "configured-key")
    respond.side_effect = lambda _: _anthropic_response(model="claude-haiku-5-5")
    requested_tokens = 8000

    assert llm.complete(
        "System", "User", max_tokens=requested_tokens, task="enrich", search="Research."
    ) == (
        "Model response",
        [],
    )
    (call,) = requests
    assert call.headers["authorization"] == "Bearer configured-key"
    body = json.loads(call.content)
    assert body["model"] == "claude-haiku-5-5"
    assert body["max_tokens"] == requested_tokens
    assert body["output_config"]["effort"] == "low"
    assert not body.get("tools")


def test_anthropic_model_override_keeps_requested_budget(monkeypatch, model_http):
    requests, respond = model_http
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("SCENTFOLIO_LLM_MODEL", "claude-opus-4-8")
    respond.side_effect = lambda _: _anthropic_response(model="claude-opus-4-8")
    requested_tokens = 1500

    assert llm.complete(
        "System", "User", max_tokens=requested_tokens, task="lookup"
    ) == (
        "Model response",
        [],
    )

    (call,) = requests
    body = json.loads(call.content)
    assert body["model"] == "claude-opus-4-8"
    assert body["max_tokens"] == requested_tokens
    assert not body.get("output_config", {}).get("effort")


def test_native_openai_lookup_uses_responses_and_common_citations(
    monkeypatch, model_http
):
    requests, respond = model_http
    monkeypatch.setenv("SCENTFOLIO_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SCENTFOLIO_LLM_MODEL", "gpt-5")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    respond.side_effect = lambda _: _responses_response(
        annotations=[
            _openai_annotation("https://brand.example/product"),
            _openai_annotation("https://brand.example/product"),
            _openai_annotation("javascript:alert(1)"),
            _openai_annotation("https://user:hidden@private.example/product"),
            _openai_annotation("//relative.example"),
            _openai_annotation("http://review.example/product"),
        ]
    )

    requested_tokens = 50
    text, sources = llm.complete(
        "System",
        "User",
        max_tokens=requested_tokens,
        task="lookup",
        search="Research the perfume.",
    )

    assert "https://unverified.example" in text
    assert sources == ["https://brand.example/product", "http://review.example/product"]
    (call,) = requests
    assert str(call.url) == "https://api.openai.com/v1/responses"
    assert call.headers["authorization"] == "Bearer openai-key"
    body = json.loads(call.content)
    assert body["model"] == "gpt-5"
    assert body["max_output_tokens"] == requested_tokens
    assert body["store"] is False
    assert body["tools"][0]["type"] == "web_search"
    assert "Research the perfume." in str(body)


@pytest.mark.parametrize("task", ["classify", "enrich"])
def test_native_openai_keeps_search_out_of_other_tasks(monkeypatch, model_http, task):
    requests, respond = model_http
    monkeypatch.setenv("SCENTFOLIO_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SCENTFOLIO_LLM_MODEL", "gpt-5")
    monkeypatch.setenv("SCENTFOLIO_LLM_API_KEY", "explicit-key")
    monkeypatch.setenv("SCENTFOLIO_LLM_BASE_URL", "https://proxy.example/v1/")
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-forward")
    monkeypatch.setenv("OPENAI_ORG_ID", "ambient-org")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "ambient-project")
    monkeypatch.setenv("OPENAI_CUSTOM_HEADERS", "X-App-Secret: ambient-value")
    respond.side_effect = lambda _: _responses_response(
        annotations=[_openai_annotation("https://not-used.example/product")]
    )

    assert (
        llm.complete(
            "System", "User", max_tokens=50, task=task, search="Research the perfume."
        )[1]
        == []
    )

    (call,) = requests
    assert str(call.url) == "https://proxy.example/v1/responses"
    assert call.headers["authorization"] == "Bearer explicit-key"
    assert "OpenAI-Organization" not in call.headers
    assert "OpenAI-Project" not in call.headers
    assert "X-App-Secret" not in call.headers
    body = json.loads(call.content)
    assert body["store"] is False
    assert not body.get("tools")
    assert "Research the perfume." not in str(body)


@pytest.mark.parametrize("key", [None, "custom-key"])
def test_compatible_mode_keeps_vendor_fallback_keys_local(monkeypatch, model_http, key):
    requests, respond = model_http
    monkeypatch.setenv("SCENTFOLIO_LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("SCENTFOLIO_LLM_MODEL", "test-model")
    monkeypatch.setenv("SCENTFOLIO_LLM_BASE_URL", "http://localhost:11434/v1/")
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-forward")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "do-not-forward-either")
    monkeypatch.setenv("OPENAI_ORG_ID", "ambient-org")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "ambient-project")
    if key:
        monkeypatch.setenv("SCENTFOLIO_LLM_API_KEY", key)
    respond.side_effect = lambda _: _chat_response()
    requested_tokens = 50

    assert llm.complete(
        "System",
        "User",
        max_tokens=requested_tokens,
        task="lookup",
        search="Research the perfume.",
    ) == ("Model response", [])

    (call,) = requests
    assert str(call.url) == "http://localhost:11434/v1/chat/completions"
    assert call.headers.get("authorization") == (f"Bearer {key}" if key else None)
    assert "OpenAI-Organization" not in call.headers
    assert "OpenAI-Project" not in call.headers
    body = json.loads(call.content)
    assert body["max_tokens"] == requested_tokens
    assert not body.get("tools")
    assert "Omit unknown details" in str(body)
    assert "Research the perfume." not in str(body)


def test_official_openai_chat_uses_canonical_key_and_token_limit(
    monkeypatch, model_http
):
    requests, respond = model_http
    monkeypatch.setenv("SCENTFOLIO_LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("SCENTFOLIO_LLM_MODEL", "gpt-5")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_ORG_ID", "own-organization")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "own-project")
    respond.side_effect = lambda _: _chat_response()
    requested_tokens = 50

    assert llm.complete(
        "System", "User", max_tokens=requested_tokens, task="enrich"
    ) == (
        "Model response",
        [],
    )
    (call,) = requests
    assert str(call.url) == "https://api.openai.com/v1/chat/completions"
    assert call.headers["authorization"] == "Bearer openai-key"
    assert call.headers["OpenAI-Organization"] == "own-organization"
    assert call.headers["OpenAI-Project"] == "own-project"
    assert json.loads(call.content)["max_completion_tokens"] == requested_tokens


def test_classification_concurrent_operations_use_separate_clients(
    monkeypatch, model_http
):
    requests, respond = model_http
    monkeypatch.setenv("ANTHROPIC_API_KEY", "legacy-key")
    respond.side_effect = lambda _: _anthropic_response()

    def classify(name):
        return llm.complete(
            "System", name, max_tokens=50, task="classify", search="Research."
        )

    perfumes = ("A", "B", "C", "D")
    with ThreadPoolExecutor(max_workers=len(perfumes)) as workers:
        results = list(workers.map(classify, perfumes))
    assert results == [("Model response", [])] * len(perfumes)
    assert len(requests) == len(perfumes)
    for call in requests:
        body = json.loads(call.content)
        assert body["tools"]
        assert body["model"] == "claude-opus-5-5"
        assert body["max_tokens"] == CLAUDE_ADAPTIVE_MIN_TOKENS


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({}, "ANTHROPIC_API_KEY"),
        ({"SCENTFOLIO_LLM_PROVIDER": "unsupported"}, "SCENTFOLIO_LLM_PROVIDER"),
        (
            {"SCENTFOLIO_LLM_PROVIDER": "openai", "OPENAI_API_KEY": "key"},
            "SCENTFOLIO_LLM_MODEL",
        ),
        (
            {
                "SCENTFOLIO_LLM_PROVIDER": "openai",
                "SCENTFOLIO_LLM_MODEL": "gpt-5",
                "SCENTFOLIO_LLM_BASE_URL": "https://private.example/v1",
                "OPENAI_API_KEY": "do-not-forward",
            },
            "SCENTFOLIO_LLM_API_KEY",
        ),
        (
            {"SCENTFOLIO_LLM_BASE_URL": "https://private.example/?secret=hidden"},
            "SCENTFOLIO_LLM_BASE_URL",
        ),
    ],
)
def test_configuration_errors_prevent_requests(
    monkeypatch, model_http, settings, message
):
    requests, _ = model_http
    for name, value in settings.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(llm.LookupError, match=message) as exc:
        llm.complete("System", "User", max_tokens=50, task="lookup")
    assert "hidden" not in str(exc.value)
    assert "private.example" not in str(exc.value)
    assert requests == []


def test_provider_failure_does_not_expose_body_or_credentials(monkeypatch, model_http):
    _, respond = model_http
    monkeypatch.setenv("SCENTFOLIO_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SCENTFOLIO_LLM_MODEL", "gpt-5")
    monkeypatch.setenv("SCENTFOLIO_LLM_API_KEY", "confidential")
    respond.side_effect = lambda _: Response(
        401,
        json={"error": {"message": "confidential", "type": "invalid_request_error"}},
    )

    with pytest.raises(llm.LookupError, match="HTTP 401") as exc:
        llm.complete("System", "User", max_tokens=50, task="enrich")
    assert "confidential" not in str(exc.value)
