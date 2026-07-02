"""Conversation state inferred from message history (stateless server)."""

from enum import Enum

from pydantic import BaseModel, Field


class Intent(str, Enum):
    CLARIFY = "clarify"
    RECOMMEND = "recommend"
    REFINE = "refine"
    COMPARE = "compare"
    REFUSE = "refuse"
    GREET = "greet"
    OFF_TOPIC = "off_topic"


class SlotName(str, Enum):
    ROLE = "role"
    SENIORITY = "seniority"
    TECHNICAL_DOMAIN = "technical_domain"
    HIRING_OBJECTIVE = "hiring_objective"
    LEADERSHIP = "leadership"
    PERSONALITY = "personality"
    LANGUAGE = "language"
    DOMAIN = "domain"
    SOFT_SKILLS = "soft_skills"
    CONSTRAINTS = "constraints"


SLOT_PRIORITY: list[SlotName] = [
    SlotName.ROLE,
    SlotName.SENIORITY,
    SlotName.TECHNICAL_DOMAIN,
    SlotName.HIRING_OBJECTIVE,
    SlotName.SOFT_SKILLS,
    SlotName.LEADERSHIP,
    SlotName.PERSONALITY,
    SlotName.LANGUAGE,
    SlotName.DOMAIN,
    SlotName.CONSTRAINTS,
]


class ConversationSlots(BaseModel):
    role: str | None = None
    seniority: str | None = None
    technical_domain: str | None = None
    hiring_objective: str | None = None
    leadership: str | None = None
    personality: str | None = None
    language: str | None = None
    domain: str | None = None
    soft_skills: str | None = None
    constraints: str | None = None

    def filled_count(self) -> int:
        return sum(1 for v in self.model_dump().values() if v)

    def missing_slots(self) -> list[SlotName]:
        data = self.model_dump()
        return [slot for slot in SLOT_PRIORITY if not data.get(slot.value)]

    def retrieval_query(self) -> str:
        parts = [v for v in self.model_dump().values() if v]
        return ". ".join(parts)

    def is_ready_for_recommendation(self) -> bool:
        has_role = bool(self.role or self.technical_domain)
        has_context = self.filled_count() >= 2
        return has_role and has_context


class ConversationState(BaseModel):
    turn_count: int = 0
    intent: Intent = Intent.CLARIFY
    slots: ConversationSlots = Field(default_factory=ConversationSlots)
    comparison_targets: list[str] = Field(default_factory=list)
    wants_personality: bool = False
    wants_leadership: bool = False
    wants_remote: bool = False
    refinement_mode: bool = False
    injection_detected: bool = False
    off_topic: bool = False
