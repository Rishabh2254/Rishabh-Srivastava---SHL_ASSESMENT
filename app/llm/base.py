"""LLM provider abstraction."""

from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, system: str, user: str, temperature: float = 0.2) -> str:
        raise NotImplementedError

    async def generate_json(self, system: str, user: str) -> dict[str, Any]:
        import json
        import re

        raw = await self.generate(system, user, temperature=0.1)
        raw = raw.strip()
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fence:
            raw = fence.group(1)
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]
        return json.loads(raw)
