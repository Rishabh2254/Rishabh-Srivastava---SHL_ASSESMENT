"""Post-retrieval reranking for relevance, diversity, and noise reduction."""

from __future__ import annotations

import re

from app.models.catalog import AssessmentRecord
from app.retrieval.types import RetrievalResult
from app.utils.text import normalize_text, tokenize

SKILL_TERMS = {
    "java",
    "spring",
    "sql",
    "python",
    "javascript",
    "react",
    "angular",
    "dotnet",
    "c#",
    "aws",
    "devops",
    "oracle",
    "mysql",
    "hibernate",
    "leadership",
    "personality",
    "opq",
    "cognitive",
    "verify",
}

ROLE_MISMATCH_TERMS = {
    "java": {"banker", "call center", "receptionist", "clerical", "cashier", "teller", "industrial", "informatica", "smart interview"},
    "developer": {"banker", "call center", "receptionist", "clerical", "industrial", "hiring concepts", "smart interview", "informatica"},
    "sql": {"banker", "call center", "sales representative"},
    "spring": {"banker", "call center", "receptionist", "informatica"},
}

REPORT_PATTERN = re.compile(r"\breport\b", re.I)
JOB_SOLUTION_PATTERN = re.compile(r"\b(short form|solution)\b", re.I)


def extract_query_skills(query: str) -> set[str]:
    normalized = normalize_text(query)
    tokens = set(tokenize(normalized))
    skills = {t for t in tokens if t in SKILL_TERMS}
    if "spring" in normalized:
        skills.add("spring")
    if "sql" in normalized:
        skills.add("sql")
    if "java" in normalized:
        skills.add("java")
    if "developer" in normalized or "engineer" in normalized:
        skills.add("developer")
    return skills


def _is_report_product(record: AssessmentRecord) -> bool:
    return bool(REPORT_PATTERN.search(record.name))


def _is_job_solution_package(record: AssessmentRecord) -> bool:
    name = record.name.lower()
    if "job focused assessment" in name:
        return False
    if any(term in name for term in ["general entry level", "all industries", "graduate", "technology professional", "contact center"]):
        return True
    return bool(JOB_SOLUTION_PATTERN.search(record.name))


def _role_mismatch_penalty(record: AssessmentRecord, query_skills: set[str], query: str) -> float:
    blob = record.embedding_text().lower()
    penalty = 0.0
    for skill, bad_terms in ROLE_MISMATCH_TERMS.items():
        if skill in query_skills or skill in query:
            if any(term in blob for term in bad_terms):
                penalty += 0.9
    return penalty


def _skill_overlap_boost(record: AssessmentRecord, query_skills: set[str]) -> float:
    if not query_skills:
        return 0.0
    blob = record.embedding_text().lower()
    matches = sum(1 for skill in query_skills if skill in blob)
    return min(matches * 0.12, 0.48)


def rerank_results(
    results: list[RetrievalResult],
    query: str,
    wants_personality: bool = False,
    max_results: int = 10,
) -> list[RetrievalResult]:
    if not results:
        return []

    query_skills = extract_query_skills(query)
    adjusted: list[RetrievalResult] = []

    for result in results:
        record = result.record
        penalty = 0.0

        if _is_report_product(record) and not wants_personality:
            penalty += 0.55

        if _is_job_solution_package(record) and query_skills:
            penalty += 0.35

        penalty += _role_mismatch_penalty(record, query_skills, normalize_text(query))
        boost = _skill_overlap_boost(record, query_skills)
        new_score = result.score + boost - penalty

        adjusted.append(
            RetrievalResult(
                record=record,
                score=new_score,
                semantic_score=result.semantic_score,
                lexical_score=result.lexical_score,
                metadata_boost=result.metadata_boost + boost,
            )
        )

    adjusted.sort(key=lambda r: r.score, reverse=True)
    positive = [r for r in adjusted if r.score > 0]
    if not positive:
        positive = adjusted

    return _diversify(positive, query_skills, max_results)


def _record_covers_skill(record: AssessmentRecord, skill: str) -> bool:
    name = record.name.lower()
    skill = skill.lower()
    skill_fields = [s.lower() for s in record.skills]

    if skill in skill_fields:
        return True
    if skill in name:
        return True
    if skill == "sql" and "sql" in name:
        return True
    if skill == "spring" and "spring" in name:
        return True
    if skill == "java" and "java" in name:
        return True
    return False


def _diversify(
    results: list[RetrievalResult],
    query_skills: set[str],
    max_results: int,
) -> list[RetrievalResult]:
    if not query_skills:
        return results[:max_results]

    selected: list[RetrievalResult] = []
    seen_slugs: set[str] = set()
    covered_skills: set[str] = set()

    def add(result: RetrievalResult, forced: bool = False) -> None:
        slug = result.record.slug()
        if slug in seen_slugs:
            return
        seen_slugs.add(slug)
        score = max(result.score, 0.3) if forced else result.score
        selected.append(
            RetrievalResult(
                record=result.record,
                score=score,
                semantic_score=result.semantic_score,
                lexical_score=result.lexical_score,
                metadata_boost=result.metadata_boost,
            )
        )
        for skill in query_skills:
            if _record_covers_skill(result.record, skill):
                covered_skills.add(skill)

    for skill in sorted(query_skills):
        for result in results:
            if _record_covers_skill(result.record, skill):
                add(result, forced=True)
                break
        if len(selected) >= max_results:
            return selected[:max_results]

    java_count = 0
    for result in results:
        if len(selected) >= max_results:
            break
        slug = result.record.slug()
        if slug in seen_slugs:
            continue
        blob = result.record.embedding_text().lower()
        if "java" in query_skills and "java" in blob:
            if java_count >= 5:
                continue
            java_count += 1
        add(result)

    return selected[:max_results]
