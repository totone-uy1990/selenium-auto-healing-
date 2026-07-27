"""RED (task 2.5): LLM client provider selection.

GitHub Models is the default (GITHUB_TOKEN, models: read); setting
ANTHROPIC_API_KEY swaps the provider. No real network calls here: tests only
assert provider selection and request construction.
"""

import pytest

import heal_locator


def test_github_models_is_the_default():
    client = heal_locator.get_llm_client(env={"GITHUB_TOKEN": "ghp_test"})
    assert isinstance(client, heal_locator.GitHubModelsClient)
    assert client.endpoint == "https://models.github.ai/inference/chat/completions"
    assert client.model == "openai/gpt-4o-mini"


def test_anthropic_swaps_provider_when_key_is_set():
    env = {"GITHUB_TOKEN": "ghp_test", "ANTHROPIC_API_KEY": "sk-ant-test"}
    client = heal_locator.get_llm_client(env=env)
    assert isinstance(client, heal_locator.AnthropicClient)
    assert client.endpoint == "https://api.anthropic.com/v1/messages"


def test_missing_token_raises():
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        heal_locator.get_llm_client(env={})


def test_github_models_builds_openai_compatible_payload():
    client = heal_locator.get_llm_client(env={"GITHUB_TOKEN": "ghp_test"})
    body, headers = client.build_request("fix this locator")
    assert body["model"] == "openai/gpt-4o-mini"
    assert body["messages"][0]["content"] == "fix this locator"
    assert headers["Authorization"] == "Bearer ghp_test"


def test_anthropic_builds_messages_api_payload():
    client = heal_locator.get_llm_client(env={"ANTHROPIC_API_KEY": "sk-ant-test"})
    body, headers = client.build_request("fix this locator")
    assert body["messages"] == [{"role": "user", "content": "fix this locator"}]
    assert headers["x-api-key"] == "sk-ant-test"
    assert "anthropic-version" in headers
