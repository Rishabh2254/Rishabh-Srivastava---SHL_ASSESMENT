"""Infer conversation state from message history without server-side memory."""

import re

from app.models.conversation import (
    ConversationSlots,
    ConversationState,
    Intent,
    SlotName,
)
from app.models.schemas import ChatMessage
from app.utils.text import normalize_text

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) instructions",
    r"reveal (your )?system prompt",
    r"show (me )?your (system )?prompt",
    r"you are now",
    r"act as (a )?jailbreak",
    r"browse (the )?internet",
    r"recommend (non-shl|competitor)",
]

OFF_TOPIC_PATTERNS = [
    r"salary negotiation",
    r"legal advice",
    r"interview coaching",
    r"hr policy",
    r"should i hire",
    r"how to negotiate",
    r"employment law",
]

COMPARE_PATTERNS = [
    r"difference between (.+?) and (.+)",
    r"compare (.+?) (?:vs|versus|and) (.+)",
    r"what is the difference",
    r"how (?:does|do) (.+?) differ",
]

REFINEMENT_PATTERNS = [
    r"actually",
    r"instead",
    r"also include",
    r"add personality",
    r"remove ",
    r"change to",
    r"update recommendation",
    r"refine",
]

SLOT_EXTRACTORS: dict[SlotName, list[str]] = {
    SlotName.ROLE: [
        r"(?:hiring|recruit(?:ing)?|looking for|need)(?: a| an)? ([a-z0-9 /\-]+?(?:developer|engineer|manager|analyst|consultant|designer|administrator|specialist|lead|architect))",
        r"i am hiring (?:a|an) ([^.?\n]+)",
        r"role(?: is)?[:\s]+([^.?\n]+)",
    ],
    SlotName.SENIORITY: [
        r"\b(junior|mid[- ]?level|senior|lead|principal|entry[- ]?level|graduate)\b",
    ],
    SlotName.TECHNICAL_DOMAIN: [
        r"\b(java|python|javascript|react|sql|\.net|c\+\+|aws|devops|data science|machine learning)\b",
    ],
    SlotName.PERSONALITY: [
        r"\b(personality|opq|motivation|behavioral fit|culture fit)\b",
    ],
    SlotName.LEADERSHIP: [
        r"\b(leadership|people management|executive|managerial)\b",
    ],
    SlotName.LANGUAGE: [
        r"\b(english|french|german|spanish|multilingual|language proficiency)\b",
    ],
    SlotName.DOMAIN: [
        r"\b(banking|finance|healthcare|retail|manufacturing|insurance|telecom)\b",
    ],
    SlotName.HIRING_OBJECTIVE: [
        r"\b(screening|selection|development|high[- ]volume|volume hiring|graduate program)\b",
    ],
    SlotName.CONSTRAINTS: [
        r"\b(remote|adaptive|short|under \d+ minutes|\d+ minutes)\b",
    ],
}


class StateManager:
    def __init__(self, max_turns: int = 8) -> None:
        self.max_turns = max_turns

    def infer(self, messages: list[ChatMessage]) -> ConversationState:
        user_messages = [m.content for m in messages if m.role == "user"]
        turn_count = len(user_messages)
        combined = normalize_text(" ".join(user_messages))
        latest = normalize_text(user_messages[-1]) if user_messages else ""

        state = ConversationState(turn_count=turn_count)
        state.slots = self._extract_slots(combined)

        if self._matches_any(latest, INJECTION_PATTERNS):
            state.injection_detected = True
            state.intent = Intent.REFUSE
            return state

        if self._matches_any(latest, OFF_TOPIC_PATTERNS):
            state.off_topic = True
            state.intent = Intent.REFUSE
            return state

        if self._matches_any(latest, COMPARE_PATTERNS):
            state.intent = Intent.COMPARE
            state.comparison_targets = self._extract_comparison_targets(latest)
            return state

        if turn_count > 1 and self._matches_any(latest, REFINEMENT_PATTERNS):
            state.refinement_mode = True
            state.intent = Intent.REFINE
            return state

        if "personality" in latest:
            state.wants_personality = True
            state.slots.personality = state.slots.personality or "personality assessment requested"

        if "leadership" in latest:
            state.wants_leadership = True
            state.slots.leadership = state.slots.leadership or "leadership assessment requested"

        if "remote" in latest:
            state.wants_remote = True
            state.slots.constraints = state.slots.constraints or "remote testing required"

        vague = latest in {"i need an assessment", "need an assessment", "help me choose an assessment"}
        if vague or (turn_count == 1 and state.slots.filled_count() == 0):
            state.intent = Intent.CLARIFY
            return state

        if state.slots.is_ready_for_recommendation() or turn_count >= 3:
            state.intent = Intent.RECOMMEND
            return state

        state.intent = Intent.CLARIFY
        return state

    def next_clarification_question(self, state: ConversationState) -> str:
        missing = state.slots.missing_slots()
        if not missing:
            return (
                "Could you share the most important skills or competencies "
                "you want the assessment to measure?"
            )
        slot = missing[0]
        prompts = {
            SlotName.ROLE: "What role are you hiring for (e.g., Java Developer, Sales Manager)?",
            SlotName.SENIORITY: "What seniority level is this role (junior, mid-level, senior)?",
            SlotName.TECHNICAL_DOMAIN: "Which technical skills or technologies should the assessment cover?",
            SlotName.HIRING_OBJECTIVE: "What is your hiring objective (screening, selection, development)?",
            SlotName.SOFT_SKILLS: "Are there soft skills or behaviors you need to evaluate?",
            SlotName.LEADERSHIP: "Do you need to assess leadership or people management capabilities?",
            SlotName.PERSONALITY: "Should personality or motivation traits be included?",
            SlotName.LANGUAGE: "Do you need language proficiency assessment? If so, which language?",
            SlotName.DOMAIN: "Which industry or business domain is this role in?",
            SlotName.CONSTRAINTS: "Any constraints such as remote delivery, duration, or adaptive testing?",
        }
        return prompts.get(slot, "Could you provide a bit more detail about your hiring needs?")

    def _extract_slots(self, text: str) -> ConversationSlots:
        slots = ConversationSlots()
        data = slots.model_dump()
        for slot, patterns in SLOT_EXTRACTORS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    value = match.group(1).strip() if match.lastindex else match.group(0).strip()
                    data[slot.value] = value
                    break
        return ConversationSlots(**data)

    def _extract_comparison_targets(self, text: str) -> list[str]:
        for pattern in COMPARE_PATTERNS[:2]:
            match = re.search(pattern, text, re.I)
            if match and match.lastindex and match.lastindex >= 2:
                return [match.group(1).strip(), match.group(2).strip()]
        tokens = re.findall(r"\b(opq|gsa|verify|mq|sjt|java|python)\b", text, re.I)
        return tokens[:2]

    @staticmethod
    def _matches_any(text: str, patterns: list[str]) -> bool:
        return any(re.search(p, text, re.I) for p in patterns)
