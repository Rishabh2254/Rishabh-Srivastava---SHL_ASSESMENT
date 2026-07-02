"""Shared retrieval types."""

from dataclasses import dataclass

from app.models.catalog import AssessmentRecord


@dataclass
class RetrievalResult:
    record: AssessmentRecord
    score: float
    semantic_score: float
    lexical_score: float
    metadata_boost: float
