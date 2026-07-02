"""LLM client factory."""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.llm.base import LLMClient
from app.llm.gemini_client import GeminiLLMClient
from app.llm.groq_client import GroqLLMClient
from app.llm.mock_client import MockLLMClient
from app.llm.openrouter_client import OpenRouterLLMClient

logger = get_logger(__name__)


@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    try:
        if provider == "groq":
            return GroqLLMClient(settings)
        if provider == "gemini":
            return GeminiLLMClient(settings)
        if provider == "openrouter":
            return OpenRouterLLMClient(settings)
        if provider == "mock":
            logger.warning("Using mock LLM provider")
            return MockLLMClient()
    except ValueError as exc:
        logger.warning("LLM provider init failed (%s); falling back to mock", exc)
        return MockLLMClient()
    logger.warning("Unknown LLM provider '%s'; using mock", provider)
    return MockLLMClient()
