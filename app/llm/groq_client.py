"""Groq LLM client."""

from groq import AsyncGroq

from app.core.config import Settings
from app.llm.base import LLMClient


class GroqLLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required for groq provider")
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.llm_model or "llama-3.3-70b-versatile"

    async def generate(self, system: str, user: str, temperature: float = 0.2) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
