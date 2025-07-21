"""LLM provider adapters for RAGAS compatibility."""

import asyncio
from typing import Any

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM

from src.config import get_logger
from src.question.providers import BaseLLMProvider

logger = get_logger("ragas_adapter")


class RAGASLLMAdapter(LLM):
    """Adapter to make our LLM providers compatible with RAGAS/LangChain."""

    def __init__(self, provider: BaseLLMProvider):
        super().__init__()
        self.provider = provider

    def _call(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> str:
        """Sync wrapper for our async provider."""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            from src.question.providers import LLMMessage

            response = loop.run_until_complete(
                self.provider.generate_with_retry(
                    messages=[LLMMessage(role="user", content=prompt)]
                )
            )
            return str(response.content)
        except Exception as e:
            logger.error(f"LLM adapter call failed: {e}")
            raise
        finally:
            loop.close()

    @property
    def _llm_type(self) -> str:
        return f"ragatuit_{getattr(self.provider, 'provider_name', 'unknown')}"
