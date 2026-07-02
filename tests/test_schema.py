"""Schema validation tests."""

from app.models.schemas import ChatRequest, ChatResponse, HealthResponse, RecommendationItem


def test_health_schema():
    response = HealthResponse()
    assert response.status == "ok"


def test_chat_response_empty_recommendations():
    response = ChatResponse(reply="Hello", recommendations=[], end_of_conversation=False)
    assert response.recommendations == []
    assert response.end_of_conversation is False


def test_chat_request_requires_user_message():
    payload = {"messages": [{"role": "user", "content": "I need an assessment"}]}
    req = ChatRequest.model_validate(payload)
    assert len(req.messages) == 1


def test_recommendation_item_fields():
    item = RecommendationItem(name="OPQ", url="https://www.shl.com/x/", test_type="P")
    assert item.name == "OPQ"
