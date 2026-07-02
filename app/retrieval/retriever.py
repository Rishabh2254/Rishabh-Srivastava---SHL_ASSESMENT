"""Hybrid retriever with semantic search, BM25, and metadata-aware reranking."""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.catalog import AssessmentRecord
from app.models.conversation import ConversationSlots
from app.retrieval.embedder import Embedder
from app.retrieval.reranker import rerank_results
from app.retrieval.types import RetrievalResult
from app.utils.text import tokenize

logger = get_logger(__name__)


class AssessmentRetriever:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedder = Embedder(settings.embedding_model)
        self.index: faiss.Index | None = None
        self.records: list[AssessmentRecord] = []
        self.corpus_tokens: list[list[str]] = []
        self.bm25: BM25Okapi | None = None
        self._load()

    def _load(self) -> None:
        meta_path = self.settings.vectorstore_meta_path
        index_path = self.settings.vectorstore_path
        if not meta_path.exists() or not index_path.exists():
            logger.warning("Vector store not found; retriever will return empty results")
            return
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        self.records = [AssessmentRecord.model_validate(item) for item in metadata]
        self.corpus_tokens = [tokenize(r.embedding_text()) for r in self.records]
        self.bm25 = BM25Okapi(self.corpus_tokens)
        self.index = faiss.read_index(str(index_path))
        logger.info("Loaded retriever with %s catalog records", len(self.records))

    @property
    def is_ready(self) -> bool:
        return self.index is not None and bool(self.records)

    def retrieve(
        self,
        query: str,
        slots: ConversationSlots | None = None,
        top_k: int | None = None,
        wants_personality: bool = False,
    ) -> list[RetrievalResult]:
        if not self.is_ready or not query.strip():
            return []
        top_k = top_k or self.settings.retrieval_top_k
        query_vec = self.embedder.encode_one(query).reshape(1, -1)
        scores, indices = self.index.search(query_vec, min(top_k * 2, len(self.records)))
        semantic_hits: dict[int, float] = {}
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            semantic_hits[int(idx)] = float(score)

        lexical_scores = self._bm25_scores(query)
        combined: list[RetrievalResult] = []
        candidate_ids = set(semantic_hits) | set(
            i for i, s in enumerate(lexical_scores) if s > 0
        )
        candidate_ids |= self._skill_candidate_ids(query)
        for idx in candidate_ids:
            record = self.records[idx]
            sem = semantic_hits.get(idx, 0.0)
            lex = lexical_scores[idx]
            meta = self._metadata_boost(record, slots)
            final = 0.55 * sem + 0.25 * lex + 0.20 * meta
            combined.append(
                RetrievalResult(
                    record=record,
                    score=final,
                    semantic_score=sem,
                    lexical_score=lex,
                    metadata_boost=meta,
                )
            )
        combined.sort(key=lambda r: r.score, reverse=True)
        skill_ids = self._skill_candidate_ids(query)
        pool = combined[: max(top_k * 3, 30)]
        pool_ids = {id(r.record) for r in pool}
        for idx in skill_ids:
            record = self.records[idx]
            if id(record) in pool_ids:
                continue
            sem = semantic_hits.get(idx, 0.0)
            lex = lexical_scores[idx]
            meta = self._metadata_boost(record, slots)
            final = 0.55 * sem + 0.25 * lex + 0.20 * meta
            pool.append(
                RetrievalResult(
                    record=record,
                    score=final,
                    semantic_score=sem,
                    lexical_score=lex,
                    metadata_boost=meta,
                )
            )
        reranked = rerank_results(
            pool,
            query=query,
            wants_personality=wants_personality,
            max_results=self.settings.rerank_top_k,
        )
        return [
            r for r in reranked if r.score >= self.settings.min_retrieval_score
        ][: self.settings.rerank_top_k]

    def _skill_candidate_ids(self, query: str) -> set[int]:
        from app.retrieval.reranker import extract_query_skills

        skills = extract_query_skills(query)
        if not skills:
            return set()
        matches: set[int] = set()
        for idx, record in enumerate(self.records):
            blob = record.embedding_text().lower()
            if any(skill in blob for skill in skills):
                matches.add(idx)
        return matches

    def _bm25_scores(self, query: str) -> list[float]:
        if not self.bm25:
            return [0.0] * len(self.records)
        tokens = tokenize(query)
        if not tokens:
            return [0.0] * len(self.records)
        raw = self.bm25.get_scores(tokens)
        max_score = float(max(raw)) if len(raw) else 1.0
        if max_score <= 0:
            return [0.0] * len(raw)
        return [float(s / max_score) for s in raw]

    def _metadata_boost(self, record: AssessmentRecord, slots: ConversationSlots | None) -> float:
        if slots is None:
            return 0.0
        blob = record.embedding_text().lower()
        boost = 0.0
        checks = {
            slots.role: 0.15,
            slots.technical_domain: 0.2,
            slots.seniority: 0.1,
            slots.personality: 0.15,
            slots.leadership: 0.15,
            slots.language: 0.1,
            slots.domain: 0.1,
        }
        for value, weight in checks.items():
            if not value:
                continue
            if value.lower() in blob:
                boost += weight
        if slots.constraints and "remote" in slots.constraints.lower() and record.remote_support.lower() == "yes":
            boost += 0.1
        return min(boost, 1.0)

    def find_by_names(self, names: list[str]) -> list[AssessmentRecord]:
        lowered = {n.lower(): n for n in names}
        found: list[AssessmentRecord] = []
        for record in self.records:
            if record.name.lower() in lowered:
                found.append(record)
        return found

    def format_context(self, results: list[RetrievalResult]) -> str:
        if not results:
            return "No catalog entries retrieved."
        blocks: list[str] = []
        for i, result in enumerate(results, start=1):
            r = result.record
            blocks.append(
                f"{i}. Name: {r.name}\n"
                f"   URL: {r.url}\n"
                f"   Test Type: {r.test_type}\n"
                f"   Category: {r.category}\n"
                f"   Duration: {r.duration}\n"
                f"   Remote: {r.remote_support} | Adaptive: {r.adaptive_support}\n"
                f"   Description: {r.description[:500]}\n"
                f"   Skills: {', '.join(r.skills)}\n"
                f"   Score: {result.score:.3f}"
            )
        return "\n\n".join(blocks)
