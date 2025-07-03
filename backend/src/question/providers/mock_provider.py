"""Mock LLM provider for testing purposes."""

import asyncio
import json
import time
from typing import Any

from src.logging_config import get_logger

from .base import (
    BaseLLMProvider,
    LLMConfiguration,
    LLMMessage,
    LLMModel,
    LLMProvider,
    LLMResponse,
)

logger = get_logger("mock_provider")


class MockProvider(BaseLLMProvider):
    """Mock LLM provider for testing and development."""

    def __init__(self, configuration: LLMConfiguration):
        super().__init__(configuration)

        # Mock model definitions
        self._models = [
            LLMModel(
                provider=LLMProvider.MOCK,
                model_id="mock-model",
                display_name="Mock Model",
                max_tokens=4096,
                supports_streaming=False,
                cost_per_1k_tokens=0.0,
                description="Mock model for testing",
            ),
            LLMModel(
                provider=LLMProvider.MOCK,
                model_id="mock-large",
                display_name="Mock Large Model",
                max_tokens=8192,
                supports_streaming=False,
                cost_per_1k_tokens=0.0,
                description="Large mock model for testing",
            ),
        ]

        # Mock responses for different question types
        self._mock_responses = {
            "multiple_choice": {
                "question_text": "What is the capital of France?",
                "option_a": "London",
                "option_b": "Berlin",
                "option_c": "Paris",
                "option_d": "Madrid",
                "correct_answer": "C",
            },
            "true_false": {
                "question_text": "The Earth is round.",
                "answer": "true",
                "explanation": "The Earth is approximately spherical in shape.",
            },
            "short_answer": {
                "question_text": "What is the primary function of the heart?",
                "answer": "To pump blood throughout the body",
                "explanation": "The heart is a muscular organ that pumps blood through the circulatory system.",
            },
        }

    @property
    def provider_name(self) -> LLMProvider:
        """Return the provider name."""
        return LLMProvider.MOCK

    async def initialize(self) -> None:
        """Initialize the mock provider (no-op)."""
        logger.info("mock_provider_initialized")

    async def generate(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        """
        Generate a mock response.

        Args:
            messages: List of messages for the conversation
            **kwargs: Additional generation parameters

        Returns:
            Mock LLM response
        """
        start_time = time.time()

        # Simulate API delay
        delay = self.configuration.provider_settings.get("mock_delay", 0.1)
        await asyncio.sleep(delay)

        # Determine question type from messages
        question_type = self._detect_question_type(messages)

        # Generate appropriate mock response
        if question_type in self._mock_responses:
            mock_data = self._mock_responses[question_type].copy()
        else:
            mock_data = self._mock_responses["multiple_choice"].copy()

        # Convert to JSON string as LLMs would return
        content = json.dumps(mock_data, indent=2)

        response_time = time.time() - start_time

        # Simulate token usage
        prompt_tokens = sum(len(msg.content.split()) for msg in messages)
        completion_tokens = len(content.split())
        total_tokens = prompt_tokens + completion_tokens

        logger.info(
            "mock_generation_completed",
            model=self.configuration.model,
            question_type=question_type,
            response_time=response_time,
            content_length=len(content),
        )

        return LLMResponse(
            content=content,
            model=self.configuration.model,
            provider=self.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            response_time=response_time,
            metadata={"mock_response": True, "question_type": question_type, **kwargs},
        )

    async def get_available_models(self) -> list[LLMModel]:
        """
        Get list of available mock models.

        Returns:
            List of mock models
        """
        return self._models.copy()

    def validate_configuration(self) -> None:
        """
        Validate the mock provider configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.configuration.provider != LLMProvider.MOCK:
            raise ValueError(f"Configuration provider must be {LLMProvider.MOCK}")

        # Validate model is supported
        available_model_ids = [model.model_id for model in self._models]
        if self.configuration.model not in available_model_ids:
            raise ValueError(
                f"Model {self.configuration.model} is not supported. "
                f"Available models: {', '.join(available_model_ids)}"
            )

    def _detect_question_type(self, messages: list[LLMMessage]) -> str:
        """
        Detect question type from messages.

        Args:
            messages: List of messages

        Returns:
            Detected question type
        """
        # Simple detection based on keywords in messages
        content = " ".join(msg.content.lower() for msg in messages)

        if "true" in content and "false" in content:
            return "true_false"
        elif "short answer" in content or "explain" in content:
            return "short_answer"
        else:
            return "multiple_choice"

    def set_mock_response(self, question_type: str, response: dict[str, Any]) -> None:
        """
        Set a custom mock response for a question type.

        Args:
            question_type: The question type
            response: The mock response data
        """
        self._mock_responses[question_type] = response.copy()

        logger.info(
            "mock_response_updated",
            question_type=question_type,
            response_keys=list(response.keys()),
        )

    def should_fail(self, failure_mode: str = "general") -> None:
        """
        Configure the mock provider to fail on next request.

        Args:
            failure_mode: Type of failure to simulate
        """
        # Store failure mode in provider settings
        self.configuration.provider_settings["mock_failure_mode"] = failure_mode

        logger.info("mock_provider_configured_to_fail", failure_mode=failure_mode)
