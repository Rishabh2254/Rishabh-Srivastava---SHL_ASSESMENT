"""OpenRouter LLM client."""

import httpx

from app.core.config import Settings
from app.llm.base import LLMClient


class OpenRouterLLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required for openrouter provider")
        self._api_key = settings.openrouter_api_key
        self._model = settings.llm_model or "meta-llama/llama-3.3-70b-instruct:free"

    async def generate(self, system: str, user: str, temperature: float = 0.2) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"] or ""
