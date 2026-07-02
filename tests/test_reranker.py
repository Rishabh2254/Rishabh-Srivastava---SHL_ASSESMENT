"""Reranker tests."""

from app.models.catalog import AssessmentRecord
from app.retrieval.reranker import rerank_results
from app.retrieval.types import RetrievalResult


def _result(name: str, score: float, text: str) -> RetrievalResult:
    record = AssessmentRecord(
        name=name,
        url=f"https://www.shl.com/solutions/products/product-catalog/view/{name.lower().replace(' ', '-')}/",
        description=text,
        test_type="Knowledge",
        skills=[word for word in ["java", "sql", "spring"] if word in text.lower()],
    )
    return RetrievalResult(
        record=record,
        score=score,
        semantic_score=score,
        lexical_score=0.0,
        metadata_boost=0.0,
    )


def test_penalizes_irrelevant_phone_banker_for_java_query():
    results = [
        _result("Java 8 (New)", 0.9, "Java programming assessment"),
        _result("Phone Banker - Short Form", 0.85, "Call center banking role solution"),
        _result("Automata - SQL (New)", 0.8, "SQL query writing assessment"),
        _result("Spring (New)", 0.78, "Spring framework assessment"),
    ]
    reranked = rerank_results(
        results,
        query="mid-level Java Developer with Spring and SQL experience",
        max_results=4,
    )
    names = [r.record.name for r in reranked]
    assert "Phone Banker - Short Form" not in names
    assert "Automata - SQL (New)" in names
    assert "Spring (New)" in names


def test_includes_sql_and_spring_when_mentioned():
    results = [
        _result("Core Java (Advanced Level) (New)", 0.95, "Java OOP assessment"),
        _result("Java Design Patterns (New)", 0.94, "Java design patterns"),
        _result("Automata - SQL (New)", 0.7, "SQL assessment"),
        _result("Spring (New)", 0.68, "Spring framework assessment"),
    ]
    reranked = rerank_results(
        results,
        query="Java Developer with Spring and SQL",
        max_results=4,
    )
    names = [r.record.name for r in reranked]
    assert "Automata - SQL (New)" in names
    assert "Spring (New)" in names
