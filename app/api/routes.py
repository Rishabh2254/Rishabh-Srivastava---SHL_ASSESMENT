"""API route handlers."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_agent
from app.models.schemas import ChatRequest, ChatResponse, HealthResponse
from app.services.agent import AssessmentAgent

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: AssessmentAgent = Depends(get_agent),
) -> ChatResponse:
    return await agent.handle(request.messages)
