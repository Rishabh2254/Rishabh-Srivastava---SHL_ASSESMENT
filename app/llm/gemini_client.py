"""Google Gemini LLM client."""

import google.generativeai as genai

from app.core.config import Settings
from app.llm.base import LLMClient


class GeminiLLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for gemini provider")
        genai.configure(api_key=settings.gemini_api_key)
        model_name = settings.llm_model or "gemini-2.0-flash"
        self._model = genai.GenerativeModel(model_name)

    async def generate(self, system: str, user: str, temperature: float = 0.2) -> str:
        prompt = f"{system}\n\n{user}"
        response = await self._model.generate_content_async(
            prompt,
            generation_config={"temperature": temperature},
        )
        return response.text or ""
