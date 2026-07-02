"""Deterministic mock LLM for tests and offline development."""

import json
import re

from app.llm.base import LLMClient


class MockLLMClient(LLMClient):
    async def generate(self, system: str, user: str, temperature: float = 0.2) -> str:
        text = user.lower()
        if "recommendation_names" in user or "valid json" in user.lower():
            if any(k in text for k in ["java", "developer", "software engineer", "programming"]):
                payload = {
                    "reply": (
                        "Based on your requirements, I recommend these SHL assessments "
                        "for evaluating Java development skills and related competencies."
                    ),
                    "recommendation_names": [],
                    "end_of_conversation": False,
                }
            elif "personality" in text:
                payload = {
                    "reply": "I have updated recommendations to include personality assessments.",
                    "recommendation_names": [],
                    "end_of_conversation": False,
                }
            else:
                payload = {
                    "reply": "Could you share the role and key skills you need to assess?",
                    "recommendation_names": [],
                    "end_of_conversation": False,
                }
            return json.dumps(payload)
        return "Acknowledged."

    async def generate_json(self, system: str, user: str) -> dict:
        raw = await self.generate(system, user)
        return json.loads(raw)
