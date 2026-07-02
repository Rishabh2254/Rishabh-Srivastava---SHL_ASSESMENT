"""Conversational agent orchestrating retrieval, prompting, and validation."""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.llm.base import LLMClient
from app.models.conversation import ConversationState, Intent
from app.models.schemas import ChatMessage, ChatResponse, RecommendationItem
from app.prompts.templates import (
    CONVERSATION_PROMPT_TEMPLATE,
    FORMAT_INSTRUCTION,
    INJECTION_REPLY,
    REFUSAL_REPLY,
    RETRIEVAL_CONTEXT_TEMPLATE,
    SYSTEM_PROMPT,
)
from app.retrieval.retriever import AssessmentRetriever
from app.retrieval.types import RetrievalResult
from app.services.state_manager import StateManager
from app.utils.text import truncate
from app.utils.validation import CatalogRegistry

logger = get_logger(__name__)


class AssessmentAgent:
    def __init__(
        self,
        settings: Settings,
        retriever: AssessmentRetriever,
        llm: LLMClient,
        registry: CatalogRegistry,
    ) -> None:
        self.settings = settings
        self.retriever = retriever
        self.llm = llm
        self.registry = registry
        self.state_manager = StateManager(max_turns=settings.max_conversation_turns)

    async def handle(self, messages: list[ChatMessage]) -> ChatResponse:
        state = self.state_manager.infer(messages)
        logger.info("Inferred intent=%s turns=%s", state.intent, state.turn_count)

        if state.turn_count > self.settings.max_conversation_turns:
            return ChatResponse(
                reply=(
                    "We have reached the maximum number of conversation turns. "
                    "Here is my final recommendation based on the information provided."
                ),
                recommendations=[],
                end_of_conversation=True,
            )

        if state.injection_detected:
            return ChatResponse(reply=INJECTION_REPLY, recommendations=[], end_of_conversation=False)

        if state.off_topic:
            return ChatResponse(reply=REFUSAL_REPLY, recommendations=[], end_of_conversation=False)

        if state.intent == Intent.CLARIFY:
            question = self.state_manager.next_clarification_question(state)
            return ChatResponse(reply=question, recommendations=[], end_of_conversation=False)

        if state.intent == Intent.COMPARE:
            return await self._handle_comparison(messages, state)

        query = self._build_query(messages, state)
        results = self.retriever.retrieve(
            query,
            slots=state.slots,
            wants_personality=state.wants_personality or bool(state.slots.personality),
        )
        if not results:
            return ChatResponse(
                reply=(
                    "I could not find sufficiently relevant SHL catalog entries for your request. "
                    "Could you clarify the role, skills, and seniority level?"
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        if state.intent in {Intent.RECOMMEND, Intent.REFINE}:
            return await self._handle_recommendation(messages, state, results)

        question = self.state_manager.next_clarification_question(state)
        return ChatResponse(reply=question, recommendations=[], end_of_conversation=False)

    async def _handle_recommendation(
        self,
        messages: list[ChatMessage],
        state: ConversationState,
        results: list[RetrievalResult],
    ) -> ChatResponse:
        context = self.retriever.format_context(results)
        history = self._format_history(messages)
        action = (
            "Recommend 1-10 SHL assessments from the retrieved context. "
            "Explain briefly why each is relevant."
        )
        if state.refinement_mode:
            action = (
                "The user refined their requirements. Update recommendations accordingly "
                "without restarting the conversation."
            )

        user_prompt = self._build_user_prompt(state, history, context, action)
        llm_payload = await self.llm.generate_json(SYSTEM_PROMPT, user_prompt)
        names = llm_payload.get("recommendation_names", [])
        recs = self._names_to_recommendations(names, results)
        if not recs:
            recs = self._fallback_recommendations(results)

        response = ChatResponse(
            reply=str(llm_payload.get("reply", "Here are SHL assessments that match your needs.")),
            recommendations=recs,
            end_of_conversation=bool(llm_payload.get("end_of_conversation", False)),
        )
        return self.registry.enforce_response(response)

    async def _handle_comparison(
        self, messages: list[ChatMessage], state: ConversationState
    ) -> ChatResponse:
        targets = state.comparison_targets or ["OPQ", "GSA"]
        query = " ".join(targets)
        results = self.retriever.retrieve(
            query,
            slots=state.slots,
            wants_personality=state.wants_personality or bool(state.slots.personality),
        )
        if len(results) < 2:
            user_text = " ".join(m.content for m in messages if m.role == "user")
            results = self.retriever.retrieve(
                user_text,
                slots=state.slots,
                wants_personality=state.wants_personality or bool(state.slots.personality),
            )

        named = self.retriever.find_by_names(targets)
        if named:
            results = [
                RetrievalResult(record=r, score=1.0, semantic_score=1.0, lexical_score=1.0, metadata_boost=0.0)
                for r in named
            ] + results

        deduped: list[RetrievalResult] = []
        seen: set[str] = set()
        for r in results:
            if r.record.slug() in seen:
                continue
            seen.add(r.record.slug())
            deduped.append(r)
            if len(deduped) >= 2:
                break

        if len(deduped) < 2:
            return ChatResponse(
                reply=(
                    "I could not locate both assessments in the SHL catalog for a grounded comparison. "
                    "Please provide exact assessment names from SHL."
                ),
                recommendations=[],
                end_of_conversation=False,
            )

        context = self.retriever.format_context(deduped[:2])
        history = self._format_history(messages)
        action = (
            "Compare the assessments using ONLY retrieved catalog fields "
            "(purpose, test type, duration, remote support). Do not recommend additional products."
        )
        user_prompt = self._build_user_prompt(state, history, context, action)
        llm_payload = await self.llm.generate_json(SYSTEM_PROMPT, user_prompt)
        return ChatResponse(
            reply=str(llm_payload.get("reply", "Here is a comparison based on the SHL catalog.")),
            recommendations=[],
            end_of_conversation=False,
        )

    def _build_query(self, messages: list[ChatMessage], state: ConversationState) -> str:
        user_text = " ".join(m.content for m in messages if m.role == "user")
        slot_query = state.slots.retrieval_query()
        parts = [user_text, slot_query]
        if state.wants_personality:
            parts.append("personality assessment OPQ motivation")
        if state.wants_leadership:
            parts.append("leadership management assessment")
        if state.wants_remote:
            parts.append("remote testing supported")
        return truncate(" ".join(p for p in parts if p), 2000)

    def _build_user_prompt(
        self,
        state: ConversationState,
        history: str,
        context: str,
        action: str,
    ) -> str:
        slots_summary = ", ".join(
            f"{k}={v}" for k, v in state.slots.model_dump().items() if v
        ) or "none"
        missing = ", ".join(s.value for s in state.slots.missing_slots()[:3]) or "none"
        conversation = CONVERSATION_PROMPT_TEMPLATE.format(
            turn_count=state.turn_count,
            max_turns=self.settings.max_conversation_turns,
            intent=state.intent.value,
            slots_summary=slots_summary,
            missing_slots=missing,
            refinement_mode=state.refinement_mode,
            comparison_targets=", ".join(state.comparison_targets),
            history=history,
            action_instruction=action,
        )
        retrieval = RETRIEVAL_CONTEXT_TEMPLATE.format(context_block=context)
        return f"{conversation}\n\n{retrieval}\n\n{FORMAT_INSTRUCTION}"

    def _format_history(self, messages: list[ChatMessage]) -> str:
        lines = []
        for msg in messages[-12:]:
            lines.append(f"{msg.role.upper()}: {msg.content}")
        return "\n".join(lines)

    def _names_to_recommendations(
        self, names: list[str], results: list[RetrievalResult]
    ) -> list[RecommendationItem]:
        items: list[RecommendationItem] = []
        for name in names:
            record = self.registry.get_by_name(name)
            if record:
                items.append(
                    RecommendationItem(
                        name=record.name,
                        url=record.url,
                        test_type=record.test_type,
                    )
                )
        if items:
            return items
        for result in results[:10]:
            r = result.record
            items.append(
                RecommendationItem(name=r.name, url=r.url, test_type=r.test_type)
            )
        return items[:10]

    def _fallback_recommendations(self, results: list[RetrievalResult]) -> list[RecommendationItem]:
        items: list[RecommendationItem] = []
        for result in results[:10]:
            r = result.record
            items.append(
                RecommendationItem(name=r.name, url=r.url, test_type=r.test_type)
            )
        return items
