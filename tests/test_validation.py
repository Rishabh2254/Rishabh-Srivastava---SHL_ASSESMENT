"""Catalog validation and hallucination prevention tests."""

from app.models.catalog import AssessmentRecord
from app.models.schemas import ChatResponse, RecommendationItem
from app.utils.validation import CatalogRegistry


def _sample_registry() -> CatalogRegistry:
    records = [
        AssessmentRecord(
            name="Java 8 Programming",
            url="https://www.shl.com/solutions/products/product-catalog/view/java-8-programming/",
            test_type="Knowledge & Skills",
            description="Java programming assessment",
        ),
        AssessmentRecord(
            name="OPQ32",
            url="https://www.shl.com/solutions/products/product-catalog/view/opq32/",
            test_type="Personality & Behavior",
            description="Occupational personality questionnaire",
        ),
    ]
    return CatalogRegistry(records)


def test_rejects_hallucinated_url():
    registry = _sample_registry()
    response = ChatResponse(
        reply="Try this fake test",
        recommendations=[
            RecommendationItem(
                name="Fake Assessment",
                url="https://www.shl.com/solutions/products/product-catalog/view/fake/",
                test_type="K",
            )
        ],
    )
    enforced = registry.enforce_response(response)
    assert enforced.recommendations == []


def test_accepts_valid_catalog_entry():
    registry = _sample_registry()
    response = ChatResponse(
        reply="Use OPQ",
        recommendations=[
            RecommendationItem(
                name="OPQ32",
                url="https://www.shl.com/solutions/products/product-catalog/view/opq32/",
                test_type="P",
            )
        ],
    )
    enforced = registry.enforce_response(response)
    assert len(enforced.recommendations) == 1
    assert enforced.recommendations[0].name == "OPQ32"
