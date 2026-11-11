import json

import httpx
import pytest
from pydantic import SecretStr

from apps.api.multimodal import AzureProvider, AzureSettings, FixtureProvider
from packages.domain.design import DomainError


def test_fixture_is_repeatable_and_free():
    provider = FixtureProvider()
    result = provider.run("image", "a")
    assert result == provider.run("image", "b")
    assert result.thumbnail_jpeg and result.estimated_cost == 0


def test_azure_requires_opt_in_and_distinct_deployments():
    provider = AzureProvider(AzureSettings(enabled=True, chat_deployment="chat"))
    with pytest.raises(DomainError, match="azure_capability_disabled"):
        provider.run("image", "synthetic")
    with pytest.raises(DomainError, match="invalid_azure_endpoint"):
        provider.run("chat", "synthetic")


def test_azure_vision_image_and_embedding_use_their_configured_deployments():
    jpeg = FixtureProvider().run("image", "fixture").thumbnail_jpeg
    assert jpeg is not None

    def upstream(request):
        assert request.headers["authorization"] == "Bearer synthetic"
        assert "api-key" not in request.headers
        body = json.loads(request.content)
        if request.url.path.endswith("images/generations"):
            assert request.url.params["api-version"] == "preview"
            assert body["model"] == "image-deployment" and body["n"] == 1
            result = {"data": [{"b64_json": jpeg}]}
        elif request.url.path.endswith("embeddings"):
            assert body["model"] == "embedding-deployment"
            result = {"data": [{"embedding": [0.5, 0.25]}]}
        else:
            assert body["model"] == "vision-deployment"
            image_url = body["messages"][1]["content"][1]["image_url"]["url"]
            assert image_url.startswith("data:image/jpeg;base64,")
            result = {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"summary":"Synthetic thumbnail"}'},
                    }
                ]
            }
        return httpx.Response(200, stream=httpx.ByteStream(json.dumps(result).encode()))

    provider = AzureProvider(
        AzureSettings(
            enabled=True,
            endpoint="https://test.openai.azure.com",
            entra_token=SecretStr("synthetic"),
            vision_deployment="vision-deployment",
            image_deployment="image-deployment",
            embedding_deployment="embedding-deployment",
        ),
        httpx.MockTransport(upstream),
    )
    assert provider.run("image", "synthetic").thumbnail_jpeg
    assert provider.run("embedding", "synthetic").vector == [0.5, 0.25]
    assert provider.run("vision", "synthetic", jpeg).analysis.summary == "Synthetic thumbnail"


@pytest.mark.parametrize(
    ("status", "reply", "error"),
    [
        (
            200,
            {
                "choices": [
                    {"finish_reason": "stop", "message": {"content": '{"summary":"Sketch"}'}}
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            },
            None,
        ),
        (
            200,
            {"choices": [{"finish_reason": "stop", "message": {"content": '{"tool":"write"}'}}]},
            "invalid_azure_output",
        ),
        (200, {"choices": [{"finish_reason": "content_filter"}]}, "azure_content_filtered"),
        (429, {"secret": "untrusted provider text"}, "azure_rate_limited"),
    ],
)
def test_azure_response_validation_and_failure_taxonomy(status, reply, error):
    def upstream(request):
        assert request.url.path == "/openai/v1/chat/completions"
        assert request.headers["api-key"] == "synthetic"
        payload = json.loads(request.content)
        assert payload["model"] == "chat-deployment"
        assert payload["max_completion_tokens"] == 256
        assert "tools" not in payload
        return httpx.Response(
            status,
            stream=httpx.ByteStream(json.dumps(reply).encode()),
            headers={"x-request-id": "test-request"},
        )

    provider = AzureProvider(
        AzureSettings(
            enabled=True,
            endpoint="https://test.openai.azure.com",
            api_key=SecretStr("synthetic"),
            chat_deployment="chat-deployment",
        ),
        httpx.MockTransport(upstream),
    )
    if error:
        with pytest.raises(DomainError, match=error):
            provider.run("chat", "synthetic")
    else:
        result = provider.run("chat", "synthetic")
        assert result.analysis.summary == "Sketch"
        assert result.request_id == "test-request"
        assert result.input_tokens == 5
        assert result.estimated_cost is None
