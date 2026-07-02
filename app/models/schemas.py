"""Pydantic request/response schemas for the public API."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)

    @field_validator("messages")
    @classmethod
    def must_have_user_message(cls, messages: list[ChatMessage]) -> list[ChatMessage]:
        if not any(m.role == "user" for m in messages):
            raise ValueError("At least one user message is required")
        return messages


class RecommendationItem(BaseModel):
    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    reply: str
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    end_of_conversation: bool = False


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
