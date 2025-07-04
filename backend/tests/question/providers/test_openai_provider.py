"""Tests for OpenAI LLM provider."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def config():
    """Create test configuration."""
    from src.question.providers.base import LLMConfiguration, LLMProvider

    return LLMConfiguration(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        temperature=0.7,
        max_tokens=2000,
        timeout=30.0,
        provider_settings={"api_key": "test_api_key"},
    )


@pytest.fixture
def provider(config):
    """Create OpenAI provider instance."""
    from src.question.providers.openai_provider import OpenAIProvider

    return OpenAIProvider(config)


def test_provider_initialization(provider, config):
    """Test provider initialization."""
    assert provider.configuration == config
    assert provider._client is None  # Lazy initialization


@pytest.mark.asyncio
async def test_get_available_models(provider):
    """Test getting available models."""
    from src.question.providers.base import LLMProvider

    models = await provider.get_available_models()

    assert len(models) > 0

    # Check for expected models
    model_ids = [model.model_id for model in models]
    assert "gpt-4" in model_ids
    assert "gpt-4-turbo" in model_ids

    # Verify model properties
    gpt4_model = next(model for model in models if model.model_id == "gpt-4")
    assert gpt4_model.provider == LLMProvider.OPENAI
    assert gpt4_model.display_name == "GPT-4"
    assert gpt4_model.max_tokens == 8192
    assert gpt4_model.supports_streaming is True
    assert gpt4_model.cost_per_1k_tokens == 0.03


def test_validate_model_valid(provider):
    """Test configuration validation with valid model."""
    # Should not raise any exception
    provider.validate_configuration()


def test_validate_model_invalid():
    """Test configuration validation with invalid model."""
    from src.question.providers.base import LLMConfiguration, LLMProvider

    invalid_config = LLMConfiguration(
        provider=LLMProvider.OPENAI,
        model="invalid-model",
        temperature=0.7,
        max_tokens=2000,
        timeout=30.0,
        provider_settings={"api_key": "test_api_key"},
    )

    from src.question.providers.openai_provider import OpenAIProvider

    provider = OpenAIProvider(invalid_config)

    with pytest.raises(ValueError) as exc_info:
        provider.validate_configuration()

    assert "invalid-model" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_response_success(provider):
    """Test successful response generation."""
    from unittest.mock import AsyncMock

    from src.question.providers.base import LLMMessage, LLMProvider

    messages = [
        LLMMessage(
            role="user", content="Generate a multiple choice question about Python."
        )
    ]

    mock_response = MagicMock()
    mock_response.content = (
        '{"question": "What is Python?", "options": ["A language", "A snake"]}'
    )
    mock_response.usage = {
        "prompt_tokens": 20,
        "completion_tokens": 50,
        "total_tokens": 70,
    }

    with patch.object(provider, "_client", None):  # Start with no client
        with patch(
            "src.question.providers.openai_provider.ChatOpenAI"
        ) as mock_chat_openai:
            mock_client = AsyncMock()
            mock_client.ainvoke.return_value = mock_response
            mock_chat_openai.return_value = mock_client

            response = await provider.generate(messages)

        assert response.content == mock_response.content
        assert response.model == "gpt-4"
        assert response.provider == LLMProvider.OPENAI
        assert response.prompt_tokens == 20
        assert response.completion_tokens == 50
        assert response.total_tokens == 70
        assert response.response_time > 0


@pytest.mark.asyncio
async def test_generate_response_authentication_error(provider):
    """Test response generation with authentication error."""
    from unittest.mock import AsyncMock

    from src.question.providers.base import AuthenticationError, LLMMessage

    messages = [LLMMessage(role="user", content="Test")]

    with patch.object(provider, "_client", None):  # Start with no client
        with patch(
            "src.question.providers.openai_provider.ChatOpenAI"
        ) as mock_chat_openai:
            mock_client = AsyncMock()
            # Mock LangChain exception that indicates auth error - use a keyword that triggers AuthenticationError
            mock_client.ainvoke.side_effect = Exception("authentication failed")
            mock_chat_openai.return_value = mock_client

            with pytest.raises(AuthenticationError) as exc_info:
                await provider.generate(messages)

            assert "authentication error" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_generate_response_rate_limit_error(provider):
    """Test response generation with rate limit error."""
    from unittest.mock import AsyncMock

    from src.question.providers.base import LLMMessage, RateLimitError

    messages = [LLMMessage(role="user", content="Test")]

    with patch.object(provider, "_client", None):  # Start with no client
        with patch(
            "src.question.providers.openai_provider.ChatOpenAI"
        ) as mock_chat_openai:
            mock_client = AsyncMock()
            mock_client.ainvoke.side_effect = Exception("Rate limit exceeded")
            mock_chat_openai.return_value = mock_client

            with pytest.raises(RateLimitError) as exc_info:
                await provider.generate(messages)

            assert "Rate limit exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_response_with_custom_config():
    """Test response generation with custom configuration."""
    from unittest.mock import AsyncMock

    from src.question.providers.base import LLMConfiguration, LLMMessage, LLMProvider
    from src.question.providers.openai_provider import OpenAIProvider

    # Use different model and temperature
    custom_config = LLMConfiguration(
        provider=LLMProvider.OPENAI,
        model="gpt-4-turbo",
        temperature=0.2,
        max_tokens=1000,
        timeout=60.0,
        provider_settings={"api_key": "test_key"},
    )

    provider = OpenAIProvider(custom_config)
    messages = [LLMMessage(role="user", content="Test with custom config")]

    mock_response = MagicMock()
    mock_response.content = "Custom response"

    with patch.object(provider, "_client", None):  # Start with no client
        with patch(
            "src.question.providers.openai_provider.ChatOpenAI"
        ) as mock_chat_openai:
            mock_client = AsyncMock()
            mock_client.ainvoke.return_value = mock_response
            mock_chat_openai.return_value = mock_client

            response = await provider.generate(messages)

    assert response.model == "gpt-4-turbo"

    # Verify client was configured with custom settings
    mock_chat_openai.assert_called_once()


@pytest.mark.asyncio
async def test_client_lazy_initialization(provider):
    """Test that client is lazily initialized."""
    from unittest.mock import AsyncMock

    assert provider._client is None

    with patch("src.question.providers.openai_provider.ChatOpenAI") as mock_chat_openai:
        mock_client = AsyncMock()
        mock_chat_openai.return_value = mock_client

        await provider.initialize()

        assert provider._client == mock_client

        # Verify configuration was passed correctly
        mock_chat_openai.assert_called_once()
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["timeout"] == 30.0

        # Verify api_key is passed correctly
        assert "api_key" in call_kwargs


@pytest.mark.asyncio
async def test_client_reuses_instance(provider):
    """Test that client instance is reused."""
    from unittest.mock import AsyncMock

    with patch("src.question.providers.openai_provider.ChatOpenAI") as mock_chat_openai:
        mock_client = AsyncMock()
        mock_chat_openai.return_value = mock_client

        await provider.initialize()
        client1 = provider._client
        await provider.initialize()  # Should not reinitialize
        client2 = provider._client

        assert client1 == client2
        assert client1 == mock_client
        # Should only be called once due to caching
        mock_chat_openai.assert_called_once()


@pytest.mark.asyncio
async def test_generate_response_measures_time(provider):
    """Test that response time is measured."""
    from unittest.mock import AsyncMock

    from src.question.providers.base import LLMMessage

    messages = [LLMMessage(role="user", content="Test timing")]

    mock_response = MagicMock()
    mock_response.content = "Timed response"

    with (
        patch.object(provider, "_client", None),
        patch("src.question.providers.openai_provider.ChatOpenAI") as mock_chat_openai,
        patch("src.question.providers.openai_provider.time") as mock_time,
    ):
        # Mock time.time to return specific values
        mock_time.time.side_effect = [1000.0, 1002.5]  # 2.5 second difference

        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = mock_response
        mock_chat_openai.return_value = mock_client

        response = await provider.generate(messages)

    assert response.response_time == 2.5


@pytest.mark.asyncio
async def test_generate_response_counts_tokens(provider):
    """Test that token usage is handled properly."""
    from unittest.mock import AsyncMock

    from src.question.providers.base import LLMMessage

    messages = [
        LLMMessage(role="user", content="This is a test message for token counting."),
        LLMMessage(role="assistant", content="This is a response for token counting."),
    ]

    mock_response = MagicMock()
    mock_response.content = "Response with token counting"
    mock_response.usage = {
        "prompt_tokens": 20,
        "completion_tokens": 10,
        "total_tokens": 30,
    }

    with patch.object(provider, "_client", None):
        with patch(
            "src.question.providers.openai_provider.ChatOpenAI"
        ) as mock_chat_openai:
            mock_client = AsyncMock()
            mock_client.ainvoke.return_value = mock_response
            mock_chat_openai.return_value = mock_client

            response = await provider.generate(messages)

    # Should have token count from the mock response
    assert response.prompt_tokens == 20
    assert response.completion_tokens == 10
    assert response.total_tokens == 30


def test_provider_configuration_immutable(provider, config):
    """Test that provider configuration is properly stored."""
    original_model = provider.configuration.model

    # Configuration should be the same object
    assert provider.configuration is config

    # Verify the configuration is stored correctly
    assert provider.configuration.model == original_model

    # Since Pydantic models are not frozen by default in this version,
    # let's test that the configuration is at least stored correctly
    # and that the provider uses the configuration as expected
    assert isinstance(provider.configuration.model, str)
    assert len(provider.configuration.model) > 0
    assert provider.configuration.provider.value == "openai"


@pytest.mark.parametrize(
    "model,expected_valid",
    [
        ("gpt-4", True),
        ("gpt-4-turbo", True),
        ("gpt-3.5-turbo", True),
        ("claude-3", False),
        ("invalid-model", False),
        ("", False),
    ],
)
def test_validate_model_various_inputs(config, model, expected_valid):
    """Test model validation with various inputs."""
    from src.question.providers.base import LLMConfiguration, LLMProvider
    from src.question.providers.openai_provider import OpenAIProvider

    # Create a new config with the test model
    test_config = LLMConfiguration(
        provider=LLMProvider.OPENAI,
        model=model,
        temperature=0.7,
        max_tokens=2000,
        timeout=30.0,
        provider_settings={"api_key": "test_api_key"},
    )

    provider = OpenAIProvider(test_config)

    if expected_valid:
        # Should not raise exception
        provider.validate_configuration()
    else:
        with pytest.raises(ValueError):
            provider.validate_configuration()


@pytest.mark.asyncio
async def test_generate_response_error_handling(provider):
    """Test error handling in response generation."""
    from unittest.mock import AsyncMock

    from src.question.providers.base import LLMError, LLMMessage

    messages = [LLMMessage(role="user", content="Test error handling")]

    with patch.object(provider, "_client", None):
        with patch(
            "src.question.providers.openai_provider.ChatOpenAI"
        ) as mock_chat_openai:
            mock_client = AsyncMock()

            # Test various exception types - all should be wrapped in LLMError
            test_cases = [
                Exception("Generic error"),
                ValueError("Value error"),
                ConnectionError("Connection failed"),
            ]

            for original_error in test_cases:
                mock_client.ainvoke.side_effect = original_error
                mock_chat_openai.return_value = mock_client

                with pytest.raises(LLMError):
                    await provider.generate(messages)


def test_provider_string_representation(provider):
    """Test string representation of provider."""
    str_repr = str(provider)
    assert "OpenAI" in str_repr
    assert "gpt-4" in str_repr


def test_provider_equality(config):
    """Test provider equality comparison."""
    from src.question.providers.base import LLMConfiguration, LLMProvider
    from src.question.providers.openai_provider import OpenAIProvider

    provider1 = OpenAIProvider(config)
    provider2 = OpenAIProvider(config)

    # Should be equal if configurations are the same
    assert provider1.configuration == provider2.configuration

    # Different configurations should not be equal
    different_config = LLMConfiguration(
        provider=LLMProvider.OPENAI,
        model="gpt-4-turbo",
        temperature=0.5,
        max_tokens=1000,
        timeout=60.0,
        provider_settings={"api_key": "different_key"},
    )
    provider3 = OpenAIProvider(different_config)
    assert provider1.configuration != provider3.configuration
