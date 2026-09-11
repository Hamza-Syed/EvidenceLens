import json

import httpx2
import pytest

from app.config import Settings
from app.errors import VerifierOutputError, VerifierUnavailableError
from app.verifier_provider import ChatCompletionProvider, generation_schema


def provider(handler):
    return ChatCompletionProvider(Settings(verifier_api_key="test-key"), transport=httpx2.MockTransport(handler))


def test_transport_sends_only_separated_messages_and_schema():
    def handler(request):
        body = json.loads(request.content)
        assert body["messages"] == [{"role": "system", "content": "instructions"}, {"role": "user", "content": "data"}]
        assert body["response_format"]["type"] == "json_schema"
        assert body["temperature"] == 0
        assert "tools" not in body and "logprobs" not in body
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx2.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]})

    assert provider(handler).complete(system="instructions", data="data", schema={"type": "object"}) == "{}"


@pytest.mark.parametrize("status", [401, 429, 500, 503, 302])
def test_http_failures_are_safe(status):
    with pytest.raises(VerifierUnavailableError):
        provider(lambda _: httpx2.Response(status, text="secret provider detail")).complete(system="x", data="y", schema={})


def test_timeout_is_safe():
    def handler(request):
        raise httpx2.ReadTimeout("sensitive detail", request=request)

    with pytest.raises(VerifierUnavailableError):
        provider(handler).complete(system="x", data="y", schema={})


@pytest.mark.parametrize("response", [
    {}, {"choices": []}, {"choices": [None]}, {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
    {"choices": [{"finish_reason": "stop", "message": {"content": None}}]},
])
def test_bad_envelopes(response):
    with pytest.raises(VerifierOutputError):
        provider(lambda _: httpx2.Response(200, json=response)).complete(system="x", data="y", schema={})


def test_response_size_is_bounded():
    with pytest.raises(VerifierOutputError):
        provider(lambda _: httpx2.Response(200, text="x" * 100001)).complete(system="x", data="y", schema={})


def test_generation_schema_preserves_structure_without_expanding_bounds():
    schema = {"type": "array", "maxItems": 50, "items": {"type": "string", "maxLength": 2000, "enum": ["E1"]}}
    assert generation_schema(schema) == {"type": "array", "items": {"type": "string", "enum": ["E1"]}}
    assert schema["maxItems"] == 50
